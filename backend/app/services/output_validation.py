"""Common terminal guard: rejected content has no weaker fallback."""

import re

from backend.app.errors import envelope

INSTRUCTIONS = re.compile(
    r"\b(?:take|give|administer|dispense|inject|swallow)\b[^.!?\n]{0,100}"
    r"(?:\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|tablets?|capsules?)\b|\b(?:your child|your mouth|prescribed dos(?:e|age))\b)"
    r"|\b(?:you should take|your diagnosis|you have (?:cancer|pneumonia)|definitely normal|stop taking|increase your dose)\b"
    r"|\b(?:dosage|dose)\s+(?:is|should be|of)\s+\d+"
    r"|\b\d+(?:\.\d+)?\s*(?:mg|ml|tablets?)\s*(?:every|daily|twice|per day|per kg)\b",
    re.I,
)


def facet_coverage(plan, result, source_metadata=None, source_records=None, reviewed_units=(), review_flags=None):
    """Compute requested coverage from validated display text, never model flags."""
    from backend.app.services.evidence_plan import supports_facet, valid_span
    from backend.app.services.prepared_evidence import valid_prepared_mapping

    sources = {c["chunk_id"]: c for c in result.get("citations", [])}
    claims = result.get("claims", [])
    covered, missing = [], []
    conflicts = {(f["request"]["topic_id"], f["request"]["facet"]) for f in result.get("evidence_plan", {}).get("facets", []) if f.get("state") == "contradictory"}
    for facet in plan.facets:
        supported = False
        for index, claim in enumerate(claims):
            axes = result.get("comparison", {}).get("axes", [])
            if facet.facet in plan.comparison_axes or any(axis.get("facet") == facet.facet for axis in axes):
                visible = any(axis.get("facet") == facet.facet and cell.get("topic_id") == facet.topic_id and index in cell.get("claim_indices", []) for axis in axes for cell in axis.get("cells", []))
            elif result.get("structured_answer"):
                visible = any(section.get("topic_id") == facet.topic_id and section.get("facet") == facet.facet and index in section.get("claim_indices", []) for section in result["structured_answer"].get("sections", []))
            else:
                visible = True
            if not visible:
                continue
            prepared_mappings = [m for m in result.get("prepared_claim_evidence", []) if isinstance(m, dict) and m.get("claim_index") == index and m.get("topic_id") == facet.topic_id and m.get("facet") == facet.facet]
            if any(valid_prepared_mapping(m, facet, claim, reviewed_units, sources, source_records,
                                          source_metadata, review_flags) for m in prepared_mappings):
                supported = True
            mappings = [m for m in result.get("claim_evidence", []) if m.get("claim_index") == index and m.get("topic_id") == facet.topic_id and m.get("facet") == facet.facet]
            for key in claim.get("citation_ids", []):
                source = sources.get(key, {})
                if supports_facet(facet, claim.get("text", ""), source.get("section", "")) or reviewed_claim(facet, claim, key, sources, source_metadata, source_records):
                    if "claim_evidence" not in result or any(valid_span(m, claim, sources) for m in mappings):
                        supported = True
        if (facet.topic_id, facet.facet) in conflicts:
            supported = False
        (covered if supported else missing).append(facet.model_dump())
    shape = True
    if plan.task == "compare":
        comparison = result.get("comparison", {})
        shape = bool(comparison.get("axes") or comparison.get("rows"))
    if plan.task in {"viva", "quiz"}:
        shape = bool(result.get("viva") or result.get("practice_item"))
    if plan.task == "fictional_case":
        shape = bool(result.get("structured_answer"))
    if not shape:
        missing = [f.model_dump() for f in plan.facets]
        covered = []
    status = "complete" if covered and not missing else "partial" if covered else "insufficient_evidence"
    if result.get("status") in {"unsupported_input", "urgent_guidance", "quality_rejected"}:
        status = "blocked"
    result.update(coverage_status=status, covered_facets=covered, missing_facets=missing,
                  clinical_review_status="pending", task_completion=status == "complete")
    if result.get("status") in {"ok", "partial"}:
        result["status"] = {"complete": "ok", "partial": "partial"}.get(status, "insufficient_evidence")
    if missing:
        result["unsupported_parts"] = [f["query"] for f in missing]
    if status in {"insufficient_evidence", "blocked"}:
        result.setdefault("unsupported_topics", [plan.original_question])
    return result


