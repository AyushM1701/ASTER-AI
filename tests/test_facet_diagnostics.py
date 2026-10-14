import json

from backend.app.services.output_validation import finalize
from backend.app.services.question_plan import plan_question


def test_terminal_guard_emits_nullable_observations_without_fake_triage():
    plan = plan_question("Define oral epithelium.", "study")
    result = finalize(plan.original_question, {
        "status": "insufficient_evidence", "claims": [], "citations": [],
        "evidence_plan": {"source_set_version": "fixture-v1", "facets": [{
            "request": plan.facets[0].model_dump(), "state": "missing", "chunk_ids": [],
            "candidate_count": 1, "reason_codes": ["no_applicable_source_span"],
        }], "rejected": [{"topic_id": "oral_epithelium", "facet": "definition",
                            "chunk_id": "fixture-rejected", "reason_codes": ["facet_not_supported"]}]},
    }, question_plan=plan)
    trace = result["facet_diagnostics"][0]
    assert trace["candidate_count"] == 1
    assert trace["plan_valid"] is None
    assert trace["source_available_in_release"] is None
    assert trace["primary_failure_reason"] is None
    assert trace["observed_failure_reason"] == "EVIDENCE_INSUFFICIENT"
    assert trace["displayed"] is None
    assert trace["terminal_guard_executed"]
    assert not trace["composition_included"]
    assert "facet_not_supported" in trace["secondary_reasons"]
    assert trace["source_pack_version"] == "fixture-v1"


def test_diagnostics_do_not_copy_original_question_or_evidence_text():
    plan = plan_question("Define oral epithelium. My identifier is PRIVATE-123.", "study")
    result = finalize(plan.original_question, {"status": "insufficient_evidence",
                                             "claims": [], "citations": []}, question_plan=plan)
    encoded = json.dumps(result["facet_diagnostics"])
    assert "PRIVATE-123" not in encoded
    assert "Define oral epithelium" not in encoded


def test_policy_only_result_does_not_invent_an_evidence_trace():
    result = finalize("Do I have oral cancer?", {"status": "unsupported_input", "claims": [], "citations": []})
    assert result["facet_diagnostics"] == []


def test_freeform_subject_and_detail_are_not_copied_into_diagnostics():
    for question in ("Define Patient John Smith tumor.", "Define oral epithelium, including PRIVATE-123 receptor."):
        plan = plan_question(question, "study")
        result = finalize(question, {"status": "insufficient_evidence", "claims": [], "citations": []}, question_plan=plan)
        encoded = json.dumps(result["facet_diagnostics"]).casefold()
        assert "john_smith" not in encoded
        assert "private_123" not in encoded
