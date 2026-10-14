"""Stage an immutable AI-inspected development pack from an admitted source release.

Inspection JSONL must contain actual source-inspection annotations, not generated
topic tags: review_status=source_inspected, review_origin=ai_source_inspection,
reviewer=Codex, clinical_review=False, qualifications_retained=True, exact retained
qualification phrases and nonempty support_rationale/qualification_note/source_context.
Identity, full-unit hashes and coordinates follow reviewed_evidence.py. Original
records, source identities and license conditions remain unchanged. This script
never acquires or activates sources, creates human attestations, builds an index,
or establishes clinical correctness. Newly acquired material must first become a
separate admitted release with verifiable source rights and provenance.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402
from backend.app.services.evidence_plan import source_reasons  # noqa: E402
from backend.app.services.question_plan import RequestedFacet  # noqa: E402
from backend.app.services.reviewed_evidence import reviewed_support  # noqa: E402
from backend.app.services.teaching import TeachingStore  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_teacher(path):
    return TeachingStore(Settings(_env_file=None, enable_teaching=True,
        teaching_backend="lexical", teaching_release_path=path,
        teaching_explanations_sha256=""))


def stage(release, inspection, output):
    """Validate inspected whole units, publish a new inactive directory, return its report."""
    release, inspection, output = (Path(p).resolve() for p in (release, inspection, output))
    if output.exists():
        raise FileExistsError("immutable candidate output already exists")
    if output.is_relative_to(release) or output.is_relative_to(ROOT / "data/references"):
        raise ValueError("candidate output must stay outside source and active reference releases")
    manifest_bytes = (release / "manifest.json").read_bytes()
    inspection_bytes = inspection.read_bytes()
    annotations = [json.loads(line) for line in inspection_bytes.decode("utf-8-sig").splitlines() if line.strip()]
    if not annotations:
        raise ValueError("no actual inspected bindings were supplied")
    teacher = load_teacher(release)
    try:
        if teacher.error:
            raise ValueError("source TeachingStore rejected release: " + teacher.error)
        source_document = yaml.safe_load((release / "sources.yaml").read_text(encoding="utf-8"))
        registered = {source["source_id"]: source for source in source_document["sources"]}
        grouped, selected, seen = {}, {}, set()
        for annotation in annotations:
            if not isinstance(annotation, dict) or any(
                annotation.get(field) != value for field, value in (
                    ("review_status", "source_inspected"), ("review_origin", "ai_source_inspection"), ("reviewer", "Codex"))
            ) or any(not isinstance(annotation.get(field), str) or not annotation[field].strip()
                     for field in ("support_rationale", "qualification_note", "source_context")):
                raise ValueError("explicit Codex source-inspection origin and context are required")
            if any(field in annotation for field in ("attestation", "reviewer_institution", "human_review_confirmed")):
                raise ValueError("human attestation fields cannot enter an AI-inspection binding")
            if not all(isinstance(annotation.get(field), str) for field in ("topic_id", "facet", "scope")):
                raise ValueError("exact topic, facet and scope strings are required")
            row = teacher.references.id_records.get(annotation.get("chunk_id"))
            if row is None:
                raise ValueError("inspected chunk does not exist in admitted release")
            original_metadata = teacher.metadata.get(row.chunk_id, {})
            source = registered[row.source_id]
            if (teacher.review_flags.get(row.chunk_id) or source_reasons(row, original_metadata)
                    or source_reasons(row, source) or original_metadata.get("runtime_policy") == "exclude"):
                raise ValueError("existing source hold cannot be overridden by inspection")
            facet = RequestedFacet(topic_id=annotation["topic_id"], facet=annotation["facet"],
                scope=annotation["scope"], query="explicit inspection binding")
            context = copy.deepcopy(original_metadata)
            # Validate this supplied entry alone: earlier human/AI annotations
            # must never rescue a malformed new annotation.
            context.pop("reviewed_facet_bindings", None)
            context["ai_inspected_facet_bindings"] = [annotation]
            if not reviewed_support(facet, row, context):
                raise ValueError("inspection failed whole-unit/source/hash/qualification checks")
            key = (row.chunk_id, facet.topic_id, facet.facet, facet.scope)
            if key in seen:
                raise ValueError("duplicate inspected chunk/facet/scope")
            seen.add(key)
            grouped.setdefault(row.chunk_id, []).append(annotation)
            selected[row.chunk_id] = row
        records = [selected[key] for key in sorted(selected)]
        metadata = {}
        for row in records:
            metadata[row.chunk_id] = copy.deepcopy(teacher.metadata.get(row.chunk_id, {}))
            metadata[row.chunk_id]["ai_inspected_facet_bindings"] = grouped[row.chunk_id]
        sources, snapshot_checks = [], []
        for identity in sorted({row.source_id for row in records}):
            source = copy.deepcopy(registered[identity])
            source["record_checksums"] = [row.content_hash() for row in records if row.source_id == identity]
            # Preserve original source rights/approval and verify local rights
            # snapshots where the inherited register identifies their bytes.
            for path_field, hash_field in (("raw_snapshot_path", "raw_sha256"),
                                            ("license_snapshot_path", "license_snapshot_sha256")):
                if source.get(path_field):
                    path = (ROOT / source[path_field]).resolve()
                    if not path.is_relative_to(ROOT) or not path.is_file() or sha(path.read_bytes()) != source.get(hash_field):
                        raise ValueError("inherited source/rights snapshot bytes changed")
                    snapshot_checks.append({"source_id": identity, "kind": path_field, "sha256": source[hash_field]})
            sources.append(source)
        provenance = {"path": str(release), "version": teacher.version,
            "manifest_sha256": sha(manifest_bytes), "inspection_sha256": sha(inspection_bytes)}
        report = {"version": output.name, "records": len(records), "sources": len(sources),
            "inspected_bindings": len(annotations), "activation": "none", "index_built": False,
            "clinical_review": "pending_F03", "qualified_review_verified": False,
            "review_origin": "ai_source_inspection", "provenance": provenance,
            "verified_inherited_snapshot_bytes": snapshot_checks,
            "rights_notice": "Original per-source terms, attribution, NC/SA conditions and approvals are preserved. This candidate does not authorize redistribution, commercial use or training.",
            "source_rights_verification": "Existing admitted register and hashes retained; local raw/license bytes checked wherever inherited snapshot paths exist."}
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="mds-ai-inspected-", dir=output.parent) as temp:
            staging = Path(temp) / "pack"
            staging.mkdir()
            (staging / "records.jsonl").write_text("\n".join(row.model_dump_json() for row in records) + "\n", encoding="utf-8")
            (staging / "sources.yaml").write_text(yaml.safe_dump({"sources": sources}, sort_keys=False, allow_unicode=True), encoding="utf-8")
            (staging / "inspection.jsonl").write_bytes(inspection_bytes)
            for name, value in (("metadata.json", {"chunks": metadata}), ("stage-report.json", report)):
                (staging / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            names = ("records.jsonl", "sources.yaml", "metadata.json", "inspection.jsonl", "stage-report.json")
            manifest = {"schema_version": 1, "version": output.name, "records": len(records), "sources": len(sources),
                "status": "inactive_ai_inspected_development_candidate", "clinical_review": False, "faculty_review": "pending",
                "lineage": [provenance], "licenses": sorted({row.permission_basis.get("license", "unknown") for row in records}),
                "files": {name: sha((staging / name).read_bytes()) for name in names}}
            (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            candidate = load_teacher(staging)
            try:
                if candidate.error or len(candidate.records) != len(records):
                    raise ValueError("candidate TeachingStore rejected pack: " + str(candidate.error))
            finally:
                candidate.close()
            if (release / "manifest.json").read_bytes() != manifest_bytes or inspection.read_bytes() != inspection_bytes:
                raise ValueError("source release or inspection changed during staging")
            source_manifest = json.loads(manifest_bytes)
            for name, checksum in source_manifest["files"].items():
                path = (release / name).resolve()
                if not path.is_relative_to(release) or sha(path.read_bytes()) != checksum:
                    raise ValueError("source release contents changed during staging")
            if output.exists():
                raise FileExistsError("immutable candidate output appeared during staging")
            staging.rename(output)
        return report
    finally:
        teacher.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(stage(args.release, args.inspection, args.output), ensure_ascii=True, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "preflight_rejected", "activation": "none", "reason": str(exc)}))
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
