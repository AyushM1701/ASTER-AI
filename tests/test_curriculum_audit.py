"""Assessment workflow tests: completeness is not clinical correctness."""
import csv
import hashlib
import json
from pathlib import Path

import pytest


def api():
    # Missing implementation is a feature failure, not an import/collection error.
    path = Path(__file__).parents[1] / "scripts/curriculum_audit.py"
    assert path.exists(), "Curriculum assessment workflow is not implemented"
    from scripts import curriculum_audit
    return curriculum_audit


def item(code="MDS-F001", kind="theory", programme="MDS"):
    return {"id": code, "programme": programme, "subject": "Oral pathology",
            "title": "Odontogenic cysts", "kind": kind,
            "expected_facets": ["formation", "expansion"],
            "source": {"url": "https://dciindia.gov.in/syllabus.pdf", "pdf_pages": [198]},
            "active": True}


def test_blueprint_covers_each_active_item_with_multiple_prompts_and_no_scores():
    result = api().build_blueprint([item(), item("P1", "practical"),
                                   dict(item("deleted"), active=False)])
    assert len(result["cases"]) == 6
    assert {x["curriculum_id"] for x in result["cases"]} == {"MDS-F001", "P1"}
    assert len({x["question"] for x in result["cases"]}) == 6
    assert all(x["faculty_accuracy"] is None and x["reference_agreement"] is None
               for x in result["cases"])
    practical = [x for x in result["cases"] if x["curriculum_id"] == "P1"]
    assert all(x["practical_performance_assessable"] is False for x in practical)
    assert practical[0]["expected_facets"] == ["formation", "expansion"]


def test_blinded_pack_binds_answers_and_drops_model_and_patient_metadata(tmp_path):
    cases = api().build_blueprint([item()])["cases"][:1]
    answer = [{"case_id": cases[0]["case_id"], "question": cases[0]["question"],
               "answer": "A written explanation.", "model": "secret-model",
               "patient_name": "must never be copied", "faculty_accuracy": 100}]
    result = api().create_faculty_pack(cases, answer, tmp_path)
    rows = json.loads((tmp_path / "blinded-cases.json").read_text())
    assert len(rows) == 1 and rows[0]["answer"] == "A written explanation."
    assert "secret-model" not in json.dumps(rows) and "must never" not in json.dumps(rows)
    assert "faculty_accuracy" not in rows[0]
    assert rows[0]["answer_sha256"] == hashlib.sha256(b"A written explanation.").hexdigest()
    scores = list(csv.DictReader((tmp_path / "scores-blank.csv").open()))
    assert scores[0]["accuracy"] == "" and scores[0]["review_status"] == "pending"
    assert result["qualified_human_accuracy"] is None


def test_pack_rejects_unmatched_or_duplicate_answers_instead_of_silently_scoring(tmp_path):
    cases = api().build_blueprint([item()])["cases"][:1]
    with pytest.raises(ValueError, match="unknown"):
        api().create_faculty_pack(cases, [{"case_id": "wrong", "answer": "a"}], tmp_path)
    a = {"case_id": cases[0]["case_id"], "answer": "a"}
    with pytest.raises(ValueError, match="duplicate"):
        api().create_faculty_pack(cases, [a, a], tmp_path)


def completed_row(blinded):
    return {"review_id": blinded["review_id"], "answer_sha256": blinded["answer_sha256"],
            "accuracy": "4", "coverage": "3", "reference_agreement": "4", "safety": "4",
            "review_status": "completed", "reviewer_name": "Dr Example Human",
            "qualification": "MDS Oral Pathology", "institution": "Example Dental College",
            "reviewer_registration": "faculty-record-42", "credential_evidence": "verified-staff-directory",
            "review_date": "2026-10-09", "assessment_origin": "human_entered",
            "attestation": "I personally reviewed this answer and entered these assessments.",
            "reference_source": "Textbook chapter 3, edition 2024", "reference_locator": "pages 20-25",
            "rationale": "Content checked independently against the cited chapter."}


def test_import_requires_actual_completed_human_assessment_and_pinned_answer(tmp_path):
    cases = api().build_blueprint([item()])["cases"][:1]
    api().create_faculty_pack(cases, [{"case_id": cases[0]["case_id"], "answer": "a"}], tmp_path)
    blinded = json.loads((tmp_path / "blinded-cases.json").read_text())[0]
    row = completed_row(blinded)
    result = api().import_scores([row], [blinded])
    assert result["qualified_human_accuracy"] is None  # credentials require independent verification
    assert result["human_attested_accuracy_mean"] == 4
    assert result["credential_verification"] == "external_verification_pending"
    for patch in ({"review_status": "pending"}, {"accuracy": ""},
                  {"accuracy": "NaN"}, {"accuracy": "5"}, {"answer_sha256": "0" * 64},
                  {"assessment_origin": "model_generated"}, {"reviewer_name": "AI assistant"},
                  {"attestation": "simulated human review"}, {"qualification": "self-claimed faculty"},
                  {"reference_source": ""}, {"review_date": "not-a-date"}):
        with pytest.raises(ValueError):
            api().import_scores([dict(row, **patch)], [blinded])


