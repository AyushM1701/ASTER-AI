"""Conversation continuity without silently reusing detached document context."""
from tests import test_workflows
from tests.test_workflows import session

client = test_workflows.client


def test_repeated_followups_keep_topic_and_accept_punctuation(client, monkeypatch):
    seen = []
    def answer(question, *args):
        seen.append(question)
        return {"status": "ok", "claims": [], "citations": []}
    monkeypatch.setattr(client.app.state.answers, "answer", answer)
    headers = session(client)
    for question in ["What is asthma?", " Tell me more! ", "EXPLAIN THAT?", "what does that mean."]:
        assert client.post("/v1/chat", headers=headers, json={"question": question}).status_code == 200
    assert seen == ["What is asthma?"] * 4
    client.post("/v1/chat", headers=headers, json={"question": "What is anemia?"})
    client.post("/v1/chat", headers=headers, json={"question": "Tell me more"})
    assert seen[-2:] == ["What is anemia?"] * 2
    before = len(seen)
    result = client.post("/v1/chat", headers=headers, json={"question": "I have severe chest pain right now"}).json()
    assert result["status"] == "urgent_guidance"
    assert len(seen) == before


def test_followup_without_topic_asks_for_one(client):
    result = client.post("/v1/chat", headers=session(client), json={"question": "Explain that?"}).json()
    assert result["status"] == "insufficient_evidence"


def test_followup_does_not_reuse_document_context(client):
    # A document-bound message cannot become an implicit topic after detaching.
    from types import SimpleNamespace

    from backend.app.api.chat import chat
    from backend.app.schemas import ChatRequest
    fake_session = SimpleNamespace(messages=[{"question": "Explain this prescription", "resolved_question": None}])
    result = chat(SimpleNamespace(app=client.app), ChatRequest(question="Tell me more"), fake_session)
    assert result["status"] == "insufficient_evidence"
