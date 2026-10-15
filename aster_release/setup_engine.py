"""Aster setup engine (per-user, no administrator rights).

Trust root: ``release-lock.json`` compiled into AsterSetup / committed in the
source tree. Every downloaded byte is checked against hashes from that lock, so
mirror or CDN hosts cannot substitute content. Hosts are additionally
allow-listed (defence in depth); a loopback mirror is permitted only when the
caller passes ``mirror`` explicitly (testing/offline LAN use).
"""
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from aster_release.release import ReleaseError, contained

APP_NAME = "Aster"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Aster"
ALLOWED_HOSTS = ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com",
                 "registry.ollama.ai")
ALLOWED_SUFFIXES = (".r2.cloudflarestorage.com", ".githubusercontent.com")
CHUNK = 1024 * 1024


class SetupCancelled(ReleaseError):
    pass


def default_install_root():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / APP_NAME


def default_writable_root():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP_NAME


def sha256_file(path, progress=None):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(8 * CHUNK):
            digest.update(block)
            if progress:
                progress(len(block))
    return digest.hexdigest()


# --------------------------------------------------------------------------- hardware
def hardware(target=None):
    """Measured facts about this PC; nothing is assumed about untested machines."""
    info = {"os": "windows", "ram_gb": None, "cpu": None, "logical_cpus": os.cpu_count(), "avx2": None, "gpus": [],
            "free_disk_gb": None}
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            info["ram_gb"] = round(status.ullTotalPhys / 1024 ** 3, 1)
            info["available_ram_gb"] = round(status.ullAvailPhys / 1024 ** 3, 1)
        info["avx2"] = bool(ctypes.windll.kernel32.IsProcessorFeaturePresent(40))
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                info["cpu"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
        info["gpus"] = nvidia_gpus()
    if target:
        probe = Path(target)
        while not probe.exists() and probe.parent != probe:
            probe = probe.parent
        info["free_disk_gb"] = round(shutil.disk_usage(probe).free / 1024 ** 3, 1)
    return info


def nvidia_gpus():
    """NVIDIA GPUs via nvidia-smi (installed with the NVIDIA driver). Empty if none."""
    candidates = [shutil.which("nvidia-smi"), str(Path(os.environ.get("SYSTEMROOT", "C:/Windows")) / "System32/nvidia-smi.exe")]
    for exe in [c for c in candidates if c and Path(c).is_file()]:
        try:
            output = subprocess.run([exe, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                                    capture_output=True, text=True, timeout=10, creationflags=0x08000000).stdout
            gpus = []
            for line in output.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2 and parts[1].isdigit():
                    gpus.append({"vendor": "nvidia", "name": parts[0], "vram_gb": round(int(parts[1]) / 1024, 1),
                                 "driver": parts[2] if len(parts) > 2 else None})
            return gpus
        except (OSError, subprocess.SubprocessError):
            continue
    return []


def recommend_profile(hw, lock):
    """Choose the evaluated default. GPU profiles only with a detected, sufficient NVIDIA GPU."""
    profiles = lock["profiles"]
    reasons = []
    for name in lock.get("profile_order", list(profiles)):
        rule = profiles[name].get("requires", {})
        if rule.get("nvidia_vram_gb") and not any(g["vram_gb"] >= rule["nvidia_vram_gb"] for g in hw.get("gpus", [])):
            reasons.append(f"{name}: no NVIDIA GPU with ≥{rule['nvidia_vram_gb']} GB memory detected")
            continue
        if rule.get("ram_gb") and (hw.get("ram_gb") or 0) < rule["ram_gb"]:
            reasons.append(f"{name}: needs ≥{rule['ram_gb']} GB RAM")
            continue
        if rule.get("manual_only"):
            continue
        return name, reasons
    return lock.get("default_profile", "standard"), reasons


# --------------------------------------------------------------------------- planning
@dataclass
class Plan:
    version: str
    profile: str
    components: list
    download_bytes: int
    cached_bytes: int
    unpacked_bytes: int
    required_free_bytes: int
    install_root: Path
    include_nc: bool = True
    notes: list = field(default_factory=list)


def components_for(lock, profile, include_nc=True):
    chosen = []
    for component in lock["components"]:
        profiles = component.get("profiles", ["*"])
        if "*" not in profiles and profile not in profiles:
            continue
        if component.get("edition") == "nc" and not include_nc:
            continue
        chosen.append(component)
    return chosen


def component_files(component):
    if component["type"] == "ollama-model":
        files = [component["manifest"]]
        for blob in component["blobs"]:
            files.extend(blob.get("parts") or [blob])
        return files
    return component["parts"]


def make_plan(lock, profile, install_root, downloads, include_nc=True):
    components = components_for(lock, profile, include_nc)
    download = cached = unpacked = 0
    for component in components:
        for part in component_files(component):
            path = Path(downloads) / part["file"]
            if path.exists() and path.stat().st_size == part["bytes"]:
                cached += part["bytes"]
            else:
                download += part["bytes"] - (path.with_name(path.name + ".partial").stat().st_size
                                             if path.with_name(path.name + ".partial").exists() else 0)
        unpacked += component.get("unpacked_bytes") or sum(p["bytes"] for p in component_files(component))
    # Downloads + extracted version + one retained previous version is bounded by 2x unpacked.
    required = download + unpacked + 512 * 1024 ** 2
    return Plan(lock["version"], profile, components, download, cached, unpacked, required, Path(install_root), include_nc)


# --------------------------------------------------------------------------- downloads
def allowed_url(url, mirror=None):
    parsed = urllib.parse.urlsplit(url)
    if mirror and url.startswith(mirror.rstrip("/") + "/"):
        if parsed.hostname in {"127.0.0.1", "localhost"} or parsed.scheme == "https":
            return url
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ReleaseError("Download address is not an allowed HTTPS release host")
    host = parsed.hostname or ""
    if host not in ALLOWED_HOSTS and not host.endswith(ALLOWED_SUFFIXES):
        raise ReleaseError(f"Download host {host} is not allowed")
    return url


class Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, mirror):
        self.mirror = mirror

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed_url(newurl, self.mirror)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(urls, dest, sha256, size, *, mirror=None, offline_dir=None, progress=lambda n: None, cancelled=lambda: False,
          retries=4):
    """Resumable, hash-verified download of one file from the first working source.

    ``progress(n)`` receives the absolute number of bytes present for this file.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == size:
        if sha256_file(dest) == sha256:
            progress(size)
            return dest
        dest.unlink()
    if offline_dir:
        local = Path(offline_dir) / dest.name
        if local.exists() and local.stat().st_size == size and sha256_file(local) == sha256:
            shutil.copyfile(local, dest)
            progress(size)
            return dest
        if not urls:
            raise ReleaseError(f"{dest.name} is missing or damaged in the offline folder.")
    partial = dest.with_name(dest.name + ".partial")
    errors = []
    for url in urls:
        try:
            allowed_url(url, mirror)
        except ReleaseError as exc:
            errors.append(str(exc))
            continue
        for attempt in range(retries):
            if cancelled():
                raise SetupCancelled("Setup paused. Run setup again to resume; finished downloads are kept.")
            start = partial.stat().st_size if partial.exists() else 0
            if start > size:
                partial.unlink()
                start = 0
            headers = {"User-Agent": "AsterSetup/2", "Accept-Encoding": "identity"}
            if start:
                headers["Range"] = f"bytes={start}-"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler(), Redirects(mirror))
            try:
                with opener.open(urllib.request.Request(url, headers=headers), timeout=60) as response:
                    if response.status == 200 and start:
                        start = 0  # server ignored Range: restart cleanly
                    elif response.status not in (200, 206):
                        raise ReleaseError(f"Unexpected server response {response.status}")
                    progress(start)
                    with partial.open("ab" if start else "wb") as target:
                        while block := response.read(CHUNK):
                            if cancelled():
                                raise SetupCancelled("Setup paused. Run setup again to resume; finished downloads are kept.")
                            target.write(block)
                            start += len(block)
                            if start > size:
                                raise ReleaseError("Download is larger than expected")
                            progress(start)
                if start == size:
                    if sha256_file(partial) != sha256:
                        partial.unlink(missing_ok=True)
                        raise ReleaseError("Downloaded file failed its checksum")
                    os.replace(partial, dest)
                    return dest
            except SetupCancelled:
                raise
            except (urllib.error.URLError, OSError, ReleaseError, TimeoutError) as exc:
                errors.append(f"{urllib.parse.urlsplit(url).hostname}: {exc}")
                time.sleep(min(2 ** attempt, 20))
    raise ReleaseError(f"Could not download {dest.name}. Check the internet connection and retry. ({errors[-1] if errors else ''})")


def sources(part, lock, mirror=None):
    urls = []
    if mirror:
        urls.append(mirror.rstrip("/") + "/" + part["file"])
    urls.append(lock["release_base_url"].rstrip("/") + "/" + part["file"])
    urls.extend(part.get("upstream", []))
    return urls


def replace_with_retry(source, target, attempts=12, delay=0.5, sleep=time.sleep):
    """os.replace that waits out transient Windows locks (antivirus scanning new files, a process
    that is still exiting). Raises the last error after ~30 s."""
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            sleep(min(5.0, delay * 2 ** attempt))


def swap_version(staging, version_dir, replace=replace_with_retry):
    """Move a fully built staging folder into place (install or repair).

    The previous version is moved aside, not deleted, until the new one is in place; if the swap
    fails the previous version is restored, so the installation is never left without a version."""
    retired = None
    if version_dir.exists():
        retired = version_dir.with_name(version_dir.name + ".replaced-" + str(int(time.time())))
        replace(version_dir, retired)
    try:
        replace(staging, version_dir)
    except OSError:
        if retired is not None and retired.exists() and not version_dir.exists():
            replace(retired, version_dir)
        raise
    if retired is not None:
        shutil.rmtree(retired, ignore_errors=True)


# --------------------------------------------------------------------------- extraction
def safe_extract(archive, destination, expected_bytes=None, progress=lambda n: None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    total, names = 0, set()
    reserved = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
    with zipfile.ZipFile(archive) as handle:
        members = handle.infolist()
        for info in members:
            name = info.filename.replace("\\", "/")
            parts = [p for p in name.split("/") if p]
            if (name.startswith("/") or ".." in parts or ":" in name or any(reserved.match(p) for p in parts)
                    or (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise ReleaseError(f"Unsafe archive entry rejected: {info.filename}")
            if name.casefold() in names:
                raise ReleaseError("Archive contains duplicate entries")
            names.add(name.casefold())
            total += info.file_size
            if expected_bytes and total > expected_bytes * 1.01 + 1024 ** 2:
                raise ReleaseError("Archive expands beyond its declared size")
            if not (destination / name).resolve().is_relative_to(root):
                raise ReleaseError("Archive entry escapes the installation folder")
        for info in members:
            target = destination / info.filename
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with handle.open(info) as source, target.open("wb") as out:
                while block := source.read(CHUNK):
                    out.write(block)
            progress(info.file_size)


def assemble(parts, downloads, target, sha256, size):
    """Concatenate verified parts into one file and verify the whole."""
    target = Path(target)
    if target.exists() and target.stat().st_size == size and sha256_file(target) == sha256:
        return target
    tmp = target.with_name(target.name + ".assembling")
    with tmp.open("wb") as out:
        for part in parts:
            with (Path(downloads) / part["file"]).open("rb") as source:
                shutil.copyfileobj(source, out, 8 * CHUNK)
    if tmp.stat().st_size != size or sha256_file(tmp) != sha256:
        tmp.unlink(missing_ok=True)
        raise ReleaseError(f"{target.name} failed verification after assembly")
    os.replace(tmp, target)
    return target


# --------------------------------------------------------------------------- install
class Installer:
    def __init__(self, lock, install_root=None, writable_root=None, *, mirror=None, offline_dir=None,
                 notify=lambda stage, detail, done=None, total=None: None, cancelled=lambda: False,
                 setup_exe=None, shortcuts=True, register=True, desktop_icon=True, shortcut_dirs=None,
                 registry_key=UNINSTALL_KEY):
        self.lock = lock
        self.install_root = Path(install_root or default_install_root())
        self.writable_root = Path(writable_root or default_writable_root())
        self.downloads = self.writable_root / "downloads" / lock["version"]
        self.mirror, self.offline_dir = mirror, offline_dir
        self.notify, self.cancelled = notify, cancelled
        self.setup_exe = setup_exe
        self.shortcuts, self.register, self.desktop_icon = shortcuts, register, desktop_icon
        self.shortcut_dirs = shortcut_dirs
        self.registry_key = registry_key

    # -- steps
    def download(self, plan):
        files = [part for component in plan.components for part in component_files(component)]
        total = sum(part["bytes"] for part in files)
        present = {}

        for part in files:
            def advance(n, name=part["file"]):
                present[name] = n
                done = sum(present.values())
                self.notify("download", f"Downloading {fmt(done)} of {fmt(total)}", done, total)

            fetch(sources(part, self.lock, self.mirror), self.downloads / part["file"], part["sha256"], part["bytes"],
                  mirror=self.mirror, offline_dir=self.offline_dir, progress=advance, cancelled=self.cancelled)

    def build_version(self, plan, profile_lock):
        version_dir = self.install_root / "versions" / plan.version
        staging = self.install_root / "versions" / (plan.version + ".staging")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        total = sum(c.get("unpacked_bytes", 0) for c in plan.components if c["type"] == "zip")
        done = [0]

        def advance(n):
            done[0] += n
            self.notify("extract", f"Installing files {fmt(done[0])} of {fmt(total)}", done[0], total)

        models = []
        for component in plan.components:
            if self.cancelled():
                raise SetupCancelled("Setup cancelled before installation finished. Nothing was activated.")
            if component["type"] == "zip":
                archive = assemble(component["parts"], self.downloads, self.downloads / component["archive"],
                                   component["sha256"], component["bytes"]) if len(component["parts"]) > 1 \
                    else self.downloads / component["parts"][0]["file"]
                safe_extract(archive, staging / component.get("dest", "."), component.get("unpacked_bytes"), advance)
            elif component["type"] == "ollama-model":
                store = staging / "data/models/ollama-store"
                manifest = component["manifest"]
                target = contained(store, manifest["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.downloads / manifest["file"], target)
                for blob in component["blobs"]:
                    blob_target = contained(store, "blobs/sha256-" + blob["digest"])
                    blob_target.parent.mkdir(parents=True, exist_ok=True)
                    if blob_target.exists() and blob_target.stat().st_size == blob["bytes"]:
                        continue  # same blob referenced twice (or shared between models)
                    source = self.downloads / blob["file"]
                    if blob.get("parts"):
                        source = assemble(blob["parts"], self.downloads, self.downloads / blob["file"], blob["sha256"], blob["bytes"])
                    try:
                        os.link(source, blob_target)  # same volume: no second copy of multi-GB weights
                    except OSError:
                        shutil.copyfile(source, blob_target)
                    if blob_target.stat().st_size != blob["bytes"]:
                        raise ReleaseError("Model file size mismatch after installation")
                models.append({"name": component["name"], "manifest_digest": manifest["sha256"]})
        self.notify("verify", "Verifying installed files…")
        (staging / "release-profile.json").write_text(json.dumps(profile_lock, indent=2), encoding="utf-8")
        from aster_release.v2 import write_installed_manifest
        manifest = write_installed_manifest(staging, [c["id"] for c in plan.components], plan.profile, profile_lock)
        manifest["models"] = models
        (staging / "installed-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        if not (staging / "Aster.exe").is_file():
            raise ReleaseError("The application component is incomplete")
        swap_version(staging, version_dir)
        return version_dir

    def install_library(self, plan):
        from aster_library import install as library

        root = self.install_root / "library"
        pack_ids = []
        for component in plan.components:
            if component["type"] != "pack":
                continue
            target = root / "packs" / component["pack_id"]
            if not target.exists():
                self.notify("library", f"Installing reference library: {component['pack_id']}")
                archive = self.downloads / component["parts"][0]["file"]
                if len(component["parts"]) > 1:
                    archive = assemble(component["parts"], self.downloads, self.downloads / component["archive"],
                                       component["sha256"], component["bytes"])
                staging = root / "packs" / (".staging-" + component["pack_id"])
                if staging.exists():
                    shutil.rmtree(staging)
                safe_extract(archive, staging, component.get("unpacked_bytes"))
                inner = staging / component["pack_id"] if (staging / component["pack_id"]).is_dir() else staging
                library.quality_check(inner)
                os.replace(inner, target)
                shutil.rmtree(staging, ignore_errors=True)
            else:
                library.quality_check(target)
            pack_ids.append(component["pack_id"])
        library.activate(root, pack_ids, channel="release")
        return pack_ids

    def switch_current(self, plan):
        current_path = self.install_root / "current.json"
        previous = json.loads(current_path.read_text(encoding="utf-8")) if current_path.exists() else None
        data = {"version": plan.version, "profile": plan.profile, "include_nc": plan.include_nc,
                "installed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "previous": previous["version"] if previous and previous.get("version") != plan.version else
                (previous or {}).get("previous")}
        tmp = current_path.with_name("current.json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, current_path)
        return data

    def exclusive(self):
        """One setup at a time per download folder (two writers would corrupt partial files)."""
        import msvcrt

        self.downloads.mkdir(parents=True, exist_ok=True)
        handle = (self.downloads / "setup.lock").open("a+b")
        handle.seek(0)
        handle.write(b"1")
        handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            raise ReleaseError("Another Aster setup is already running. Wait for it to finish or close it first.") from None
        self._setup_lock = handle

    def run(self, profile, include_nc=True):
        if getattr(self, "_setup_lock", None) is None:
            self.exclusive()
        hw = hardware(self.install_root)
        plan = make_plan(self.lock, profile, self.install_root, self.downloads, include_nc)
        free = shutil.disk_usage(existing_parent(self.install_root)).free
        if free < plan.required_free_bytes:
            raise ReleaseError(f"Not enough free disk space: {fmt(plan.required_free_bytes)} needed, {fmt(free)} free on "
                               f"this drive. Free some space or choose another folder.")
        self.notify("plan", f"{fmt(plan.download_bytes)} to download, {fmt(plan.unpacked_bytes)} installed.", 0, plan.download_bytes)
        self.download(plan)
        version_dir = self.build_version(plan, self.lock["release_profile"])
        self.install_library(plan)
        current = self.switch_current(plan)
        self.prune_versions(keep={current["version"], current.get("previous")})
        if self.setup_exe and Path(self.setup_exe).is_file():
            shutil.copyfile(self.setup_exe, self.install_root / "AsterSetup.exe")
        (self.install_root / "release-lock.json").write_text(json.dumps(self.lock, indent=1), encoding="utf-8")
        if self.shortcuts:
            self.create_shortcuts(version_dir)
        if self.register:
            self.register_uninstall(plan)
        self.notify("done", "Installation verified.", 1, 1)
        return {"version_dir": str(version_dir), "plan": plan, "hardware": hw, "current": current}

    def prune_versions(self, keep):
        versions = self.install_root / "versions"
        for path in versions.iterdir() if versions.exists() else []:
            if path.is_dir() and path.name not in keep:
                shutil.rmtree(path, ignore_errors=True)

    # -- desktop integration (per user)
    def shortcut_targets(self):
        if self.shortcut_dirs:
            return [Path(p) for p in self.shortcut_dirs]
        appdata = Path(os.environ.get("APPDATA", str(Path.home())))
        dirs = [appdata / "Microsoft/Windows/Start Menu/Programs" / APP_NAME]
        if self.desktop_icon:
            dirs.append(Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop")
        return dirs

    def create_shortcuts(self, version_dir):
        entries = [("Aster.lnk", version_dir / "Aster.exe", "", "Start Aster (local medical information and study assistant)")]
        setup = self.install_root / "AsterSetup.exe"
        entries += [("Repair Aster.lnk", setup, "--repair", "Verify and repair the Aster installation"),
                    ("Uninstall Aster.lnk", setup, "--uninstall", "Remove Aster")]
        icon = version_dir / "Aster.exe"
        for directory in self.shortcut_targets():
            directory.mkdir(parents=True, exist_ok=True)
            for name, target, args, description in entries:
                if directory.name == "Desktop" and name != "Aster.lnk":
                    continue
                make_shortcut(directory / name, target, args, target.parent, icon, description)

    def remove_shortcuts(self):
        for directory in self.shortcut_targets():
            for name in ("Aster.lnk", "Repair Aster.lnk", "Uninstall Aster.lnk"):
                (directory / name).unlink(missing_ok=True)
            if directory.name == APP_NAME and directory.exists() and not any(directory.iterdir()):
                directory.rmdir()

    def register_uninstall(self, plan):
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.registry_key) as key:
            values = {"DisplayName": "Aster", "DisplayVersion": plan.version, "Publisher": "Aster project",
                      "InstallLocation": str(self.install_root),
                      "DisplayIcon": str(self.install_root / "versions" / plan.version / "Aster.exe"),
                      "UninstallString": f'"{self.install_root / "AsterSetup.exe"}" --uninstall',
                      "ModifyPath": f'"{self.install_root / "AsterSetup.exe"}" --repair',
                      "URLInfoAbout": "https://github.com/AyushM1701/ASTER-AI"}
            for name, value in values.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, int(plan.unpacked_bytes / 1024))
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 0)

    def unregister(self):
        import winreg

        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self.registry_key)
        except FileNotFoundError:
            pass

    # -- maintenance
    def repair(self, full=True):
        """Re-verify; rebuild the current version from (re)downloaded components if anything is damaged."""
        from aster_release.v2 import read_current, verify_installed

        current = read_current(self.install_root)
        if not current:
            raise ReleaseError("Aster is not installed here.")
        version_dir = self.install_root / "versions" / current["version"]
        problem = None
        try:
            self.notify("verify", "Checking every installed file…")
            verify_installed(version_dir, full=full)
            from aster_library import install as library

            for pack_id in json.loads((self.install_root / "library/active.json").read_text(encoding="utf-8"))["packs"]:
                library.quality_check(self.install_root / "library/packs" / pack_id)
        except (ReleaseError, OSError, ValueError, KeyError) as exc:
            problem = str(exc)
        if problem is None:
            self.notify("done", "No problems found.", 1, 1)
            return {"repaired": False}
        self.notify("repair", "Repairing: " + problem[:160])
        library_root = self.install_root / "library"
        for pack_dir in (library_root / "packs").glob("*") if (library_root / "packs").exists() else []:
            try:
                from aster_library import install as library

                library.quality_check(pack_dir)
            except Exception:
                shutil.rmtree(pack_dir, ignore_errors=True)
        self.run(current["profile"], current.get("include_nc", True))
        return {"repaired": True, "problem": problem}

    def rollback(self):
        from aster_release.v2 import read_current, verify_installed

        current = read_current(self.install_root)
        if not current or not current.get("previous"):
            raise ReleaseError("No previous Aster version is available to return to.")
        previous_dir = self.install_root / "versions" / current["previous"]
        verify_installed(previous_dir, full=True)
        data = {**current, "version": current["previous"], "previous": current["version"], "rolled_back": True}
        (self.install_root / "current.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        if self.shortcuts:
            self.create_shortcuts(previous_dir)
        from aster_library import install as library

        try:
            library.rollback(self.install_root / "library")
        except Exception:
            pass
        return data

    def uninstall(self, remove_user_data=False):
        if is_running(self.writable_root):
            raise ReleaseError("Close Aster before uninstalling.")
        self.remove_shortcuts()
        self.unregister()
        if self.install_root.exists():
            shutil.rmtree(self.install_root, ignore_errors=True)
        if remove_user_data and self.writable_root.exists():
            shutil.rmtree(self.writable_root, ignore_errors=True)
        return {"removed": str(self.install_root), "user_data_removed": remove_user_data}


def is_running(writable_root):
    lock = Path(writable_root) / "instance.lock"
    if not lock.exists():
        return False
    import msvcrt

    with lock.open("a+b") as handle:
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return False
        except OSError:
            return True


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16), ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, text):
        super().__init__()
        ctypes.oledll.ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(self))


def _method(pointer, index, *argtypes):
    """Call slot ``index`` of a COM object's vtable."""
    vtable = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    return ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *argtypes)(vtable[index])


