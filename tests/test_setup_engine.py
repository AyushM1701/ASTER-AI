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
