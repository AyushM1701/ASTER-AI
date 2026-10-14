import asyncio
from contextlib import contextmanager

import httpx
from fastapi.testclient import TestClient

from frontend.webserver import MAX_BODY, app


@contextmanager
def web_client(handler):
    with TestClient(app, base_url="http://127.0.0.1:8501") as client:
        upstream = app.state.client
        # The upstream boundary is mocked; real routing, headers and body gates
        # run through the frontend ASGI application.
        fake = httpx.AsyncClient(
            base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(handler)
        )
        app.state.client = fake
        try:
            yield client
        finally:
            app.state.client = upstream
            asyncio.run(fake.aclose())


def test_page_hosts_fonts_icons_and_only_local_resources():
    with TestClient(app, base_url="http://127.0.0.1:8501") as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Understand more." in response.text
        assert "script-src 'self'" in response.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        for path in ("fonts/manrope.woff2", "fonts/dm-sans.woff2", "icons/link.svg", "app.js"):
            assert len(client.get("/assets/" + path).content) > 100
        assert client.get("/_stcore/health").text == "ok"


def test_cross_origin_and_missing_client_header_never_reach_api():
    requests = []
    with web_client(lambda request: requests.append(request)) as client:
        assert client.post("/api/v1/sessions").status_code == 403
        assert (
            client.post(
                "/api/v1/sessions",
                headers={"X-Aster-Client": "1", "Origin": "https://evil.example"},
            ).status_code
            == 403
        )
        assert (
            client.options(
                "/api/v1/sessions", headers={"Origin": "https://evil.example"}
            ).status_code
            == 405
        )
    assert not requests


def test_proxy_preserves_owned_revision_and_upstream_status():
    received = []

    def handler(request):
        received.append(request)
        return httpx.Response(
            409, json={"status": "needs_confirmation", "message": "Reload revision"}
        )

    with web_client(handler) as client:
        response = client.put(
            "/api/v1/documents/doc_123/confirm",
            headers={"X-Aster-Client": "1", "Authorization": "Bearer owned-token"},
            json={"expected_revision": 1},
        )
    assert response.status_code == 409
    assert response.json()["status"] == "needs_confirmation"
    assert received[0].url == "http://127.0.0.1:8000/v1/documents/doc_123/confirm"
    assert received[0].headers["authorization"] == "Bearer owned-token"
    assert received[0].content == b'{"expected_revision":1}'


def test_image_multipart_reaches_classifier_without_reencoding():
    received = []

    def handler(request):
        received.append(request)
        return httpx.Response(201, json={"status": "ok", "classification": {"kind": "xray"}})

    with web_client(handler) as client:
        response = client.post(
            "/api/v1/attachments",
            headers={"X-Aster-Client": "1"},
            files={"file": ("attachment.png", b"original-image-bytes", "image/png")},
        )
    assert response.status_code == 201
    assert b"original-image-bytes" in received[0].content
    assert "multipart/form-data; boundary=" in received[0].headers["content-type"]


def test_unknown_routes_and_oversized_bodies_do_not_reach_api():
    received = []
    with web_client(lambda request: received.append(request)) as client:
        assert client.post("/api/admin/reset", headers={"X-Aster-Client": "1"}).status_code == 404
        assert (
            client.post(
                "/api/v1/attachments",
                headers={"X-Aster-Client": "1", "Content-Length": str(MAX_BODY + 1)},
            ).status_code
            == 413
        )
        assert (
            client.post(
                "/api/v1/chat", headers={"X-Aster-Client": "1", "Content-Length": "invalid"}
            ).status_code
            == 400
        )
    assert not received


def test_transport_outage_has_recovery_message():
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    with web_client(handler) as client:
        result = client.get("/api/health/ready", headers={"X-Aster-Client": "1"})
    assert result.status_code == 503
    assert "Refresh connections" in result.json()["message"]


def test_private_pdf_proxy_preserves_raw_body_permission_and_owned_revision():
    received = []

    def handler(request):
        received.append(request)
        return httpx.Response(200, json={"status": "ok"})

    headers = {"X-Aster-Client": "1", "Authorization": "Bearer synthetic-owned-token", "Content-Type": "application/pdf"}
    raw = b"%PDF-1.4 synthetic private body"
    with web_client(handler) as client:
        assert client.post("/api/v1/papers?private_analysis_authorized=true", headers=headers, content=raw).status_code == 200
        for suffix in ("confirm", "reopen"):
            assert client.post("/api/v1/papers/paper_fixture/" + suffix, headers=headers, json={"expected_revision": 2}).status_code == 200
        assert client.delete("/api/v1/papers/paper_fixture", headers=headers).status_code == 200
        assert client.post("/api/v1/papers", headers={**headers, "Origin": "https://evil.example"}, content=raw).status_code == 403
    assert len(received) == 4
    assert received[0].content == raw and received[0].headers["content-type"] == "application/pdf"
    assert str(received[0].url).endswith("/v1/papers?private_analysis_authorized=true")
    assert received[0].headers["authorization"] == "Bearer synthetic-owned-token"


def test_untrusted_host_is_rejected():
    with TestClient(app, base_url="http://127.0.0.1:8501") as client:
        assert client.get("/", headers={"Host": "attacker.example"}).status_code == 400