def make_shortcut(path, target, arguments, workdir, icon, description):
    """Create a .lnk with the Unicode shell API (IShellLinkW + IPersistFile); no admin rights.

    WScript.Shell is ANSI-based and fails on paths such as 'Aster ✓', so it is not used."""
    ole32 = ctypes.oledll.ole32
    ole32.CoInitialize(None)
    link = ctypes.c_void_p()
    ole32.CoCreateInstance(ctypes.byref(_GUID("{00021401-0000-0000-C000-000000000046}")), None, 1,
                           ctypes.byref(_GUID("{000214F9-0000-0000-C000-000000000046}")), ctypes.byref(link))
    persist = ctypes.c_void_p()
    try:
        wstr = ctypes.c_wchar_p
        _method(link, 20, wstr)(link, str(target))            # SetPath
        _method(link, 11, wstr)(link, str(arguments))         # SetArguments
        _method(link, 9, wstr)(link, str(workdir))            # SetWorkingDirectory
        _method(link, 7, wstr)(link, str(description))        # SetDescription
        _method(link, 17, wstr, ctypes.c_int)(link, str(icon), 0)  # SetIconLocation
        _method(link, 0, ctypes.c_void_p, ctypes.c_void_p)(link, ctypes.byref(_GUID("{0000010b-0000-0000-C000-000000000046}")),
                                                           ctypes.byref(persist))  # QueryInterface(IPersistFile)
        _method(persist, 6, wstr, ctypes.c_int)(persist, str(path), 1)  # Save
    finally:
        if persist:
            _method(persist, 2)(persist)  # Release
        _method(link, 2)(link)
        ole32.CoUninitialize()


def existing_parent(path):
    path = Path(path)
    while not path.exists() and path.parent != path:
        path = path.parent
    return path


def fmt(n):
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} GB"
