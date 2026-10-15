"""Setup engine: planning, disk checks, verified downloads, extraction and profiles."""
import functools
import hashlib
import http.server
import threading
import zipfile
from pathlib import Path

import pytest

from aster_release import setup_engine as se
from aster_release.release import ReleaseError

LOCK = {
    "version": "9.9.9", "release_base_url": "https://github.com/AyushM1701/ASTER-AI/releases/download/v9.9.9/",
    "default_profile": "standard", "profile_order": ["enhanced-gpu", "standard", "quality-cpu"],
    "profiles": {"standard": {}, "quality-cpu": {"requires": {"ram_gb": 16, "manual_only": True}},
                 "enhanced-gpu": {"requires": {"nvidia_vram_gb": 5.5}}},
    "components": [
        {"id": "app", "type": "zip", "parts": [{"file": "app.zip", "bytes": 100, "sha256": "0" * 64}], "unpacked_bytes": 1000, "profiles": ["*"]},
        {"id": "cuda", "type": "zip", "parts": [{"file": "cuda.zip", "bytes": 500, "sha256": "1" * 64}], "unpacked_bytes": 900,
         "profiles": ["enhanced-gpu"]},
        {"id": "library-nc", "type": "pack", "edition": "nc", "parts": [{"file": "nc.zip", "bytes": 50, "sha256": "2" * 64}],
         "unpacked_bytes": 60, "profiles": ["*"]},
    ],
}


def test_plan_selects_profile_components_and_counts_space(tmp_path):
    standard = se.make_plan(LOCK, "standard", tmp_path, tmp_path / "dl", include_nc=False)
    assert [c["id"] for c in standard.components] == ["app"]
    gpu = se.make_plan(LOCK, "enhanced-gpu", tmp_path, tmp_path / "dl")
    assert {c["id"] for c in gpu.components} == {"app", "cuda", "library-nc"}
    assert gpu.download_bytes == 650 and gpu.required_free_bytes > gpu.download_bytes + gpu.unpacked_bytes


def test_low_disk_is_refused_before_downloading(tmp_path, monkeypatch):
    monkeypatch.setattr(se.shutil, "disk_usage", lambda path: type("U", (), {"free": 10})())
    monkeypatch.setattr(se, "hardware", lambda target=None: {})
    installer = se.Installer(LOCK, tmp_path / "install", tmp_path / "writable", shortcuts=False, register=False)
    with pytest.raises(ReleaseError, match="Not enough free disk space"):
        installer.run("standard")
    assert not (tmp_path / "writable" / "downloads" / "9.9.9" / "app.zip").exists()


def test_profile_recommendation_uses_measured_hardware():
    assert se.recommend_profile({"gpus": [{"vram_gb": 6.0}], "ram_gb": 8}, LOCK)[0] == "enhanced-gpu"
    assert se.recommend_profile({"gpus": [{"vram_gb": 4.0}], "ram_gb": 32}, LOCK)[0] == "standard"
    assert se.recommend_profile({"gpus": [], "ram_gb": 8}, LOCK)[0] == "standard"


@pytest.mark.parametrize("url", ["http://github.com/x", "https://evil.example.com/x", "https://user:pw@github.com/x"])
def test_untrusted_hosts_are_rejected(url):
    with pytest.raises(ReleaseError):
        se.allowed_url(url)


def test_registry_and_cdn_hosts_are_allowed():
    assert se.allowed_url("https://registry.ollama.ai/v2/library/qwen3/blobs/sha256:abc")
    assert se.allowed_url("https://x.r2.cloudflarestorage.com/blob")


@pytest.fixture
def mirror(tmp_path):
    served = tmp_path / "served"
    served.mkdir()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler,
                                                                                directory=str(served)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield served, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_fetch_verifies_hash_and_rejects_tampered_content(tmp_path, mirror):
    served, base = mirror
    data = b"aster" * 1000
    (served / "file.bin").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    seen = []
    path = se.fetch([base + "/file.bin"], tmp_path / "out" / "file.bin", digest, len(data), mirror=base, progress=seen.append)
    assert path.read_bytes() == data and seen[-1] == len(data)
    (served / "bad.bin").write_bytes(b"x" * len(data))
    with pytest.raises(ReleaseError):
        se.fetch([base + "/bad.bin"], tmp_path / "out" / "bad.bin", digest, len(data), mirror=base, retries=1)
    assert not (tmp_path / "out" / "bad.bin").exists()


def test_loopback_requires_explicit_mirror(tmp_path, mirror):
    _, base = mirror
    with pytest.raises(ReleaseError):
        se.fetch([base + "/file.bin"], tmp_path / "f", "0" * 64, 1, retries=1)


def test_offline_folder_is_used_when_hash_matches(tmp_path):
    offline = tmp_path / "offline"
    offline.mkdir()
    data = b"offline asset"
    (offline / "a.bin").write_bytes(data)
    target = se.fetch([], tmp_path / "dl" / "a.bin", hashlib.sha256(data).hexdigest(), len(data), offline_dir=offline)
    assert target.read_bytes() == data


@pytest.mark.parametrize("name", ["../escape.txt", "dir/../../escape.txt", "C:/escape.txt", "CON/x.txt"])
def test_safe_extract_rejects_unsafe_entries(tmp_path, name):
    archive = tmp_path / "a.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(name, "x")
    with pytest.raises(ReleaseError):
        se.safe_extract(archive, tmp_path / "out")


