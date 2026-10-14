"""Record code changes against the pre-upgrade checkpoint, without secrets."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "artifacts/checkpoints/mds-upgrade-2026-10-11"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original = json.loads((CHECKPOINT / "checkpoint.json").read_text(encoding="utf-8"))
    baseline = {row["path"].replace("\\", "/"): row["sha256"] for row in original["files"]}
    changed = []
    for name, previous in baseline.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError("checkpoint path escapes workspace")
        current = sha(path) if path.is_file() else None
        if current != previous:
            changed.append({"path": name, "before_sha256": previous, "after_sha256": current})
    added, existing_uncaptured = [], []
    for directory in ("backend", "frontend", "scripts", "configs", "tests"):
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            name = path.relative_to(ROOT).as_posix()
            if name not in baseline:
                record = {"path": name, "sha256": sha(path)}
                # The baseline deliberately copied source files, not fonts,
                # icons or prompt assets. Their omission never means new work.
                if name.startswith(("backend/app/prompts/", "frontend/web/")):
                    existing_uncaptured.append(record)
                else:
                    added.append(record)
    reports = ["README.md", "docs/MDS_IMPLEMENTATION_2026-10-11.md", "docs/MDS_EVALUATION_2026-10-11.md", "docs/MDS_OPEN_CORPUS_2026-10-11.md", "docs/MDS_STAGED_PACKS_2026-10-11.md", "docs/superpowers/plans/2026-10-11-mds-evidence-upgrade.md"]
    result = {"date": "2026-10-11", "git": "unavailable", "changed_existing": changed,
              "new_upgrade_files": added,
              "existing_assets_outside_checkpoint_preserve": existing_uncaptured,
              "reports_current_hashes": [{"path": p, "sha256": sha(ROOT / p)} for p in reports],
              "clinical_review": "pending_F03", "source_readiness": "failed_150_task_gate",
              "protected_assets": "No .env contents recorded; production source/index bytes are verified by the locked evaluation source manifest. No active import, training, upload or publication.",
              "rollback": "Preserve newer work; compare hashes before restoring individual changed files from the checkpoint. Do not overwrite secrets, source releases, active indexes or unrelated later changes."}
    (CHECKPOINT / "change-inventory.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    from backend.app.services.mds_curriculum import registry

    destination = ROOT / "artifacts/evaluation/mds-upgrade-2026-10-11/curriculum-registry.json"
    destination.write_text(json.dumps(registry(), indent=2), encoding="utf-8")
    print(json.dumps({"changed_existing": len(changed), "added_monitored": len(added), "source_readiness": result["source_readiness"]}))


if __name__ == "__main__":
    # Running as a script needs the same project import root as other tools.
    import sys

    sys.path.insert(0, str(ROOT))
    main()
