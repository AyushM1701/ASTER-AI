"""Compose immutable teaching releases without changing existing source identities."""

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compose(base, components, explanations, syllabus, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Release exists; choose a new immutable version")
    records, sources, metadata, lineage = [], [], {"chunks": {}, "sources": {}}, []
    ids, source_ids, component_flags = set(), set(), []
    for path in [Path(base), *map(Path, components)]:
        store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical",
                                       teaching_release_path=path, teaching_explanations_sha256=""))
        if store.error or not store.records:
            raise ValueError(f"Component rejected: {path}: {store.error}")
        rows = [row.model_dump() for row in store.records]
        register = yaml.safe_load((path / "sources.yaml").read_text(encoding="utf-8"))["sources"]
        if ids & {row["chunk_id"] for row in rows} or source_ids & {source["source_id"] for source in register}:
            raise ValueError("Duplicate source or chunk identity across components")
        ids.update(row["chunk_id"] for row in rows)
        source_ids.update(source["source_id"] for source in register)
        records.extend(rows)
        sources.extend(register)
        context = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        metadata["chunks"].update(context.get("chunks", context))
        metadata["sources"].update(context.get("sources", {}))
        component_flags.extend(context.get("source_review_flags", []))
        lineage.append({"path": str(path.resolve()), "manifest_sha256": digest(path / "manifest.json"),
                        "version": store.version, "records": len(rows), "sources": len(register)})
        store.close()
    document = json.loads(Path(explanations).read_text(encoding="utf-8"))
    document["release_version"] = output.name
    document.setdefault("source_review_flags", []).extend(component_flags)
    syllabus_document = json.loads(Path(syllabus).read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="mds-composition-", dir=output.parent))
    (staging / "records.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n", encoding="utf-8")
    (staging / "sources.yaml").write_text(yaml.safe_dump({"library_version": output.name, "sources": sources}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    metadata.update(schema_version=1, clinical_review=False, faculty_review="pending", lineage=lineage,
                    scope="Photographed MDS topics plus preserved MBBS material; not complete curriculum mastery")
    for name, value in (("metadata.json", metadata), ("explanations.json", document), ("syllabus.json", syllabus_document)):
        (staging / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    names = ["records.jsonl", "sources.yaml", "metadata.json", "explanations.json", "syllabus.json"]
    manifest = {"version": output.name, "schema_version": 1, "records": len(records), "sources": len(sources),
                "files": {name: digest(staging / name) for name in names}, "lineage": lineage,
                "photographed_topics": syllabus_document["topic_count"], "clinical_review": False, "faculty_review": "pending",
                "licenses": sorted({source.get("license", "unspecified") for source in sources}),
                "usage": "Local noncommercial educational retrieval. Preserve attribution, source-specific licenses and share-alike obligations."}
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical",
                                       teaching_release_path=staging, teaching_explanations_path=staging / "explanations.json",
                                       teaching_explanations_sha256=digest(staging / "explanations.json")))
    if validation.error or len(validation.records) != len(records):
        raise ValueError("Composed release rejected: " + str(validation.error))
    validation.close()
    staging.rename(output)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--component", type=Path, action="append", required=True)
    parser.add_argument("--explanations", type=Path, required=True)
    parser.add_argument("--syllabus", type=Path, default=ROOT / "configs/mds_syllabus.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compose(args.base, args.component, args.explanations, args.syllabus, args.output), indent=2))
