"""Immutable segmented archives with a trust hash embedded into AsterSetup."""
import argparse
import json
import re
import zipfile
from pathlib import Path

from aster_release.release import ReleaseError, sha256, verify_package

MAX_PART = 1800 * 1024**2  # strictly under GitHub's 2 GiB limit


def split_archive(archive, output, part_size=MAX_PART):
    if not 1024 <= part_size < 2 * 1024**3:
        raise ReleaseError("Parts must be between 1 KiB and strictly under 2 GiB")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    parts = []
    with Path(archive).open("rb") as stream:
        number = 1
        while True:
            block = stream.read(min(part_size, 4 * 1024**2))
            if not block:
                break
            path = output / f"Aster-Windows-x64.zip.part{number:03}"
            if path.exists():
                raise ReleaseError("Release parts are immutable; choose a new output directory")
            remaining = part_size
            with path.open("wb") as target:
                while block:
                    target.write(block)
                    remaining -= len(block)
                    if not remaining:
                        break
                    block = stream.read(min(remaining, 4 * 1024**2))
            parts.append({"name": path.name, "size": path.stat().st_size, "sha256": sha256(path)})
            number += 1
    return parts


def create_distribution(root, output, repository, tag, part_size=MAX_PART):
    report = verify_package(root)
    if report["edition"] == "ValidationOnly":
        raise ReleaseError("ValidationOnly builds must not be distributed")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not re.fullmatch(r"v[0-9][A-Za-z0-9_.-]*", tag):
        raise ReleaseError("Invalid pinned repository or release tag")
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root):
        raise ReleaseError("Release output must be outside installation")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "Aster-Offline-Windows-x64.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=5, allowZip64=True) as bundle:
        for item in report["manifest"]["files"]:
            bundle.write(root / item["path"], item["path"])
        bundle.write(root / "release-manifest.json", "release-manifest.json")
    parts = split_archive(archive, output, part_size)
    base = f"https://github.com/{repository}/releases/download/{tag}/"
    for part in parts:
        part["url"] = base + part["name"]
    dist = {"schema_version": 1, "app_version": report["manifest"]["app_version"],
            "edition": report["edition"], "parts": parts, "archive_sha256": sha256(archive),
            "archive_bytes": archive.stat().st_size, "installed_bytes": report["bytes"],
            "release_manifest_sha256": report["manifest_sha256"]}
    path = output / "distribution.json"
    path.write_text(json.dumps(dist, indent=2) + "\n", encoding="utf-8")
    trust = {"url": base + "distribution.json", "sha256": sha256(path)}
    (output / "installer-trust.json").write_text(json.dumps(trust, indent=2) + "\n", encoding="utf-8")
    checks = [f"{sha256(p)}  {p.name}" for p in sorted(output.iterdir()) if p.is_file() and p.name != "installer-trust.json"]
    (output / "SHA256SUMS.txt").write_text("\n".join(checks) + "\n", encoding="utf-8")
    return dist


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", default="AyushM1701/ASTER-AI")
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    print(json.dumps(create_distribution(args.root, args.output, args.repository, args.tag), indent=2))
