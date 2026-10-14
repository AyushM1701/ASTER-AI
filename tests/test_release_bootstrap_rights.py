import csv

import pytest

from aster_release.build_support import check_bootstrap_rights
from aster_release.release import ReleaseError


def register(root, approved, pattern="installer/**"):
    folder = root / "packaging"
    folder.mkdir()
    row = {"asset_id": "bootstrap-runtime", "path_glob": pattern, "redistribution_allowed": str(approved),
           "modification_allowed": "true", "decision": "approved" if approved else "pending",
           "permission_basis": "Reviewed bundled licenses", "reviewer": "Fixture reviewer",
           "review_date": "2026-10-10", "attribution": "Fixture notices"}
    with (folder / "asset-rights.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def test_setup_runtime_pending_even_if_portable_can_be_cleared(tmp_path):
    register(tmp_path, False)
    with pytest.raises(ReleaseError, match="bootstrap-runtime"):
        check_bootstrap_rights(tmp_path)


def test_setup_runtime_requires_coverage(tmp_path):
    register(tmp_path, True, "bin/**")
    with pytest.raises(ReleaseError, match="no runtime rights coverage"):
        check_bootstrap_rights(tmp_path)


def test_affirmatively_reviewed_setup_runtime(tmp_path):
    register(tmp_path, True)
    check_bootstrap_rights(tmp_path)
