"""CI copies only approved immutable data from a preverified asset installation."""
import argparse
import shutil
from pathlib import Path

from aster_release.release import ReleaseError, contained, sha256, verify_package


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    report = verify_package(args.source)
    if report["edition"] != "PublicStandard":
        raise ReleaseError("CI public provisioning requires a rights-approved public asset installation")
    for item in report["manifest"]["files"]:
        if item["path"].startswith(("data/", "configs/", "runtime/ollama/", "runtime/tesseract/")):
            source = contained(args.source, item["path"])
            target = contained(args.destination, item["path"])
            if target.exists() and (target.stat().st_size != item["size"] or sha256(target) != item["sha256"]):
                raise ReleaseError("Provisioned data differs from committed configuration")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


if __name__ == "__main__":
    main()
