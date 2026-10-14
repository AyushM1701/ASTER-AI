import hashlib
import json

import pytest

from tests.mds_fixtures import make_teacher


def setup_inputs(tmp_path):
    teacher, rows = make_teacher(tmp_path, [("apoptosis", "Definition",
        "Apoptosis is a synthetic example used only to test software mechanics.")])
    row = rows[0]
    unit = {"id": "fixture", "topics": ["apoptosis"], "text": row.text,
            "citation_ids": [row.chunk_id], "source_hashes": {row.chunk_id: row.content_hash()},
            "review_status": "developer_reviewed", "reviewer": "Test fixture", "clinical_review": False}
    release = teacher.settings.teaching_release_path
    (release / "explanations.json").write_text(json.dumps({"units": [unit], "release_version": "synthetic-v1"}))
    manifest = json.loads((release / "manifest.json").read_text())
    manifest["files"]["explanations.json"] = hashlib.sha256((release / "explanations.json").read_bytes()).hexdigest()
    (release / "manifest.json").write_text(json.dumps(manifest))
    teacher.close()
    decisions = [{"unit_id": unit["id"], "prepared_sha256": hashlib.sha256(unit["text"].encode()).hexdigest(),
                  "parent_hashes": unit["source_hashes"], "review_origin": "ai_source_inspection",
                  "clinical_review": False, "support_rationale": "Synthetic fixture read; definition only.",
                  "qualification_note": "Synthetic software fixture retained in full.",
                  "bindings": [{"topic_id": "apoptosis", "facet": "definition", "scope": ""}]}]
    return release, decisions, tmp_path / "new-pack"


def test_binding_stage_preserves_parent_bytes_and_original_release(tmp_path):
    from scripts.stage_prepared_bindings import stage

    release, decisions, output = setup_inputs(tmp_path)
    old = (release / "manifest.json").read_bytes()
    report = stage(release, decisions, output)
    assert report["activation"] == "none"
    assert (release / "manifest.json").read_bytes() == old
    assert (output / "records.jsonl").read_bytes() == (release / "records.jsonl").read_bytes()
    unit = json.loads((output / "explanations.json").read_text())["units"][0]
    assert unit["facet_bindings"] == decisions[0]["bindings"]
    assert unit["facet_review"]["review_origin"] == "ai_source_inspection"
    assert unit["clinical_review"] is False


@pytest.mark.parametrize("field,value", [
    ("prepared_sha256", "0" * 64), ("parent_hashes", {}),
    ("clinical_review", True), ("review_origin", "faculty"),
])
def test_forged_or_changed_decision_cannot_create_pack(tmp_path, field, value):
    from scripts.stage_prepared_bindings import stage

    release, decisions, output = setup_inputs(tmp_path)
    decisions[0][field] = value
    with pytest.raises(ValueError):
        stage(release, decisions, output)
    assert not output.exists()