def reviewed_claim(facet, claim, key, sources, metadata, records):
    from backend.app.services.reviewed_evidence import reviewed_support

    row = (records or {}).get(key)
    source = sources.get(key, {})
    return bool(row and claim.get("text") == row.text and source.get("excerpt") == row.text
                and all(source.get(field) == getattr(row, field) for field in ("source_id", "snapshot_id", "section", "section_id", "url", "permission_basis"))
                and reviewed_support(facet, row, (metadata or {}).get(key, {})))


def finalize(question, result, reviewed_units=(), question_plan=None, source_metadata=None, review_flags=None, source_records=None, *, paper_context=None):
    from backend.app.services.evidence_states import annotate
    from backend.app.services.facet_diagnostics import trace_facets

    if paper_context is not None:
        from backend.app.services.papers import validate_paper_result

        return annotate(validate_paper_result(question, result, paper_context))
    # Retain stage observations even when the guard removes rejected content.
    original = dict(result)
    checked = _finalize(question, result, reviewed_units, question_plan,
                        source_metadata, review_flags, source_records)
    checked["facet_diagnostics"] = trace_facets(question_plan, original, checked)
    return annotate(checked)


def _finalize(question, result, reviewed_units=(), question_plan=None, source_metadata=None, review_flags=None, source_records=None):
    from backend.app.services.question_plan import plan_question

    plan = question_plan or plan_question(question)
    result = dict(result)
    # These are application-owned labels/surfaces, not model-supplied authority.
    for key in ("provisional_explanation", "evidence_state", "evidence_states"):
        result.pop(key, None)
    result["clinical_review"] = False
    private_identity = (result.get("route") == "private_paper_analysis" or result.get("paper_evidence") or result.get("paper_sections")
                        or any(source.get("source_type") == "private_paper" or str(source.get("url", "")).startswith("aster-private://")
                               or str(source.get("source_id", "")).startswith("paper_") or str(source.get("chunk_id", "")).startswith("paper_chunk_")
                               for source in result.get("citations", [])))
    if private_identity:
        return envelope("insufficient_evidence", result.get("route", "medical_education"),
                        "Private paper excerpts require the current confirmed document context.",
                        rejection_codes=["private_paper_context_required"], task_completion=False,
                        coverage_status="insufficient_evidence",
                        validation={"reference_integrity": "failed", "source_support": "unsupported", "clinical_review": "pending"})
    if result.get("status") not in {"ok", "partial"}:
        if plan.facets:
            result = facet_coverage(plan, result, source_metadata, source_records, reviewed_units, review_flags)
        result.setdefault("task_completion", False)
        result.setdefault("coverage_status", "blocked" if result.get("status") in {"unsupported_input", "urgent_guidance", "quality_rejected"} else "insufficient_evidence")
        if result.get("status") == "error":
            result["outcome"] = "transport_error"
        result.setdefault(
            "validation",
            {
                "reference_integrity": "unknown",
                "source_support": "unsupported",
                "clinical_review": "pending",
            },
        )
        return result
    sources = {c["chunk_id"]: c for c in result.get("citations", [])}
    reasons = []
    from backend.app.services.prepared_evidence import prepared_citation, valid_prepared_mapping

    if result.get("prepared_claim_evidence"):
        citation_ids = []
        for citation in result.get("citations", []):
            key = citation.get("chunk_id")
            actual = (source_records or {}).get(key)
            if not actual or citation != prepared_citation(actual, (review_flags or {}).get(key)) or key in citation_ids:
                reasons.append("source_identity_changed")
            citation_ids.append(key)
    # Provenance belongs to a separate prepared-text channel. A generated
    # pointer must resolve to an actual release unit and an exact request.
    for mapping in result.get("prepared_claim_evidence", []):
        index = mapping.get("claim_index") if isinstance(mapping, dict) else None
        facet = next((f for f in plan.facets if isinstance(mapping, dict)
                      and f.topic_id == mapping.get("topic_id") and f.facet == mapping.get("facet")
                      and f.scope == mapping.get("scope")), None)
        if (type(index) is not int or not 0 <= index < len(result.get("claims", [])) or facet is None
                or not valid_prepared_mapping(mapping, facet, result["claims"][index], reviewed_units,
                                              sources, source_records, source_metadata, review_flags)):
            reasons.append("invalid_prepared_binding")
    if plan.intent == "symptom_information":
        from backend.app.services.patient_information import validate_patient_response

        reasons.extend(validate_patient_response(plan, result, reviewed_units))
    from backend.app.services.evidence_plan import (
        applicable_text,
        source_reasons,
        structural_reasons,
        supports_facet,
        valid_span,
    )
    from backend.app.services.mds_curriculum import has_topic

    for index, claim in enumerate(result.get("claims", [])):
        ids = claim.get("citation_ids", [])
        from types import SimpleNamespace

        prepared_mappings = [m for m in result.get("prepared_claim_evidence", [])
                             if isinstance(m, dict) and m.get("claim_index") == index]
        prepared_bound = bool(prepared_mappings) and all(any(
            valid_prepared_mapping(m, f, claim, reviewed_units, sources, source_records, source_metadata, review_flags)
            for f in plan.facets if f.topic_id == m.get("topic_id") and f.facet == m.get("facet") and f.scope == m.get("scope")
        ) for m in prepared_mappings)
        for key in ids:
            source = sources.get(key, {})
            actual = (source_records or {}).get(key)
            if actual and plan.facets and (source.get("excerpt") != actual.text or any(source.get(field) != getattr(actual, field) for field in ("source_id", "snapshot_id", "section", "section_id", "url", "permission_basis"))):
                reasons.append("source_identity_changed")
            context = (source_metadata or {}).get(key, {})
            source_issues = source_reasons(SimpleNamespace(text=source.get("excerpt", ""), section=source.get("section", "")), context)
            if prepared_bound and isinstance(context, dict) and context.get("runtime_policy") == "explanation_only":
                source_issues = [reason for reason in source_issues if reason != "source_runtime_hold"]
            reasons.extend(source_issues)
            if (review_flags or {}).get(key) and not prepared_bound:
                reasons.append("source_review_hold")
        if not ids or any(key not in sources for key in ids):
            reasons.append("missing_attribution")

        def normalize(text):
            return " ".join(text.casefold().split())

        exact = any(
            normalize(claim["text"]) == normalize(sources[key].get("excerpt", ""))
            for key in ids
            if key in sources
        )
        legacy_prepared = any(
            unit.get("text") == claim["text"] and set(unit.get("citation_ids", [])) == set(ids)
            for unit in reviewed_units
        )
        prepared = prepared_bound or (legacy_prepared and "claim_evidence" not in result and not prepared_mappings)
        mappings = [m for m in result.get("claim_evidence", []) if m.get("claim_index") == index]
        span_supported = bool(mappings) and all(valid_span(m, claim, sources) for m in mappings)
        if mappings and not span_supported:
            reasons.append("invalid_source_span")
        if ids and not exact and not prepared and not span_supported:
            reasons.append("unsupported_claim")
        if plan.facets and plan.intent != "symptom_information":
            topical = any(applicable_text(t, claim["text"], sources.get(key, {}).get("section", "")) for t in plan.canonical_topics for key in ids)
            reviewed_topic = prepared_bound or prepared and any(
                unit.get("text") == claim["text"] and any(has_topic(t, " ".join(unit.get("topics", []))) for t in plan.canonical_topics)
                for unit in reviewed_units
            )
            annotated = any(reviewed_claim(f, claim, key, sources, source_metadata, source_records) for f in plan.facets for key in ids)
            if not topical and not reviewed_topic and not annotated:
                reasons.append("topic_not_in_supporting_text")
            if not prepared and not annotated and not any(supports_facet(f, claim["text"], sources.get(key, {}).get("section", "")) for f in plan.facets for key in ids):
                reasons.append("facet_not_supported")
            reasons.extend(structural_reasons(claim["text"]))
        if INSTRUCTIONS.search(claim["text"]):
            reasons.append("treatment_instruction")
    for key in ("answer", "deeper_explanation"):
        if INSTRUCTIONS.search(result.get(key, "")):
            reasons.append("treatment_instruction")
    # Structured views must select checked claims, never introduce another
    # source-free medical answer surface. User-submitted review text is an
    # explicitly unverified input, not an Aster claim.
    for view, rows_key in (("comparison", "rows"), ("report_explanation", "terms")):
        data = result.get(view)
        if data:
            for row in data.get(rows_key, []):
                index = row.get("claim_index")
                if type(index) is not int or not 0 <= index < len(result.get("claims", [])):
                    reasons.append("invalid_presentation_binding")
            for key in ("scope", "limitations"):
                if INSTRUCTIONS.search(data.get(key, "")):
                    reasons.append("treatment_instruction")
    for section in result.get("structured_answer", {}).get("sections", []):
        if any(type(i) is not int or not 0 <= i < len(result.get("claims", [])) for i in section.get("claim_indices", [])):
            reasons.append("invalid_presentation_binding")
        requested = any(f.topic_id == section.get("topic_id") and f.facet == section.get("facet") for f in plan.facets)
        if not requested:
            reasons.append("invalid_presentation_binding")
        for index in section.get("claim_indices", []):
            if not any(m.get("claim_index") == index and m.get("topic_id") == section.get("topic_id") and m.get("facet") == section.get("facet") for m in [*result.get("claim_evidence", []), *result.get("prepared_claim_evidence", [])] if isinstance(m, dict)):
                reasons.append("invalid_presentation_binding")
    for axis in result.get("comparison", {}).get("axes", []):
        if len(axis.get("cells", [])) != len(plan.canonical_topics):
            reasons.append("invalid_comparison_shape")
        for entity_index, cell in enumerate(axis.get("cells", [])):
            expected_topic = plan.canonical_topics[entity_index] if entity_index < len(plan.canonical_topics) else None
            if cell.get("topic_id") != expected_topic:
                reasons.append("invalid_comparison_shape")
            if any(type(i) is not int or not 0 <= i < len(result.get("claims", [])) for i in cell.get("claim_indices", [])):
                reasons.append("invalid_presentation_binding")
            for index in cell.get("claim_indices", []):
                if not any(m.get("claim_index") == index and m.get("topic_id") == expected_topic and m.get("facet") == axis.get("facet") for m in [*result.get("claim_evidence", []), *result.get("prepared_claim_evidence", [])] if isinstance(m, dict)):
                    reasons.append("invalid_comparison_binding")
    if reasons:
        rejected = envelope(
            "insufficient_evidence",
            result.get("route", "medical_education"),
            "The available answer did not pass the evidence and output checks. Ask about the general concept or clarify the product.",
            rejection_codes=sorted(set(reasons)),
            unsupported_parts=[question],
            task_completion=False,
        )
        # Preserve reviewed transcription state, never unsafe explanation text.
        for key in ("document_id", "revision", "confirmed_fields"):
            if key in result:
                rejected[key] = result[key]
        result = rejected
    if plan.facets:
        result = facet_coverage(plan, result, source_metadata, source_records, reviewed_units, review_flags)
    result["validation"] = {
        "reference_integrity": "failed"
        if "missing_attribution" in reasons
        else "passed"
        if sources
        else "unknown",
        "source_support": "unsupported" if reasons else "not_independently_measured",
        "task_relevance": "failed"
        if any(r.startswith("patient_") or r == "topic_not_in_supporting_text" for r in reasons)
        else "passed_by_bounded_contract"
        if plan.intent == "symptom_information"
        else "passed_by_bounded_facet_contract" if plan.facets and not reasons else "not_independently_measured",
        "automated_evaluation": "not_run",
        "clinical_review": "pending",
        "release_eligibility": "restricted",
    }
    result.setdefault("task_completion", not reasons and result.get("status") == "ok")
    result["outcome"] = {
        "ok": "supported",
        "partial": "partial",
        "unsupported_input": "blocked",
    }.get(result["status"], "insufficient_evidence")
    return result
