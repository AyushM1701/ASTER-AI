from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from backend.app.config import Settings
from backend.app.errors import AppError
from backend.app.schemas import GeneratedAnswer
from backend.app.services.answers import AnswerService
from backend.app.services.policy import check_policy
from tests.test_knowledge_v2 import make_store, note


@pytest.mark.parametrize(
    "mode,failure", [("extractive", None), ("ollama", 502), ("ollama", 503), ("ollama", None)]
)
def test_every_output_path_rejects_unsolicited_dose(tmp_path, mode, failure):
    record = note(text="Give 0.8 ml to your child every four hours.")
    store = make_store(tmp_path, [record])

    def generate(*args):
        if failure:
            raise AppError(failure, "error", "Unavailable")
        return GeneratedAnswer(
            claims=[{"text": record.text, "citation_ids": [store.records[0].chunk_id]}]
        )

    service = AnswerService(
        Settings(answer_mode=mode, strict_source_grounding=True),
        store,
        SimpleNamespace(generate=generate),
        SimpleNamespace(enter=nullcontext),
    )
    result = service.answer("Explain anemia")
    assert not result["claims"]
    assert result["status"] == "insufficient_evidence"
    assert result["validation"]["clinical_review"] == "pending"


def test_multipart_keeps_missing_part_visible(tmp_path):
    store = make_store(tmp_path, [note()])
    service = AnswerService(Settings(), store, None, None)
    result = service.answer("Explain anemia and an unknown medical concept")
    assert result["claims"]
    assert result["status"] == "partial"
    assert result["unsupported_parts"] == ["Explain an unknown medical concept"]


def test_unknown_citation_is_never_emitted():
    from backend.app.services.output_validation import finalize

    result = finalize(
        "Explain anemia",
        {
            "status": "ok",
            "claims": [{"text": "Anemia.", "citation_ids": ["missing"]}],
            "citations": [],
        },
    )
    assert result["status"] == "insufficient_evidence"
    assert not result["claims"]


def test_definition_intent_does_not_disable_personal_boundary():
    assert check_policy("Explain what prescribe means.") is None
    assert (
        check_policy("Explain what prescribe means and prescribe a medicine for my symptoms.")[
            "status"
        ]
        == "unsupported_input"
    )
    assert check_policy("Do I have oral cancer?")["status"] == "unsupported_input"


def test_viva_requires_an_actual_activity(tmp_path):
    store = make_store(tmp_path, [note()])
    service = AnswerService(Settings(), store, None, None)
    result = service.answer("Give me a viva question on anemia.")
    assert result["status"] == "ok"
    assert result["practice_item"]["question"].endswith("?")
    assert result["practice_item"]["source_ids"]
    assert result["practice_item"]["review_status"] == "clinical_review_pending"


def test_compare_never_labels_an_excerpt_as_completed(tmp_path):
    service = AnswerService(Settings(), make_store(tmp_path, [note()]), None, None)
    result = service.answer("Compare anemia and an unknown medical concept")
    assert result["status"] == "insufficient_evidence"
    assert result["task_completion"] is False


def test_more_does_not_repeat_previous_claims(tmp_path):
    service = AnswerService(Settings(), make_store(tmp_path, [note()]), None, None)
    previous = service.answer("What is anemia?")
    result = service.answer("What is anemia?", [{"response": previous}], followup="deeper")
    assert result["claims"] != previous["claims"]
    assert result["status"] == "insufficient_evidence"


def test_source_id_is_not_claim_support():
    from backend.app.services.medical_evaluation import evaluate_claims

    result = {
        "claims": [{"text": "Anemia is always harmless.", "citation_ids": ["a"]}],
        "citations": [{"chunk_id": "a", "excerpt": "Anemia has several causes."}],
    }
    evaluated = evaluate_claims(result)
    assert evaluated["claims"][0]["relationship"] == "insufficient_evidence"
    assert evaluated["clinical_review"] == "pending"


def test_benchmark_counts_missing_predictions_as_unanswered():
    from backend.app.services.medical_evaluation import score_pubmedqa

    result = score_pubmedqa(
        {"1": {"final_decision": "yes"}, "2": {"final_decision": "no"}}, {"1": "yes"}
    )
    assert result["correct"] == 1 and result["total"] == 2
    assert result["accuracy"] == 0.5 and result["unanswered"] == 1


def test_benchmark_never_prompts_with_answer_key():
    from backend.app.services.medical_evaluation import benchmark_prompt

    prompt = benchmark_prompt(
        {
            "QUESTION": "Does it work?",
            "CONTEXTS": ["Observed data"],
            "LONG_ANSWER": "SECRET",
            "final_decision": "yes",
        }
    )
    assert "SECRET" not in prompt


def test_common_guard_rejects_claim_not_in_source_or_prepared_note():
    from backend.app.services.output_validation import finalize
    result = {"status": "ok", "claims": [{"text": "Anemia is always harmless.", "citation_ids": ["a"]}],
              "citations": [{"chunk_id": "a", "excerpt": "Anemia has several causes."}]}
    assert finalize("Explain anemia", result)["status"] == "insufficient_evidence"
