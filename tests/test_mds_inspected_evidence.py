"""AI inspection is explicit development evidence, never a human attestation."""

import copy

import pytest

from backend.app.services.reviewed_evidence import reviewed_support
from tests.test_mds_reviewed_evidence import annotation_for
from tests.test_mds_reviewed_evidence import reviewed_unit as reviewed_unit


def inspected_metadata(facet, row):
    entry = annotation_for(facet, row)
    entry.update(review_status="source_inspected", review_origin="ai_source_inspection",
                 reviewer="Codex", support_rationale="The complete unit explains the named function, including its analogy.",
                 qualification_note="The stated analogy limitation is preserved verbatim.")
    return {"ai_inspected_facet_bindings": [entry]}


def test_ai_inspection_is_separately_bound(reviewed_unit):
    facet, row, _ = reviewed_unit
    metadata = inspected_metadata(facet, row)
    assert reviewed_support(facet, row, metadata)
    assert "reviewed_facet_bindings" not in metadata
    assert not reviewed_support(facet.model_copy(update={"scope": "in pregnancy"}), row, metadata)


@pytest.mark.parametrize("field,value", [
    ("review_origin", "human"), ("review_status", "developer_reviewed"),
    ("reviewer", ""), ("support_rationale", ""), ("qualification_note", ""),
    ("clinical_review", True), ("text_sha256", "a" * 64),
    ("retained_qualifications", ["Invented qualification"]),
])
def test_invalid_inspection_cannot_supply_evidence(reviewed_unit, field, value):
    facet, row, _ = reviewed_unit
    metadata = inspected_metadata(facet, row)
    metadata["ai_inspected_facet_bindings"][0][field] = value
    assert not reviewed_support(facet, row, metadata)


def test_ai_annotations_cannot_be_relabelled_human(reviewed_unit):
    facet, row, _ = reviewed_unit
    metadata = inspected_metadata(facet, row)
    entry = copy.deepcopy(metadata["ai_inspected_facet_bindings"][0])
    assert not reviewed_support(facet, row, {"reviewed_facet_bindings": [entry]})
    entry["review_status"] = "developer_reviewed"
    assert not reviewed_support(facet, row, {"reviewed_facet_bindings": [entry]})


def test_inspected_unit_is_retrieved_even_when_generic_search_misses(tmp_path):
    from backend.app.services.answers import AnswerService
    from backend.app.services.question_plan import plan_question
    from tests.mds_fixtures import make_teacher

    teacher, rows = make_teacher(tmp_path, [("apoptosis", "Cell death / Definition",
        "Apoptosis is a synthetic test concept. A scaffold is removed when construction finishes. This analogy has qualified limitations.")])
    plan = plan_question("Define apoptosis", "study")
    teacher.metadata[rows[0].chunk_id] = inspected_metadata(plan.facets[0], rows[0])
    teacher.search = lambda *args, **kwargs: []
    service = AnswerService(teacher.settings, teacher.references, None, None, teaching=teacher)
    result = service.answer(plan.original_question, audience="study")
    assert result["coverage_status"] == "complete"
    assert result["claim_evidence"][0]["facet"] == "definition"
    assert result["evidence_review_origin"] == "ai_source_inspection"


def test_explicit_appraisal_uses_available_facet_evidence(tmp_path):
    from backend.app.services.answers import AnswerService
    from tests.mds_fixtures import make_teacher

    teacher, _ = make_teacher(tmp_path, [("immunohistochemistry", "Immunohistochemistry",
        "Immunohistochemistry is a synthetic diagnostic method for this test fixture. Immunohistochemistry diagnostic tests have synthetic limitations.")])
    service = AnswerService(teacher.settings, teacher.references, None, None, teaching=teacher)
    result = service.answer("Critically appraise immunohistochemistry: definition and investigations.", audience="research")
    assert result["claims"] and result["question_plan"]["audience"] == "research"
    assert "research_setup" not in result


def test_runtime_hold_blocks_heuristic_evidence(tmp_path):
    from backend.app.services.answers import AnswerService
    from tests.mds_fixtures import make_teacher

    teacher, rows = make_teacher(tmp_path, [("apoptosis", "Apoptosis",
        "Apoptosis is a synthetic process. Apoptosis activates a synthetic pathway for this fixture.")])
    teacher.metadata[rows[0].chunk_id]["runtime_policy"] = "exclude"
    result = AnswerService(teacher.settings, teacher.references, None, None, teaching=teacher).answer("Explain apoptosis mechanism", audience="study")
    assert not result["claims"] and not result["task_completion"]
