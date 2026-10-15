"""Writable Ollama store backed by verified immutable installation blobs."""
import os
import re
import shutil
from pathlib import Path

from aster_release.release import ReleaseError, contained, read_json, sha256


def prepare_model_store(root, writable, manifest):
    root, writable = Path(root).resolve(), Path(writable).resolve()
    model = manifest["model"]
    if not re.fullmatch(r"[0-9a-f]{64}", model["digest"]):
        raise ReleaseError("Invalid model digest")
    runtime_digest = sha256(root / "runtime/ollama/ollama.exe")
    cache = contained(writable, "cache/model-store/" + model["digest"][:16] + "-" + runtime_digest[:12])
    cache.mkdir(parents=True, exist_ok=True)
    source = contained(root, model["store"])
    relative = "manifests/registry.ollama.ai/library/qwen3-vl/2b-instruct"
    recipe = read_json(source / relative)
    expected = [(relative, model["digest"])]
    for layer in [recipe["config"], *recipe["layers"]]:
        digest = layer["digest"].removeprefix("sha256:")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ReleaseError("Invalid model layer digest")
        expected.append(("blobs/sha256-" + digest, digest))
    for name, digest in expected:
        original, target = contained(source, name), contained(cache, name)
        if sha256(original) != digest:
            raise ReleaseError("Included model changed; repair installation")
        if target.exists():
            if sha256(target) != digest:
                raise ReleaseError("Model cache changed. Close Aster, remove its cache/model-store folder and relaunch.")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(original, target)  # no extra weight bytes when on the same NTFS volume
        except OSError:
            if shutil.disk_usage(cache).free < original.stat().st_size + 128 * 1024**2:
                raise ReleaseError("Insufficient disk space for the local model cache")
            shutil.copy2(original, target)  # portable installs on another volume need a copy
        if sha256(target) != digest:
            raise ReleaseError("Local model cache failed integrity verification")
    # Ollama's derived metadata/ is mutable here, never inside the installation.
    return cache


def prepare_model_stores(root, writable, installed_manifest):
    """Writable Ollama store for every installed model (v2 installs).

    Blobs are hardlinked from the verified installation when possible; the
    installation itself was integrity-checked just before this call. Ollama
    writes its derived metadata only in the writable copy.
    """
    root, writable = Path(root).resolve(), Path(writable).resolve()
    source = contained(root, "data/models/ollama-store")
    runtime_digest = installed_digest(installed_manifest, "runtime/ollama/ollama.exe")
    cache = contained(writable, "cache/model-store/" + installed_manifest["app_version"] + "-" + runtime_digest[:12])
    cache.mkdir(parents=True, exist_ok=True)
    sizes = {f["path"]: f["size"] for f in installed_manifest["files"]}
    for item in installed_manifest["files"]:
        if not item["path"].startswith("data/models/ollama-store/"):
            continue
        name = item["path"][len("data/models/ollama-store/"):]
        original, target = contained(source, name), contained(cache, name)
        if target.exists() and target.stat().st_size == sizes[item["path"]]:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        try:
            os.link(original, target)
        except OSError:
            if shutil.disk_usage(cache).free < original.stat().st_size + 256 * 1024 ** 2:
                raise ReleaseError("Not enough free disk space to prepare the AI model cache. Free some space and retry.")
            shutil.copy2(original, target)
            if sha256(target) != item["sha256"]:
                raise ReleaseError("The AI model cache could not be written correctly. Free disk space and retry.")
    return cache


def installed_digest(manifest, path):
    for item in manifest["files"]:
        if item["path"] == path:
            return item["sha256"]
    raise ReleaseError(f"{path} is missing from the installation. Choose Repair Aster.")
