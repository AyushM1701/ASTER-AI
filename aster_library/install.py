"""Install, activate, update and roll back signed reference packs.

Layout under ``library_root``::

    packs/<pack_id>/...         immutable installed packs (manifest.json(.sig), units, index/)
    active.json                 {"packs": [...], "activated": ts, "channel": ...}
    last-known-good.json        previous working selection (kept on every switch)
    downloads/                  resumable verified downloads for updates

Activation only happens after signature, hash, schema and quality checks pass.
A failed update leaves ``active.json`` untouched; ``rollback`` restores
``last-known-good.json``.
"""
import hashlib
import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

from aster_library.signing import SignatureError, load_public_key, verify_bytes, verify_file

REQUIRED_UNIT_FIELDS = {"unit_id", "doc_id", "text", "content_class", "license", "url", "acquired", "text_sha256"}


class InstallError(RuntimeError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def quality_check(pack_dir, public_key=None, sample=2000):
    """Integrity + quality gate. Automated checks are not medical review."""
    pack_dir = Path(pack_dir)
    try:
        verify_file(pack_dir / "manifest.json", public_key)
        verify_file(pack_dir / "index" / "index-manifest.json", public_key)
    except (SignatureError, FileNotFoundError) as exc:
        raise InstallError(f"{pack_dir.name}: signature verification failed") from exc
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    for name, meta in manifest["files"].items():
        path = pack_dir / name
        if not path.exists() or path.stat().st_size != meta["bytes"] or sha256_file(path) != meta["sha256"]:
            raise InstallError(f"{pack_dir.name}: {name} does not match the signed manifest")
    index = json.loads((pack_dir / "index" / "index-manifest.json").read_text(encoding="utf-8"))
    if index["pack_manifest_sha256"] != sha256_file(pack_dir / "manifest.json"):
        raise InstallError(f"{pack_dir.name}: index belongs to a different pack")
    for name, meta in index["files"].items():
        path = pack_dir / "index" / name
        if not path.exists() or path.stat().st_size != meta["bytes"] or sha256_file(path) != meta["sha256"]:
            raise InstallError(f"{pack_dir.name}: index file {name} does not match")
    if manifest["counts"]["units"] != index["units"] or manifest["counts"]["units"] < 1:
        raise InstallError(f"{pack_dir.name}: unit count mismatch")
    with (pack_dir / "units.jsonl").open(encoding="utf-8") as handle:
        for i, line in enumerate(handle):
            if i >= sample:
                break
            unit = json.loads(line)
            missing = REQUIRED_UNIT_FIELDS - {k for k, v in unit.items() if v not in (None, "")}
            if missing - {"url"} or (missing and unit.get("content_class") != "professional"):
                raise InstallError(f"{pack_dir.name}: unit {i} lacks provenance fields {sorted(missing)}")
            if unit.get("publication_status") == "retracted":
                raise InstallError(f"{pack_dir.name}: retracted material present")
    return manifest


def _atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)


def install_pack_dir(source_dir, library_root, public_key=None):
    """Copy a built pack into the library (verified before and after copy)."""
    source_dir, library_root = Path(source_dir), Path(library_root)
    manifest = quality_check(source_dir, public_key)
    target = library_root / "packs" / manifest["pack_id"]
    if target.exists():
        quality_check(target, public_key)
        return target
    staging = library_root / "packs" / (".staging-" + manifest["pack_id"])
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(source_dir, staging)
    quality_check(staging, public_key)
    os.replace(staging, target)
    return target


def safe_extract(zip_path, destination, max_bytes=8 * 1024 ** 3):
    """Extract a pack archive, refusing traversal, links and oversized content."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    total = 0
    with zipfile.ZipFile(zip_path) as archive:
        names = set()
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/") or ":" in name or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise InstallError(f"Unsafe archive entry: {info.filename}")
            if name.casefold() in names:
                raise InstallError(f"Duplicate archive entry: {info.filename}")
            names.add(name.casefold())
            total += info.file_size
            if total > max_bytes:
                raise InstallError("Archive expands beyond the allowed size")
            target = (destination / name).resolve()
            if not target.is_relative_to(root):
                raise InstallError(f"Archive entry escapes destination: {info.filename}")
        archive.extractall(destination)


def activate(library_root, pack_ids, public_key=None, channel="release"):
    library_root = Path(library_root)
    for pack_id in pack_ids:
        quality_check(library_root / "packs" / pack_id, public_key)
    active_path = library_root / "active.json"
    if active_path.exists():
        previous = json.loads(active_path.read_text(encoding="utf-8"))
        if previous.get("packs") != list(pack_ids):
            _atomic_write(library_root / "last-known-good.json", previous)
    _atomic_write(active_path, {"packs": list(pack_ids), "activated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "channel": channel})
    return pack_ids


def rollback(library_root, public_key=None):
    library_root = Path(library_root)
    previous_path = library_root / "last-known-good.json"
    if not previous_path.exists():
        raise InstallError("No previous library selection is available")
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    for pack_id in previous["packs"]:
        quality_check(library_root / "packs" / pack_id, public_key)
    current = library_root / "active.json"
    current_data = json.loads(current.read_text(encoding="utf-8")) if current.exists() else None
    _atomic_write(current, {**previous, "activated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rolled_back": True})
    if current_data:
        _atomic_write(previous_path, current_data)
    return previous["packs"]


def verify_update_manifest(raw, signature, public_key=None):
    """Authenticate a downloaded update manifest with the compiled-in public key."""
    try:
        verify_bytes(raw, signature, public_key or load_public_key())
    except SignatureError as exc:
        raise InstallError("Update manifest signature is invalid; update refused") from exc
    manifest = json.loads(raw)
    if manifest.get("schema_version") != 1 or not manifest.get("packs"):
        raise InstallError("Update manifest format is not supported")
    return manifest


def apply_update(library_root, manifest, fetch, public_key=None, editions=("core", "nc")):
    """Download, verify and activate packs listed in an authenticated manifest.

    ``fetch(url, dest, sha256, size)`` performs a resumable, hash-verified
    download (setup's downloader). Nothing is activated unless every selected
    pack passes ``quality_check``; on failure the active library is unchanged.
    """
    library_root = Path(library_root)
    downloads = library_root / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    selected = [p for p in manifest["packs"] if p["edition"] in editions]
    installed = []
    for pack in selected:
        target = library_root / "packs" / pack["pack_id"]
        if not target.exists():
            archive = downloads / (pack["pack_id"] + ".zip")
            fetch(pack["url"], archive, pack["sha256"], pack["bytes"])
            if sha256_file(archive) != pack["sha256"]:
                raise InstallError(f"{pack['pack_id']}: download hash mismatch")
            staging = library_root / "packs" / (".staging-" + pack["pack_id"])
            if staging.exists():
                shutil.rmtree(staging)
            safe_extract(archive, staging)
            inner = staging / pack["pack_id"] if (staging / pack["pack_id"]).is_dir() else staging
            quality_check(inner, public_key)
            os.replace(inner, target)
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        else:
            quality_check(target, public_key)
        installed.append(pack["pack_id"])
    return activate(library_root, installed, public_key, channel=manifest.get("channel", "release"))
