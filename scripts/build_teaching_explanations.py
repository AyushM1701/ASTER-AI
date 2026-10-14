"""Bind manually authored teaching notes to an immutable source release."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.teaching import TeachingStore, validate_explanation_units  # noqa: E402


def build(release, output):
    store = TeachingStore(Settings(enable_teaching=True, teaching_release_path=release, teaching_backend="lexical", teaching_explanations_sha256=""))
    if store.error:
        raise ValueError(store.error)
    spec = json.loads((ROOT / "configs/teaching_explanations_v1.json").read_text(encoding="utf-8"))
    units = []
    for authored in spec["units"]:
        rows = []
        for source_id, section in authored["sources"]:
            found = [r for r in store.records if r.source_id == source_id and r.section == section]
            if len(found) != 1:
                raise ValueError(f"Manual explanation source is ambiguous or absent: {source_id}/{section}")
            rows.extend(found)
        unit = {k: v for k, v in authored.items() if k != "sources"}
        unit.update(citation_ids=[r.chunk_id for r in rows], source_hashes={r.chunk_id: r.content_hash() for r in rows},
                    reviewer="Developer source comparison", review_status="developer_reviewed", clinical_review=False,
                    review_scope=spec["review_scope"], attribution=[{"publisher": r.publisher, "title": r.title, "url": r.url,
                    "license": r.permission_basis.get("license"), "license_url": r.permission_basis.get("license_url")} for r in rows])
        units.append(unit)
    flags = []
    concerns = [
        ("aldolase B", "explanation_only", "Generic glycolysis description specifies aldolase B without tissue context; enzyme isoform detail needs faculty review."),
        ("not required for oxidative phosphorylation", "exclude", "Complex II wording may overstate its dispensability; hold the complete passage pending faculty review."),
        ("only cells that do not", "exclude", "Absolute MHC-I exception wording needs immunology review."),
        ("vomiting center in the cerebellum", "exclude", "Vomiting centre anatomical location is questionable; hold the complete passage."),
        ("a type of apoptosis", "exclude", "Pyroptosis classification wording needs pathology review."),
        ("This concept is broadly termed as drug bioavailability", "exclude", "Receptor-binding discussion appears to misdefine bioavailability; use the separately supported PK/PD distinction."),
        ('they have no “memory”', "explanation_only", "Absolute innate-memory wording omits the nuance of trained immunity; do not copy this passage into detailed answers."),
    ]
    for row in store.records:
        for phrase, policy, reason in concerns:
            if phrase.casefold() in row.text.casefold():
                flags.append({"chunk_id": row.chunk_id, "content_sha256": row.content_hash(), "runtime_policy": policy,
                              "reason": reason, "clinical_review": False, "faculty_decision": None})
    validate_explanation_units(units, store.references.id_records)
    value = {"schema_version": 1, "release_version": store.version, "review_scope": spec["review_scope"],
             "clinical_review": False, "faculty_review": "pending", "units": units, "source_review_flags": flags}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return {"path": str(output), "units": len(units), "source_review_flags": len(flags), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.release, args.output), indent=2))
