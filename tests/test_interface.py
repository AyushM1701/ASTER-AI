from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def fake_service(monkeypatch, model_down=False):
    from frontend import client

    st.cache_data.clear()
    calls = []

    def fake_call(method, path, token=None, **kwargs):
        calls.append((method, path, kwargs))
        if path == "/health/ready":
            return {
                "status": "unavailable" if model_down else "ready",
                "references": {"records": 9},
                "answer_mode": "ollama",
                "ocr": {"available": True},
                "attachment_classifier": {"available": True},
            }
        if path == "/v1/sessions":
            return {"token": "test-session-token"}
        if path == "/v1/chat":
            return {
                "status": "ok",
                "answer": "A test explanation of " + kwargs["json"]["question"],
                "citations": [],
            }
        return {"status": "ok"}

    monkeypatch.setattr(client, "call", fake_call)
    return calls


def test_single_chat_keeps_previous_messages_visible(monkeypatch):
    fake_service(monkeypatch)
    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=20).run()
    assert not app.exception
    assert not app.tabs
    assert len(app.chat_input) == 1
    app.chat_input[0].set_value("Explain asthma").run()
    app.chat_input[0].set_value("Explain quantum entanglement").run()
    assert not app.exception
    assert len(app.chat_message) == 4
    assert any("test explanation of Explain asthma" in text.value for text in app.text)
    assert any("test explanation of Explain quantum" in text.value for text in app.text)


def test_unconfirmed_attachment_cannot_be_sent_as_chat_context(monkeypatch):
    calls = fake_service(monkeypatch)
    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=20).run()
    app.session_state["active_document"] = {
        "document_id": "doc_pending",
        "revision": 1,
        "confirmed_revision": None,
    }
    app.chat_input[0].set_value("What is asthma?").run()
    chat_call = next(c for c in reversed(calls) if c[1] == "/v1/chat")
    assert "context_id" not in chat_call[2]["json"]


def test_confirmed_attachment_stays_in_followup_context(monkeypatch):
    calls = fake_service(monkeypatch)
    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=20).run()
    app.session_state["active_document"] = {
        "document_id": "doc_confirmed",
        "revision": 2,
        "confirmed_revision": 2,
    }
    app.chat_input[0].set_value("Explain this term").run()
    chat_call = next(c for c in reversed(calls) if c[1] == "/v1/chat")
    assert chat_call[2]["json"]["context_id"] == "doc_confirmed"
    assert chat_call[2]["json"]["expected_revision"] == 2


def test_attachment_model_error_is_visible_and_offers_retry(monkeypatch):
    fake_service(monkeypatch)
    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=20).run()
    app.session_state["messages"] = [
        {
            "role": "assistant",
            "result": {
                "status": "error",
                "message": "Classifier unavailable",
                "document_id": "doc_retry",
                "classification": None,
            },
        }
    ]
    app.run()
    assert any("Classifier unavailable" in w.value for w in app.warning)
    assert any(b.label == "Retry attachment classification" for b in app.button)


def test_model_outage_does_not_disable_the_chat_policy_path(monkeypatch):
    calls = fake_service(monkeypatch, model_down=True)
    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=20).run()
    assert not app.chat_input[0].disabled
    app.chat_input[0].set_value("I cannot breathe").run()
    assert any(c[1] == "/v1/chat" for c in calls)
