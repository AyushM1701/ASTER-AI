from scripts.research_mbbs_curriculum import build_coverage, extract_competencies

HEADER = ["Number", "COMPETENCY\nThe student should be able to", "Domain"]


def test_preserves_wrapped_and_page_continued_competency_descriptions():
    rows, issues = extract_competencies([
        (11, [[HEADER, ["PY 2.9", "Describe hemostasis and\ncoagulation pathways", "K"]]]),
        (12, [[HEADER, ["", "including bleeding disorders; not all tests diagnose disease.", ""],
               ["PY2.10", "Discuss blood groups", "K"]]]),
    ])
    assert rows[0]["code"] == "PY2.9"
    assert rows[0]["subject"] == "Physiology"
    assert rows[0]["text"] == (
        "Describe hemostasis and coagulation pathways including bleeding disorders; "
        "not all tests diagnose disease."
    )
    assert rows[0]["pages"] == [11, 12]
    assert rows[0]["page"] == 11
    assert "\ncoagulation" in rows[0]["raw_text"]
    assert not issues


def test_deduplicates_equal_codes_but_preserves_conflicting_variants_for_review():
    rows, issues = extract_competencies([
        (3, [[HEADER, ["AN1.1", "Describe normal anatomy", "K"]]]),
        (4, [[HEADER, ["AN 1.1", "Describe normal\nanatomy", "K"],
              ["AN1.1", "Describe abnormal anatomy", "K"]]]),
    ])
    assert len(rows) == 1
    assert rows[0]["text"] == "Describe normal anatomy"
    assert rows[0]["occurrences"] == [3, 4]
    assert rows[0]["extraction_status"] == "conflict_requires_review"
    conflict = next(issue for issue in issues if issue["kind"] == "conflicting_duplicate")
    assert conflict["variant_text"] == "Describe abnormal anatomy"


def test_topic_boundaries_do_not_append_orphan_fragments_to_previous_competency():
    rows, issues = extract_competencies([
        (5, [[HEADER, ["AN1.1", "Describe the body", "K"],
              ["Topic 2: Muscles", None, None], ["", "orphan fragment", ""]]]),
        (6, [[HEADER, ["ZZ1.1", "Unknown subject", "K"]]]),
    ])
    assert rows[0]["text"] == "Describe the body"
    assert {issue["kind"] for issue in issues} >= {"orphan_continuation", "unknown_subject"}
    assert rows[1]["subject"] == "Unknown"


def test_headerless_split_table_still_extracts_competencies_with_domain_columns():
    rows, issues = extract_competencies([
        (162, [[HEADER, ["BC1.1", "Describe cells", "K"]]]),
        (163, [[["BC2.1", "Describe enzymes\nand their actions", "K", "KH", "Y"]]]),
    ])
    assert [row["code"] for row in rows] == ["BC1.1", "BC2.1"]
    assert rows[1]["subject"] == "Biochemistry"
    assert rows[1]["text"] == "Describe enzymes and their actions"
    assert not issues


def test_unambiguous_punctuation_variants_normalize_but_ambiguous_codes_keep_text_in_issues():
    rows, issues = extract_competencies([(9, [[HEADER,
        ["PS2.1*", "Describe delirium", "K"],
        ["PA.29.1", "Describe carcinoma", "K"],
        ["FM2:12", "Describe mortuary requirements", "K"],
        ["MI8.", "Discuss syndromic management", "K"],
        ["OR2. 2.9", "Discuss femoral fracture", "K"],
        ["ASS.4", "Discuss regional anesthesia", "K"],
        ["14.1", "Describe safe laboratory practice", "K"],
    ]] )])
    assert [row["code"] for row in rows] == ["PS2.1", "PA29.1", "FM2.12"]
    assert rows[0]["raw_code"] == "PS2.1*"
    malformed = [issue for issue in issues if issue["kind"] == "malformed_code"]
    assert [issue["text"] for issue in malformed] == ["Discuss syndromic management",
                                                     "Discuss femoral fracture",
                                                     "Discuss regional anesthesia",
                                                     "Describe safe laboratory practice"]


def test_blank_only_table_fragment_continues_previous_competency():
    rows, issues = extract_competencies([
        (1, [[HEADER, ["AS11.5", "Demonstrate airway skills including", "S"]]]),
        (2, [[["", "bag-mask ventilation.", "", "", "", "", "", ""]]]),
    ])
    assert rows[0]["text"] == "Demonstrate airway skills including bag-mask ventilation."
    assert rows[0]["pages"] == [1, 2]
    assert not issues


def test_explicit_mapping_never_promotes_keyword_matches_to_verified_coverage():
    competencies = [{"code": "AN1.1", "subject": "Anatomy", "text": "heart"},
                    {"code": "AN1.2", "subject": "Anatomy", "text": "heart"}]
    coverage = build_coverage(competencies, {"AN1.1": ["teaching-heart"]})
    assert coverage["competencies"][0]["status"] == "mapped_material_pending_faculty_review"
    assert coverage["competencies"][1]["status"] == "unmapped_gap"
    assert coverage["subjects"]["Anatomy"]["mapped_competencies"] == 1
    assert coverage["subjects"]["Anatomy"]["faculty_verified_competencies"] is None
    assert coverage["faculty_review"] == "not_performed"


def test_deleted_competency_is_not_an_active_coverage_gap_and_replacement_retains_original():
    from scripts.research_mbbs_curriculum import apply_clarifications

    rows = [{"code": "PS9.2", "subject": "Psychiatry", "text": "deleted description", "raw_text": "deleted description"},
            {"code": "PY9.1", "subject": "Physiology", "text": "old description", "raw_text": "old description"}]
    amended = apply_clarifications(rows, [
        {"code": "PS9.2", "action": "delete", "source_page": 3},
        {"code": "PY9.1", "action": "replace", "text": "new description", "source_page": 3},
    ])
    assert amended[0]["active"] is False
    assert amended[0]["curriculum_status"] == "deleted_by_clarification"
    assert amended[1]["active"] is True
    assert amended[1]["text"] == "new description"
    assert amended[1]["original_text"] == "old description"
    assert amended[1]["clarification"]["source_page"] == 3
    assert [row["code"] for row in build_coverage(amended)["competencies"]] == ["PY9.1"]


def test_cached_table_content_cannot_change_while_retaining_source_pdf_hash(tmp_path, monkeypatch):
    import hashlib
    import json

    import pytest
    from pypdf import PdfWriter

    from scripts import research_mbbs_curriculum as curriculum

    raw = tmp_path / "data/references/mbbs/raw"
    raw.mkdir(parents=True)
    source = raw / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    cache = raw / "curriculum-table-extraction.json"
    cache.write_text(json.dumps({"source_sha256": source_hash, "pages": []}), encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "curriculum_sources": [{"path": "data/references/mbbs/raw/source.pdf", "sha256": source_hash}],
        "table_extraction_sha256": "0" * 64,
        "competency_table_pdf_page_ranges": [[1, 1]], "clarifications": [],
        "published_summary_counts": {}, "source_candidates": [], "limitations": [],
    }), encoding="utf-8")
    monkeypatch.setattr(curriculum, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="Table extraction integrity failed"):
        curriculum.research(config)
