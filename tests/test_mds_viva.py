from fastapi.testclient import TestClient

from backend.app.main import create_app
from tests.mds_fixtures import make_teacher


def setup(tmp_path):
    teacher, _ = make_teacher(tmp_path, [
        ("apoptosis", "Apoptosis", "Apoptosis is a synthetic source-bound cell-death definition for this mechanics fixture with qualified limitations."),
        ("apoptosis", "Apoptosis", "Apoptosis is a second synthetic source explanation for this mechanics fixture with separate qualified limitations."),
    ])
    return TestClient(create_app(teacher.settings))


def owner(client):
    return {"Authorization": "Bearer " + client.post("/v1/sessions").json()["token"]}


def test_viva_hides_rubric_until_answer_then_gives_provisional_feedback(tmp_path):
    with setup(tmp_path) as client:
        headers = owner(client)
        first = client.post("/v1/chat", headers=headers, json={"question": "Ask me a viva question on apoptosis", "audience": "study"}).json()
        assert first["viva"]["stage"] == "await_answer"
        assert first["viva"]["question"].count("?") == 1
        assert not first["claims"] and not first["citations"]
        assert "expected_points" not in str(first) and "rubric" not in str(first)
        next_turn = client.post("/v1/chat", headers=headers, json={"question": "It is cell death, with limitations", "viva_question_id": first["viva"]["question_id"]}).json()
        assert next_turn["viva"]["feedback"]["review_status"] == "provisional_educational"
        assert next_turn["claims"] and next_turn["citations"]
        assert next_turn["viva"]["question_id"] != first["viva"]["question_id"]


def test_viva_out_of_order_submission_does_not_advance_or_leak(tmp_path):
    with setup(tmp_path) as client:
        a, b = owner(client), owner(client)
        first = client.post("/v1/chat", headers=a, json={"question": "Start a viva on apoptosis", "audience": "study"}).json()
        stale = client.post("/v1/chat", headers=a, json={"question": "Answer", "viva_question_id": "old"}).json()
        assert stale["status"] == "needs_confirmation" and not stale["claims"]
        foreign = client.post("/v1/chat", headers=b, json={"question": "Answer", "viva_question_id": first["viva"]["question_id"]}).json()
        assert foreign["status"] == "needs_confirmation" and not foreign["claims"]
        valid = client.post("/v1/chat", headers=a, json={"question": "A qualified definition", "viva_question_id": first["viva"]["question_id"]}).json()
        assert valid["viva"]["feedback"]


def test_viva_restart_exit_patient_boundary_and_expiry(tmp_path):
    with setup(tmp_path) as client:
        a = owner(client)
        first = client.post("/v1/chat", headers=a, json={"question": "Viva on apoptosis", "audience": "study"}).json()
        restarted = client.post("/v1/chat", headers=a, json={"question": "Restart viva"}).json()
        assert restarted["viva"]["question_id"] != first["viva"]["question_id"]
        unsafe = client.post("/v1/chat", headers=a, json={"question": "Fictional case: diagnose me, I have a tongue lesion", "viva_question_id": restarted["viva"]["question_id"]}).json()
        assert unsafe["status"] == "unsupported_input"
        stopped = client.post("/v1/chat", headers=a, json={"question": "Exit viva"}).json()
        assert stopped["viva"]["stage"] == "exited"
        replay = client.post("/v1/chat", headers=a, json={"question": "Answer", "viva_question_id": restarted["viva"]["question_id"]}).json()
        assert replay["status"] == "needs_confirmation"
        client.delete("/v1/sessions/current", headers=a)
        assert client.post("/v1/chat", headers=a, json={"question": "Restart viva"}).status_code == 401


def test_elliptical_followup_resolves_only_current_session_topic(tmp_path):
    teacher, _ = make_teacher(tmp_path, [
        ("oral epithelium", "Oral epithelium", "Oral epithelium is a synthetic epithelial cover whose functions include a synthetic barrier, with qualifications."),
    ])
    with TestClient(create_app(teacher.settings)) as client:
        a, b = owner(client), owner(client)
        client.post("/v1/chat", headers=a, json={"question": "Define oral epithelium", "audience": "study"})
        follow = client.post("/v1/chat", headers=a, json={"question": "What are its functions?"}).json()
        assert follow["claims"] and follow["question_plan"]["original_question"] == "What are its functions?"
        unknown = client.post("/v1/chat", headers=b, json={"question": "What are its functions?"}).json()
        assert unknown["status"] == "insufficient_evidence" and not unknown["claims"]


def test_patient_question_and_new_task_exit_viva_even_with_current_turn_id(tmp_path):
    with setup(tmp_path) as client:
        headers = owner(client)
        for question in ("My tooth hurts when I bite", "Explain oral epithelium functions"):
            first = client.post("/v1/chat", headers=headers, json={"question": "Viva on apoptosis", "audience": "study"}).json()
            result = client.post("/v1/chat", headers=headers, json={"question": question, "viva_question_id": first["viva"]["question_id"]}).json()
            assert "viva" not in result
            assert not any("apoptosis" in c["text"].lower() for c in result.get("claims", []))


def test_single_source_unit_still_supports_one_qualification_followup(tmp_path):
    teacher, _ = make_teacher(tmp_path, [("apoptosis", "Apoptosis", "Apoptosis is a synthetic source-bound definition with qualifications retained in this fixture.")])
    with TestClient(create_app(teacher.settings)) as client:
        headers = owner(client)
        first = client.post("/v1/chat", headers=headers, json={"question": "Viva on apoptosis", "audience": "study"}).json()
        second = client.post("/v1/chat", headers=headers, json={"question": "A definition retaining its qualifications", "viva_question_id": first["viva"]["question_id"]}).json()
        assert second["viva"]["stage"] == "await_answer"
        assert second["viva"]["number"] == 2 and "qualifications" in second["viva"]["question"]


def test_grading_instruction_is_not_scored_as_a_learner_answer(tmp_path):
    with setup(tmp_path) as client:
        headers = owner(client)
        first = client.post("/v1/chat", headers=headers, json={"question": "Viva on apoptosis", "audience": "study"}).json()
        result = client.post("/v1/chat", headers=headers, json={"question": "After I answer, grade it out of 10 using an explicit rubric and explain what I missed.", "viva_question_id": first["viva"]["question_id"]}).json()
        assert result["viva"]["question_id"] == first["viva"]["question_id"]
        assert result["viva"]["number"] == 1 and result["viva"]["stage"] == "await_answer"
        assert "feedback" not in result["viva"] and not result["claims"]
