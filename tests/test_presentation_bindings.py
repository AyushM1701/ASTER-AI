from backend.app.services.output_validation import finalize


def base(**extra):
    return dict(
        status="ok",
        route="medical_education",
        claims=[{"text": "Bound source text.", "citation_ids": ["s"]}],
        citations=[{"chunk_id": "s", "excerpt": "Bound source text."}],
        **extra,
    )


def test_structured_presentation_cannot_reference_missing_claim():
    result = finalize(
        "Compare concepts",
        base(
            comparison={"scope": "Basic comparison.", "rows": [{"topic": "A", "claim_index": 99}]}
        ),
    )
    assert result["status"] == "insufficient_evidence"


def test_structured_presentation_cannot_carry_treatment_instruction():
    result = finalize(
        "Explain this report: Hb: 8",
        base(
            report_explanation={
                "scope": "terminology_only",
                "terms": [{"label": "Hb", "claim_index": 0}],
                "limitations": "Take 50 mg daily.",
            }
        ),
    )
    assert result["status"] == "insufficient_evidence"
