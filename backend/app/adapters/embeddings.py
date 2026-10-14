import hashlib
import json
import os

import numpy as np


def dense_records(records, manifest):
    excluded = set(manifest.get("dense_excluded_source_types", []))
    if not excluded <= {"retailer_monograph"}:
        raise ValueError("Only exact-identity retailer material may be excluded from semantic vectors")
    return [r for r in records if r.source_type not in excluded]


class DenseRetriever:
    def __init__(self, settings, records):
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from sentence_transformers import SentenceTransformer

        manifest = json.loads((settings.chroma_path / "manifest.json").read_text(encoding="utf-8"))
        snapshot = hashlib.sha256("".join(r.chunk_id for r in records).encode()).hexdigest()
        if manifest["snapshot_hash"] != snapshot or manifest["chunker"] != "curated-paragraph-v1":
            raise ValueError("Dense index differs from active references")
        if (
            manifest.get("collection", settings.reference_collection)
            != settings.reference_collection
        ):
            raise ValueError("Dense index collection differs from active configuration")
        model_manifest = json.loads(
            (settings.embedding_path / "aster-model-manifest.json").read_text()
        )
        if manifest.get("embedding_revision") != model_manifest["revision"]:
            raise ValueError("Embedding revision differs from indexed model")
        for name, expected in model_manifest["files"].items():
            path = (settings.embedding_path / name).resolve()
            if (
                not path.is_relative_to(settings.embedding_path.resolve())
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                raise ValueError("Embedding file changed")
        self.model = SentenceTransformer(
            str(settings.embedding_path), device="cpu", local_files_only=True
        )
        self.dimension = manifest["dimension"]
        self.client = None
        indexed_records = dense_records(records, manifest)
        self.ids = [r.chunk_id for r in indexed_records]
        if manifest.get("vector_store") == "numpy_exact":
            path = settings.chroma_path / "vectors.npy"
            if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["vectors_sha256"]:
                raise ValueError("Vector index hash changed")
            self.vectors = np.load(path, allow_pickle=False)
            if (
                self.vectors.shape != (len(indexed_records), self.dimension)
                or not np.isfinite(self.vectors).all()
            ):
                raise ValueError("Invalid vector index")
            if not np.allclose(np.linalg.norm(self.vectors, axis=1), 1, atol=1e-5):
                raise ValueError("Index vectors are not normalized")
        else:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.client = chromadb.PersistentClient(
                path=str(settings.chroma_path), settings=ChromaSettings(anonymized_telemetry=False)
            )
            self.collection = self.client.get_collection(
                settings.reference_collection, embedding_function=None
            )
            if self.collection.count() != len(records):
                raise ValueError("Incomplete reference collection")

    def rank(self, question, allowed):
        scores = self.scores(question, allowed)
        return sorted(scores, key=scores.get, reverse=True)

    def scores(self, question, allowed):
        vector = self.model.encode([question], normalize_embeddings=True)
        if vector.shape != (1, self.dimension) or not np.isfinite(vector).all():
            raise ValueError("Invalid embedding dimension or value")
        if self.client is None:
            allowed = set(allowed)
            values = self.vectors @ vector[0]
            return {
                key: float(value)
                for key, value in zip(self.ids, values, strict=True)
                if key in allowed
            }
        result = self.collection.query(
            query_embeddings=vector.tolist(),
            n_results=self.collection.count(),
            include=["distances"],
        )
        allowed = set(allowed)
        return {
            key: 1.0 - distance
            for key, distance in zip(result["ids"][0], result["distances"][0], strict=True)
            if key in allowed
        }
