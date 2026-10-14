"""Create a new source-bound notes version with explicit audit holds."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import TeachingStore, validate_explanation_units  # noqa: E402


def build(base, components, audits, output, reviewed_components=()):
    base = Path(base)
    document = json.loads((base / "explanations.json").read_text(encoding="utf-8"))
    references, pins = {}, {}
    for path in [base, *map(Path, components)]:
        store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_release_path=path))
        if store.error:
            raise ValueError(store.error)
        references.update(store.references.id_records)
        pins[str(path.resolve())] = hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest()
        store.close()
    reviewed_records = {}
    for path in map(Path, reviewed_components):
        pins[str(path.resolve())] = hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest()
        reviewed_records.update({row["chunk_id"]: row for row in (json.loads(line) for line in (path / "records.jsonl").read_text(encoding="utf-8").splitlines())})
    existing = {flag["chunk_id"]: flag for flag in document["source_review_flags"]}
    absent = []
    for audit in map(Path, audits):
        pins[str(audit.resolve())] = hashlib.sha256(audit.read_bytes()).hexdigest()
        for finding in json.loads(audit.read_text(encoding="utf-8"))["source_holds"]:
            key = finding["chunk_id"]
            matched = [references[key]] if key in references else []
            if not matched and key in reviewed_records:
                old = reviewed_records[key]
                candidates = [row for row in references.values() if row.source_id == old["source_id"] and row.section == old["section"]]
                matched = [row for row in candidates if row.text == old["text"]] or candidates
            if not matched:
                if key not in reviewed_records:
                    raise ValueError("Audit identity not found; provide the reviewed component: " + key)
                absent.append({"chunk_id": key, "reason": "Reviewed section absent from selected components.", "audit": str(audit)})
            for row in matched:
                existing[row.chunk_id] = {"chunk_id": row.chunk_id, "content_sha256": row.content_hash(),
                                         "reviewed_chunk_id": key,
                                         "runtime_policy": finding["recommended_runtime_policy"], "reason": finding["reason"],
                                         "medical_counterevidence_urls": finding.get("medical_counterevidence_urls", []),
                                         "clinical_review": False, "faculty_decision": None}
    additions = [
        {"id": "audit-free-bound-drug", "topics": ["free drug", "protein binding", "drug distribution", "protein-bound drug"],
         "text": "Free drug is the unbound portion dissolved in plasma water. It can cross cell membranes and produce effects. Protein-bound drug can act as a reservoir that releases drug slowly and prolongs its action. This explains the role of protein binding in drug distribution; the amount available to tissues and the reserve released over time both matter.",
         "citation_ids": ["chunk_33c108fbd442f97275875a6b"], "qualifications": ["can"]},
        {"id": "audit-metabolism-lifespan", "topics": ["liver metabolism", "hepatic metabolism", "drug metabolism", "microsomal enzymes"],
         "text": "In infants and young children, the developing liver produces decreased levels of microsomal enzymes. This may reduce their ability to metabolize medications. Older children may have increased metabolism as hepatic enzymes mature. Drug metabolism may also be impaired due to liver damage, because medicines are broken down less efficiently. These are general lifespan and liver-function concepts, without personal dosing advice.",
         "citation_ids": ["chunk_43a5607bdd134996d92a90a0"], "qualifications": ["may", "without personal dosing advice"]},
    ]
    for unit in additions:
        rows = [references[key] for key in unit["citation_ids"]]
        unit.update(source_hashes={row.chunk_id: row.content_hash() for row in rows},
                    reviewer="Developer comparison of bounded source claims; no faculty validation",
                    review_status="developer_reviewed", clinical_review=False,
                    attribution=[{"publisher": row.publisher, "title": row.title, "url": row.url,
                                  "license": row.permission_basis["license"], "license_url": row.permission_basis["license_url"],
                                  "changes": "Plain-language adaptation; omitted dosing instructions and unsupported generalizations."} for row in rows])
        for row in rows:
            existing[row.chunk_id] = {"chunk_id": row.chunk_id, "content_sha256": row.content_hash(),
                                      "runtime_policy": "explanation_only", "reason": "Use the bounded explanation; full context includes clinical dosing narrative or irrelevant examples.",
                                      "clinical_review": False, "faculty_decision": None}
    excluded = {key for key, flag in existing.items() if flag["runtime_policy"] == "exclude"}
    removed = [unit["id"] for unit in document["units"] if set(unit["citation_ids"]) & excluded]
    document["units"] = [unit for unit in document["units"] if unit["id"] not in removed] + additions
    validate_explanation_units(document["units"], references)
    document["source_review_flags"] = list(existing.values())
    document["comprehensive_audit"] = {"input_hashes": pins, "absent_reviewed_chunks": absent,
                                       "units_removed_due_to_source_exclusion": removed, "faculty_review": "pending"}
    with Path(output).open("x", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return {"units": len(document["units"]), "holds": len(existing), "absent": len(absent), "removed_units": removed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--component", type=Path, action="append", default=[])
    parser.add_argument("--audit", type=Path, action="append", required=True)
    parser.add_argument("--reviewed-component", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.base, args.component, args.audit, args.output, args.reviewed_component)))
