"""Acquire a pinned official MiniLM snapshot; runtime retrieval remains offline."""

import hashlib
import json
from pathlib import Path

import requests
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    dest = ROOT / "data/models/minilm"
    manifest = dest / "aster-model-manifest.json"
    if manifest.exists():
        print(manifest.read_text())
        return
    response = requests.get(f"https://huggingface.co/api/models/{MODEL}", timeout=30)
    response.raise_for_status()
    revision = response.json()["sha"]
    snapshot_download(
        MODEL,
        revision=revision,
        local_dir=dest,
        token=False,
        allow_patterns=["*.json", "*.txt", "model.safetensors", "1_Pooling/*", "README.md"],
        ignore_patterns=["onnx/*", "openvino/*"],
    )
    hashes = {
        str(path.relative_to(dest)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in dest.rglob("*")
        if path.is_file() and ".cache" not in path.parts
    }
    payload = {
        "model": MODEL,
        "revision": revision,
        "license": "Apache-2.0",
        "retrieved_date": "2026-10-07",
        "files": hashes,
    }
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
