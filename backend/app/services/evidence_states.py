"""Evidence presentation derived after validation, never a medical accuracy score."""

LABELS = {
    "current_authoritative": "Current authoritative source",
    "source_supported_review_pending": "Source supported — human review pending",
    "preliminary_or_conflicting": "Research finding — preliminary or conflicting evidence",
    "model_unverified": "General model knowledge — not source verified",
    "clinical_assessment_required": "Clinical assessment required",
    "evidence_missing": "Source verification unavailable",
}


def descriptor(state, **fields):
    return {"state": state, "label": LABELS[state],
            "independent_clinical_review": "pending", "currency": "not_verified", **fields}


def annotate(result):
    """Pending review alone does not withhold an admitted educational claim.

    Current-authoritative is reserved until an item-specific version/currency
    verifier exists. A domain, citation type or model flag cannot establish it.
    """
    checked = result.get("status") in {"ok", "partial"} and not result.get("rejection_codes")
    sources = {c.get("chunk_id"): c for c in result.get("citations", [])}
    claims = []
    for index, claim in enumerate(result.get("claims", [])):
        state = "evidence_missing"
        citations = [sources[key] for key in claim.get("citation_ids", []) if key in sources]
        if checked and citations:
            state = "source_supported_review_pending"
            if any(c.get("source_type") in {"unverified_secondary", "retailer_monograph"} for c in citations):
                state = "evidence_missing"
            elif claim.get("text", "").startswith("[Research context:"):
                state = "preliminary_or_conflicting"
        claims.append(descriptor(state, claim_index=index))
    if result.get("status") in {"urgent_guidance", "unsupported_input"} or result.get("route") == "professional_review":
        response = descriptor("clinical_assessment_required")
    elif claims:
        response = descriptor(claims[0]["state"] if len({c["state"] for c in claims}) == 1 else "preliminary_or_conflicting")
    elif result.get("answer_method") == "ollama_model_knowledge":
        response = descriptor("model_unverified")
    else:
        response = descriptor("evidence_missing")
    result["evidence_states"] = {"version": "1", "response": response, "claims": claims}
    return result
