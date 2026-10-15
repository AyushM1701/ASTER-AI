"""Release v2: component-based installs assembled and verified by setup.

Install layout (per user, no administrator rights)::

    <install_root>/
      current.json                  {"version", "profile", "previous"}
      versions/<version>/           immutable app + runtimes + models (the controller root)
        installed-manifest.json     every file: path, size, sha256 (+ component, profile)
        release-profile.json        settings/features/profiles shipped with the app
      library/                      signed reference packs (active.json, last-known-good.json)
      AsterSetup.exe                copy used for repair / uninstall
    %LOCALAPPDATA%/Aster/           logs, caches, temp, workspace database (writable)
"""
import json
import os
import time
from pathlib import Path

from aster_release.release import ReleaseError, contained, read_json, sha256

INSTALLED_MANIFEST = "installed-manifest.json"
VERIFIED_INDEX = "verified-index.json"
PATH_SETTINGS = {
    "embedding_path": "data/models/minilm",
    "nli_model_path": "data/models/nli-deberta-v3-xsmall",
    "rerank_model_path": "data/models/medcpt-cross-encoder",
    "xray_gates_config": "configs/xray_gates.json",
    "xray_weights_dir": "data/models/xray",
    "xray_manifest": "configs/xray_assets.release.yaml",
    "xray_weights_manifest": "configs/xray_weights.json",
}
DISABLED_LEGACY = {
    "corpus_path": "data/disabled/corpus.jsonl", "source_register": "data/disabled/sources.yaml",
    "chroma_path": "data/disabled/index", "teaching_release_path": "data/disabled/teaching",
    "teaching_index_path": "data/disabled/teaching-index", "teaching_explanations_path": "data/disabled/explanations.json",
    "secondary_reference_path": "data/disabled/secondary", "patient_release_path": "data/disabled/patient",
}


def is_v2(root):
    return (Path(root) / INSTALLED_MANIFEST).is_file()


def install_root_for(version_root):
    version_root = Path(version_root).resolve()
    if version_root.parent.name == "versions":
        return version_root.parent.parent
    return version_root


def write_installed_manifest(root, components, profile_name, release_profile):
    """Called by setup after verified extraction. Hashes every file once."""
    root = Path(root).resolve()
    files, seen = [], set()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ReleaseError("Symlinks are not allowed in installations")
        if not path.is_file() or path.name in {INSTALLED_MANIFEST, VERIFIED_INDEX} and path.parent == root:
            continue
        name = path.relative_to(root).as_posix()
        contained(root, name)
        if name.casefold() in seen:
            raise ReleaseError("Case-colliding paths in installation")
        seen.add(name.casefold())
        stat = path.stat()
        files.append({"path": name, "size": stat.st_size, "sha256": sha256(path), "mtime_ns": stat.st_mtime_ns})
    manifest = {"schema_version": 2, "app_version": release_profile["app_version"], "profile": profile_name,
                "components": components, "files": files, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (root / INSTALLED_MANIFEST).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def verify_installed(root, *, full=False, progress=lambda done, total: None):
    """Fast mode re-hashes only files whose size/mtime changed since install; full mode hashes all."""
    root = Path(root).resolve()
    manifest = read_json(root / INSTALLED_MANIFEST)
    if manifest.get("schema_version") != 2:
        raise ReleaseError("Unsupported installation manifest")
    total = len(manifest["files"])
    expected = {INSTALLED_MANIFEST, VERIFIED_INDEX}
    changed = []
    for index, item in enumerate(manifest["files"], 1):
        path = contained(root, item["path"])
        expected.add(item["path"])
        if not path.is_file():
            changed.append(item["path"])
            continue
        stat = path.stat()
        if full or stat.st_size != item["size"] or stat.st_mtime_ns != item.get("mtime_ns"):
            if stat.st_size != item["size"] or sha256(path) != item["sha256"]:
                changed.append(item["path"])
        if index % 200 == 0:
            progress(index, total)
    if changed:
        raise ReleaseError(f"{len(changed)} installed file(s) are missing or damaged (for example {changed[0]}). "
                           "Choose Repair Aster from the Start menu.")
    extra = [p for p in root.rglob("*") if p.is_file() and p.relative_to(root).as_posix() not in expected
             and not p.relative_to(root).as_posix().startswith("data/models/ollama-store/history")]
    if extra:
        raise ReleaseError("Unexpected files were found in the installation folder. Choose Repair Aster.")
    profile = read_json(root / "release-profile.json")
    return {"status": "verified", "mode": "full" if full else "fast", "files": total,
            "bytes": sum(f["size"] for f in manifest["files"]), "manifest": manifest, "profile": profile}


def release_settings_v2(root, profile, profile_name, *, writable, api_port, ollama_port):
    from backend.app.config import Settings

    root = Path(root).resolve()
    install_root = install_root_for(root)
    values = {key: field.get_default(call_default_factory=True) for key, field in Settings.model_fields.items()}
    selected = profile["profiles"][profile_name]
    overrides = dict(profile["settings"])
    unknown = set(overrides) - set(values)
    if unknown:
        raise ReleaseError("Unknown release setting: " + ", ".join(sorted(unknown)))
    values.update(overrides)
    for key, relative in {**PATH_SETTINGS, **DISABLED_LEGACY}.items():
        values[key] = contained(root, relative)
    values["tesseract_cmd"] = str(contained(root, "runtime/tesseract/tesseract.exe"))
    values["library_root"] = install_root / "library"
    values["workspace_path"] = Path(writable) / "workspaces" / "education.sqlite3"
    values["text_model"], values["vision_model"] = selected["text_model"], selected["vision_model"]
    values["ollama_base_url"] = f"http://127.0.0.1:{int(ollama_port)}"
    values["app_env"] = "packaged"
    if values["answer_engine"] != "grounded" or values["strict_source_grounding"] is not True:
        raise ReleaseError("Unsupported release safety profile")
    os.environ["ASTER_API_PORT"] = str(int(api_port))
    return Settings(_env_file=None, **values)


def read_current(install_root):
    path = Path(install_root) / "current.json"
    return read_json(path) if path.exists() else None
