from types import SimpleNamespace

from backend.app.services.question_plan import plan_question
from backend.app.services.study_operations import operation_answer, topic_capabilities


def teacher():
    def source(key, text):
        return SimpleNamespace(
            citation=lambda: {"chunk_id": key, "excerpt": text, "url": "https://example.org/" + key}
        )

    units = [
        dict(
            id="osmosis",
            topics=["osmosis"],
            text="Osmosis is movement of water across a selectively permeable membrane.",
            citation_ids=["o"],
        ),
        dict(
            id="diffusion",
            topics=["diffusion"],
            text="Diffusion is movement down a concentration gradient.",
            citation_ids=["d"],
        ),
    ]
    return SimpleNamespace(
        units=units,
        version="test-v1",
        metadata={},
        references=SimpleNamespace(
            id_records={"o": source("o", units[0]["text"]), "d": source("d", units[1]["text"])}
        ),
    )


def test_basic_comparison_uses_both_bound_notes():
    result = operation_answer(plan_question("Compare osmosis and diffusion", "study"), teacher())
    assert result["status"] == "ok"
    assert result["task_completion"] is True
    assert len(result["comparison"]["rows"]) == 2
    assert {c["citation_ids"][0] for c in result["claims"]} == {"o", "d"}


def test_unsupported_qualifier_is_not_lost():
    assert (
        operation_answer(
            plan_question("Compare osmosis and diffusion in renal impairment", "study"), teacher()
        )
        is None
    )


def test_review_is_rubric_not_automated_grading():
    result = operation_answer(
        plan_question("Review my answer on osmosis: It moves salt.", "study"), teacher()
    )
    assert result["answer_review"]["grading"] == "self_assessment_only"
    assert result["task_completion"] is False
    assert result["status"] == "partial"


def test_capabilities_do_not_assert_faculty_approval():
    result = topic_capabilities(teacher())
    assert result["version"] == "test-v1"
    assert result["topics"][0]["clinical_review"] == "pending"
    assert result["topics"][0]["operations"]["review_answer"] == "reference_rubric_only"
    assert result["topics"][0]["curriculum_mapping_status"] == "not_mapped"
