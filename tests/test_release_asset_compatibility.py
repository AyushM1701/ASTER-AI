import hashlib
import json

import pytest

from aster_release.release import ReleaseError, verify_compatibility


def test_different_named_teaching_index_uses_content_hash(tmp_path):
    teaching = tmp_path / "teaching-release"
    index = tmp_path / "different-index-name"
    model = tmp_path / "encoder"
    for folder in (teaching, index, model):
        folder.mkdir()
    records = json.dumps({"chunk_id": "chunk-one"}) + "\n"
    (teaching / "records.jsonl").write_text(records)
    (teaching / "explanations.json").write_text("{}")
    def digest(data):
        return hashlib.sha256(data).hexdigest()
    files = {name: digest((teaching / name).read_bytes()) for name in ["records.jsonl", "explanations.json"]}
    (teaching / "manifest.json").write_text(json.dumps({"files": files, "records": 1}))
    (index / "vectors.npy").write_bytes(b"test-vector-bytes")
    im = {"snapshot_hash": digest(b"chunk-one"), "embedding_revision": "pinned", "dimension": 384,
          "vectors_sha256": digest(b"test-vector-bytes")}
    (index / "manifest.json").write_text(json.dumps(im))
    (model / "aster-model-manifest.json").write_text(json.dumps({"revision": "pinned"}))
    profile = {"settings": {"enable_teaching": True, "teaching_backend": "hybrid", "teaching_release_path": "teaching-release",
               "teaching_index_path": "different-index-name", "embedding_path": "encoder",
               "teaching_explanations_path": "teaching-release/explanations.json",
               "teaching_explanations_sha256": files["explanations.json"]}}
    verify_compatibility(tmp_path, profile)
    im["snapshot_hash"] = "0" * 64
    (index / "manifest.json").write_text(json.dumps(im))
    with pytest.raises(ReleaseError, match="snapshot mismatch"):
        verify_compatibility(tmp_path, profile)
    profile["settings"]["teaching_backend"] = "lexical"
    model.rename(tmp_path / "unused-encoder")
    verify_compatibility(tmp_path, profile)  # lexical teaching requires no dense index/encoder


def test_secondary_record_binding_survives_outer_manifest_regeneration(tmp_path):
    secondary = tmp_path / "secondary"
    secondary.mkdir()
    records = secondary / "records.jsonl"
    records.write_text('{}\n')
    digest = hashlib.sha256(records.read_bytes()).hexdigest()
    manifest = secondary / "manifest.json"
    manifest.write_text(json.dumps({"records_sha256": digest, "records": 1}))
    profile = {"settings": {"enable_secondary_references": True, "secondary_reference_path": "secondary",
                           "secondary_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()}}
    verify_compatibility(tmp_path, profile)
    records.write_text('{"changed": true}\n')
    with pytest.raises(ReleaseError, match="Secondary records hash"):
        verify_compatibility(tmp_path, profile)


def test_primary_index_collection_must_match_runtime_settings(tmp_path):
    records = tmp_path / "records.jsonl"
    records.write_text('{"chunk_id":"chunk-one"}\n')
    index = tmp_path / "index"
    index.mkdir()
    (index / "vectors.npy").write_bytes(b"vectors")
    def digest(data):
        return hashlib.sha256(data).hexdigest()
    (index / "manifest.json").write_text(json.dumps({
        "snapshot_hash": digest(b"chunk-one"), "embedding_revision": "pinned",
        "dimension": 384, "collection": "medical_reference_v2",
        "vectors_sha256": digest(b"vectors")}))
    model = tmp_path / "encoder"
    model.mkdir()
    (model / "aster-model-manifest.json").write_text('{"revision":"pinned"}')
    profile = {"settings": {"retrieval_backend": "hybrid", "corpus_path": "records.jsonl",
               "chroma_path": "index", "embedding_path": "encoder",
               "reference_collection": "medical_reference_v1"}, "data": {"primary": {"records": 1}}}
    with pytest.raises(ReleaseError, match="collection"):
        verify_compatibility(tmp_path, profile)
    profile["settings"]["reference_collection"] = "medical_reference_v2"
    verify_compatibility(tmp_path, profile)