def test_import_does_not_double_count_reviews_or_accept_tampered_answer(tmp_path):
    cases = api().build_blueprint([item()])["cases"][:1]
    api().create_faculty_pack(cases, [{"case_id": cases[0]["case_id"], "answer": "a"}], tmp_path)
    blinded = json.loads((tmp_path / "blinded-cases.json").read_text())[0]
    row = completed_row(blinded)
    with pytest.raises(ValueError, match="duplicate"):
        api().import_scores([row, row], [blinded])
    with pytest.raises(ValueError, match="integrity"):
        api().import_scores([row], [dict(blinded, answer="modified")])


def test_pack_preserves_real_claims_and_qualifications_without_automatic_scores(tmp_path):
    cases = api().build_blueprint([item()])["cases"][:1]
    response = {"status": "ok", "claims": [{"text": "This may occur in some patients.", "citation_ids": ["c"]}],
                "citations": [{"chunk_id": "c", "url": "https://example.org/reference", "section": "Definition",
                               "excerpt": "This may occur in some patients.", "snapshot_id": "hidden-release"}],
                "teaching_version": "hidden-release", "clinical_review": False}
    api().create_faculty_pack(cases, [{"case_id": cases[0]["case_id"], "answer": response}], tmp_path)
    row = json.loads((tmp_path / "blinded-cases.json").read_text())[0]
    assert "may occur in some" in row["answer"]
    assert row["citations"][0]["url"] == "https://example.org/reference"
    assert "hidden-release" not in json.dumps(row)
    assert "evaluation" not in row


def test_abstention_cannot_receive_an_invented_medical_accuracy_score(tmp_path):
    cases = api().build_blueprint([item()])["cases"][:1]
    api().create_faculty_pack(cases, [{"case_id": cases[0]["case_id"], "answer": None}], tmp_path)
    row = json.loads((tmp_path / "blinded-cases.json").read_text())[0]
    assert row["written_response_available"] is False
    score = completed_row(row)
    with pytest.raises(ValueError, match="abstention"):
        api().import_scores([score], [row])
    score.update(accuracy="", reference_agreement="", coverage="0")
    result = api().import_scores([score], [row])
    assert result["human_attested_accuracy_mean"] is None
    assert result["accuracy_assessed_answers"] == 0


def test_pack_does_not_hide_the_actual_response_uncertainty_from_reviewers(tmp_path):
    cases = api().build_blueprint([item()])["cases"][:1]
    response = {"status": "ok", "claims": [{"text": "Supported concept only.", "citation_ids": ["c"]}],
                "warnings": ["No supported material for the second topic."],
                "limitations": ["The fictional case reasoning remains unverified."]}
    api().create_faculty_pack(cases, [{"case_id": cases[0]["case_id"], "answer": response}], tmp_path)
    row = json.loads((tmp_path / "blinded-cases.json").read_text())[0]
    assert "No supported material for the second topic." in row["answer"]
    assert "fictional case reasoning remains unverified" in row["answer"]


def test_mbbs_table_domains_survive_normalization_and_deleted_rows_stay_in_inventory():
    rows = [{"code": "AN1.1", "text": "Demonstrate normal position", "subject": "Anatomy",
             "pages": [108], "active": True},
            {"code": "PS9.2", "text": "deleted", "subject": "Psychiatry",
             "pages": [355], "active": False}]
    tables = {"source_sha256": "pdf-hash", "pages": [[108, [[["AN1.1",
                "Demonstrate normal position", "K/S", "SH", "Y", "Demo", "OSCE", "1"]]]]]}
    items = api().normalize_mbbs(rows, tables, {"url": "https://nmc.org.in/curriculum.pdf"})
    assert len(items) == 2 and items[1]["active"] is False
    assert items[0]["domain"] == "K/S" and items[0]["level"] == "SH"
    assert items[0]["kind"] == "practical"
    assert len(api().build_blueprint(items)["cases"]) == 3


def test_null_spacer_columns_do_not_misclassify_observed_mbbs_skills_as_theory():
    rows = [{"code": "GM28.9", "text": "Perform systematic examination",
             "subject": "General Medicine", "pages": [323]}]
    tables = {"pages": [[323, [[["GM28.9", "Perform systematic examination",
                None, "K S", "KH SH", "Y", "Bedside clinic", "OSCE", ""]]]]]}
    result = api().normalize_mbbs(rows, tables, {})[0]
    assert result["domain"] == "K S"
    assert result["level"] == "KH SH"
    assert result["kind"] == "practical"
    assert result["assessment_method"] == "OSCE"


def test_pinned_original_photo_register_cannot_be_changed_without_invalidating_inventory(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "data/references/mbbs/raw").mkdir(parents=True)
    (tmp_path / "configs/mds_syllabus.json").write_text('{"topics": []}')
    config = {"sources": [], "items": [], "mbbs_register_sha256": hashlib.sha256(b"").hexdigest(),
              "photographed_topics_sha256": "0" * 64}
    (tmp_path / "configs/mds_full_curriculum.json").write_text(json.dumps(config))
    tables = tmp_path / "data/references/mbbs/raw/curriculum-table-extraction.json"
    tables.write_text('{"pages": []}')
    (tmp_path / "data/references/mbbs/raw/curriculum-competencies.jsonl").write_text("")
    (tmp_path / "configs/mbbs_curriculum.json").write_text(json.dumps({"curriculum_sources": [{
        "path": "configs/mds_syllabus.json", "sha256": hashlib.sha256(b'{"topics": []}').hexdigest()}],
        "table_extraction_sha256": hashlib.sha256(tables.read_bytes()).hexdigest()}))
    with pytest.raises(ValueError, match="photograph"):
        api().load_inventory(tmp_path)
