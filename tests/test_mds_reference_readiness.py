"""Read-only preflight tests; not medical verification."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_mds_reference_readiness import PACK, BANK, audit, safe_pack_file


def fixture(root):
    p = root / PACK
    p.mkdir(parents=True)
    blobs = {
        "records.jsonl": b'{"chunk_id":"c1","source_id":"s1"}\n',
        "sources.yaml": b'sources:\n  - source_id: s1\n',
    }
    for name, data in blobs.items():
        (p / name).write_bytes(data)
    (p / "manifest.json").write_text(json.dumps({
        "version": "fixture", "records": 1, "sources": 1,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in blobs.items()},
        "clinical_review": False, "faculty_review": "pending",
    }))
    docs = root / "data/references/mds/raw"
    docs.mkdir(parents=True)
    (docs / "PMCX.xml").write_text("<article/>")
    (docs / "PMCX.license.xml").write_text(
        '<license>https://creativecommons.org/licenses/by/4.0/</license>')
    cfg = root / "configs"
    cfg.mkdir()
    (cfg / "all_mds_topics.json").write_text(json.dumps({
        "specialties": [{"id": str(i), "topics": [{"id": str(j)} for j in range(14)]}
                        for i in range(9)]}))
    (cfg / "teaching.env").write_text(
        "TEACHING_RELEASE_PATH=data/missing/release\nTEACHING_INDEX_PATH=data/missing/index\n")
    bank = root / BANK
    bank.mkdir(parents=True)
    row = {"case_id":"case-1", "task_shape":"comparison", "specialties":["oral_pathology"],
           "turns":[{"question":"Compare X and Y in children"}],
           "turn_content_contracts":[[{"topic_id":"x","facet":"definition"},
                                      {"topic_id":"y","facet":"limitations","scope":"children"}]]}
    (bank / "supplied.jsonl").write_text(json.dumps(row)+"\n")
    (bank / "variations.jsonl").write_text("")
    return p, docs


def test_read_only_facet_and_scope_preservation(tmp_path):
    fixture(tmp_path)
    before = {str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in tmp_path.rglob("*") if p.is_file()}
    report, queue = audit(tmp_path)
    after = {str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert report["eligible_for_activation"] is False
    assert report["candidate_records_declared"] == 1
    assert report["raw_mds_article_xml_files"] == 1
    assert [q["facet"] for q in queue] == ["definition", "limitations"]
    assert queue[-1]["scope"] == "children"
    assert not queue[-1]["exact_passage_id"]
    assert "independent_clinical_review_not_verified" in report["findings"]


def test_checksum_mismatch_blocks(tmp_path):
    pack, _ = fixture(tmp_path)
    (pack / "records.jsonl").write_text('{"chunk_id":"tampered","source_id":"s1"}\n')
    report, _ = audit(tmp_path)
    assert "pack_checksum_missing_or_mismatch:records.jsonl" in report["findings"]
    assert not report["eligible_for_activation"]


def test_missing_license_snapshot_blocks(tmp_path):
    _, docs = fixture(tmp_path)
    (docs / "PMCX.license.xml").unlink()
    report, _ = audit(tmp_path)
    assert "research_source_license_snapshots_missing_or_invalid" in report["findings"]


@pytest.mark.parametrize("name", ["../secret", "nested/file", "..", "/absolute"])
def test_unsafe_pack_file(name, tmp_path):
    with pytest.raises(ValueError):
        safe_pack_file(tmp_path, name)
