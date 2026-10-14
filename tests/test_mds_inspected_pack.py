"""Synthetic staging mechanics; no medical or human review attestations."""

import copy
import hashlib
import json

import pytest
import yaml

from backend.app.config import Settings
from backend.app.services.question_plan import RequestedFacet
from backend.app.services.teaching import TeachingStore
from tests.mds_fixtures import make_teacher
from tests.test_mds_reviewed_evidence import annotation_for


@pytest.fixture
def inputs(tmp_path):
    teacher, rows = make_teacher(tmp_path, [("apoptosis", "Apoptosis / Context",
        "Apoptosis has a synthetic developmental role in this mechanics fixture. "
        "A scaffold is removed when construction finishes. "
        "This analogy has qualified limitations and is not a clinical explanation.")])
    row = rows[0]
    facet = RequestedFacet(topic_id="apoptosis", facet="functions", query="apoptosis functions")
    annotation = annotation_for(facet, row) | {
        "review_status": "source_inspected", "review_origin": "ai_source_inspection",
        "reviewer": "Codex", "support_rationale": "Synthetic mechanics: this whole unit explains a role with contextual analogy.",
        "qualification_note": "Synthetic mechanics: the complete limitation sentence is retained.",
        "source_context": "Synthetic mechanics fixture, not a biomedical source or production annotation.",
    }
    inspection = tmp_path / "inspection.jsonl"
    inspection.write_text(json.dumps(annotation) + "\n", encoding="utf-8")
    return teacher.settings.teaching_release_path, inspection, annotation, row, tmp_path / "candidate-pack"


def test_staging_preserves_whole_source_identity_and_ai_origin(inputs):
    from scripts.stage_mds_inspected_pack import stage

    release, inspection, annotation, row, output = inputs
    input_manifest = (release / "manifest.json").read_bytes()
    report = stage(release, inspection, output)
    assert report["activation"] == "none"
    assert report["clinical_review"] == "pending_F03"
    assert report["records"] == 1 and report["inspected_bindings"] == 1
    assert (release / "manifest.json").read_bytes() == input_manifest
    packed = json.loads((output / "records.jsonl").read_text(encoding="utf-8"))
    assert packed == row.model_dump()
    source = yaml.safe_load((output / "sources.yaml").read_text(encoding="utf-8"))["sources"][0]
    original = yaml.safe_load((release / "sources.yaml").read_text(encoding="utf-8"))["sources"][0]
    assert source == original
    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))["chunks"][row.chunk_id]
    assert metadata["ai_inspected_facet_bindings"] == [annotation]
    assert "reviewed_facet_bindings" not in metadata
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "inactive_ai_inspected_development_candidate"
    assert manifest["lineage"][0]["manifest_sha256"] == hashlib.sha256(input_manifest).hexdigest()
    store = TeachingStore(Settings(_env_file=None, teaching_backend="lexical", teaching_release_path=output, enable_teaching=True))
    try:
        assert store.error is None and store.records[0].content_hash() == row.content_hash()
    finally:
        store.close()


@pytest.mark.parametrize("field,value", [
    ("review_origin", "human_entered"), ("reviewer", "Faculty reviewer"),
    ("review_status", "developer_reviewed"), ("clinical_review", True),
    ("support_rationale", ""), ("qualification_note", ""), ("source_context", ""),
    ("text_sha256", "b" * 64), ("source_sha256", "b" * 64),
    ("record_sha256", "b" * 64), ("source_id", "forged"),
    ("start", 1), ("end", 15), ("retained_qualifications", ["absent qualification"]),
])
def test_invalid_inspection_rejects_without_output(inputs, field, value):
    from scripts.stage_mds_inspected_pack import stage

    release, inspection, annotation, _, output = inputs
    annotation[field] = value
    inspection.write_text(json.dumps(annotation), encoding="utf-8")
    with pytest.raises(ValueError):
        stage(release, inspection, output)
    assert not output.exists()


def test_staging_output_is_immutable(inputs):
    from scripts.stage_mds_inspected_pack import stage

    release, inspection, _, _, output = inputs
    stage(release, inspection, output)
    before = (output / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        stage(release, inspection, output)
    assert (output / "manifest.json").read_bytes() == before


def test_changed_release_manifest_cannot_be_staged(inputs):
    from scripts.stage_mds_inspected_pack import stage

    release, inspection, _, _, output = inputs
    with (release / "records.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(ValueError):
        stage(release, inspection, output)
    assert not output.exists()


def test_existing_source_hold_cannot_be_overridden(inputs):
    from scripts.stage_mds_inspected_pack import stage

    release, inspection, _, row, output = inputs
    metadata = {row.chunk_id: {"retraction_status": "retracted"}}
    (release / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"]["metadata.json"] = hashlib.sha256((release / "metadata.json").read_bytes()).hexdigest()
    (release / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        stage(release, inspection, output)
    assert not output.exists()


def test_multiple_inspected_facets_reuse_one_unchanged_unit(inputs):
    from scripts.stage_mds_inspected_pack import stage

    release, inspection, annotation, _, output = inputs
    second = copy.deepcopy(annotation)
    second["facet"] = "outcome"
    inspection.write_text("\n".join(json.dumps(a) for a in (annotation, second)), encoding="utf-8")
    report = stage(release, inspection, output)
    assert report["records"] == 1 and report["inspected_bindings"] == 2


def test_output_cannot_enter_source_release(inputs):
    from scripts.stage_mds_inspected_pack import stage

    release, inspection, _, _, _ = inputs
    with pytest.raises(ValueError):
        stage(release, inspection, release / "new-pack")


def test_release_bound_source_review_hold_cannot_be_staged(inputs):
    from scripts.stage_mds_inspected_pack import stage

    release, inspection, _, row, output = inputs
    manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    explanations = {"release_version": manifest["version"], "units": [], "source_review_flags": [{
        "chunk_id": row.chunk_id, "content_sha256": row.content_hash(),
        "runtime_policy": "explanation_only", "reason": "Synthetic editorial hold.", "clinical_review": False,
    }]}
    (release / "explanations.json").write_text(json.dumps(explanations), encoding="utf-8")
    manifest["files"]["explanations.json"] = hashlib.sha256((release / "explanations.json").read_bytes()).hexdigest()
    (release / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="source hold"):
        stage(release, inspection, output)
    assert not output.exists()
