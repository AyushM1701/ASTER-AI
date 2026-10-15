"""Bootstrap exact, authenticated assets; verify before committing a version."""
import json
import os
import re
import shutil
import stat
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path

from aster_release.release import ReleaseError, contained, sha256, verify_package

DOWNLOAD_HOSTS = {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}


def allowed_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in DOWNLOAD_HOSTS
            or parsed.port not in {None, 443} or parsed.username or parsed.password or parsed.fragment):
        raise ReleaseError("Download address is outside trusted HTTPS release hosts")
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, path, expected, size, progress=lambda done, total: None, cancelled=lambda: False):
    allowed_url(url)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    if path.exists() and path.stat().st_size == size and sha256(path) == expected:
        progress(size, size)
        return path
    start = partial.stat().st_size if partial.exists() else 0
    if start >= size:
        partial.unlink()
        start = 0
    headers = {"User-Agent": "AsterSetup/1", "Accept-Encoding": "identity"}
    if start:
        headers["Range"] = f"bytes={start}-"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), SafeRedirect())
    with opener.open(urllib.request.Request(url, headers=headers), timeout=30) as response:
        if response.status == 206:
            content_range = response.headers.get("Content-Range", "")
            if not re.fullmatch(rf"bytes {start}-{size-1}/{size}", content_range):
                raise ReleaseError("Invalid resumed download range")
        elif response.status == 200:
            start = 0  # Server ignored Range: replace partial rather than append
        else:
            raise ReleaseError("Unexpected release server response")
        if response.headers.get("Content-Encoding", "identity") != "identity":
            raise ReleaseError("Unexpected download encoding")
        done = start
        with partial.open("ab" if start else "wb") as target:
            while block := response.read(1024 * 1024):
                if cancelled():
                    raise ReleaseError("Setup paused. Run setup again to resume verified downloads.")
                done += len(block)
                if done > size:
                    raise ReleaseError("Download exceeds expected release size")
                target.write(block)
                progress(done, size)
    if done != size or sha256(partial) != expected:
        partial.unlink(missing_ok=True)
        raise ReleaseError("Download checksum failed. Retry setup.")
    os.replace(partial, path)
    return path


def authenticated_distribution(trust):
    allowed_url(trust["url"])
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), SafeRedirect())
    with opener.open(trust["url"], timeout=30) as response:
        raw = response.read(1024 * 1024 + 1)
    return authenticated_bytes(raw, trust)


def authenticated_bytes(raw, trust):
    import hashlib
    if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != trust["sha256"]:
        raise ReleaseError("Release metadata authentication failed. Download official setup again.")
    manifest = json.loads(raw)
    validate_distribution(manifest)
    return manifest


def validate_distribution(manifest):
    if (manifest.get("schema_version") != 1 or not re.fullmatch(r"[0-9][A-Za-z0-9_.-]{0,60}", manifest.get("app_version", ""))
            or manifest.get("edition") not in {"PublicStandard", "PrivateAuthorized"}
            or not 1 <= len(manifest.get("parts", [])) <= 990):
        raise ReleaseError("Unsupported distribution manifest")
    total, seen = 0, set()
    for part in manifest["parts"]:
        if (not re.fullmatch(r"Aster-Windows-x64\.zip\.part[0-9]{3}", part["name"])
                or part["name"] in seen or not 0 < part["size"] < 2 * 1024**3
                or not re.fullmatch(r"[0-9a-f]{64}", part["sha256"])):
            raise ReleaseError("Invalid release part")
        allowed_url(part["url"])
        seen.add(part["name"])
        total += part["size"]
    if total != manifest["archive_bytes"] or not 0 < manifest["installed_bytes"] < 100 * 1024**3:
        raise ReleaseError("Release sizes differ")


def extract_verified(archive, destination, installed_bytes):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(archive) as bundle:
            seen, total = set(), 0
            for item in bundle.infolist():
                name = item.filename.rstrip("/") if item.is_dir() else item.filename
                target = contained(destination, name)
                if name.casefold() in seen or stat.S_ISLNK(item.external_attr >> 16):
                    raise ReleaseError("Duplicate or symlink archive entry")
                seen.add(name.casefold())
                total += item.file_size
                if total > installed_bytes + 8 * 1024**2:
                    raise ReleaseError("Archive exceeds verified installation size")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(item) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
    except BaseException:
        # This freshly created UUID staging directory is owned exclusively by setup.
        shutil.rmtree(destination)
        raise


