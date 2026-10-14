import io
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.config import Settings
from backend.app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def mock_model(client, content):
    adapter = client.app.state.ollama
    adapter.client.close()
    adapter.client = httpx.Client(
        base_url="http://127.0.0.1:11434",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"message": {"content": json.dumps(content)}})
        ),
    )


def headers(client):
    return {"Authorization": "Bearer " + client.post("/v1/sessions").json()["token"]}


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (512, 512), "gray").save(output, "PNG")
    return output.getvalue()


def attach(client, auth, data=None):
    return client.post(
        "/v1/attachments",
        headers=auth,
        files={"file": ("misleading-xray.png", data or image_bytes(), "image/png")},
    )


def test_attachment_is_classified_then_extracted_without_filename_routing():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        mock_model(client, {"kind": "prescription", "reason": "A printed medicine document."})
        auth = headers(client)
        response = attach(
            client, auth, (ROOT / "data/samples/synthetic_prescription.png").read_bytes()
        )
        assert response.status_code == 201
        body = response.json()
        assert body["classification"]["kind"] == "prescription"
        assert body["status"] == "needs_confirmation"
        assert body["fields"] and body["raw_text"]
        blocked = client.post(
            f"/v1/documents/{body['document_id']}/explain",
            headers=auth,
            json={"expected_revision": body["revision"]},
        )
        assert blocked.status_code == 409
        assert (
            client.get(f"/v1/documents/{body['document_id']}", headers=headers(client)).status_code
            == 404
        )


def test_xray_classification_does_not_authorize_diagnostic_scoring():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        mock_model(client, {"kind": "xray", "reason": "A radiograph."})
        response = attach(client, headers(client))
        assert response.status_code == 201
        body = response.json()
        assert body["classification"]["kind"] == "xray"
        assert body["route"] == "xray"
        assert body["fields"] == []
        assert not body.get("findings")
        assert body["imaging_result"]["status"] == "unsupported_input"


@pytest.mark.parametrize("kind", ["other", "uncertain"])
def test_unknown_attachment_is_not_forced_into_a_medical_workflow(kind):
    with TestClient(create_app(Settings(_env_file=None))) as client:
        mock_model(client, {"kind": kind, "reason": "The image cannot be safely routed."})
        body = attach(client, headers(client)).json()
        assert body["status"] == "unsupported_input"
        assert body["classification"]["kind"] == kind
        assert body["fields"] == []


def test_bad_classifier_output_can_be_retried_without_guessing():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        mock_model(client, {"kind": "definitely-normal", "reason": "Bad response"})
        auth = headers(client)
        body = attach(client, auth).json()
        assert body["status"] == "error"
        assert body["document_id"]
        mock_model(client, {"kind": "uncertain", "reason": "Cannot identify this."})
        retry = client.post(f"/v1/attachments/{body['document_id']}/classify", headers=auth)
        assert retry.json()["classification"]["kind"] == "uncertain"


def test_general_chat_uses_model_without_fabricating_source_citations():
    settings = Settings(_env_file=None, answer_mode="ollama", enable_general_chat=True)
    with TestClient(create_app(settings)) as client:
        mock_model(
            client, {"answer": "Quantum entanglement describes correlations in quantum states."}
        )
        body = client.post(
            "/v1/chat", headers=headers(client), json={"question": "Explain quantum entanglement"}
        ).json()
        assert body["status"] == "ok"
        assert "Quantum" in body["answer"]
        assert body["citations"] == []
        assert body["answer_method"] == "ollama_model_knowledge"


def test_greeting_allows_question_invitation_and_discards_unrequested_depth():
    settings = Settings(_env_file=None, answer_mode="ollama", enable_general_chat=True)
    with TestClient(create_app(settings)) as client:
        mock_model(client, {
            "answer": "Hello! If you have a question, please let me know.",
            "deeper_explanation": "This is a greeting from a user. Please ask any question you have.",
        })
        response = client.post("/v1/chat", headers=headers(client), json={"question": "Hello"})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok" and "question" in body["answer"]
        assert not body["deeper_explanation"] and not body.get("explanation_layers")
        assert not body["citations"]


@pytest.mark.parametrize("text", [
    "You have diabetes.", "You have a bacterial infection.",
    "If you have a question, ask me. You have cancer.",
    "You should take 500 mg twice daily.",
])
def test_question_invitation_exception_does_not_allow_diagnosis_or_dosing(text):
    from backend.app.errors import AppError
    from backend.app.services.answers import validate_conversation
    with pytest.raises(AppError):
        validate_conversation(text)


def test_general_chat_cannot_bypass_urgent_or_personal_dose_policy():
    settings = Settings(_env_file=None, answer_mode="ollama", enable_general_chat=True)
    with TestClient(create_app(settings)) as client:
        auth = headers(client)
        for question, expected in [
            ("I cannot breathe", "urgent_guidance"),
            ("Calculate my insulin dose", "unsupported_input"),
        ]:
            body = client.post("/v1/chat", headers=auth, json={"question": question}).json()
            assert body["status"] == expected


def test_model_knowledge_output_rejects_personal_treatment_instructions():
    settings = Settings(_env_file=None, answer_mode="ollama", enable_general_chat=True)
    with TestClient(create_app(settings)) as client:
        mock_model(client, {"answer": "You should take 500 mg twice a day."})
        response = client.post(
            "/v1/chat", headers=headers(client), json={"question": "Explain quantum entanglement"}
        )
        assert response.status_code == 502
        assert "500 mg" not in response.text


