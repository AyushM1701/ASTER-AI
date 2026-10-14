"""Preserve the corpus and withhold a disputed inherited dentin classification unit."""

import hashlib
import json
import shutil
from pathlib import Path

from backend.app.services.retrieval import Reference

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/references/mds/releases/aster-teaching-all-mds-v2-2026-10-10"
VERSION = "aster-teaching-all-mds-v3-2026-10-10"
HELD = "chunk_e9a8236cee2f5b0382dcd5fc"


def main():
    output = BASE.parent / VERSION
    if output.exists():
        raise ValueError("Use a new revision; never overwrite a release")
    manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        if hashlib.sha256((BASE / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Base artifact changed")
    row = next(Reference.model_validate(json.loads(line)) for line in
               (BASE / "records.jsonl").read_text(encoding="utf-8").splitlines()
               if json.loads(line)["chunk_id"] == HELD)
    notes = json.loads((BASE / "explanations.json").read_text(encoding="utf-8"))
    assert not any(HELD in unit["citation_ids"] for unit in notes["units"])
    notes["release_version"] = VERSION
    notes["source_review_flags"].append({
        "chunk_id": HELD, "content_sha256": row.content_hash(), "runtime_policy": "exclude",
        "reason": "Developer appraisal hold: primary dentin timing is equated with eruption, and reactionary dentin is equated with sclerotic dentin. These simplifications need independent dental review; the whole unit is withheld, not silently rewritten.",
        "clinical_review": False, "faculty_decision": None,
        "comparison_references": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC2100295/",
                                  "https://pubmed.ncbi.nlm.nih.gov/7626417/",
                                  "https://www.ncbi.nlm.nih.gov/books/NBK549878/"],
    })
    output.mkdir()
    for name in manifest["files"]:
        shutil.copy2(BASE / name, output / name)
    (output / "explanations.json").write_text(json.dumps(notes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest["version"] = VERSION
    manifest["files"]["explanations.json"] = hashlib.sha256((output / "explanations.json").read_bytes()).hexdigest()
    manifest["lineage"].append({"path": str(BASE), "version": json.loads((BASE / "manifest.json").read_text(encoding="utf-8"))["version"],
                                "manifest_sha256": hashlib.sha256((BASE / "manifest.json").read_bytes()).hexdigest(),
                                "change": "Additional source appraisal hold; source records and dense vectors unchanged"})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"release": str(output), "held_chunk": HELD, "source_review_holds": len(notes["source_review_flags"])}, indent=2))


if __name__ == "__main__":
    main()
