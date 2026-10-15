"""Build preflight captures evidence before expensive freezing or copying."""
import argparse
import fnmatch
import importlib.metadata
import json
from pathlib import Path

from aster_release.release import ReleaseError, check_rights, read_json, sha256
from aster_release.staging import inventory, reviewed_components, selected_components


def check_bootstrap_rights(root):
    components = [item for item in reviewed_components(Path(root) / "packaging/asset-rights.csv")
                  if fnmatch.fnmatchcase("installer/AsterSetup-Windows-x64.exe", item["path_glob"])]
    if not components:
        raise ReleaseError("Bootstrapper has no runtime rights coverage")
    check_rights({"edition": "PublicStandard", "components": components})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--edition", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    profile = read_json(root / "packaging/release-profile.json")
    profile.update(edition=args.edition, app_version=args.version)
    items = inventory(root, profile)
    profile["components"] = selected_components(root, profile, items)
    check_rights(profile)
    if args.edition != "ValidationOnly":
        check_bootstrap_rights(root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    report = {"edition": args.edition, "version": args.version, "assets": [
        {"path": name, "size": path.stat().st_size, "sha256": sha256(path)} for path, name in items],
        "dependencies": sorted({dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}.items())}
    (args.output / "build-inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(items), "asset_bytes": sum(x["size"] for x in report["assets"]), "edition": args.edition}, indent=2))


if __name__ == "__main__":
    main()
