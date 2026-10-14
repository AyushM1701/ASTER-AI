import io
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.adapters.ollama import OllamaAdapter
from backend.app.config import Settings
from backend.app.errors import AppError
from backend.app.main import create_app
from backend.app.schemas import GeneratedAnswer
from backend.app.services.answers import validate_generated
from backend.app.services.documents import parse_fields
from backend.app.services.policy import check_policy
from backend.app.services.retrieval import ReferenceStore
from backend.app.services.sessions import SessionStore
from backend.app.services.uploads import decode_image
from backend.app.services.xray import validate_asset


def test_session_expiration_and_hard_lifetime():
    now = [0.0]
    store = SessionStore(
        Settings(session_ttl_seconds=10, session_hard_ttl_seconds=15), lambda: now[0]
    )
    token = store.create()
    session = store.get(token)
    assert token not in store.sessions
    session.documents["temporary"] = object()
    now[0] = 9
    store.get(token)
    now[0] = 16
    with pytest.raises(AppError) as error:
        store.get(token)
    assert error.value.code == 401
    assert session.documents == {}


def test_session_capacity():
    store = SessionStore(Settings(max_active_sessions=1))
    store.create()
    with pytest.raises(AppError) as error:
        store.create()
    assert error.value.code == 429


def test_config_disallows_remote_model_servers():
    for url in [
        "https://api.example.com",
        "http://192.168.1.2:11434",
        "http://user:secret@localhost",
    ]:
        with pytest.raises(ValueError):
            Settings(ollama_base_url=url)


def test_parser_preserves_missing_fields_and_decimal():
    fields = parse_fields("Medicine: ExampleMedicine\nStrength: 0.5 mg")
    values = {f["kind"]: f["candidate_value"] for f in fields}
    assert values["strength"] == "0.5 mg"
    assert values["frequency"] is None and values["duration"] is None


def test_citation_forgery_is_rejected():
    refs = ReferenceStore(Settings()).search("asthma")
    answer = GeneratedAnswer(claims=[{"text": "Unsupported claim", "citation_ids": ["invented"]}])
    with pytest.raises(AppError) as error:
        validate_generated(answer, refs)
    assert error.value.code == 502


@pytest.mark.parametrize(
    "text",
    [
        "What is severe chest pain?",
        "I do not have severe chest pain",
        "Years ago I had severe chest pain",
    ],
)
def test_general_or_negated_symptom_mentions_are_not_live_triage(text):
    assert check_policy(text) is None


@pytest.mark.parametrize(
    "text",
    [
        "How many mg should I take?",
        "Tell me how much metformin to take",
        "I have crushing chest pian right now",
    ],
)
def test_unsafe_variants_are_not_treated_as_education(text):
    assert check_policy(text) is not None


def test_animated_and_high_pixel_images_are_rejected():
    image = Image.new("RGB", (100, 100), "white")
    buf = io.BytesIO()
    image.save(
        buf, format="PNG", save_all=True, append_images=[Image.new("RGB", (100, 100), "black")]
    )
    with pytest.raises(AppError):
        decode_image(buf.getvalue(), Settings())
    buf = io.BytesIO()
    Image.new("RGB", (1000, 1000)).save(buf, format="PNG")
    with pytest.raises(AppError) as error:
        decode_image(buf.getvalue(), Settings(max_image_pixels=1000))
    assert error.value.code == 413


def test_image_byte_limit():
    with pytest.raises(AppError) as error:
        decode_image(b"x" * 1025, Settings(max_upload_bytes=1024))
    assert error.value.code == 413


def test_xray_metadata_rejects_lateral():
    asset = dict(
        asset_id="test",
        path="unused",
        sha256="unused",
        source="test",
        license="test",
        view="LATERAL",
        adult=True,
        supported_input_review=True,
        deidentified=True,
        partition="test",
        patient_group="synthetic",
    )
    with pytest.raises(AppError) as error:
        validate_asset(asset, Settings())
    assert error.value.status == "unsupported_input"


def test_malformed_model_output_fails_closed():
    adapter = OllamaAdapter(Settings())
    adapter.client.close()
    adapter.client = httpx.Client(
        base_url="http://127.0.0.1:11434",
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"message": {"content": "not JSON"}})
        ),
    )
    with pytest.raises(AppError) as error:
        adapter.generate("What is asthma?", ReferenceStore(Settings()).search("asthma"))
    adapter.close()
    assert error.value.code == 502


