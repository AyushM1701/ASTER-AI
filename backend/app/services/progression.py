"""Progressive teaching preserves complete claims and their provenance."""

import re


def asks_for_depth(question):
    return bool(re.search(r"^(?:go deeper|(?:now )?explain .+ (?:in .*detail|without repeating))|\bwithout repeating\b", question.strip(), re.I))


def remove_previous_claims(result, history):
    """Omit exact repeats only; never trim a qualification from a new claim."""
    previous = history[-1].get("response", {}) if history else {}
    old = {c.get("text") for c in previous.get("claims", [])}
    claims = result.get("claims", [])
    retained = [i for i, c in enumerate(claims) if c.get("text") not in old]
    if len(retained) == len(claims):
        return result
    indices = {old_index: new_index for new_index, old_index in enumerate(retained)}
    result["claims"] = [claims[i] for i in retained]
    for field in ("claim_evidence", "prepared_claim_evidence"):
        result[field] = [{**m, "claim_index": indices[m["claim_index"]]} for m in result.get(field, []) if m.get("claim_index") in indices]
    for section in result.get("structured_answer", {}).get("sections", []):
        section["claim_indices"] = [indices[i] for i in section["claim_indices"] if i in indices]
        if not section["claim_indices"] and section["state"] != "contradictory":
            section["state"] = "missing"
    for axis in result.get("comparison", {}).get("axes", []):
        for cell in axis["cells"]:
            cell["claim_indices"] = [indices[i] for i in cell["claim_indices"] if i in indices]
    used = {key for claim in result["claims"] for key in claim.get("citation_ids", [])}
    result["citations"] = [c for c in result.get("citations", []) if c["chunk_id"] in used]
    result.setdefault("limitations", []).append("Previously displayed whole explanations were omitted. New source units retain their qualifications and may share necessary context.")
    result["followup_operation"] = "deeper"
    return result
