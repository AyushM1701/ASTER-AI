import hashlib
import json

import pytest

from aster_release.release import ReleaseError, contained, generate_manifest, verify_package


def package(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app/test.txt").write_text("Aster")
    profile = {"schema_version": 1, "app_version": "0.1.0-beta.1", "edition": "ValidationOnly",
               "settings": {}, "model": None, "features": {}, "components": [], "data": {}}
    generate_manifest(tmp_path, profile)
    return tmp_path


@pytest.mark.parametrize("name", ["../escape", "/etc/passwd", "C:/escape", "x\\y", "x:stream", "a/../../b", "CON", "a./b", "a//b"])
def test_unsafe_paths_rejected(tmp_path, name):
    with pytest.raises(ReleaseError):
        contained(tmp_path, name)


def test_integrity_fails_closed(tmp_path):
    root = package(tmp_path)
    assert verify_package(root)["status"] == "verified"
    (root / "app/test.txt").write_text("tampered")
    with pytest.raises(ReleaseError, match="changed"):
        verify_package(root)


def test_unlisted_file_rejected(tmp_path):
    root = package(tmp_path)
    (root / ".env").write_text("SECRET=x")
    with pytest.raises(ReleaseError, match="Unlisted"):
        verify_package(root)


def test_manifest_trust_pin(tmp_path):
    root = package(tmp_path)
    digest = hashlib.sha256((root / "release-manifest.json").read_bytes()).hexdigest()
    assert verify_package(root, digest)["status"] == "verified"
    with pytest.raises(ReleaseError, match="trust"):
        verify_package(root, "0" * 64)


def test_public_requires_rights(tmp_path):
    root = package(tmp_path)
    data = json.loads((root / "release-manifest.json").read_text())
    data["edition"] = "PublicStandard"
    (root / "release-manifest.json").write_text(json.dumps(data))
    with pytest.raises(ReleaseError, match="rights"):
        verify_package(root)
