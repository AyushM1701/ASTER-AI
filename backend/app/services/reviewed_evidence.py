"""Explicit review of complete source units, including context and analogies.

``metadata.reviewed_facet_bindings`` is a list of human-authored annotations:
review_status=developer_reviewed, named reviewer, clinical_review=False,
qualifications_retained=True and retained_qualifications (exact source phrases).
Each entry binds topic_id/facet/scope, source_id/chunk_id/snapshot_id/section/
section_id, start=0/end=len(text), the complete text_sha256, record_sha256 and
source_sha256 (the raw snapshot hash in the actual source's permission basis).
``ai_inspected_facet_bindings`` is a separate development-source inspection
channel: source_inspected status, ai_source_inspection origin, named reviewer,
support_rationale and qualification_note are mandatory. It uses exactly the same
source integrity and whole-unit checks. It is not a human or clinical review.
No annotations are inferred or generated here. Callers must use admitted,
integrity-checked source records and metadata. This verifies the review binding,
not biomedical correctness; independent qualified clinical review stays pending.
"""

import hashlib
import re

from backend.app.services.retrieval import permitted_source


def reviewed_support(facet, row, metadata):
    """Admit a whole unit only for its explicitly reviewed facet and exact scope."""
    # Lazy imports avoid a cycle when evidence_plan uses this bounded exception.
    from backend.app.services.evidence_plan import source_reasons
    from backend.app.services.output_validation import INSTRUCTIONS
    from backend.app.services.policy import check_policy

    if not isinstance(metadata, dict):
        return False
    human = metadata.get("reviewed_facet_bindings", [])
    inspected = metadata.get("ai_inspected_facet_bindings", [])
    if not isinstance(human, list) or not isinstance(inspected, list) or row.clinical_review is not False:
        return False
    entries = [(entry, False) for entry in human] + [(entry, True) for entry in inspected]
    if any(metadata.get(field) is not None and not isinstance(metadata[field], str)
           for field in ("retraction_status", "review_state", "extraction_quality")):
        return False
    if (source_reasons(row, metadata) or metadata.get("runtime_policy") == "exclude"
            or check_policy("Explain in general: " + row.text) or INSTRUCTIONS.search(row.text)):
        return False
    basis = row.permission_basis
    raw_hash = basis.get("snapshot_sha256")
    if not isinstance(raw_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", raw_hash):
        return False
    if (basis.get("clinical_review") is not False or any(
            not isinstance(basis.get(field), str)
            for field in ("type", "license", "license_url", "approved_host"))):
        return False
    if not permitted_source(row.url, {"permission_basis": basis, "raw_sha256": raw_hash}):
        return False
    binding = {
        "topic_id": facet.topic_id,
        "facet": facet.facet,
        "scope": facet.scope,
        "chunk_id": row.chunk_id,
        "source_id": row.source_id,
        "snapshot_id": row.snapshot_id,
        "section": row.section,
        "section_id": row.section_id,
        "text_sha256": hashlib.sha256(row.text.encode()).hexdigest(),
        "record_sha256": row.content_hash(),
        "source_sha256": raw_hash,
    }
    for entry, ai_inspected in entries:
        if not isinstance(entry, dict):
            continue
        if not ai_inspected and entry.get("review_origin") == "ai_source_inspection":
            continue
        if ai_inspected and (entry.get("review_origin") != "ai_source_inspection" or any(
                not isinstance(entry.get(field), str) or not entry[field].strip()
                for field in ("support_rationale", "qualification_note"))):
            continue
        if (entry.get("review_status") != ("source_inspected" if ai_inspected else "developer_reviewed")
                or not isinstance(entry.get("reviewer"), str) or not entry["reviewer"].strip()
                or entry.get("clinical_review") is not False
                or entry.get("qualifications_retained") is not True):
            continue
        if any(key not in entry or entry[key] != value for key, value in binding.items()):
            continue
        if (type(entry.get("start")) is not int or entry["start"] != 0
                or type(entry.get("end")) is not int or entry["end"] != len(row.text)):
            continue
        qualifications = entry.get("retained_qualifications")
        if not isinstance(qualifications, list) or any(
            not isinstance(phrase, str) or not phrase.strip() or phrase not in row.text
            for phrase in qualifications
        ):
            continue
        return True
    return False
