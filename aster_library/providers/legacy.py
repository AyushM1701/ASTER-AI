"""Import the existing curated MBBS/MDS teaching pack (candidate-v5) into the
new library format, preserving each source's recorded licence, attribution,
raw snapshot hash and AI-inspection metadata. Licences decide the edition:
CC BY/PD -> default, CC BY-NC(-SA) -> noncommercial pack, anything else excluded.
"""
import json
from pathlib import Path

import yaml

from aster_library.common import ROOT, WORK, log, register
from aster_library.model import clean_text, edition_for, make_unit, today

PACK = ROOT / "artifacts/source-packs/mds-master-evidence-candidate-v5-2026-10-13"


@register("legacy")
def acquire(client=None, refresh=False):
    out_dir = WORK / "legacy"
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = yaml.safe_load((PACK / "sources.yaml").read_text(encoding="utf-8"))
    sources = sources["sources"] if isinstance(sources, dict) else sources
    by_url = {s.get("url"): s for s in sources}
    metadata = json.loads((PACK / "metadata.json").read_text(encoding="utf-8"))
    chunk_meta = metadata.get("chunks", {})
    docs = {}
    for line in (PACK / "records.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        meta = chunk_meta.get(record["chunk_id"], {})
        source = by_url.get(record.get("url"), {})
        license_id = meta.get("license") or source.get("license")
        doc_id = "legacy:" + record["source_id"]
        if doc_id not in docs:
            docs[doc_id] = {
                "status": "acquired" if edition_for(license_id) else "excluded",
                "reason": None if edition_for(license_id) else f"licence not redistributable: {license_id}",
                "doc": {
                    "doc_id": doc_id, "provider": "legacy-candidate-v5", "title": clean_text(record.get("title", "")),
                    "url": record.get("url"), "publisher": record.get("publisher"),
                    "jurisdiction": record.get("jurisdiction") or "International",
                    "content_class": "professional", "evidence_type": "textbook" if meta.get("level") else "educational",
                    "published": record.get("source_date"), "version": meta.get("edition") or record.get("snapshot_id"),
                    "acquired": record.get("retrieved_date") or today(), "license": license_id,
                    "license_url": None, "attribution": source.get("attribution") or record.get("publisher"),
                    "terms": source.get("terms"), "raw_snapshot_path": source.get("raw_snapshot_path"),
                    "raw_sha256": source.get("raw_sha256"), "acquisition_endpoint": record.get("url"),
                    "subjects": meta.get("subjects", []), "level": meta.get("level"),
                    "ai_inspected_facet_bindings": bool(meta.get("ai_inspected_facet_bindings")),
                    "access": "full_text", "publication_status": "published",
                    "legacy_pack": PACK.name,
                },
                "units": [],
            }
        doc = docs[doc_id]["doc"]
        unit = make_unit(doc, section_path=[record.get("section") or "Section"],
                         paragraph=meta.get("paragraph_start", 0), text=record["text"],
                         extra={"legacy_chunk_id": record["chunk_id"], "topics": record.get("topics", [])})
        docs[doc_id]["units"].append(unit)
    items = list(docs.values())
    with (out_dir / "docs.jsonl").open("w", encoding="utf-8") as out:
        for item in items:
            out.write(json.dumps(item, ensure_ascii=False) + "\n")
    log(f"legacy: {len(items)} source documents, {sum(len(i['units']) for i in items)} units")


def load(work=WORK):
    path = Path(work) / "legacy" / "docs.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
