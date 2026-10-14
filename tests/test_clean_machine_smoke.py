import json

import pytest

from aster_release.acceptance import validate_acceptance
from aster_release.release import ReleaseError, sha256


def test_source_tests_cannot_satisfy_packaged_release_acceptance(tmp_path):
    manifest = tmp_path / "release-manifest.json"
    manifest.write_text("{}")
    report = {"manifest_sha256": sha256(manifest), "reviewer": "Developer", "review_date": "2026-10-10",
              "tests": {"pytest": {"passed": True, "evidence": "all source tests passed"}}}
    with pytest.raises(ReleaseError, match="acceptance incomplete"):
        validate_acceptance(report, manifest)


def test_acceptance_template_is_unclaimed():
    from pathlib import Path
    template = json.loads((Path(__file__).parents[1] / "packaging/acceptance-template.json").read_text())
    assert all(value["passed"] is None for value in template["tests"].values())
    assert template["clinical_validation"] is False
