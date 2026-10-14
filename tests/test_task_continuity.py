from tests import test_workflows
from tests.test_workflows import session

client = test_workflows.client


def test_followup_retains_student_task_and_topic(client, monkeypatch):
    seen = []

    def answer(question, history=(), context="", followup=None, audience="understand"):
        seen.append((question, followup, audience))
        return {"status": "ok", "claims": [], "citations": []}

    monkeypatch.setattr(client.app.state.answers, "answer", answer)
    h = session(client)
    client.post("/v1/chat", headers=h, json={"question": "What is osmosis?", "audience": "study"})
    client.post("/v1/chat", headers=h, json={"question": "Tell me more"})
    client.post("/v1/chat", headers=h, json={"question": "Quiz me"})
    assert seen[-2] == ("What is osmosis?", "deeper", "study")
    assert seen[-1] == ("quiz me on osmosis", None, "study")


def test_explicit_task_change_and_detached_document_context(client, monkeypatch):
    seen = []

    def answer(question, history=(), context="", followup=None, audience="understand"):
        seen.append(audience)
        return {"status": "ok", "claims": [], "citations": []}

    monkeypatch.setattr(client.app.state.answers, "answer", answer)
    h = session(client)
    client.post("/v1/chat", headers=h, json={"question": "What is osmosis?", "audience": "study"})
    client.post(
        "/v1/chat",
        headers=h,
        json={"question": "Tell me more", "audience": "understand", "task_explicit": True},
    )
    assert seen[-1] == "understand"


def test_research_chat_clarifies_setup_instead_of_claiming_a_search(client):
    r = client.post(
        "/v1/chat",
        headers=session(client),
        json={"question": "Find literature on oral leukoplakia", "audience": "research"},
    ).json()
    assert r["task_completion"] is False
    assert r["research_setup"] and not r["claims"]
