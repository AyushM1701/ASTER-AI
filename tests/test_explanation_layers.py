import copy
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services.explanation_layers import LAYOUTS, present_answer, valid_layout
from tests.test_chat_attachments import headers, mock_model

PLANS = json.loads(LAYOUTS.read_text(encoding="utf-8"))["plans"]


def response(plan):
    return {
        "status": "ok",
        "route": "medical_education",
        "claims": [{"text": plan["original"], "citation_ids": plan["citation_ids"]}],
        "citations": [{"chunk_id": key, "source_type": "teaching"} for key in plan["citation_ids"]],
        "warnings": ["Existing uncertainty remains."],
    }


@pytest.mark.parametrize("plan", PLANS, ids=lambda p: p["unit_id"])
def test_complete_checked_notes_are_conserved(plan):
    assert valid_layout(plan)
    original = response(plan)
    before = copy.deepcopy(original)
    shown = present_answer(original)
    assert original == before
    assert shown["claims"] == original["claims"]
    assert shown["warnings"] == original["warnings"]
    layers = shown["explanation_layers"]
    assert layers["simple"][0]["text"] == plan["simple"]
    assert [p["text"] for p in layers["deeper"]] == ([plan["deeper"]] if plan["deeper"] else [])
    assert [p["text"] for p in layers["context"]] == ([plan["context"]] if plan["context"] else [])
    for key in ("simple", "deeper", "context"):
        assert all(
            p["citation_ids"] == plan["citation_ids"] and p["claim_index"] == 0 for p in layers[key]
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("simple", "Made up explanation."),
        ("deeper", "Omitted qualifications."),
        ("context", ""),
        ("text_sha256", "bad"),
        ("simple_sentence_indices", [-1]),
    ],
)
def test_corrupt_layouts_fail_closed(field, value):
    plan = copy.deepcopy(next(p for p in PLANS if p["context"]))
    plan[field] = value
    assert not valid_layout(plan)


def test_changed_source_or_citation_cannot_use_old_simple_explanation():
    for change in ("text", "citation_ids"):
        result = response(PLANS[0])
        result["claims"][0][change] = "Changed source wording." if change == "text" else ["unknown"]
        layers = present_answer(result)["explanation_layers"]
        assert not layers["simple"] and layers["simple_notice"]
        assert layers["deeper"][0]["text"] == result["claims"][0]["text"]


@pytest.mark.parametrize(
    "status",
    ["urgent_guidance", "needs_confirmation", "insufficient_evidence", "error", "quality_rejected"],
)
def test_non_answer_states_stay_direct(status):
    result = response(PLANS[0])
    result["status"] = status
    assert present_answer(result) == result


def test_short_patient_note_stays_complete_and_missing_depth_is_honest():
    result = {
        "status": "ok",
        "route": "document_explanation",
        "claims": [
            {"text": "A complete short note. Keep its qualification.", "citation_ids": ["a"]}
        ],
        "citations": [{"chunk_id": "a", "source_type": "education"}],
    }
    layers = present_answer(result)["explanation_layers"]
    assert layers["simple"][0]["text"] == result["claims"][0]["text"]
    assert not layers["deeper"] and layers["deeper_notice"]


def test_general_answer_fields_are_both_presented():
    with TestClient(
        create_app(Settings(_env_file=None, answer_mode="ollama", enable_general_chat=True))
    ) as client:

        def incidental_medical_match(question):
            raise AssertionError("Explicit programming intent reached medical retrieval")

        client.app.state.teaching.answer = incidental_medical_match
        mock_model(
            client,
            {
                "answer": "Programming gives a computer instructions.",
                "deeper_explanation": "A program expresses these instructions using a programming language.",
            },
        )
        reply = client.post(
            "/v1/chat", headers=headers(client), json={"question": "Explain programming"}
        )
        assert reply.status_code == 200
        result = reply.json()
        assert result["explanation_layers"]["simple"][0]["text"] == result["answer"]
        assert result["explanation_layers"]["deeper"][0]["text"] == result["deeper_explanation"]
        assert result["citations"] == [] and result["warnings"]


def test_deeper_model_field_cannot_bypass_output_safety():
    with TestClient(
        create_app(Settings(_env_file=None, answer_mode="ollama", enable_general_chat=True))
    ) as client:
        mock_model(
            client,
            {
                "answer": "Programming gives a computer instructions.",
                "deeper_explanation": "Your dose is 500 mg twice daily.",
            },
        )
        reply = client.post(
            "/v1/chat", headers=headers(client), json={"question": "Explain programming"}
        )
        assert reply.status_code == 502
        assert "500 mg" not in reply.text
