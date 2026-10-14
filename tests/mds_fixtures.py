"""Synthetic mechanics fixtures; never admitted into production source packs."""

import hashlib
import json

import yaml

from backend.app.config import Settings
from backend.app.services.retrieval import Reference
from backend.app.services.teaching import TeachingStore


def make_teacher(tmp_path, passages):
    root = tmp_path / "synthetic-release"
    root.mkdir()
    rows, metadata = [], {}
    for i, item in enumerate(passages):
        topic, section, body = item[:3]
        row = Reference(
            source_id=f"synthetic-{i}", title="SYNTHETIC pipeline fixture",
            publisher="Test fixture", jurisdiction="Global",
            url=f"https://opentextbc.ca/synthetic/{i}/", section=section,
            retrieved_date="2026-10-11", source_date="2026-10-01",
            snapshot_id="synthetic-v1", text=body, topics=[topic], keywords=topic.split(),
            source_type="teaching", permission_basis={"type": "open_license",
                "approved_host": "opentextbc.ca", "license": "CC-BY-4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "snapshot_sha256": "a" * 64, "clinical_review": False},
        )
        row.chunk_id = row.stable_id()
        rows.append(row)
        metadata[row.chunk_id] = {"synthetic": True, **(item[3] if len(item) > 3 else {})}
    (root / "records.jsonl").write_text("\n".join(r.model_dump_json() for r in rows), encoding="utf-8")
    (root / "sources.yaml").write_text(yaml.safe_dump({"sources": [
        {"source_id": r.source_id, "url": r.url, "approval": "developer_reviewed",
         "terms": "Synthetic fixture only", "permission_basis": r.permission_basis,
         "raw_sha256": "a" * 64, "record_checksums": [r.content_hash()]} for r in rows
    ]}), encoding="utf-8")
    (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    manifest = {"version": "synthetic-v1", "files": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ("records.jsonl", "sources.yaml", "metadata.json")}}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    settings = Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical", teaching_release_path=root)
    store = TeachingStore(settings)
    assert store.error is None
    return store, rows
