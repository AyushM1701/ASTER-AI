"""Synthetic nonmedical adapter mechanics; never authoritative source approval."""
import importlib.util
import json

import pytest


def adapter():
    assert importlib.util.find_spec("scripts.stage_mds_pack") is not None, "Reviewed staging adapter is missing"
    from scripts import stage_mds_pack
    return stage_mds_pack


def fixture(tmp_path, text="This is a nonmedical synthetic pipeline fixture demonstrating exact source coordinates for testing."):
    import hashlib
    root = tmp_path / "collector"
    for folder in ("manifests", "rag_chunks", "extracted", "rights_evidence"):
        (root / folder).mkdir(parents=True)
    doc = {"id": "fixture-v1", "title": "Synthetic engineering fixture", "version": "v1", "version_family_id": "family-one",
           "canonical_url": "https://europepmc.org/articles/PMC0000000", "publication_date": "2026-01-01",
           "retrieved_at": "2026-10-11T00:00:00Z", "license": "CC-BY-4.0", "license_url": "http://creativecommons.org/licenses/by/4.0/",
           "raw_sha256": "a" * 64, "stored_document_path": "extracted/retained.xml", "extracted_path": "extracted/doc.json",
           "rights_evidence_path": "rights_evidence/doc.json", "quality_pass": True, "quality_flags": ["clinical_appraisal_pending"],
           "status": "STAGED", "split": "training_candidate", "duplicate_of": None, "source_set_version": "fixture-staged",
           "attribution": "Synthetic fixture only; no medical claims", "exclusions": []}
    (root / doc["stored_document_path"]).write_bytes(b"<fixture>nonmedical</fixture>")
    extracted = {"id": doc["id"], "sections": [{"coordinate": "/article/body/sec[1]/p[1]", "heading": ["Fixture"], "text": text, "page": None}]}
    (root / doc["extracted_path"]).write_text(json.dumps(extracted), encoding="utf-8")
    rights = {"article_sha256": doc["raw_sha256"], "source_url": doc["canonical_url"], "license": doc["license"],
              "license_url": doc["license_url"], "exact_notice": "Synthetic fixture license mechanics only", "attribution": doc["attribution"], "omitted_assets": []}
    (root / doc["rights_evidence_path"]).write_text(json.dumps(rights), encoding="utf-8")
    for field, path in (("stored_sha256", doc["stored_document_path"]), ("extracted_sha256", doc["extracted_path"])):
        doc[field] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    chunk = {"chunk_id": "collector:chunk", "document_id": doc["id"], "version_family_id": doc["version_family_id"],
             "section_id": extracted["sections"][0]["coordinate"], "coordinate": extracted["sections"][0]["coordinate"],
             "section": "Fixture", "heading_hierarchy": ["Fixture"], "source_char_start": 0, "source_char_end": len(text), "text": text,
             "page": None, "source_url": doc["canonical_url"], "license": doc["license"], "status": "STAGED", "split": doc["split"]}
    save_rows(root, doc, [chunk])
    return root, doc, chunk


def save_rows(root, doc, chunks):
    (root / "manifests/catalogue.jsonl").write_text(json.dumps(doc) + "\n", encoding="utf-8")
    (root / "rag_chunks/staged_rag.jsonl").write_text("\n".join(json.dumps(c) for c in chunks) + "\n", encoding="utf-8")


def reviewed(root):
    a = adapter()
    value = a.review_template(root)
    value.update(reviewer_name="Test-only Human", reviewer_institution="Synthetic fixture", assessment_origin="human_entered",
                 review_date="2026-10-11", attestation=a.ATTESTATION)
    for row in value["documents"]:
        row.update(publisher="Synthetic fixture publisher", study_type="nonmedical_fixture", study_context="Synthetic nonmedical engineering study context.",
                   population_context="No people or patients", limitations=["Test only; no medical evidence"], topic_names=["fixture"], keywords=["fixture"],
                   rights_confirmed=True, extraction_confirmed=True, editorial_confirmed=True, source_review_confirmed=True,
                   editorial_status="not_retracted_not_superseded", editorial_checked_date="2026-10-11", editorial_reference_url="https://europepmc.org/articles/PMC0000000")
    return value


def test_reviewed_pack_loads_existing_teaching_contract(tmp_path):
    from backend.app.config import Settings
    from backend.app.services.teaching import TeachingStore
    root, _, _ = fixture(tmp_path)
    output = tmp_path / "new-pack"
    report = adapter().stage(root, reviewed(root), output)
    assert report["records"] == 1
    with_store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=output))
    assert with_store.error is None
    row = with_store.records[0]
    assert "[Research context:" in row.text
    assert row.section_id == "/article/body/sec[1]/p[1]"
    assert with_store.metadata[row.chunk_id]["collector_coordinates"]["start"] == 0
    assert row.permission_basis["clinical_review"] is False
    with_store.close()


