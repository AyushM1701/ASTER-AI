"""Register a locally reviewed asset; metadata must come from reliable provenance."""

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.xray import validate_asset  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--view", choices=["AP", "PA"], required=True)
    parser.add_argument("--patient-group", required=True)
    parser.add_argument("--partition", choices=["development", "test", "demo"], required=True)
    parser.add_argument(
        "--reviewed-adult-deidentified",
        action="store_true",
        required=True,
        help="Attest you verified adult/view, de-identification, permitted use and supported input",
    )
    args = parser.parse_args()
    settings = Settings()
    path = args.path.resolve()
    asset = {
        "asset_id": args.asset_id,
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source": args.source,
        "license": args.license,
        "view": args.view,
        "adult": True,
        "supported_input_review": True,
        "deidentified": True,
        "patient_group": args.patient_group,
        "partition": args.partition,
    }
    validate_asset(asset, settings)
    manifest = yaml.safe_load(settings.xray_manifest.read_text(encoding="utf-8"))
    if any(a["asset_id"] == args.asset_id for a in manifest["assets"]):
        parser.error("Asset ID exists; register a new version after changes.")
    manifest["assets"].append(asset)
    settings.xray_manifest.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    print("Registered verified asset. Restart the API to load the new manifest.")


if __name__ == "__main__":
    main()
