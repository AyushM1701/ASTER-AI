"""Build the hybrid retrieval index for one pack.

Outputs ``<pack>/index/``:
  units.sqlite       FTS5 (porter, unicode61) over title/section/text + unit metadata
  dense.f16.npy      L2-normalised MiniLM embeddings, row i == sqlite rowid i+1
  index-manifest.json  binds the index to the pack manifest hash and model revision
"""
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "models" / "minilm"
INDEX_SCHEMA = 1
COLUMNS = ["unit_id", "doc_id", "title", "section", "text", "content_class", "evidence_type", "license",
           "jurisdiction", "domains", "publisher", "url", "published", "acquired", "access", "publication_status",
           "kind", "extraction_reliability", "location"]


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def embedding_text(unit):
    return f"{unit.get('title') or ''}. {unit.get('section') or ''}. {unit['text']}"[:2000]


def load_encoder(model_dir=MODEL_DIR, providers=None):
    from aster_library.embed import OnnxEncoder

    return OnnxEncoder(model_dir, providers=providers)


def build_index(pack_dir, *, log=print, model_dir=MODEL_DIR, batch_size=64):
    pack_dir = Path(pack_dir)
    index_dir = pack_dir / "index"
    tmp_dir = pack_dir / "index.tmp"
    if tmp_dir.exists():
        for path in tmp_dir.iterdir():
            path.unlink()
    tmp_dir.mkdir(exist_ok=True)
    manifest_hash = sha256_file(pack_dir / "manifest.json")
    db = sqlite3.connect(tmp_dir / "units.sqlite")
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA synchronous=OFF")
    db.execute(f"CREATE TABLE units (rowid INTEGER PRIMARY KEY, {', '.join(c + ' TEXT' for c in COLUMNS)})")
    db.execute("CREATE VIRTUAL TABLE units_fts USING fts5(title, section, text, content='units', content_rowid='rowid', "
               "tokenize='porter unicode61 remove_diacritics 2')")
    units = []
    with (pack_dir / "units.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                units.append(json.loads(line))
    rows = []
    for i, unit in enumerate(units, start=1):
        row = [i]
        for column in COLUMNS:
            value = unit.get(column)
            row.append(json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value)
        rows.append(row)
    db.executemany(f"INSERT INTO units VALUES ({', '.join('?' * (len(COLUMNS) + 1))})", rows)
    db.execute("INSERT INTO units_fts(rowid, title, section, text) SELECT rowid, title, section, text FROM units")
    db.execute("INSERT INTO units_fts(units_fts) VALUES('optimize')")
    db.execute("CREATE INDEX units_doc ON units(doc_id)")
    db.commit()
    db.close()
    log(f"index: FTS5 built for {len(units)} units")
    from aster_library.embed import EmbeddingCache

    providers = [p for p in os.environ.get("ASTER_EMBED_PROVIDERS", "DmlExecutionProvider,CPUExecutionProvider").split(",") if p]
    encoder = load_encoder(model_dir, providers)
    model_manifest = json.loads((Path(model_dir) / "aster-model-manifest.json").read_text(encoding="utf-8"))
    cache = EmbeddingCache(os.environ.get("ASTER_EMBED_CACHE") or ROOT / "data" / "library-work" / "embed-cache.sqlite",
                           model_manifest["revision"] + "/onnx-fp32")
    started = time.monotonic()
    texts = [embedding_text(u) for u in units]
    keys = [cache.key(t) for t in texts]
    cached = cache.get_many(keys)
    missing = [i for i, k in enumerate(keys) if k not in cached]
    log(f"index: {len(units) - len(missing)} cached embeddings, {len(missing)} to compute on {encoder.providers[0]}")
    for start in range(0, len(missing), 4096):
        block = missing[start:start + 4096]
        encoded = encoder.encode([texts[i] for i in block], batch_size=batch_size)
        cache.put_many([(keys[i], encoded[j]) for j, i in enumerate(block)])
        cached.update({keys[i]: encoded[j].astype(np.float16) for j, i in enumerate(block)})
        log(f"index: embedded {start + len(block)}/{len(missing)} ({time.monotonic() - started:.0f}s)")
    cache.close()
    vectors = np.stack([cached[k] for k in keys]).astype(np.float16) if keys else np.zeros((0, 384), dtype=np.float16)
    if not np.isfinite(vectors.astype(np.float32)).all():
        raise ValueError("non-finite embeddings")
    np.save(tmp_dir / "dense.f16.npy", vectors, allow_pickle=False)
    index_manifest = {
        "schema_version": INDEX_SCHEMA,
        "pack_manifest_sha256": manifest_hash,
        "units": len(units),
        "dense": {"model": model_manifest["model"], "revision": model_manifest["revision"], "dimension": 384,
                  "dtype": "float16", "normalized": True, "text": "title. section. text[:2000]",
                  "encoder": "onnx/model.onnx fp32, mean pooling, max 256 tokens"},
        "fts": {"tokenizer": "porter unicode61 remove_diacritics 2"},
        "files": {name: {"sha256": sha256_file(tmp_dir / name), "bytes": (tmp_dir / name).stat().st_size}
                  for name in ("units.sqlite", "dense.f16.npy")},
        "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "embedding_seconds": round(time.monotonic() - started, 1),
    }
    (tmp_dir / "index-manifest.json").write_text(json.dumps(index_manifest, indent=2), encoding="utf-8")
    from aster_library.signing import sign_file

    sign_file(tmp_dir / "index-manifest.json")
    if index_dir.exists():
        for path in index_dir.iterdir():
            path.unlink()
        index_dir.rmdir()
    tmp_dir.rename(index_dir)
    log(f"index: done in {time.monotonic() - started:.0f}s -> {index_dir}")
    return index_dir
