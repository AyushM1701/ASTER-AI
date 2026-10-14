from pathlib import Path

from backend.app.config import Settings
from backend.app.services.answers import AnswerService
from backend.app.services.prepared_evidence import prepared_support
from backend.app.services.question_plan import plan_question
from backend.app.services.teaching import TeachingStore

PACK = Path(__file__).resolve().parents[1] / "artifacts/source-packs/mds-master-necrosis-acquired-v1-2026-10-13"


def test_necrosis_foundation_retains_regulation_and_immune_qualifications():
    settings = Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=PACK,
                        teaching_explanations_sha256="", enable_patient_information=False)
    store = TeachingStore(settings)
    assert not store.error, store.error
    try:
        unit = next(item for item in store.units if item["id"] == "mds-master-necrosis-phenotype-2017")
        assert "passive injury or regulated cell-death programmes" in unit["text"]
        assert "do not necessarily have identical immunogenic effects" in unit["text"]
        assert unit["review_origin"] == "ai_source_inspection" and unit["clinical_review"] is False
        for facet in plan_question("Define necrosis and describe membrane changes and inflammation.", "study").facets:
            assert prepared_support(facet, unit, store.references.id_records, store.metadata, store.review_flags)
        for facet in plan_question("Describe necrosis nuclear changes and histopathology.", "study").facets:
            assert not prepared_support(facet, unit, store.references.id_records, store.metadata, store.review_flags)
        assert all(row.permission_basis["license"] == "CC-BY-4.0" for row in store.records)
        assert all("different immunogenic effects" in row.text or "intrinsic programs can lead to necrotic cell death" in row.text for row in store.records)
    finally:
        store.close()


def test_apoptosis_inflammation_is_qualified_and_source_bound():
    settings = Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=PACK,
                        teaching_explanations_sha256="", enable_patient_information=False)
    store = TeachingStore(settings)
    assert not store.error, store.error
    try:
        response = AnswerService(settings, None, None, None, teaching=store).answer(
            "Explain inflammation associated with apoptosis.", audience="study")
        assert response["claims"] and response["prepared_claim_evidence"]
        assert "not invariably non-inflammatory" in str(response["claims"])
        assert response["evidence_review_origin"] == "ai_source_inspection"
        assert response["clinical_review_status"] == "pending" and response["clinical_review"] is False
    finally:
        store.close()


def test_merged_candidate_retains_the_new_named_source_allowances():
    merged = PACK.with_name("mds-master-evidence-candidate-v5-2026-10-13")
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical",
                                   teaching_release_path=merged, teaching_explanations_sha256=""))
    assert not store.error, store.error
    try:
        unit = next(item for item in store.units if item["id"] == "mds-master-necrosis-phenotype-2017")
        for facet in plan_question("Define necrosis and describe membrane changes and inflammation.", "study").facets:
            assert prepared_support(facet, unit, store.references.id_records, store.metadata, store.review_flags)
    finally:
        store.close()
