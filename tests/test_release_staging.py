import json

import pytest

from aster_release.release import ReleaseError
from aster_release.staging import inventory


def inputs(root):
    names = ["data/records.jsonl", "data/sources.yaml", "frontend/web/index.html",
             "configs/explanation_layouts.json", "data/samples/synthetic_prescription.png",
             "LICENSE", "THIRD_PARTY_NOTICES.md", "SECURITY.md", "CHANGELOG.md",
             "runtime/ollama/ollama.exe", "runtime/tesseract/tesseract.exe",
             "runtime/tesseract/needed.dll", "runtime/tesseract/tessdata/eng.traineddata",
             "runtime/tesseract/tessdata/unselected.traineddata", "data/models/store/blobs/sha256-test"]
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    recipe = root / "data/models/store/manifests/registry.ollama.ai/library/qwen3-vl/2b-instruct"
    recipe.parent.mkdir(parents=True)
    recipe.write_text(json.dumps({"config": {"digest": "sha256:test"}, "layers": []}))
    return {"edition": "PublicStandard", "model": {"store": "data/models/store"}, "settings": {
        "corpus_path": "data/records.jsonl", "source_register": "data/sources.yaml",
        "retrieval_backend": "lexical", "enable_teaching": False, "enable_secondary_references": False}}


def test_provisioned_native_assets_do_not_use_build_machine_installation(tmp_path):
    pairs = inventory(tmp_path, inputs(tmp_path))
    selected = {name: path for path, name in pairs}
    assert selected["runtime/tesseract/tesseract.exe"] == tmp_path / "runtime/tesseract/tesseract.exe"
    assert "runtime/tesseract/needed.dll" in selected
    assert "runtime/tesseract/tessdata/unselected.traineddata" not in selected
    assert selected["runtime/ollama/ollama.exe"] == tmp_path / "runtime/ollama/ollama.exe"
    assert all(path.is_relative_to(tmp_path) for path, _ in pairs)


def test_public_build_rejects_missing_provisioned_tesseract(tmp_path):
    profile = inputs(tmp_path)
    (tmp_path / "runtime/tesseract").rename(tmp_path / "runtime/not-selected")
    with pytest.raises(ReleaseError, match="provisioned runtime/tesseract"):
        inventory(tmp_path, profile)


def test_lexical_primary_with_dense_teaching_includes_encoder(tmp_path):
    profile = inputs(tmp_path)
    profile["settings"].update(enable_teaching=True, teaching_backend="hybrid", teaching_release_path="data/teaching",
                               teaching_index_path="data/teaching-index", embedding_path="data/encoder")
    for name in ["data/teaching/records.jsonl", "data/teaching-index/vectors.npy", "data/encoder/model.safetensors"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    selected = {name for _, name in inventory(tmp_path, profile)}
    assert "data/encoder/model.safetensors" in selected
    assert "data/teaching-index/vectors.npy" in selected
