"""Build a source-bound teaching index without truncating long source units."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402


def token_windows(tokens, size):
    if size <= 0:
        raise ValueError("Embedding window size must be positive")
    return [tokens[start:start + size] for start in range(0, len(tokens), size)]


def pool_vectors(vectors):
    if vectors.ndim != 2 or not len(vectors) or not np.isfinite(vectors).all():
        raise ValueError("Invalid window embedding")
    vector = vectors.mean(axis=0)
    norm = np.linalg.norm(vector)
    if not np.isfinite(norm) or norm <= 1e-12:
        raise ValueError("Invalid pooled embedding")
    return (vector / norm).astype(np.float32)


def build(release, output):
    if output.exists():
        raise ValueError("Index exists; use a new versioned directory")
    settings = Settings(enable_teaching=True, teaching_release_path=release, teaching_backend="lexical", teaching_explanations_sha256="")
    store = TeachingStore(settings)
    if store.error:
        raise ValueError(store.error)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(2)
    model_manifest = json.loads((settings.embedding_path / "aster-model-manifest.json").read_text(encoding="utf-8"))
    for name, expected in model_manifest["files"].items():
        path = (settings.embedding_path / name).resolve()
        if not path.is_relative_to(settings.embedding_path.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Embedding model changed")
    model = SentenceTransformer(str(settings.embedding_path), device="cpu", local_files_only=True)
    texts, ranges = [], []
    for row in store.records:
        original = row.section + "\n" + row.text
        ids = model.tokenizer.encode(original, add_special_tokens=False, verbose=False)
        start = len(texts)
        for window in token_windows(ids, model.max_seq_length - 8):
            decoded = model.tokenizer.decode(window, skip_special_tokens=False)
            if len(model.tokenizer.encode(decoded, add_special_tokens=True)) > model.max_seq_length:
                raise ValueError("Decoded window exceeds model capacity; no truncation allowed")
            texts.append(decoded)
        ranges.append((start, len(texts)))
    vectors = model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    pooled = np.stack([pool_vectors(vectors[start:end]) for start, end in ranges])
    output.mkdir(parents=True, exist_ok=False)
    np.save(output / "vectors.npy", pooled, allow_pickle=False)
    manifest = {
        "snapshot_hash": store.references.snapshot_hash, "chunker": "curated-paragraph-v1",
        "collection": "medical_teaching_v1", "embedding_revision": model_manifest["revision"],
        "dimension": int(pooled.shape[1]), "vector_store": "numpy_exact",
        "vectors_sha256": hashlib.sha256((output / "vectors.npy").read_bytes()).hexdigest(),
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "records": len(store.records),
        "encoded_windows": len(texts), "embedding_window_policy": "All source-unit tokens encoded in consecutive windows; normalized mean of window vectors. Original complete evidence is retained.",
        "clinical_review": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    store.close()
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.release.resolve(), args.output.resolve()), indent=2))


if __name__ == "__main__":
    main()
