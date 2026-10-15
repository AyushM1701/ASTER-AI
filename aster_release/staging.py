"""Allowlisted staging; never copy development .env, uploads or backups."""
import argparse
import csv
import fnmatch
import json
import shutil
from pathlib import Path

from aster_release.release import (
    ReleaseError,
    check_rights,
    contained,
    generate_manifest,
    needs_encoder,
    read_json,
    verify_package,
)


def inventory(source, profile):
    source = Path(source).resolve()
    pairs = []
    def add(path, destination=None):
        if not path.is_file() or path.is_symlink():
            raise ReleaseError(f"Required staging input is absent or symlinked: {path}")
        relative = destination or path.relative_to(source).as_posix()
        contained(source, relative)
        pairs.append((path, relative))
    def tree(relative):
        base = contained(source, relative)
        if not base.is_dir():
            raise ReleaseError(f"Required asset folder absent: {relative}")
        for path in sorted(base.rglob("*")):
            if path.is_file() and not any(p in {".cache", "__pycache__"} for p in path.parts):
                add(path)
    settings = profile["settings"]
    for field in ("corpus_path", "source_register"):
        add(contained(source, settings[field]))
    primary = contained(source, settings["source_register"]).parent
    for name in ("india_catalog.json", "manifest.json"):
        if (primary / name).is_file():
            add(primary / name)
    if settings["retrieval_backend"] == "hybrid":
        tree(settings["chroma_path"])
    if needs_encoder(profile):
        tree(settings["embedding_path"])
    if settings["enable_teaching"]:
        tree(settings["teaching_release_path"])
        if settings.get("teaching_backend", "lexical") == "hybrid":
            tree(settings["teaching_index_path"])
    if settings["enable_secondary_references"]:
        tree(settings["secondary_reference_path"])
    tree("frontend/web")
    add(source / "configs/explanation_layouts.json")
    add(source / "data/samples/synthetic_prescription.png")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "SECURITY.md", "CHANGELOG.md"):
        add(source / name)
    # Only this pinned model's manifest and all its referenced layers; exclude other downloaded models.
    store = contained(source, profile["model"]["store"])
    model_manifest = store / "manifests/registry.ollama.ai/library/qwen3-vl/2b-instruct"
    add(model_manifest)
    model = read_json(model_manifest)
    for layer in [model["config"], *model["layers"]]:
        add(store / "blobs" / layer["digest"].replace(":", "-"))
    runtime = source / "runtime/ollama"
    if not runtime.is_dir():
        runtime = source / "data/models/ollama-runtime"
    if not (runtime / "ollama.exe").is_file():
        raise ReleaseError("Required standalone Ollama runtime absent")
    for path in sorted(runtime.rglob("*")):
        if path.is_file():
            add(path, "runtime/ollama/" + path.relative_to(runtime).as_posix())
    tesseract = source / "runtime/tesseract"
    if not tesseract.is_dir():
        if profile.get("edition") != "ValidationOnly":
            raise ReleaseError("Distributable builds require provisioned runtime/tesseract assets")
        tesseract = Path("C:/Program Files/Tesseract-OCR")
    for path in [tesseract / "tesseract.exe", *sorted(tesseract.glob("*.dll")), tesseract / "tessdata/eng.traineddata"]:
        add(path, "runtime/tesseract/" + path.relative_to(tesseract).as_posix())
    # Deduplicate source register also present in optional trees.
    return sorted({name: (path, name) for path, name in pairs}.values(), key=lambda p: p[1])


def reviewed_components(csv_path):
    with Path(csv_path).open(encoding="utf-8", newline="") as stream:
        result = list(csv.DictReader(stream))
    for item in result:
        for key in ("redistribution_allowed", "modification_allowed"):
            item[key] = item[key].strip().lower() == "true"
    return result


def selected_components(source, profile, pairs):
    names = [name for _, name in pairs] + ["Aster.exe", "_internal/python313.dll",
        "bin/aster-api/aster-api.exe", "bin/aster-api/_internal/python313.dll",
        "bin/aster-web/aster-web.exe", "bin/aster-web/_internal/python313.dll"]
    return [item for item in reviewed_components(source / "packaging/asset-rights.csv")
            if any(fnmatch.fnmatchcase(name, item["path_glob"]) for name in names)]


def stage(source, destination, profile_path, edition="ValidationOnly", frozen=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination == source or source.is_relative_to(destination):
        raise ReleaseError("Staging directory cannot contain the source workspace")
    if destination.exists() and any(destination.iterdir()):
        raise ReleaseError("Use a new empty staging directory; existing builds are never overwritten")
    profile = read_json(profile_path)
    profile["edition"] = edition
    pairs = inventory(source, profile)
    profile["components"] = selected_components(source, profile, pairs)
    check_rights(profile)  # PUBLIC/PRIVATE rights gate before copying a single byte
    if frozen:
        frozen = Path(frozen).resolve()
        for folder, target in [("Aster", ""), ("aster-api", "bin/aster-api"), ("aster-web", "bin/aster-web")]:
            expected_exe = "Aster.exe" if folder == "Aster" else folder + ".exe"
            if not (frozen / folder / expected_exe).is_file():
                raise ReleaseError("Frozen component is missing: " + folder)
            for path in (frozen / folder).rglob("*"):
                if path.is_file():
                    name = "/".join(filter(None, [target, path.relative_to(frozen / folder).as_posix()]))
                    pairs.append((path, name))
        # API and web use independent onedir runtimes. Small root executable stubs below use fixed paths.
        profile["entrypoints"] = {"api": "bin/aster-api/aster-api.exe", "web": "bin/aster-web/aster-web.exe"}
    required = sum(path.stat().st_size for path, _ in pairs)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < required + 512 * 1024**2:
        raise ReleaseError("Insufficient disk space for staging plus safety margin")
    destination.mkdir(exist_ok=True)
    for path, name in pairs:
        output = contained(destination, name)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, output)
    manifest = generate_manifest(destination, profile)
    verify_package(destination)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=Path("packaging/release-profile.json"))
    parser.add_argument("--edition", choices=["ValidationOnly", "PublicStandard", "PrivateAuthorized"], default="ValidationOnly")
    parser.add_argument("--frozen", type=Path)
    args = parser.parse_args()
    manifest = stage(args.source, args.output, args.profile, args.edition, args.frozen)
    print(json.dumps({"edition": manifest["edition"], "files": len(manifest["files"]), "bytes": sum(f["size"] for f in manifest["files"])}, indent=2))
