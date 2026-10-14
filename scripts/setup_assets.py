"""Explicit online acquisition only. The API never calls this script."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset", choices=["embeddings", "xray"])
    parser.add_argument("--revision", help="Required immutable Hugging Face commit for embeddings")
    args = parser.parse_args()
    if args.asset == "embeddings":
        if not args.revision or len(args.revision) != 40:
            parser.error("Use --revision with a verified 40-character model commit SHA.")
        from sentence_transformers import SentenceTransformer

        folder = ROOT / "data/models/minilm"
        if folder.exists():
            parser.error(
                "Embedding cache exists; preserve it and use a new versioned path for upgrades."
            )
        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2", revision=args.revision, device="cpu"
        )
        model.save(str(folder))
        (folder / "asset_manifest.json").write_text(
            json.dumps(
                {"model": "sentence-transformers/all-MiniLM-L6-v2", "revision": args.revision},
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Cached pinned embedding model. Run ingestion to build a matching index.")
    else:
        import torchxrayvision as xrv

        folder = ROOT / "data/models/xray"
        folder.mkdir(parents=True, exist_ok=True)
        model_id = "densenet121-res224-all"
        model = xrv.models.DenseNet(weights=model_id, cache_dir=str(folder))
        path = folder / xrv.models.model_urls[model_id]["weights_url"].rsplit("/", 1)[-1]
        manifest = {
            "model_id": model_id,
            "weights_path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "preprocessing_version": "xrv-8bit-center224-v1",
            "library_version": importlib.metadata.version("torchxrayvision"),
            "labels": list(getattr(model, "pathologies", getattr(model, "targets", []))),
            "evaluation": "not_independently_validated",
        }
        (ROOT / "configs/xray_weights.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print(
            "Cached weights and exact manifest. Register permitted assets before enabling imaging."
        )


if __name__ == "__main__":
    main()
