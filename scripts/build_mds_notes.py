"""Bind bounded dental explanations and known source holds; preserve old notes."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import TeachingStore, validate_explanation_units  # noqa: E402


def build(base, component, spec, output, additional_components=()):
    document = json.loads(Path(base).read_text(encoding="utf-8"))
    definitions = json.loads(Path(spec).read_text(encoding="utf-8"))
    store = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical",
                                   teaching_release_path=Path(component), teaching_explanations_sha256=""))
    if store.error:
        raise ValueError(store.error)
    if hashlib.sha256((Path(component) / "manifest.json").read_bytes()).hexdigest() != definitions["component_manifest_sha256"]:
        raise ValueError("Dental component identity changed")
    references = dict(store.references.id_records)
    for path in map(Path, additional_components):
        expected = definitions.get("additional_component_manifests", {}).get(path.name)
        if hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest() != expected:
            raise ValueError("Additional note component identity changed")
        other = TeachingStore(Settings(_env_file=None, enable_teaching=True, teaching_backend="lexical",
                                       teaching_release_path=path, teaching_explanations_sha256=""))
        if other.error or set(references) & set(other.references.id_records):
            raise ValueError("Additional component rejected or duplicate identity: " + str(other.error))
        references.update(other.references.id_records)
        other.close()
    units = []
    for authored in definitions["units"]:
        rows = [references[key] for key in authored["citation_ids"]]
        unit = dict(authored, source_hashes={row.chunk_id: row.content_hash() for row in rows},
                    reviewer="Developer source comparison; bounded claims only, no faculty validation",
                    review_status="developer_reviewed", clinical_review=False,
                    attribution=[{"publisher": row.publisher, "title": row.title, "url": row.url,
                                  "license": row.permission_basis["license"], "license_url": row.permission_basis["license_url"],
                                  "changes": "Plain-language adaptation of the explicitly supported claims; attribution retained."} for row in rows])
        units.append(unit)
    validate_explanation_units(units, references)
    flags = []
    for authored in definitions["holds"]:
        row = references[authored["chunk_id"]]
        flags.append(dict(authored, content_sha256=row.content_hash(), clinical_review=False, faculty_decision=None))
    if len({flag["chunk_id"] for flag in flags}) != len(flags):
        raise ValueError("Duplicate dental hold")
    document["units"].extend(units)
    document["source_review_flags"].extend(flags)
    document["mds_note_review"] = {"component_manifest_sha256": definitions["component_manifest_sha256"],
                                   "clinical_review": False, "faculty_review": "pending",
                                   "limitations": "Bounded source comparison does not establish whole-source or clinical accuracy."}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
    store.close()
    return {"units": len(document["units"]), "holds": len(document["source_review_flags"]), "output": str(output)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--component", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=ROOT / "configs/mds_plain_notes.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--additional-component", type=Path, action="append", default=[])
    args = parser.parse_args()
    print(json.dumps(build(args.base, args.component, args.spec, args.output, args.additional_component)))