def test_timeout_fails_closed():
    def handler(request):
        raise httpx.ReadTimeout("test", request=request)

    adapter = OllamaAdapter(Settings())
    adapter.client.close()
    adapter.client = httpx.Client(
        base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(AppError) as error:
        adapter.generate("asthma", [])
    adapter.close()
    assert error.value.code == 503


def test_expiry_during_ocr_does_not_resurrect_state():
    with TestClient(create_app()) as client:
        token = client.post("/v1/sessions").json()["token"]
        headers = {"Authorization": "Bearer " + token}
        buf = io.BytesIO()
        Image.new("RGB", (600, 600)).save(buf, format="PNG")
        doc = client.post(
            "/v1/documents", headers=headers, files={"file": ("s.png", buf.getvalue(), "image/png")}
        ).json()["document_id"]
        state = client.app.state

        def delete_during_extract(image):
            state.sessions.delete(state.sessions.get(token))
            return {"raw_text": "Medicine: Test", "words": []}

        state.ocr.extract = delete_during_extract
        response = client.post(f"/v1/documents/{doc}/extract", headers=headers)
        assert response.status_code == 401
        assert not state.sessions.sessions


def test_real_synthetic_ocr_roundtrip():
    from backend.app.adapters.ocr import OCRAdapter
    from scripts.create_fixtures import sample_bytes

    adapter = OCRAdapter(Settings())
    if not adapter.ready():
        pytest.skip("Tesseract not installed")
    image, _ = decode_image(sample_bytes(), Settings())
    text = adapter.extract(image)["raw_text"]
    values = {f["kind"]: f["candidate_value"] for f in parse_fields(text)}
    assert values["medicine_name"] == "Metformin hydrochloride"
    assert values["strength"] == "500 mg"
    assert values["duration"] is None


def test_reference_tampering_fails_closed(tmp_path):
    settings = Settings()
    rows = [json.loads(line) for line in settings.corpus_path.read_text().splitlines()]
    rows[0]["text"] = "Fabricated data injected into a previously approved source note."
    path = tmp_path / "tampered.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    assert not ReferenceStore(Settings(corpus_path=path)).records


@pytest.mark.parametrize(
    "text",
    [
        "I don't have asthma but I cannot breathe",
        "I do not have asthma but I can't breathe",
        "I am not suicidal but my father is not breathing",
    ],
)
def test_unrelated_negation_cannot_suppress_an_emergency(text):
    assert check_policy(text)["status"] == "urgent_guidance"


@pytest.mark.parametrize(
    "text",
    [
        "Years ago I was diagnosed with asthma, and now I cannot breathe",
        "I had asthma in the past and I cannot breathe",
    ],
)
def test_unrelated_history_cannot_suppress_current_breathing_distress(text):
    decision = check_policy(text)
    assert decision is not None and decision["status"] == "urgent_guidance"


def test_applicability_metadata_tampering_fails_closed(tmp_path):
    settings = Settings()
    rows = [json.loads(line) for line in settings.corpus_path.read_text().splitlines()]
    rows[-1]["formulations"].append("extended-release tablet")
    path = tmp_path / "changed-metadata.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows))
    assert not ReferenceStore(Settings(corpus_path=path)).records


def test_generic_document_confirmation_preserves_long_text():
    from backend.app.schemas import Confirmation

    verified_text = "Asthma reference document. " * 100
    payload = Confirmation(
        expected_revision=1,
        confirmation_acknowledged=True,
        fields=[
            {"field_id": "document_text", "value": verified_text, "status": "confirmed_by_user"}
        ],
    )
    assert payload.fields[0].value == verified_text.strip()


def test_full_session_rejected_before_image_expansion(monkeypatch):
    from backend.app.api import documents
    from tests.test_workflows import image_bytes, session, upload

    with TestClient(create_app(Settings(max_documents_per_session=1))) as client:
        headers = session(client)
        upload(client, headers)
        calls = []
        original = documents.decode_image

        def recorded(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)

        monkeypatch.setattr(documents, "decode_image", recorded)
        response = client.post(
            "/v1/documents",
            headers=headers,
            files={"file": ("another.png", image_bytes(), "image/png")},
        )
        assert response.status_code == 429
        assert calls == []


def test_image_expansion_obeys_compute_gate():
    from tests.test_workflows import image_bytes, session

    with TestClient(create_app(Settings(max_queue_size=0))) as client:
        headers = session(client)
        with client.app.state.compute.enter():
            response = client.post(
                "/v1/documents",
                headers=headers,
                files={"file": ("another.png", image_bytes(), "image/png")},
            )
        assert response.status_code == 429
