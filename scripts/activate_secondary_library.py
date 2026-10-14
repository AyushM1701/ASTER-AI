"""Validate and pin the unverified secondary layer while retaining rollback state."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402
from backend.app.services.secondary_references import SecondaryReferenceStore  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    if args.disable:
        changes = {"ENABLE_SECONDARY_REFERENCES": "false"}
        result = {"enabled": False, "restart_required": True}
    else:
        if not args.release:
            parser.error("Supply --release or --disable")
        release = args.release.resolve()
        digest = hashlib.sha256((release / "manifest.json").read_bytes()).hexdigest()
        refs = SecondaryReferenceStore(Settings(enable_secondary_references=True, secondary_reference_path=release, secondary_manifest_sha256=digest))
        if refs.error:
            parser.error(refs.error)
        changes = {"ENABLE_SECONDARY_REFERENCES": "true", "SECONDARY_REFERENCE_PATH": str(release), "SECONDARY_MANIFEST_SHA256": digest}
        result = {**refs.manifest(), "restart_required": True}
    env = ROOT / ".env"
    current = env.read_text(encoding="utf-8")
    backup = ROOT / ".env.before-secondary"
    if not backup.exists():
        backup.write_text(current, encoding="utf-8")
    retained = [line for line in current.splitlines() if line.split("=", 1)[0] not in changes]
    env.write_text("\n".join([*retained, *(f"{key}={value}" for key, value in changes.items())]) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
