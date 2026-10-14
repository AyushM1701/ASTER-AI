"""F21: patient intent, applicability and completion are independent of citation validity."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.config import Settings
from backend.app.services.answers import AnswerService
from backend.app.services.output_validation import finalize
from backend.app.services.policy import check_policy
from backend.app.services.question_plan import plan_question
from tests.patient_fixtures import patient_release
from tests.test_knowledge_v2 import make_store, note

BEFORE = json.loads(
    (Path(__file__).parent / "fixtures/f21/toothache_before.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    "question,subject",
    [
        ("What does it mean if a tooth aches?", "toothache"),
        ("Why does my tooth hurt?", "toothache"),
        ("What causes a toothache?", "toothache"),
        ("Why do my teeth hurt when I drink cold water?", "toothache"),
        ("What could pain when biting mean?", "toothache"),
        ("Why is my tooth throbbing?", "toothache"),
        ("My molar tooth is aching. What might explain it?", "toothache"),
        ("Can gum problems cause tooth pain?", "toothache"),
        ("What causes headaches?", "headache"),
        ("Why do people get a fever?", "fever"),
        ("What can cause a sore throat?", "sore_throat"),
        ("What could abdominal pain mean?", "abdominal_pain"),
    ],
)
def test_patient_symptom_information_is_not_generic_teaching(question, subject):
    plan = plan_question(question).model_dump()
    assert plan.get("medical_audience") == "patient"
    assert plan.get("intent") == "symptom_information"
    assert plan.get("primary_subject") == subject
    assert {
        "meaning",
        "possible_causes",
        "uncertainty",
        "professional_followup",
        "warning_signs",
    } <= set(plan.get("required_response_elements", []))


@pytest.mark.parametrize(
    "question",
    [
        "How do teeth erupt?",
        "Explain the role of BMPs in tooth eruption.",
        "Explain periodontal ligament development.",
        "Compare pulpitis and periodontitis.",
        "What are the mechanisms of odontogenic pain?",
    ],
)
def test_technical_dental_questions_retain_educational_intent(question):
    plan = plan_question(question).model_dump()
    assert plan.get("medical_audience") == "student"
    assert plan.get("intent") != "symptom_information"


def test_unknown_context_is_not_fabricated():
    plan = plan_question("What causes a toothache?").model_dump()
    assert plan.get("patient_context") == {}
    assert plan.get("individualized_advice_requested") is False


def test_citation_supported_eruption_dump_fails_final_patient_contract():
    response = finalize(BEFORE["question"], BEFORE["response"])
    assert response["status"] == "insufficient_evidence"
    assert not response["claims"] and not response["citations"]
    assert response["task_completion"] is False


@pytest.mark.parametrize(
    "method", ["source_backed_teaching", "extractive", "ollama", "extractive_verified_fallback"]
)
def test_all_output_modes_use_the_same_patient_relevance_contract(method):
    raw = {**BEFORE["response"], "answer_method": method}
    result = finalize("Why does my tooth hurt?", raw)
    assert result["status"] == "insufficient_evidence"
    assert not result["claims"]


def test_student_source_cannot_answer_patient_symptom_at_service_boundary(tmp_path):
    teaching = SimpleNamespace(answer=lambda q: BEFORE["response"], units=[])
    service = AnswerService(
        Settings(), make_store(tmp_path, [note()]), None, None, teaching=teaching
    )
    result = service.answer(BEFORE["question"])
    assert "BMP" not in " ".join(c["text"] for c in result["claims"])
    assert result["status"] in {"ok", "insufficient_evidence"}
    assert not result.get("explanation_layers")


@pytest.mark.parametrize(
    "question",
    [
        "My face is swollen and I'm having difficulty swallowing.",
        "My tooth aches and my neck is swollen.",
        "I have a sudden extremely painful headache.",
        "I have a severe stomach ache.",
    ],
)
def test_current_red_flags_are_not_ordinary_symptom_education(question):
    result = check_policy(question)
    assert result and result["status"] == "urgent_guidance"


@pytest.mark.parametrize(
    "question",
    [
        "What causes toothaches?",
        "My tooth hurts but I have no swelling and no difficulty swallowing.",
        "What warning signs with toothache need urgent care?",
        "Explain severe abdominal pain in a fictional case.",
    ],
)
def test_benign_or_educational_symptom_questions_are_not_blanket_emergencies(question):
    assert check_policy(question) is None


@pytest.mark.parametrize(
    "question",
    [
        "What does it mean if a tooth aches?",
        "Why does my tooth hurt?",
        "What causes a toothache?",
        "Why do my teeth hurt when I drink cold water?",
        "What could pain when biting mean?",
        "Why is my tooth throbbing?",
        "Can gum problems cause tooth pain?",
        "Does my toothache definitely mean I have an abscess?",
    ],
)
def test_supported_symptoms_get_complete_patient_information(tmp_path, question):
    release = patient_release(tmp_path / "patient")
    refs = make_store(tmp_path, [note()])
    service = AnswerService(Settings(patient_release_path=release), refs, None, None)
    result = service.answer(question)
    assert result["status"] == "ok"
    assert result.get("patient_response", {}).get("subject") == "toothache"
    assert result["task_completion"] is True
    assert {
        "meaning",
        "possible_causes",
        "uncertainty",
        "professional_followup",
        "warning_signs",
    } <= {p["role"] for p in result["patient_response"]["parts"]}
    assert all(
        set(c["citation_ids"]) <= {r["chunk_id"] for r in result["citations"]}
        for c in result["claims"]
    )
    assert not result.get("explanation_layers")
    assert result["validation"]["clinical_review"] == "pending"


@pytest.mark.parametrize(
    "missing,conflict,population",
    [
        (("warning_signs",), False, "all_ages"),
        ((), True, "all_ages"),
        ((), False, "adult"),
    ],
)
def test_incomplete_disputed_or_population_mismatched_evidence_does_not_complete_task(
    tmp_path, missing, conflict, population
):
    release = patient_release(tmp_path / "patient", missing, conflict, population)
    service = AnswerService(
        Settings(patient_release_path=release), make_store(tmp_path, [note()]), None, None
    )
    result = service.answer("Why does my child's tooth hurt?")
    assert result["status"] != "ok"
    assert result["task_completion"] is False


def test_no_patient_source_never_reuses_student_passage(tmp_path):
    teaching = SimpleNamespace(answer=lambda q: BEFORE["response"], units=[])
    service = AnswerService(
        Settings(patient_release_path=tmp_path / "missing"),
        make_store(tmp_path, [note()]),
        None,
        None,
        teaching=teaching,
    )
    result = service.answer(BEFORE["question"])
    assert result["status"] == "insufficient_evidence" and not result["claims"]
    assert not result["citations"]


@pytest.mark.parametrize(
    "question",
    [
        "What does it mean if a finger aches?",
        "Why does an ear hurt?",
        "My head hurts and I have fever",
    ],
)
def test_uncovered_symptom_or_combination_is_not_completed(tmp_path, question):
    service = AnswerService(
        Settings(patient_release_path=patient_release(tmp_path / "patient")),
        make_store(tmp_path, [note()]),
        None,
        None,
    )
    result = service.answer(question)
    assert plan_question(question).intent == "symptom_information"
    assert result["task_completion"] is False


@pytest.mark.parametrize(
    "question",
    [
        "My headache is suddenly extremely painful.",
        "I have fever and a stiff neck.",
        "I have no jaw swelling but my face is swollen and I have difficulty swallowing.",
    ],
)
def test_additional_current_red_flags_escalate(question):
    assert check_policy(question)["status"] == "urgent_guidance"


@pytest.mark.parametrize(
    "question",
    [
        "What warning signs include a sudden severe headache?",
        "My throat hurt last year and I had difficulty swallowing in the past.",
        "My face is not swollen and I have no difficulty swallowing.",
    ],
)
def test_no_fabricated_current_emergency(question):
    assert check_policy(question) is None


def test_staleness_and_modified_evidence_fail_closed(tmp_path):
    from datetime import timedelta

    from backend.app.services.patient_information import PatientInformationStore, utc_date

    release = patient_release(tmp_path / "patient")
    store = PatientInformationStore(release, clock=lambda: utc_date() + timedelta(days=7))
    assert (
        store.answer(plan_question("What causes toothache?"))["status"] == "insufficient_evidence"
    )
    (release / "units.json").write_text("{}", encoding="utf-8")
    changed = PatientInformationStore(release)
    assert changed.error and not changed.units and not changed.current()


def test_missing_noncritical_evidence_is_honest_partial(tmp_path):
    release = patient_release(tmp_path / "patient", missing=("possible_causes",))
    service = AnswerService(
        Settings(patient_release_path=release), make_store(tmp_path, [note()]), None, None
    )
    result = service.answer("What causes toothache?")
    assert result["status"] == "partial" and result["task_completion"] is False
    assert result["missing_response_elements"] == ["possible_causes"]


@pytest.mark.parametrize("error_code", [502, 503])
def test_model_failure_cannot_bypass_patient_contract(tmp_path, error_code):
    from backend.app.errors import AppError

    def failing_model(*args, **kwargs):
        raise AppError(error_code, "error", "Model unavailable")

    model = SimpleNamespace(answer=failing_model, converse=failing_model)
    teaching = SimpleNamespace(answer=lambda q: BEFORE["response"], units=[])
    service = AnswerService(
        Settings(patient_release_path=tmp_path / "missing", answer_mode="ollama"),
        make_store(tmp_path, [note()]),
        model,
        None,
        teaching=teaching,
    )
    result = service.answer("What causes toothache?")
    assert result["status"] == "insufficient_evidence" and not result["claims"]


def test_personal_treatment_is_blocked_even_with_patient_source(tmp_path):
    service = AnswerService(
        Settings(patient_release_path=patient_release(tmp_path / "patient")),
        make_store(tmp_path, [note()]),
        None,
        None,
    )
    assert (
        service.answer("Which antibiotic should I take for my toothache?")["status"]
        == "unsupported_input"
    )


def test_combined_independent_questions_keep_patient_contracts(tmp_path):
    service = AnswerService(
        Settings(patient_release_path=patient_release(tmp_path / "patient")),
        make_store(tmp_path, [note()]),
        None,
        None,
    )
    result = service.answer("Why does my tooth hurt? What causes a headache?")
    assert result["status"] == "partial" and result["task_completion"] is False
    assert result["component_answers"][0]["response"]["patient_response"]["subject"] == "toothache"


def test_personal_symptom_is_not_erased_by_technical_followup(tmp_path):
    service = AnswerService(
        Settings(patient_release_path=patient_release(tmp_path / "patient")),
        make_store(tmp_path, [note()]),
        None,
        None,
    )
    q = "My tooth hurts; explain the pathophysiology"
    assert plan_question(q).intent == "symptom_information"
    # The two operations may be answered separately, but the symptom part
    # must keep its safety contract rather than becoming an eruption excerpt.
    result = service.answer(q)
    assert result["component_answers"][0]["response"]["patient_response"]


def test_tampered_citation_metadata_rejected_by_terminal_guard(tmp_path):
    from backend.app.services.patient_information import PatientInformationStore

    patient = PatientInformationStore(patient_release(tmp_path / "patient"))
    q = "What causes toothache?"
    result = patient.answer(plan_question(q))
    result["citations"][0]["excerpt"] = "A chapter about unrelated development."
    assert finalize(q, result, patient.units)["rejection_codes"] == ["patient_source_binding"]


def test_confirmed_document_does_not_replace_a_symptom_question(tmp_path):
    import threading

    from fastapi.testclient import TestClient

    from backend.app.main import create_app

    settings = Settings(patient_release_path=patient_release(tmp_path / "patient"))
    with TestClient(create_app(settings)) as client:
        token = client.post("/v1/sessions").json()["token"]
        session = client.app.state.sessions.get(token)
        session.documents["doc_test"] = SimpleNamespace(
            id="doc_test", lock=threading.RLock(), revision=1, confirmed_revision=1
        )
        payload = {
            "question": "Why does my tooth hurt?",
            "context_id": "doc_test",
            "expected_revision": 1,
        }
        headers = {"Authorization": "Bearer " + token}
        result = client.post("/v1/chat", headers=headers, json=payload).json()
        assert result["patient_response"]["subject"] == "toothache"
        assert result["validation"]["task_relevance"] == "passed_by_bounded_contract"
        payload["expected_revision"] = 0
        assert client.post("/v1/chat", headers=headers, json=payload).status_code == 409


def test_failed_generation_recovers_once_with_applicable_patient_evidence(tmp_path, monkeypatch):
    service = AnswerService(
        Settings(patient_release_path=patient_release(tmp_path / "patient")),
        make_store(tmp_path, [note()]),
        None,
        None,
    )
    calls = []
    monkeypatch.setattr(
        service, "_answer", lambda *args: {**BEFORE["response"], "answer_method": "ollama"}
    )
    original = service.patient.answer

    def bounded(plan):
        calls.append(plan)
        return original(plan)

    monkeypatch.setattr(service.patient, "answer", bounded)
    result = service.answer("Why does my tooth hurt?")
    assert result["status"] == "ok" and len(calls) == 1
    assert result["relevance_recovery"] == "bounded_patient_applicability_lookup"


def test_failed_generation_without_evidence_abstains_after_one_attempt(tmp_path, monkeypatch):
    service = AnswerService(
        Settings(patient_release_path=tmp_path / "missing"),
        make_store(tmp_path, [note()]),
        None,
        None,
    )
    monkeypatch.setattr(service, "_answer", lambda *args: BEFORE["response"])
    result = service.answer("Why does my tooth hurt?")
    assert result["status"] == "insufficient_evidence" and not result["claims"]
    assert result["relevance_recovery"] == "bounded_patient_applicability_lookup"
