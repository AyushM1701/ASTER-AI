"""Readable facet/cell layout from checked source units, no model-memory facts."""

from backend.app.errors import envelope
from backend.app.services.evidence_plan import span_for
from backend.app.services.mds_curriculum import topic_name


def compose(plan, evidence, records, max_chars=18000, prepared_units=(), source_metadata=None, review_flags=None):
    # Marks constrain the source-unit budget, not an invented scoring rubric.
    # Whole units retain qualifications; an over-budget unit is withheld and
    # coverage remains partial rather than truncating its medical wording.
    if plan.marks is not None:
        max_chars = min(max_chars, max(1200, plan.marks * 600))
    from backend.app.services.prepared_evidence import (
        prepared_citation,
        prepared_mapping,
        prepared_support,
    )

    claims, bindings, indexes, sections, prepared_bindings = [], [], {}, [], []
    used_chars = 0
    for facet in evidence.facets:
        indices = []
        if facet.state != "contradictory":
            for unit in prepared_units:
                if not prepared_support(facet.request, unit, records, source_metadata, review_flags):
                    continue
                key = ("prepared", unit["id"])
                if key not in indexes:
                    if len(claims) >= 24 or used_chars + len(unit["text"]) > max_chars:
                        continue
                    indexes[key] = len(claims)
                    claims.append({"text": unit["text"], "citation_ids": list(unit["citation_ids"])})
                    used_chars += len(unit["text"])
                index = indexes[key]
                indices.append(index)
                prepared_bindings.append(prepared_mapping(unit, facet.request, index))
                # One complete prepared explanation is sufficient for this
                # facet; do not append the original paragraphs beneath it.
                break
        if facet.state == "supported" and not indices:
            for key in facet.chunk_ids:
                row = records[key]
                if key not in indexes:
                    if len(claims) >= 24 or used_chars + len(row.text) > max_chars:
                        continue
                    indexes[key] = len(claims)
                    claims.append({"text": row.text, "citation_ids": [key]})
                    used_chars += len(row.text)
                index = indexes[key]
                indices.append(index)
                bindings.append({"claim_index": index, "topic_id": facet.request.topic_id,
                                 "facet": facet.request.facet, "span": span_for(row)})
        sections.append({"topic_id": facet.request.topic_id, "facet": facet.request.facet,
                         "heading": topic_name(facet.request.topic_id) + " — " + facet.request.facet.replace("_", " "),
                         "claim_indices": indices, "state": "supported" if indices else "contradictory" if facet.state == "contradictory" else "missing"})
    used = {key for claim in claims for key in claim["citation_ids"]}
    result = envelope(
        "ok" if claims else "insufficient_evidence", "medical_education",
        "Source-supported sections; missing evidence is identified below." if claims else "No applicable evidence supports the requested facets in the installed library.",
        claims=claims, citations=[prepared_citation(records[key], (review_flags or {}).get(key)) for key in sorted(used)],
        answer_method="facet_bound_extraction", question_plan=plan.model_dump(),
        evidence_plan=evidence.model_dump(), claim_evidence=bindings,
        structured_answer={"task": plan.task, "sections": sections},
        clinical_review=False, clinical_review_status="pending",
        teaching_version=evidence.source_set_version,
        limitations=["Extracted source units preserve qualifications; deterministic facet checks do not establish medical correctness.", "Independent qualified clinical review is pending."],
        composition_budget={"requested_marks": plan.marks, "max_source_characters": max_chars, "used_source_characters": used_chars},
    )
    if prepared_bindings:
        result["prepared_claim_evidence"] = prepared_bindings
        result["answer_method"] = "facet_bound_prepared_explanation"
        used_prepared = {mapping["prepared_id"] for mapping in prepared_bindings}
        origins = set()
        for unit in prepared_units:
            if unit.get("id") not in used_prepared:
                continue
            facet_review = unit.get("facet_review")
            origin = unit.get("review_origin") or (facet_review.get("review_origin") if isinstance(facet_review, dict) else None)
            origins.add("ai_source_inspection" if origin == "ai_source_inspection" else "not_recorded")
        result["prepared_review_origins"] = sorted(origins)
        if "ai_source_inspection" in origins:
            result["evidence_review_origin"] = "ai_source_inspection"
        result["limitations"].append("Recorded paired-text review can include AI source inspection. Independent qualified human review remains pending.")
    if plan.task == "compare":
        result["comparison"] = {
            "entities": [topic_name(t) for t in plan.canonical_topics],
            "scope": "Each cell contains applicable source text or an explicit evidence gap.",
            "rows": [],  # legacy basic-comparison adapter
            "axes": [{"facet": axis, "label": axis.replace("_", " "),
                      "cells": [{"topic_id": t, "claim_indices": next((s["claim_indices"] for s in sections if s["topic_id"] == t and s["facet"] == axis), [])} for t in plan.canonical_topics]}
                     for axis in plan.comparison_axes],
        }
    if any(f.state == "contradictory" for f in evidence.facets):
        result["warnings"].append("Conflicting sources were withheld for the indicated facets; review the originals before reconciling them.")
    if plan.task == "fictional_case":
        result["warnings"].append("Fictional educational reasoning only. The evidence does not establish a definitive diagnosis for a person.")
    return result
