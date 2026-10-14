"""Observed pipeline stages, never independent support or clinical labels.

No source text or original question is copied. These request-scoped fields
are not written to routine logs. UI display requires a browser observation.
"""

FAILURE_TAXONOMY = (
    "PLAN_WRONG_SUBJECT", "PLAN_MISSING_FACET", "SOURCE_NOT_LICENSED",
    "SOURCE_NOT_IN_RELEASE", "SOURCE_REVIEW_HOLD", "RETRIEVAL_MISS",
    "RERANK_FALSE_NEGATIVE", "APPLICABILITY_FALSE_NEGATIVE", "EVIDENCE_INSUFFICIENT",
    "CONTRADICTORY_EVIDENCE", "COMPOSITION_OMISSION", "CLAIM_UNSUPPORTED",
    "WRONG_TASK_FORMAT", "POLICY_BLOCK", "MODEL_UNAVAILABLE", "INDEX_UNAVAILABLE",
    "FRONTEND_NOT_DISPLAYED",
)


def signature(facet):
    return facet.get("topic_id"), facet.get("facet"), facet.get("scope", "")


def trace_facets(plan, original_result, final_result):
    from backend.app.services.mds_curriculum import TOPICS
    from backend.app.services.question_plan import FACET_PATTERNS

    if plan is None:
        return []
    requests = plan.facets
    topic_labels = {identity: identity if identity in TOPICS else f"subject-{index + 1}"
                    for index, identity in enumerate(dict.fromkeys(item.topic_id for item in requests))}
    facet_labels = {name: name if name in FACET_PATTERNS else f"detail-{index + 1}"
                    for index, name in enumerate(dict.fromkeys(item.facet for item in requests))}
    evidence = original_result.get("evidence_plan", {})
    assessments = {signature(item.get("request", {})): item for item in evidence.get("facets", [])}
    covered = {signature(item) for item in final_result.get("covered_facets", [])}
    traces = []
    for request in requests:
        key = signature(request.model_dump())
        assessment = assessments.get(key, {})
        rejected = [item for item in evidence.get("rejected", [])
                    if (item.get("topic_id"), item.get("facet")) == key[:2]]
        candidates = sorted(set(assessment.get("chunk_ids", [])) | {
            item["chunk_id"] for item in rejected if item.get("chunk_id")
        })
        reasons = sorted(set(assessment.get("reason_codes", [])) | {
            reason for item in rejected for reason in item.get("reason_codes", [])
        } | set(final_result.get("rejection_codes", [])))
        included = key in covered
        state = assessment.get("state")
        observed = None
        if final_result.get("coverage_status") == "blocked":
            observed = "POLICY_BLOCK"
        elif final_result.get("rejection_codes"):
            observed = "CLAIM_UNSUPPORTED"
        elif state == "contradictory":
            observed = "CONTRADICTORY_EVIDENCE"
        elif not included:
            observed = "EVIDENCE_INSUFFICIENT"
        traces.append({
            "schema_version": "1", "topic_id": topic_labels[request.topic_id], "facet": facet_labels[request.facet],
            "plan_valid": None, "plan_shape_valid": bool(request.topic_id and request.facet),
            "source_available_in_release": True if included else None,
            "candidate_count": assessment.get("candidate_count", len(candidates)),
            "candidate_ids": candidates, "retrieved_at_k": None,
            "applicability_status": "accepted_by_contract" if included else "not_established",
            "support_relation": None, "observed_support_state": state,
            "composition_included": included, "terminal_guard_executed": True,
            "terminal_guard_passed": included, "displayed": None,
            "primary_failure_reason": None, "observed_failure_reason": observed,
            "secondary_reasons": reasons, "source_pack_version": evidence.get("source_set_version"),
            "independent_annotation": "pending", "clinical_review": "pending",
        })
    return traces