def test_safe_extract_rejects_oversized_archive(tmp_path):
    archive = tmp_path / "bomb.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("big.bin", b"\0" * 5_000_000)
    with pytest.raises(ReleaseError, match="expands beyond"):
        se.safe_extract(archive, tmp_path / "out", expected_bytes=1000)


def test_assemble_verifies_joined_parts(tmp_path):
    data = b"0123456789" * 100
    (tmp_path / "p1").write_bytes(data[:600])
    (tmp_path / "p2").write_bytes(data[600:])
    parts = [{"file": "p1"}, {"file": "p2"}]
    out = se.assemble(parts, tmp_path, tmp_path / "whole.bin", hashlib.sha256(data).hexdigest(), len(data))
    assert out.read_bytes() == data
    with pytest.raises(ReleaseError):
        se.assemble(parts, tmp_path, tmp_path / "other.bin", "0" * 64, len(data))


def test_unicode_shortcut_round_trips(tmp_path):
    import os

    if os.name != "nt":
        pytest.skip("Windows shortcuts")
    folder = tmp_path / "Aster ✓ ünicode"
    folder.mkdir()
    target = folder / "target ✓.txt"
    target.write_text("x")
    se.make_shortcut(folder / "Aster ✓.lnk", target, "--repair", folder, Path("C:/Windows/notepad.exe"), "test ✓")
    assert (folder / "Aster ✓.lnk").stat().st_size > 0


def test_verify_only_checks_current_installations(tmp_path, capsys, monkeypatch):
    """Aster.exe --verify-only used the v1 manifest and crashed on every v2 install."""
    import json
    import sys

    import pytest

    from aster_release.launcher import main
    from aster_release.release import ReleaseError
    from aster_release.v2 import write_installed_manifest

    root = tmp_path / "versions" / "0.2.0"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "app.txt").write_text("app", encoding="utf-8")
    profile = {"app_version": "0.2.0", "profiles": {}}
    (root / "release-profile.json").write_text(json.dumps(profile), encoding="utf-8")
    write_installed_manifest(root, [], "standard", profile)
    monkeypatch.setattr(sys, "argv", ["Aster.exe", "--verify-only", "--root", str(root)])
    main()
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "verified" and report["mode"] == "full" and report["files"] == 2
    (root / "bin" / "app.txt").write_text("tampered", encoding="utf-8")
    with pytest.raises(ReleaseError, match="damaged"):
        main()


def test_repair_swap_retries_locks_and_never_leaves_no_version(tmp_path):
    """Acceptance run 7: a locked staging folder failed the repair swap after the old version was deleted."""
    versions = tmp_path / "versions"
    old, staging = versions / "0.2.0", versions / "0.2.0.staging"
    (old / "bin").mkdir(parents=True)
    (old / "Aster.exe").write_text("old", encoding="utf-8")
    staging.mkdir()
    (staging / "Aster.exe").write_text("new", encoding="utf-8")

    # Transient lock: retried, then the new version is in place and the old one removed.
    calls = {"n": 0}
    real = se.os.replace

    def flaky(src, dst):
        if Path(src) == staging and calls["n"] < 2:
            calls["n"] += 1
            raise PermissionError(5, "Access is denied")
        real(src, dst)

    se.swap_version(staging, old, replace=lambda s, d: _retrying(flaky, s, d))
    assert (old / "Aster.exe").read_text(encoding="utf-8") == "new"
    assert sorted(p.name for p in versions.iterdir()) == ["0.2.0"]

    # Permanent lock: the previous version is restored and the error is raised.
    staging.mkdir()
    (staging / "Aster.exe").write_text("newer", encoding="utf-8")

    def locked(src, dst):
        if Path(src) == staging:
            raise PermissionError(5, "Access is denied")
        real(src, dst)

    with pytest.raises(PermissionError):
        se.swap_version(staging, old, replace=locked)
    assert (old / "Aster.exe").read_text(encoding="utf-8") == "new"


def _retrying(operation, source, target, attempts=5):
    for attempt in range(attempts):
        try:
            return operation(source, target)
        except PermissionError:
            if attempt == attempts - 1:
                raise


def test_replace_with_retry_waits_out_transient_locks(tmp_path, monkeypatch):
    source, target = tmp_path / "a", tmp_path / "b"
    source.write_text("x", encoding="utf-8")
    failures = {"left": 3}
    real = se.os.replace

    def flaky(src, dst):
        if failures["left"]:
            failures["left"] -= 1
            raise PermissionError(5, "Access is denied")
        real(src, dst)

    monkeypatch.setattr(se.os, "replace", flaky)
    waits = []
    se.replace_with_retry(source, target, sleep=waits.append)
    assert target.read_text(encoding="utf-8") == "x" and len(waits) == 3


def test_packaged_settings_keep_user_data_outside_the_versioned_app(tmp_path):
    import json
    from pathlib import Path

    from aster_release.v2 import release_settings_v2

    profile = json.loads((Path(__file__).resolve().parents[1] / "packaging/release-profile.v2.json").read_text(encoding="utf-8"))
    root = tmp_path / "Aster" / "versions" / profile["app_version"]
    root.mkdir(parents=True)
    writable = tmp_path / "writable"
    settings = release_settings_v2(root, profile, "standard", writable=writable, api_port=8000, ollama_port=11435)
    assert settings.user_library_path == writable / "library" / "user"
    assert settings.workspace_path == writable / "workspaces" / "education.sqlite3"
    assert root.resolve() not in settings.user_library_path.resolve().parents
