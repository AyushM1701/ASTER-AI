"""Build a v2 Aster release candidate (developer/CI machine only).

    python packaging/build_release.py --version 0.2.0-rc.1 --library-version 2026.10.15 [--skip-freeze]

Outputs under artifacts/release-v2/<version>/:
  assets/      every file to upload to the GitHub Release (components, model blobs,
               library packs, AsterSetup-Windows-x64.exe, release-lock.json(.sig), notices)
  stage/       component staging trees (inspectable)
and updates the source tree's trust roots: release/release-lock.json and
release/bootstrap-pin.json (pinned setup hash used by "Start Aster.cmd").
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PART_BYTES = 1_900_000_000  # below GitHub's 2 GiB per-asset limit
OLLAMA_SOURCE = ROOT / "data/models/ollama-runtime"
TESSERACT_SOURCES = [ROOT / "artifacts/release/Aster β's portable/runtime/tesseract", Path("C:/Program Files/Tesseract-OCR")]
OLLAMA_MODELS = Path(os.environ.get("OLLAMA_MODELS") or (ROOT / "data/models/ollama-store" if (ROOT / "data/models/ollama-store").exists() else Path.home() / ".ollama/models"))
REPO_URL = "https://github.com/AyushM1701/ASTER-AI"
CONFIGS = ["medical_source_inventory.v2.json", "all_mds_topics.json", "explanation_layouts.json", "mds_full_curriculum.json",
           "xray_gates.json", "xray_weights.json", "xray_assets.release.yaml", "library/query_plan.json", "library/drug_list.json",
           "release/signing-public-key.pem"]


def log(message):
    print(time.strftime("%H:%M:%S"), message, flush=True)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(8 << 20):
            digest.update(block)
    return digest.hexdigest()


def run(*cmd, env=None, cwd=ROOT):
    log("$ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, cwd=cwd, env=env)


# ----------------------------------------------------------------------------- freeze
def freeze(out):
    env_dir = out / "build-env"
    python = env_dir / "Scripts/python.exe"
    if not python.exists():
        run(sys.executable, "-m", "venv", env_dir)
        run(python, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", ROOT / "packaging/requirements-runtime-v2.in",
            "pyinstaller==6.22.3", "pyinstaller-hooks-contrib==2026.8")
    run(python, "-m", "pip", "check")
    frozen = out / "frozen"
    for spec in ("aster-launcher.spec", "aster-api-v2.spec", "aster-web.spec"):
        run(python, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", frozen, "--workpath", out / "work" / spec,
            ROOT / "packaging" / spec)
    return frozen, python


# ----------------------------------------------------------------------------- staging
def copy_tree(source, target, *, skip=()):
    for path in sorted(Path(source).rglob("*")):
        rel = path.relative_to(source)
        if any(part in skip for part in rel.parts) or not path.is_file():
            continue
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def stage_app(stage, frozen, version):
    app = stage / "app"
    shutil.rmtree(app, ignore_errors=True)
    copy_tree(frozen / "Aster", app)
    copy_tree(frozen / "aster-api", app / "bin/aster-api")
    copy_tree(frozen / "aster-web", app / "bin/aster-web")
    copy_tree(ROOT / "frontend/web", app / "frontend/web")
    for name in CONFIGS:
        source = ROOT / "configs" / name
        (app / "configs" / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, app / "configs" / name)
    for name in ("synthetic_prescription.png", "synthetic_ground_truth.json", "nih-demo-00000001_000.png"):
        (app / "data/samples").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "data/samples" / name, app / "data/samples" / name)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "SECURITY.md", "README.md"):
        shutil.copy2(ROOT / name, app / name)
    shutil.copytree(ROOT / "packaging/notices", app / "notices", dirs_exist_ok=True)
    collect_python_licenses(frozen.parent / "build-env", app / "notices/python-packages")
    return app


def collect_python_licenses(env_dir, target):
    """Copy licence/notice files of every distribution installed in the frozen build environment."""
    site = env_dir / "Lib/site-packages"
    for dist in sorted(site.glob("*.dist-info")):
        name = dist.name.split("-")[0]
        files = [p for p in dist.rglob("*") if p.is_file() and p.name.upper().startswith(("LICEN", "COPYING", "NOTICE", "AUTHORS"))]
        for path in files:
            dest = target / name / path.relative_to(dist)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        if not files:
            metadata = (dist / "METADATA").read_text(encoding="utf-8", errors="ignore") if (dist / "METADATA").exists() else ""
            lines = [line for line in metadata.splitlines() if line.startswith(("Name:", "Version:", "License", "Classifier: License"))]
            (target / name).mkdir(parents=True, exist_ok=True)
            (target / name / "LICENSE-METADATA.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def stage_models(stage):
    models = stage / "models"
    shutil.rmtree(models, ignore_errors=True)
    minilm = models / "data/models/minilm"
    for name in ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt", "config.json", "README.md",
                 "aster-model-manifest.json", "onnx/model.onnx"):
        (minilm / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "data/models/minilm" / name, minilm / name)
    copy_tree(ROOT / "data/models/nli-deberta-v3-xsmall", models / "data/models/nli-deberta-v3-xsmall")
    copy_tree(ROOT / "data/models/medcpt-cross-encoder", models / "data/models/medcpt-cross-encoder")
    copy_tree(ROOT / "data/models/xray/onnx", models / "data/models/xray/onnx")
    return models


def stage_ollama(stage):
    cpu, cuda = stage / "ollama-cpu", stage / "ollama-cuda"
    for path in (cpu, cuda):
        shutil.rmtree(path, ignore_errors=True)
    for path in sorted(OLLAMA_SOURCE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(OLLAMA_SOURCE)
        is_gpu = any(part.startswith(("cuda_", "rocm", "vulkan", "mlx")) for part in rel.parts)
        target = (cuda if is_gpu else cpu) / "runtime/ollama" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return cpu, cuda


def stage_tesseract(stage):
    out = stage / "tesseract"
    shutil.rmtree(out, ignore_errors=True)
    source = next(p for p in TESSERACT_SOURCES if (p / "tesseract.exe").exists())
    for path in sorted(source.iterdir()):
        # The OCR engine plus every DLL it may load; training tools (other .exe files) are omitted.
        if path.is_file() and (path.suffix.lower() == ".dll" or path.name.lower() == "tesseract.exe"):
            target = out / "runtime/tesseract" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    tessdata = Path("C:/Program Files/Tesseract-OCR/tessdata")
    for name in ("eng.traineddata", "osd.traineddata"):
        target = out / "runtime/tesseract/tessdata" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tessdata / name, target)
    shutil.copy2(ROOT / "packaging/notices/TESSERACT-NOTICE.md", out / "runtime/tesseract/NOTICE.md")
    return out


# ----------------------------------------------------------------------------- packaging
def deterministic_zip(source, archive, compress=True):
    archive.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED, compresslevel=6) as handle:
        for path in sorted(Path(source).rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
                info.external_attr = 0o644 << 16
                with path.open("rb") as src, handle.open(info, "w", force_zip64=True) as dst:
                    shutil.copyfileobj(src, dst, 8 << 20)
                total += path.stat().st_size
    return total


def split(path, assets):
    """Return part descriptors; files below the limit stay whole."""
    size = path.stat().st_size
    if size <= PART_BYTES:
        final = assets / path.name
        if path != final:
            shutil.move(path, final)
        return [{"file": final.name, "bytes": final.stat().st_size, "sha256": sha256(final)}]
    parts = []
    with path.open("rb") as source:
        index = 1
        while True:
            chunk_path = assets / f"{path.name}.part{index:03d}"
            written = 0
            with chunk_path.open("wb") as out:
                while written < PART_BYTES and (block := source.read(min(8 << 20, PART_BYTES - written))):
                    out.write(block)
                    written += len(block)
            if not written:
                chunk_path.unlink()
                break
            parts.append({"file": chunk_path.name, "bytes": written, "sha256": sha256(chunk_path)})
            index += 1
    return parts


def zip_component(component_id, source, assets, work, version, *, dest=".", profiles=("*",), compress=True, extra=None):
    archive = work / f"aster-{component_id}-{version}.zip"
    unpacked = deterministic_zip(source, archive, compress)
    whole_hash, whole_size = sha256(archive), archive.stat().st_size
    parts = split(archive, assets)
    log(f"component {component_id}: {whole_size / 1e6:.1f} MB archive, {unpacked / 1e6:.1f} MB unpacked, {len(parts)} part(s)")
    return {"id": component_id, "type": "zip", "dest": dest, "archive": archive.name, "sha256": whole_hash, "bytes": whole_size,
            "unpacked_bytes": unpacked, "parts": parts, "profiles": list(profiles), **(extra or {})}


def model_component(name, assets, profiles, work):
    family, tag = name.split(":", 1)
    manifest_path = OLLAMA_MODELS / "manifests/registry.ollama.ai/library" / family / tag
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    slug = name.replace(":", "-").replace(".", "_")
    manifest_file = assets / f"model-{slug}.manifest.json"
    manifest_file.write_bytes(raw)
    blobs = []
    for layer in [manifest["config"], *manifest["layers"]]:
        digest = layer["digest"].split(":", 1)[1]
        source = OLLAMA_MODELS / "blobs" / f"sha256-{digest}"
        if source.stat().st_size != layer["size"] or sha256(source) != digest:
            raise SystemExit(f"Local Ollama blob {digest[:12]} does not match its content digest")
        blob_name = f"blob-{digest[:20]}.bin"
        upstream = [f"https://registry.ollama.ai/v2/library/{family}/blobs/sha256:{digest}"]
        if layer["size"] > PART_BYTES:
            staged = work / blob_name  # parts are written to assets as blob-….bin.partNNN
            shutil.copyfile(source, staged)
            parts = split(staged, assets)
            staged.unlink(missing_ok=True)
            for part in parts:
                part["file_parts_of"] = blob_name
            blobs.append({"digest": digest, "sha256": digest, "bytes": layer["size"], "file": blob_name, "parts": parts,
                          "media_type": layer["mediaType"]})
        else:
            target = assets / blob_name
            if not target.exists():
                shutil.copyfile(source, target)
            blobs.append({"digest": digest, "sha256": digest, "bytes": layer["size"], "file": blob_name,
                          "upstream": upstream, "media_type": layer["mediaType"]})
    manifest_digest = hashlib.sha256(raw).hexdigest()
    log(f"model {name}: manifest {manifest_digest[:12]}, {sum(b['bytes'] for b in blobs) / 1e9:.2f} GB")
    return {"id": "model-" + slug, "type": "ollama-model", "name": name, "profiles": list(profiles),
            "manifest": {"file": manifest_file.name, "sha256": manifest_digest, "bytes": len(raw),
                         "path": f"manifests/registry.ollama.ai/library/{family}/{tag}",
                         "upstream": [f"https://registry.ollama.ai/v2/library/{family}/manifests/{tag}"]},
            "blobs": blobs, "unpacked_bytes": sum(b["bytes"] for b in blobs), "license": "Apache-2.0 (Qwen)"}


def pack_component(edition, library_version, assets, work):
    pack_id = f"aster-library-{edition}-{library_version}"
    source = ROOT / "data/library/packs" / pack_id
    if not (source / "index" / "index-manifest.json").exists():
        raise SystemExit(f"{pack_id} has no built index")
    archive = work / f"{pack_id}.zip"
    unpacked = deterministic_zip(source, archive)
    whole = {"sha256": sha256(archive), "bytes": archive.stat().st_size}
    parts = split(archive, assets)
    log(f"library {pack_id}: {whole['bytes'] / 1e6:.1f} MB archive")
    return {"id": "library-" + edition, "type": "pack", "pack_id": pack_id, "edition": edition, "archive": archive.name,
            "unpacked_bytes": unpacked, "parts": parts, "profiles": ["*"], **whole,
            "license_scope": json.loads((source / "manifest.json").read_text(encoding="utf-8"))["license_scope"]}


def build_setup(build_python, assets, out, lock_path, lock, version):
    env = dict(os.environ, ASTER_RELEASE_LOCK=str(lock_path))
    run(build_python, "-m", "pip", "install", "-q", "--disable-pip-version-check", "cryptography==50.0.2")
    run(build_python, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", assets, "--workpath", out / "work/setup",
        ROOT / "packaging/installer/aster-setup-v2.spec", env=env)
    setup = assets / "AsterSetup-Windows-x64.exe"
    pin = {"schema_version": 1, "version": version, "file": setup.name, "sha256": sha256(setup),
           "bytes": setup.stat().st_size, "url": lock["release_base_url"] + setup.name, "lock_sha256": sha256(lock_path)}
    (ROOT / "release").mkdir(exist_ok=True)
    (ROOT / "release/bootstrap-pin.json").write_text(json.dumps(pin, indent=2), encoding="utf-8")
    shutil.copy2(ROOT / "release/bootstrap-pin.json", assets / "bootstrap-pin.json")
    log(f"setup: {setup.stat().st_size / 1e6:.1f} MB sha256 {pin['sha256']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--library-version", required=True)
    parser.add_argument("--out", default=str(ROOT / "artifacts/release-v2"))
    parser.add_argument("--skip-freeze", action="store_true")
    parser.add_argument("--skip-setup", action="store_true")
    parser.add_argument("--setup-only", action="store_true", help="rebuild only AsterSetup from the existing signed lock")
    args = parser.parse_args()
    out = Path(args.out) / args.version
    if args.setup_only:
        lock_path = out / "assets" / "release-lock.json"
        build_setup(out / "build-env/Scripts/python.exe", out / "assets", out, lock_path,
                    json.loads(lock_path.read_text(encoding="utf-8")), args.version)
        return
    assets, stage, work = out / "assets", out / "stage", out / "work-archives"
    # Start from an empty assets folder: everything in it is meant to be uploaded, so no leftovers.
    shutil.rmtree(assets, ignore_errors=True)
    for path in (assets, stage, work):
        path.mkdir(parents=True, exist_ok=True)
    profile = json.loads((ROOT / "packaging/release-profile.v2.json").read_text(encoding="utf-8"))
    if profile["app_version"] != args.version:
        raise SystemExit("release-profile.v2.json app_version differs from --version")
    if args.skip_freeze:
        frozen, build_python = out / "frozen", out / "build-env/Scripts/python.exe"
    else:
        frozen, build_python = freeze(out)
    app_tree = stage_app(stage, frozen, args.version)
    (app_tree / "release-profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    components = [zip_component("app", app_tree, assets, work, args.version)]
    components.append(zip_component("models-onnx", stage_models(stage), assets, work, args.version))
    cpu, cuda = stage_ollama(stage)
    components.append(zip_component("ollama-cpu", cpu, assets, work, args.version))
    # No GPU profile: NVIDIA CUDA libraries are not redistributed (staged, never packaged).
    components.append(zip_component("tesseract", stage_tesseract(stage), assets, work, args.version))
    models = {}
    for name, profile_list in (("qwen3-vl:2b-instruct", ["*"]), ("qwen3:4b-q4_K_M", ["quality-cpu"])):
        models[name] = model_component(name, assets, profile_list, work)
        components.append(models[name])
    for edition in ("core", "nc"):
        components.append(pack_component(edition, args.library_version, assets, work))
    lock = {
        "schema_version": 1, "product": "Aster", "version": args.version, "tag": "v" + args.version,
        "release_base_url": f"{REPO_URL}/releases/download/v{args.version}/",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "default_profile": "standard", "profile_order": ["standard", "quality-cpu"],
        "profiles": profile["profiles"], "release_profile": profile, "components": components,
        "library_version": args.library_version,
    }
    lock_path = assets / "release-lock.json"
    lock_path.write_text(json.dumps(lock, indent=1), encoding="utf-8")
    sys.path.insert(0, str(ROOT))
    from aster_library.signing import sign_file

    sign_file(lock_path)
    # Signed library update manifest consumed by the in-app (opt-in) updater.
    library_manifest = {"schema_version": 1, "channel": "release", "version": args.library_version,
                        "created": lock["created"], "packs": [
                            {"pack_id": c["pack_id"], "edition": c["edition"], "bytes": c["bytes"], "sha256": c["sha256"],
                             "url": lock["release_base_url"] + c["parts"][0]["file"]}
                            for c in components if c["type"] == "pack" and len(c["parts"]) == 1]}
    library_path = assets / "library-latest.json"
    library_path.write_text(json.dumps(library_manifest, indent=1), encoding="utf-8")
    sign_file(library_path)
    (ROOT / "release").mkdir(exist_ok=True)
    shutil.copy2(lock_path, ROOT / "release/release-lock.json")
    shutil.copy2(str(lock_path) + ".sig", ROOT / "release/release-lock.json.sig")
    if not args.skip_setup:
        build_setup(build_python, assets, out, lock_path, lock, args.version)
    shutil.rmtree(work, ignore_errors=True)
    inventory = [{"file": p.name, "bytes": p.stat().st_size} for p in sorted(assets.iterdir()) if p.is_file()]
    (out / "asset-inventory.json").write_text(json.dumps(inventory, indent=1), encoding="utf-8")
    log(f"release assets: {len(inventory)} files, {sum(i['bytes'] for i in inventory) / 1e9:.2f} GB -> {assets}")


if __name__ == "__main__":
    main()
