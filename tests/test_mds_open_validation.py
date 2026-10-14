import importlib
import json

import pytest


def module():
    try:
        return importlib.import_module("scripts.mds_open_validate")
    except ModuleNotFoundError:
        pytest.fail("Open corpus integrity validator is missing")


def test_validator_flags_holdout_leakage_without_clinical_approval(tmp_path):
    for sub in ("manifests", "rag_chunks", "training_candidates", "evaluation_holdout"):
        (tmp_path / sub).mkdir()
    (tmp_path / "manifests/state.json").write_text(json.dumps({"documents": {}}))
    row = {"document_id": "source-heldout", "text": "Evidence"}
    for path in ("rag_chunks/staged_rag.jsonl", "training_candidates/rights_screened_candidates.jsonl", "evaluation_holdout/source_chunks.jsonl"):
        (tmp_path / path).write_text(json.dumps(row) + "\n")
    report = module().validate_corpus(tmp_path)
    assert report["passed"] is False
    assert "heldout_split_leakage" in report["issues"]
    assert report["faculty_reviewed"] == 0


def test_validator_detects_tampered_persisted_source(tmp_path):
    for sub in ("manifests", "rag_chunks", "training_candidates", "evaluation_holdout", "raw"):
        (tmp_path / sub).mkdir()
    doc = {"id": "doc", "stored_document_path": "raw/doc.xml", "stored_sha256": "0" * 64, "extracted_path": "missing", "specialties": []}
    (tmp_path / "raw/doc.xml").write_bytes(b"tampered")
    (tmp_path / "manifests/state.json").write_text(json.dumps({"documents": {"doc": doc}}))
    for path in ("rag_chunks/staged_rag.jsonl", "training_candidates/rights_screened_candidates.jsonl", "evaluation_holdout/source_chunks.jsonl"):
        (tmp_path / path).write_text("")
    report = module().validate_corpus(tmp_path)
    assert report["passed"] is False
    assert "doc:snapshot_invalid" in report["issues"]
