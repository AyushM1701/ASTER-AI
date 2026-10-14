import stat
import zipfile

import pytest

from aster_release.distribution import split_archive
from aster_release.installer import (
    allowed_url,
    commit_install,
    extract_verified,
    validate_distribution,
)
from aster_release.release import ReleaseError, generate_manifest, sha256


@pytest.mark.parametrize("url", ["http://github.com/x", "https://evil.invalid/x", "https://github.com@evil.invalid/x", "https://github.com:444/x", "file:///x"])
def test_download_hosts_are_pinned(url):
    with pytest.raises(ReleaseError):
        allowed_url(url)


@pytest.mark.parametrize("entry", ["../escape", "C:/escape", "a\\..\\escape", "CON", "a:stream"])
def test_zip_traversal_rejected(tmp_path, entry):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(entry, "payload")
    destination = tmp_path / "staging"
    with pytest.raises(ReleaseError):
        extract_verified(archive, destination, 100)
    assert not destination.exists()


def test_zip_symlink_and_case_collision_rejected(tmp_path):
    for index, symlink in enumerate([True, False]):
        archive = tmp_path / f"bad{index}.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            if symlink:
                info = zipfile.ZipInfo("link")
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                bundle.writestr(info, "../outside")
            else:
                bundle.writestr("FILE.txt", "a")
                bundle.writestr("file.txt", "b")
        with pytest.raises(ReleaseError):
            extract_verified(archive, tmp_path / f"stage{index}", 100)


def test_split_parts_reassemble_exactly(tmp_path):
    content = bytes(range(256)) * 23
    archive = tmp_path / "bundle.zip"
    archive.write_bytes(content)
    parts = split_archive(archive, tmp_path / "parts", part_size=1024)
    assert all(p["size"] <= 1024 for p in parts)
    assert b"".join((tmp_path / "parts" / p["name"]).read_bytes() for p in parts) == content
    assert all(sha256(tmp_path / "parts" / p["name"]) == p["sha256"] for p in parts)


def test_commit_verifies_before_current_pointer_changes(tmp_path):
    stage = tmp_path / "staging" / "test"
    stage.mkdir(parents=True)
    (stage / "asset").write_text("good")
    profile = {"edition": "ValidationOnly", "settings": {}, "features": {}, "data": {}, "components": [], "model": None, "app_version": "0.1.0"}
    generate_manifest(stage, profile)
    expected = sha256(stage / "release-manifest.json")
    (stage / "asset").write_text("bad")
    with pytest.raises(ReleaseError):
        commit_install(tmp_path, stage, {"app_version": "0.1.0", "release_manifest_sha256": expected})
    assert not (tmp_path / "current.json").exists()


def test_distribution_rejects_validation_build():
    with pytest.raises(ReleaseError):
        validate_distribution({"schema_version": 1, "edition": "ValidationOnly", "app_version": "0.1.0"})
