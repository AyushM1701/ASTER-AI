from aster_release.installer import required_install_space
from aster_release.release import sha256


def fixture(root):
    cache = root / "downloads/0.1.0"
    cache.mkdir(parents=True)
    part = cache / "Aster-Windows-x64.zip.part001"
    part.write_bytes(b"payload" * 100)
    manifest = {"app_version": "0.1.0", "archive_bytes": 700, "installed_bytes": 1200,
                "parts": [{"name": part.name, "size": 700, "sha256": sha256(part)}]}
    part.unlink()
    return cache, part, manifest


def test_interrupted_install_still_fits_original_disk_budget(tmp_path):
    cache, part, manifest = fixture(tmp_path)
    original_budget = required_install_space(manifest, tmp_path)
    part.with_suffix(part.suffix + ".partial").write_bytes(b"payload" * 75)
    remaining_free = original_budget - 525
    assert required_install_space(manifest, tmp_path) <= remaining_free
    # A server which restarts instead of resuming truncates those 525 bytes;
    # eventual content must still pass the full checksum before installation.


def test_verified_cached_parts_and_overwritten_archive_are_accounted(tmp_path):
    cache, part, manifest = fixture(tmp_path)
    original_budget = required_install_space(manifest, tmp_path)
    part.write_bytes(b"payload" * 100)
    (cache / "complete.zip").write_bytes(b"untrusted but overwritten" * 20)
    assert required_install_space(manifest, tmp_path) == original_budget - 700 - 500
    part.write_bytes(b"changed" * 100)
    assert required_install_space(manifest, tmp_path) == original_budget - 500


def test_offline_parts_need_no_second_download_copy(tmp_path):
    _, _, manifest = fixture(tmp_path)
    assert required_install_space(manifest, tmp_path, offline_parts=True) == required_install_space(manifest, tmp_path) - 700