def commit_install(root, staging, distribution):
    root, staging = Path(root).resolve(), Path(staging).resolve()
    if not staging.is_relative_to(root / "staging"):
        raise ReleaseError("Installation staging is outside controlled directory")
    report = verify_package(staging, distribution["release_manifest_sha256"])
    if report["manifest"]["app_version"] != distribution["app_version"] or report["edition"] != distribution.get("edition"):
        raise ReleaseError("Installed version/edition differs from authenticated distribution")
    version = distribution["app_version"]
    destination = contained(root, "versions/" + version)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ReleaseError("This version already exists. Use a new version or repair into a clean folder.")
    previous = None
    current = root / "current.json"
    if current.exists():
        previous = json.loads(current.read_text())["version"]
    os.replace(staging, destination)  # same-volume atomic version commit
    state = {"version": version, "previous": previous, "manifest_sha256": distribution["release_manifest_sha256"]}
    pending = root / "current.json.new"
    pending.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(pending, current)
    return destination


def rollback(root):
    root = Path(root).resolve()
    state = json.loads((root / "current.json").read_text())
    previous = state.get("previous")
    if not previous or not re.fullmatch(r"[0-9][A-Za-z0-9_.-]{0,60}", previous):
        raise ReleaseError("No previous installation is available")
    target = contained(root, "versions/" + previous)
    result = verify_package(target)
    pending = root / "current.json.new"
    pending.write_text(json.dumps({"version": previous, "previous": state["version"], "manifest_sha256": result["manifest_sha256"]}), encoding="utf-8")
    os.replace(pending, root / "current.json")
    return target


def required_install_space(distribution, root, offline_parts=False):
    cache = contained(root, "downloads/" + distribution["app_version"])
    needed_parts = 0
    if not offline_parts:
        for part in distribution["parts"]:
            target = contained(cache, part["name"])
            if target.is_file() and target.stat().st_size == part["size"] and sha256(target) == part["sha256"]:
                continue
            partial = contained(cache, part["name"] + ".partial")
            # These allocated bytes are resumed or truncated/reclaimed before a
            # restart. They are NEVER treated as trusted content without the hash.
            allocated = min(partial.stat().st_size, part["size"]) if partial.is_file() else 0
            needed_parts += part["size"] - allocated
    archive = contained(cache, "complete.zip")
    reclaimable = min(archive.stat().st_size, distribution["archive_bytes"]) if archive.is_file() else 0
    return needed_parts + distribution["archive_bytes"] - reclaimable + distribution["installed_bytes"] + 512 * 1024**2


def install(distribution, root, progress=lambda message: None, cancelled=lambda: False, offline_parts=None):
    validate_distribution(distribution)
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    import msvcrt
    with (root / "setup.lock").open("a+b") as lock:
        lock.write(b"1")
        lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        cache = contained(root, "downloads/" + distribution["app_version"])
        cache.mkdir(parents=True, exist_ok=True)
        required = required_install_space(distribution, root, bool(offline_parts))
        if shutil.disk_usage(root).free < required:
            raise ReleaseError(f"Setup needs {required / 1024**3:.1f} GiB additional free space including staging.")
        parts = []
        for part in distribution["parts"]:
            if offline_parts:
                path = contained(offline_parts, part["name"])
                if not path.is_file() or path.stat().st_size != part["size"] or sha256(path) != part["sha256"]:
                    raise ReleaseError("Offline part missing or changed")
            else:
                path = download(part["url"], cache / part["name"], part["sha256"], part["size"],
                                lambda done, total: progress(f"Downloading {part['name']}: {done / total:.0%}"), cancelled)
            parts.append(path)
        archive = cache / "complete.zip"
        with archive.open("wb") as output:
            for path in parts:
                with path.open("rb") as source:
                    shutil.copyfileobj(source, output, 4 * 1024**2)
        if sha256(archive) != distribution["archive_sha256"]:
            raise ReleaseError("Assembled archive checksum failed")
        staging = contained(root, "staging/" + uuid.uuid4().hex)
        staging.parent.mkdir(exist_ok=True)
        progress("Verifying and installing Aster…")
        extract_verified(archive, staging, distribution["installed_bytes"])
        try:
            destination = commit_install(root, staging, distribution)
        except BaseException:
            if staging.exists():
                shutil.rmtree(staging)
            raise
        archive.unlink()
        return destination
