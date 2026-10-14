"""Validate curated local records and stage an immutable lexical or dense index."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.retrieval import ReferenceStore  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "configs/sources.yaml")
    parser.add_argument(
        "--corpus", type=Path, default=ROOT / "data/references/normalized/seed.jsonl"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backend", choices=["lexical", "chroma", "hybrid"], default="lexical")
    parser.add_argument("--collection", default="medical_reference_v1")
    parser.add_argument(
        "--exact-retailer-search",
        action="store_true",
        help="Index user-attested retailer monographs lexically by exact identity; preserve primary-source semantic vectors",
    )
    args = parser.parse_args()
    settings = Settings(
        source_register=args.sources.resolve(),
        corpus_path=args.corpus.resolve(),
        retrieval_backend="lexical",
        reference_collection=args.collection,
    )
    refs = ReferenceStore(settings)
    if refs.error:
        parser.error(refs.error)
    manifest = {
        **refs.manifest(),
        "backend": args.backend,
        "chunker": "curated-paragraph-v1",
        "embedding_model": None,
        "dimension": None,
        "collection": args.collection,
    }
    if args.dry_run:
        print(json.dumps(manifest, indent=2))
        return
    output = args.output.resolve()
    if output.exists():
        parser.error(
            "Output exists. Build a new versioned directory; never mutate an active index."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    # Failed builds retain staging evidence and never activate a partial index.
    staging = Path(tempfile.mkdtemp(prefix="reference-staging-", dir=output.parent))
    if args.backend in {"chroma", "hybrid"}:
        from backend.app.adapters.embeddings import dense_records

        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(
            str(settings.embedding_path), device="cpu", local_files_only=True
        )
        if args.exact_retailer_search:
            if args.backend != "hybrid":
                parser.error("Exact retailer search requires the hybrid NumPy index")
            manifest["dense_excluded_source_types"] = ["retailer_monograph"]
        indexed = dense_records(refs.records, manifest)
        manifest["semantic_records"] = len(indexed)
        texts = [r.text for r in indexed]
        # Reject overflow rather than silently truncating medication qualifications.
        lengths = [len(model.tokenizer.encode(text, add_special_tokens=True)) for text in texts]
        if max(lengths) > model.max_seq_length:
            parser.error(
                "A curated paragraph exceeds the embedding token limit. Split and re-review it first."
            )
        vectors = model.encode(texts, normalize_embeddings=True)
        if args.backend == "hybrid":
            import numpy as np

            np.save(staging / "vectors.npy", vectors, allow_pickle=False)
            manifest.update(
                vector_store="numpy_exact",
                vectors_sha256=hashlib.sha256((staging / "vectors.npy").read_bytes()).hexdigest(),
            )
        else:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            client = chromadb.PersistentClient(
                path=str(staging), settings=ChromaSettings(anonymized_telemetry=False)
            )
            collection = client.create_collection(
                settings.reference_collection,
                embedding_function=None,
                configuration={"hnsw": {"space": "cosine"}},
            )
            collection.upsert(
                ids=[r.chunk_id for r in refs.records],
                embeddings=vectors.tolist(),
                documents=texts,
                metadatas=[
                    {"source_id": r.source_id, "snapshot_id": r.snapshot_id} for r in refs.records
                ],
            )
            if collection.count() != len(refs.records):
                parser.error("Staged collection is incomplete.")
            client.close()
        manifest.update(
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            dimension=int(vectors.shape[1]),
            embedding_revision=json.loads(
                (settings.embedding_path / "aster-model-manifest.json").read_text()
            )["revision"],
        )
    (staging / "records.jsonl").write_text(
        "\n".join(r.model_dump_json() for r in refs.records) + "\n", encoding="utf-8"
    )
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    staging.rename(output)
    print(
        json.dumps(
            {k: v for k, v in manifest.items() if k not in {"topics", "medicine_entities"}},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