def test_template_never_approves_sources(tmp_path):
    root, _, _ = fixture(tmp_path)
    template = adapter().review_template(root)
    assert template["attestation"] == ""
    assert template["documents"][0]["rights_confirmed"] is False
    with pytest.raises(ValueError, match="human"):
        adapter().stage(root, template, tmp_path / "pack")


@pytest.mark.parametrize("split", ["evaluation_holdout", "validation", "eval_holdout"])
def test_holdout_cannot_enter_staged_pack(tmp_path, split):
    root, doc, chunk = fixture(tmp_path)
    doc["split"] = chunk["split"] = split
    save_rows(root, doc, [chunk])
    with pytest.raises(ValueError, match="split"):
        adapter().stage(root, reviewed(root), tmp_path / "pack")


def test_forged_coordinates_rejected_even_with_fresh_review_hash(tmp_path):
    root, doc, chunk = fixture(tmp_path)
    chunk["source_char_start"] = 1
    save_rows(root, doc, [chunk])
    with pytest.raises(ValueError, match="coordinate"):
        adapter().stage(root, reviewed(root), tmp_path / "pack")


def test_stale_collector_bytes_rejected(tmp_path):
    root, doc, _ = fixture(tmp_path)
    approval = reviewed(root)
    (root / doc["stored_document_path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash"):
        adapter().stage(root, approval, tmp_path / "pack")


@pytest.mark.parametrize("license_name", ["CC-BY-2.5", "CC0-1.0"])
def test_unsupported_runtime_license_is_explicit_preflight(tmp_path, license_name):
    root, doc, chunk = fixture(tmp_path)
    doc["license"] = chunk["license"] = license_name
    save_rows(root, doc, [chunk])
    with pytest.raises(ValueError, match="runtime license"):
        adapter().stage(root, reviewed(root), tmp_path / "pack")


def test_paths_cannot_escape_collector(tmp_path):
    root, doc, chunk = fixture(tmp_path)
    doc["stored_document_path"] = "../outside.xml"
    save_rows(root, doc, [chunk])
    with pytest.raises(ValueError, match="path"):
        adapter().review_template(root)


def test_pack_is_immutable_and_cannot_be_written_inside_collector(tmp_path):
    root, _, _ = fixture(tmp_path)
    approval = reviewed(root)
    with pytest.raises(ValueError, match="output"):
        adapter().stage(root, approval, root / "new-pack")
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        adapter().stage(root, approval, output)


def test_missing_rights_and_failed_quality_rejected(tmp_path):
    root, doc, chunk = fixture(tmp_path)
    approval = reviewed(root)
    approval["documents"][0]["rights_confirmed"] = False
    with pytest.raises(ValueError, match="confirmations"):
        adapter().stage(root, approval, tmp_path / "pack")
    doc["quality_pass"] = False
    save_rows(root, doc, [chunk])
    with pytest.raises(ValueError, match="quality"):
        adapter().stage(root, reviewed(root), tmp_path / "pack")


def test_duplicate_version_family_rejected(tmp_path):
    root, doc, _ = fixture(tmp_path)
    duplicate = doc | {"id": "fixture-other-version"}
    (root / "manifests/catalogue.jsonl").write_text(json.dumps(doc) + "\n" + json.dumps(duplicate) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="family"):
        adapter().stage(root, reviewed(root), tmp_path / "pack")


def test_oversized_unit_omitted_without_truncation(tmp_path):
    root, doc, chunk = fixture(tmp_path, "x" * 4500)
    path = root / doc["extracted_path"]
    extracted = json.loads(path.read_text(encoding="utf-8"))
    text = "This separate nonmedical fixture section verifies explicit oversize omission reporting."
    coordinate = "/article/body/sec[1]/p[2]"
    extracted["sections"].append({"coordinate": coordinate, "heading": ["Fixture two"], "text": text, "page": None})
    path.write_text(json.dumps(extracted), encoding="utf-8")
    import hashlib
    doc["extracted_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    small = chunk | {"chunk_id": "second", "section_id": coordinate, "coordinate": coordinate, "section": "Fixture two",
                     "heading_hierarchy": ["Fixture two"], "text": text, "source_char_start": 0, "source_char_end": len(text)}
    save_rows(root, doc, [chunk, small])
    report = adapter().stage(root, reviewed(root), tmp_path / "pack")
    assert report["records"] == 1
    assert report["omitted"][0]["chunk_id"] == chunk["chunk_id"]
    assert report["omitted"][0]["reason"] == "runtime_text_length"


def test_cli_template_cannot_mutate_collector(tmp_path):
    import subprocess
    import sys
    root, _, _ = fixture(tmp_path)
    output = root / "review.json"
    process = subprocess.run([sys.executable, "-m", "scripts.stage_mds_pack", "template", "--collector", str(root), "--output", str(output)],
                             capture_output=True, text=True, check=False)
    assert process.returncode != 0
    assert not output.exists()
