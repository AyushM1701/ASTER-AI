"""Facet admission for release-validated prepared text, never inferred tags.

Callers supply TeachingStore.units out of band. Output provenance is only a
pointer into those trusted units; it cannot create a review or a new unit.
"""

import hashlib
import re


def allowed_prepared_hold(unit, row, flag):
    """A source hold may name exact already-reviewed explanations, never quotes."""
    return bool(isinstance(flag, dict)
                and flag.get("runtime_policy") == "explanation_only"
                and flag.get("content_sha256") == row.content_hash()
                and flag.get("clinical_review") is False
                and isinstance(flag.get("reason"), str) and flag["reason"].strip()
                and isinstance(flag.get("allowed_explanation_ids"), list)
                and all(isinstance(key, str) for key in flag["allowed_explanation_ids"])
                and unit.get("id") in flag["allowed_explanation_ids"])


def prepared_citation(row, flag=None):
    """Keep original source coordinates/text and disclose its wording hold."""
    citation = row.citation()
    if (isinstance(flag, dict) and flag.get("runtime_policy") == "explanation_only"
            and isinstance(flag.get("reason"), str) and flag["reason"].strip()):
        citation["source_review_notice"] = flag["reason"]
    return citation


def prepared_mapping(unit, facet, claim_index):
    return {
        "claim_index": claim_index,
        "prepared_id": unit["id"],
        "topic_id": facet.topic_id,
        "facet": facet.facet,
        "scope": facet.scope,
        "prepared_text_sha256": unit["prepared_text_sha256"],
        "source_hashes": dict(unit["source_hashes"]),
    }


def prepared_support(facet, unit, records, metadata=None, review_flags=None):
    """Check an explicit annotation and complete prepared/source identities."""
    from backend.app.services.evidence_plan import source_reasons, structural_reasons
    from backend.app.services.output_validation import INSTRUCTIONS
    from backend.app.services.policy import check_policy
    from backend.app.services.retrieval import permitted_source, phrase_match

    if not isinstance(unit, dict) or not isinstance(records, dict):
        return False
    text = unit.get("text")
    ids, hashes, entries = unit.get("citation_ids"), unit.get("source_hashes"), unit.get("facet_bindings")
    if (not isinstance(unit.get("id"), str) or not unit["id"].strip()
            or not isinstance(text, str) or not text.strip()
            or unit.get("review_status") != "developer_reviewed"
            or not isinstance(unit.get("reviewer"), str) or not unit["reviewer"].strip()
            or unit.get("clinical_review") is not False
            or unit.get("prepared_text_sha256") != hashlib.sha256(text.encode()).hexdigest()
            or not isinstance(ids, list) or not ids or any(not isinstance(k, str) for k in ids)
            or len(ids) != len(set(ids)) or not isinstance(hashes, dict) or set(ids) != set(hashes)
            or not isinstance(entries, list)):
        return False
    expected = {"topic_id": facet.topic_id, "facet": facet.facet, "scope": facet.scope}
    if not any(isinstance(entry, dict) and all(k in entry and entry[k] == v for k, v in expected.items()) for entry in entries):
        return False
    qualifications = unit.get("qualifications", [])
    if (not isinstance(qualifications, list) or any(not isinstance(q, str) or not q.strip()
            or not phrase_match(q, text) for q in qualifications)
            or structural_reasons(text) or check_policy("Explain in general: " + text) or INSTRUCTIONS.search(text)):
        return False
    for key in ids:
        row = records.get(key)
        context = (metadata or {}).get(key, {})
        if row is None:
            return False
        flag = (review_flags or {}).get(key)
        hold_allowed = allowed_prepared_hold(unit, row, flag)
        source_issues = source_reasons(row, context)
        if hold_allowed and isinstance(context, dict) and context.get("runtime_policy") == "explanation_only":
            source_issues = [reason for reason in source_issues if reason != "source_runtime_hold"]
        if (row.source_type != "teaching" or row.clinical_review is not False
                or hashes[key] != row.content_hash() or source_issues or flag and not hold_allowed):
            return False
        basis = row.permission_basis
        raw_hash = basis.get("snapshot_sha256")
        if (not isinstance(raw_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_hash)
                or basis.get("clinical_review") is not False
                or any(not isinstance(basis.get(field), str)
                       for field in ("type", "license", "license_url", "approved_host"))
                or not permitted_source(row.url, {"permission_basis": basis, "raw_sha256": raw_hash})):
            return False
        if context.get("material_type") == "research" or basis.get("material_type") == "research":
            limitations = context.get("limitations")
            valid_limitations = (isinstance(limitations, str) and bool(limitations.strip())) or (
                isinstance(limitations, list) and bool(limitations)
                and all(isinstance(item, str) and bool(item.strip()) for item in limitations))
            if (context.get("material_type") != "research" or not row.source_date
                    or not all(isinstance(context.get(k), str) and context[k].strip()
                               for k in ("study_type", "study_context")) or not valid_limitations
                    or context["study_context"] not in row.text or context["study_context"] not in text):
                return False
    cited = set(ids)
    for key in ids:
        contradictions = (metadata or {}).get(key, {}).get("contradicts", [])
        if (not isinstance(contradictions, list) or any(not isinstance(k, str) for k in contradictions)
                or cited & set(contradictions)):
            return False
    return True


def valid_prepared_mapping(mapping, facet, claim, units, sources, records, metadata=None, review_flags=None):
    """Validate output pointers against actual trusted units and displayed text."""
    if not isinstance(mapping, dict):
        return False
    candidates = [u for u in units if isinstance(u, dict) and u.get("id") == mapping.get("prepared_id")]
    if len(candidates) != 1:
        return False
    unit = candidates[0]
    if (not prepared_support(facet, unit, records, metadata, review_flags)
            or type(mapping.get("claim_index")) is not int
            or mapping != prepared_mapping(unit, facet, mapping["claim_index"])
            or unit.get("text") != claim.get("text")
            or set(unit.get("citation_ids", [])) != set(claim.get("citation_ids", []))
            or len(claim.get("citation_ids", [])) != len(set(claim.get("citation_ids", [])))):
        return False
    return all(sources.get(key) == prepared_citation(records[key], (review_flags or {}).get(key))
               for key in unit["citation_ids"])
