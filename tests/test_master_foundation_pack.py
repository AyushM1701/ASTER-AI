import hashlib
from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.services.evidence_plan import build_evidence_plan
from backend.app.services.prepared_evidence import prepared_support
from backend.app.services.question_plan import plan_question
from backend.app.services.teaching import TeachingStore

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "artifacts/source-packs/mds-master-normal-epithelium-acquired-v1-2026-10-13"


@pytest.mark.local  # needs licensed source packs that are not committed
def test_acquired_parent_stays_held_and_only_named_prepared_facets_are_eligible():
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical",
                                   teaching_release_path=PACK, teaching_explanations_sha256=""))
    assert not store.error, store.error
    try:
        plan = plan_question("Explain oral epithelium layers and functions.", "study")
        evidence, _ = build_evidence_plan(plan, store, None)
        assert all(facet.state == "missing" for facet in evidence.facets)
        assert any("source_review_hold" in row["reason_codes"] for row in evidence.rejected)
        unit = store.units[0]
        assert all(prepared_support(facet, unit, store.references.id_records, store.metadata, store.review_flags) for facet in plan.facets)
        assert unit["review_origin"] == "ai_source_inspection" and unit["clinical_review"] is False
        unrelated = plan_question("Explain oral epithelium differential diagnosis.", "study")
        assert all(not prepared_support(facet, unit, store.references.id_records, store.metadata, store.review_flags) for facet in unrelated.facets)
    finally:
        store.close()


@pytest.mark.local  # needs licensed source packs that are not committed
def test_source_binding_retains_region_qualifier_and_article_license_identity():
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical",
                                   teaching_release_path=PACK, teaching_explanations_sha256=""))
    assert not store.error, store.error
    try:
        row, unit = store.records[0], store.units[0]
        assert "5-40 days depending on the region" in row.text
        assert "5–40 days depending on the region" in unit["text"]
        assert "not a uniform turnover rate" in unit["text"]
        assert unit["source_hashes"] == {row.chunk_id: row.content_hash()}
        assert unit["prepared_text_sha256"] == hashlib.sha256(unit["text"].encode()).hexdigest()
        assert row.permission_basis["license"] == "CC-BY-4.0"
        assert store.metadata[row.chunk_id]["parent_article_version"] == "PMC5701542.1"
    finally:
        store.close()


@pytest.mark.local  # needs licensed source packs that are not committed
def test_prepared_response_discloses_ai_inspection_without_human_review_claim():
    from backend.app.services.answers import AnswerService

    settings = Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=PACK,
                        teaching_explanations_sha256="", enable_patient_information=False)
    store = TeachingStore(settings)
    assert not store.error, store.error
    try:
        response = AnswerService(settings, None, None, None, teaching=store).answer(
            "Explain oral epithelium layers and functions.", audience="study")
        assert response["claims"]
        assert response["evidence_review_origin"] == "ai_source_inspection"
        assert response["clinical_review_status"] == "pending"
        assert not any("have developer review" in text for text in response["limitations"])
    finally:
        store.close()