def test_retry_after_confirmation_preserves_the_current_revision():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        mock_model(client, {"kind": "prescription", "reason": "Medicine instruction document."})
        auth = headers(client)
        document = attach(
            client, auth, (ROOT / "data/samples/synthetic_prescription.png").read_bytes()
        ).json()
        confirmed = client.put(
            f"/v1/documents/{document['document_id']}/confirm",
            headers=auth,
            json={
                "expected_revision": document["revision"],
                "confirmation_acknowledged": True,
                "fields": [
                    {
                        "field_id": f["field_id"],
                        "value": f["candidate_value"],
                        "status": "confirmed_by_user" if f["candidate_value"] else "unreadable",
                    }
                    for f in document["fields"]
                ],
            },
        ).json()
        retry = client.post(
            f"/v1/attachments/{document['document_id']}/classify", headers=auth
        ).json()
        assert retry["revision"] == confirmed["revision"]
        assert retry["confirmed_revision"] == confirmed["revision"]


def test_classifying_attachment_cannot_be_edited_or_extracted():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        auth = headers(client)
        uploaded = client.post(
            "/v1/documents", headers=auth, files={"file": ("image.png", image_bytes(), "image/png")}
        ).json()
        token = auth["Authorization"].split()[1]
        session = client.app.state.sessions.get(token)
        document = client.app.state.sessions.document(session, uploaded["document_id"])
        document.state = "classifying"
        for endpoint in ["extract", "edit"]:
            response = client.post(
                f"/v1/documents/{document.id}/{endpoint}",
                headers=auth,
                json={"expected_revision": 0},
            )
            assert response.status_code == 409
        assert document.state == "classifying"


@pytest.mark.parametrize(
    "text",
    [
        "Your dose is 500 mg twice daily.",
        "The correct dose for you is 500 mg twice daily.",
        "You should begin taking insulin daily.",
    ],
)
def test_general_model_cannot_emit_personal_dosing_variants(text):
    settings = Settings(_env_file=None, answer_mode="ollama", enable_general_chat=True)
    with TestClient(create_app(settings)) as client:
        mock_model(client, {"answer": text})
        response = client.post(
            "/v1/chat", headers=headers(client), json={"question": "Explain quantum entanglement"}
        )
        assert response.status_code == 502
        assert text not in response.text


def test_context_edited_during_generation_cannot_return_an_obsolete_answer():
    from backend.app.schemas import GeneratedAnswer

    settings = Settings(_env_file=None, answer_mode="ollama", enable_general_chat=True)
    with TestClient(create_app(settings)) as client:
        mock_model(client, {"kind": "prescription", "reason": "Medicine document."})
        auth = headers(client)
        document = attach(
            client, auth, (ROOT / "data/samples/synthetic_prescription.png").read_bytes()
        ).json()
        confirmed = client.put(
            f"/v1/documents/{document['document_id']}/confirm",
            headers=auth,
            json={
                "expected_revision": document["revision"],
                "confirmation_acknowledged": True,
                "fields": [
                    {
                        "field_id": f["field_id"],
                        "value": f["candidate_value"],
                        "status": "confirmed_by_user" if f["candidate_value"] else "unreadable",
                    }
                    for f in document["fields"]
                ],
            },
        ).json()

        def edit_during_model(question, evidence):
            response = client.post(
                f"/v1/documents/{document['document_id']}/edit",
                headers=auth,
                json={"expected_revision": confirmed["revision"]},
            )
            assert response.status_code == 200
            return GeneratedAnswer(
                claims=[{"text": evidence[0].text, "citation_ids": [evidence[0].chunk_id]}]
            )

        client.app.state.ollama.generate = edit_during_model
        response = client.post(
            "/v1/chat",
            headers=auth,
            json={
                "question": "What is asthma?",
                "context_id": document["document_id"],
                "expected_revision": confirmed["revision"],
            },
        )
        assert response.status_code == 409
        assert "obsolete transcription" not in response.text


@pytest.mark.parametrize("existing_state", ["extracting", "confirmed", "explained"])
def test_classifier_cannot_overwrite_a_document_in_another_workflow(existing_state):
    with TestClient(create_app(Settings(_env_file=None))) as client:
        auth = headers(client)
        uploaded = client.post(
            "/v1/documents", headers=auth, files={"file": ("image.png", image_bytes(), "image/png")}
        ).json()
        session = client.app.state.sessions.get(auth["Authorization"].split()[1])
        document = client.app.state.sessions.document(session, uploaded["document_id"])
        document.state = existing_state
        mock_model(client, {"kind": "uncertain", "reason": "Cannot determine type."})
        response = client.post(f"/v1/attachments/{document.id}/classify", headers=auth)
        assert response.status_code == 409
        assert document.state == existing_state


def test_invalid_imaging_outputs_preserve_classification_and_allow_retry():
    import hashlib

    with TestClient(create_app(Settings(_env_file=None))) as client:
        mock_model(client, {"kind": "xray", "reason": "A radiograph."})
        client.app.state.xray.assets = {
            "reviewed": {
                "asset_id": "reviewed",
                "sha256": hashlib.sha256(image_bytes()).hexdigest(),
            }
        }

        def failed_inference(payload):
            raise ValueError("Nonfinite model outputs")

        client.app.state.xray.analyze = failed_inference
        auth = headers(client)
        response = attach(client, auth)
        assert response.status_code == 201
        body = response.json()
        assert body["classification"]["kind"] == "xray"
        assert body["imaging_result"]["status"] == "error"
        retry = client.post(f"/v1/attachments/{body['document_id']}/classify", headers=auth)
        assert retry.status_code == 200
        assert retry.json()["classification"]["kind"] == "xray"
