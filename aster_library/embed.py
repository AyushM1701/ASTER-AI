"""MiniLM sentence embeddings through ONNX Runtime (CPU or DirectML).

The fp32 ONNX export of all-MiniLM-L6-v2 at the pinned revision reproduces the
sentence-transformers embeddings (cosine > 0.9999999 on library passages), so
indexes and runtime queries share one encoder without torch.
"""
import hashlib
import sqlite3
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "models" / "minilm"
DIMENSION = 384


class OnnxEncoder:
    def __init__(self, model_dir=MODEL_DIR, providers=None, threads=None):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_dir = Path(model_dir)
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=256)
        options = ort.SessionOptions()
        options.log_severity_level = 3
        if threads:
            options.intra_op_num_threads = threads
        available = ort.get_available_providers()
        chosen = [p for p in (providers or ["CPUExecutionProvider"]) if p in available] or ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(model_dir / "onnx" / "model.onnx"), options, providers=chosen)
        self.providers = chosen

    def _batch(self, texts):
        encoded = self.tokenizer.encode_batch(list(texts))
        length = max(len(e.ids) for e in encoded)
        ids = np.array([e.ids + [0] * (length - len(e.ids)) for e in encoded], dtype=np.int64)
        mask = np.array([e.attention_mask + [0] * (length - len(e.ids)) for e in encoded], dtype=np.int64)
        out = self.session.run(None, {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)})[0]
        pooled = (out * mask[..., None]).sum(1) / np.maximum(mask.sum(1, keepdims=True), 1)
        return pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)

    def encode(self, texts, batch_size=64):
        texts = list(texts)
        if not texts:
            return np.zeros((0, DIMENSION), dtype=np.float32)
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = np.zeros((len(texts), DIMENSION), dtype=np.float32)
        for start in range(0, len(order), batch_size):
            idx = order[start:start + batch_size]
            out[idx] = self._batch([texts[i] for i in idx])
        return out


class EmbeddingCache:
    """sha256(model revision + text) -> float16 vector, so rebuilds only embed new text."""

    def __init__(self, path, revision):
        self.revision = revision
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS v (k TEXT PRIMARY KEY, vec BLOB)")

    def key(self, text):
        return hashlib.sha256((self.revision + "\0" + text).encode("utf-8")).hexdigest()

    def get_many(self, keys):
        found = {}
        for start in range(0, len(keys), 900):
            chunk = keys[start:start + 900]
            marks = ",".join("?" * len(chunk))
            for key, blob in self.db.execute(f"SELECT k, vec FROM v WHERE k IN ({marks})", chunk):
                found[key] = np.frombuffer(blob, dtype=np.float16)
        return found

    def put_many(self, items):
        self.db.executemany("INSERT OR REPLACE INTO v VALUES (?, ?)",
                            [(k, np.asarray(v, dtype=np.float16).tobytes()) for k, v in items])
        self.db.commit()

    def close(self):
        self.db.close()
