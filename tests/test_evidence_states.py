from backend.app.errors import envelope
from backend.app.services.output_validation import finalize


def test_exact_source_claim_is_pending_review_not_current_or_clinically_verified():
    body = "Anemia can result from blood loss."
    result = finalize("Explain anemia", envelope(claims=[{"text": body, "citation_ids": ["c"]}],
        citations=[{"chunk_id": "c", "excerpt": body, "source_type": "education", "section": "Causes", "url": "https://medlineplus.gov/anemia.html"}]))
    assert result["evidence_states"]["claims"][0]["state"] == "source_supported_review_pending"
    assert result["evidence_states"]["claims"][0]["independent_clinical_review"] == "pending"
    assert result["evidence_states"]["claims"][0]["currency"] == "not_verified"


def test_safety_route_has_clinical_assessment_state():
    result = finalize("Diagnose me", envelope("unsupported_input", "professional_review"))
    assert result["evidence_states"]["response"]["state"] == "clinical_assessment_required"


def test_payload_cannot_declare_current_guideline_by_citation_type():
    body = "Anemia can result from blood loss."
    result = finalize("Explain anemia", envelope(claims=[{"text": body, "citation_ids": ["c"]}],
        citations=[{"chunk_id": "c", "excerpt": body, "source_type": "guideline", "section": "Causes",
                    "current": True, "clinical_review": True, "url": "https://medlineplus.gov/anemia.html"}]))
    assert result["evidence_states"]["claims"][0]["state"] != "current_authoritative"
