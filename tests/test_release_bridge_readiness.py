import io
import urllib.error
import urllib.request

import httpx
import pytest
from fastapi.testclient import TestClient

from aster_release.launcher import get_json, workspace_ready
from frontend import webserver


def test_controller_readiness_obeys_the_actual_web_bridge_header_gate(monkeypatch):
    class Upstream:
        async def request(self, *args, **kwargs):
            return httpx.Response(200, json={"status": "ready"})

    with TestClient(webserver.app, base_url="http://127.0.0.1:8501") as client:
        webserver.app.state.client = Upstream()

        class BridgeOpener:
            def open(self, request, timeout):
                response = client.get(request.full_url, headers=dict(request.header_items()))
                if response.status_code >= 400:
                    raise urllib.error.HTTPError(request.full_url, response.status_code,
                                                 "bridge refused", {}, io.BytesIO(response.content))
                return io.BytesIO(response.content)

        monkeypatch.setattr(urllib.request, "build_opener", lambda *args: BridgeOpener())
        with pytest.raises(urllib.error.HTTPError) as denied:
            get_json("http://127.0.0.1:8501/api/health/ready")
        assert denied.value.code == 403
        assert workspace_ready()
