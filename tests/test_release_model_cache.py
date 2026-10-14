import hashlib
import json

import pytest

from aster_release.model_cache import prepare_model_store
from aster_release.release import ReleaseError


def test_generated_ollama_metadata_stays_outside_installation(tmp_path):
    root = tmp_path / "install"
    store = root / "data/models/ollama-store"
    blob = store / "blobs"
    blob.mkdir(parents=True)
    digest = hashlib.sha256(b"model fixture").hexdigest()
    (blob / ("sha256-" + digest)).write_bytes(b"model fixture")
    recipe = store / "manifests/registry.ollama.ai/library/qwen3-vl/2b-instruct"
    recipe.parent.mkdir(parents=True)
    recipe.write_text(json.dumps({"config": {"digest": "sha256:" + digest}, "layers": []}))
    runtime = root / "runtime/ollama/ollama.exe"
    runtime.parent.mkdir(parents=True)
    runtime.write_bytes(b"runtime fixture")
    manifest = {"model": {"store": "data/models/ollama-store", "digest": hashlib.sha256(recipe.read_bytes()).hexdigest()}}
    writable = tmp_path / "writable"
    writable.mkdir()
    cache = prepare_model_store(root, writable, manifest)
    (cache / "metadata").mkdir()
    (cache / "metadata/test.json").write_text("{}")
    assert not (store / "metadata").exists()
    assert prepare_model_store(root, writable, manifest) == cache
    # Recipe tampering is rejected, not silently accepted as another model.
    cached_recipe = cache / recipe.relative_to(store)
    cached_recipe.unlink()  # separate new file instead of modifying the shared hardlink
    cached_recipe.write_text("tampered")
    with pytest.raises(ReleaseError, match="cache changed"):
        prepare_model_store(root, writable, manifest)
