"""Prepared-text wiring fixtures are synthetic and never production notes."""

import copy
import hashlib
import json

import pytest

from backend.app.services.answer_composer import compose
from backend.app.services.evidence_plan import EvidencePlan, FacetEvidence
from backend.app.services.output_validation import finalize
from backend.app.services.prepared_evidence import prepared_support
from backend.app.services.question_plan import plan_question
from backend.app.services.teaching import TeachingStore
from tests.mds_fixtures import make_teacher


@pytest.fixture
def prepared_release(tmp_path):
    teacher, rows = make_teacher(tmp_path, [("apoptosis", "Synthetic mechanics source",
        "Apoptosis is a named concept in this synthetic source fixture with explicit qualifications.")])
    row = rows[0]
    plan = plan_question("Define apoptosis and explain its mechanism", "study")
    text = "This prepared fixture retains an explanatory analogy. Think of a fixture label that points to a named source. The analogy has limited scope and is not a clinical answer."
    unit = {"id": "synthetic-prepared", "topics": ["apoptosis"], "text": text,
            "citation_ids": [row.chunk_id], "source_hashes": {row.chunk_id: row.content_hash()},
            "prepared_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "facet_bindings": [{"topic_id": f.topic_id, "facet": f.facet, "scope": f.scope} for f in plan.facets],
            "qualifications": ["limited scope"], "review_status": "developer_reviewed",
            "reviewer": "Synthetic test fixture", "clinical_review": False}
    root = teacher.settings.teaching_release_path
    notes = root / "explanations.json"
    notes.write_text(json.dumps({"release_version": teacher.version, "units": [unit]}), encoding="utf-8")
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["explanations.json"] = hashlib.sha256(notes.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    teacher = TeachingStore(teacher.settings)
    assert teacher.error is None and teacher.units[0] == unit
    evidence = EvidencePlan(source_set_version=teacher.version,
        facets=[FacetEvidence(request=f) for f in plan.facets])
    records = teacher.references.id_records
    result = compose(plan, evidence, records, prepared_units=teacher.units,
                     source_metadata=teacher.metadata, review_flags=teacher.review_flags)
    return teacher, plan, evidence, result


def checked(fixture, result=None, units=None):
    teacher, plan, _, original = fixture
    return finalize(plan.original_question, result or original,
                    teacher.units if units is None else units, plan,
                    teacher.metadata, teacher.review_flags, teacher.references.id_records)


def test_loaded_prepared_unit_fills_missing_raw_facets_without_quote_coordinates(prepared_release):
    teacher, plan, evidence, result = prepared_release
    answer = checked(prepared_release)
    assert answer["coverage_status"] == "complete" and answer["task_completion"]
    assert answer["claims"] == [{"text": teacher.units[0]["text"], "citation_ids": teacher.units[0]["citation_ids"]}]
    assert not result["claim_evidence"]
    assert len(result["prepared_claim_evidence"]) == len(plan.facets)
    assert all(section["state"] == "supported" for section in result["structured_answer"]["sections"])
    assert all(f.state == "missing" for f in evidence.facets)
    assert answer["clinical_review"] is False and answer["clinical_review_status"] == "pending"


@pytest.mark.parametrize("field,value", [
    ("prepared_id", "invented"), ("prepared_text_sha256", "b" * 64),
    ("source_hashes", {}), ("scope", "in pregnancy"), ("facet", "histopathology"),
    ("topic_id", "necrosis"), ("claim_index", True), ("start", 0),
    ("review_status", "clinically_reviewed"),
])
def test_generated_provenance_cannot_forge_unit_or_coordinates(prepared_release, field, value):
    result = copy.deepcopy(prepared_release[3])
    result["prepared_claim_evidence"][0][field] = value
    answer = checked(prepared_release, result)
    assert not answer["claims"] and "invalid_prepared_binding" in answer["rejection_codes"]


@pytest.mark.parametrize("surface", ["text", "citation_ids", "source_excerpt", "source_snapshot", "source_url", "citation_review"])
def test_prepared_claim_and_citations_must_match_actual_release(prepared_release, surface):
    result = copy.deepcopy(prepared_release[3])
    if surface == "text":
        result["claims"][0]["text"] = result["claims"][0]["text"].replace("limited scope", "unlimited scope")
    elif surface == "citation_ids":
        result["claims"][0]["citation_ids"] = ["invented"]
    else:
        key = {"source_excerpt": "excerpt", "source_snapshot": "snapshot_id", "source_url": "url", "citation_review": "clinical_review"}[surface]
        result["citations"][0][key] = True if key == "clinical_review" else "invented"
    answer = checked(prepared_release, result)
    assert not answer["claims"] and not answer["task_completion"]


def test_prepared_pointer_is_not_trusted_without_out_of_band_units(prepared_release):
    answer = checked(prepared_release, units=[])
    assert not answer["claims"] and "invalid_prepared_binding" in answer["rejection_codes"]


@pytest.mark.parametrize("field,value", [
    ("facet_bindings", []), ("prepared_text_sha256", None), ("source_hashes", {}),
    ("qualifications", ["invented qualification"]), ("clinical_review", True),
])
def test_no_facets_are_inferred_from_topics_or_headings(prepared_release, field, value):
    teacher, plan, evidence, _ = prepared_release
    units = copy.deepcopy(teacher.units)
    units[0][field] = value
    result = compose(plan, evidence, teacher.references.id_records, prepared_units=units)
    assert not result["claims"]


@pytest.mark.parametrize("metadata", [
    {"runtime_policy": "exclude"}, {"runtime_policy": "explanation_only"},
    {"retraction_status": "retracted"}, {"superseded_by": "v2"},
    {"review_state": "quarantined"}, {"extraction_quality": "corrupted"},
])
def test_source_holds_are_rechecked_at_terminal_boundary(prepared_release, metadata):
    teacher = prepared_release[0]
    teacher.metadata[teacher.units[0]["citation_ids"][0]].update(metadata)
    assert not checked(prepared_release)["claims"]


def test_changed_record_or_review_hold_blocks_prepared_text(prepared_release):
    teacher, plan, _, _ = prepared_release
    key = teacher.units[0]["citation_ids"][0]
    row = teacher.references.id_records[key]
    teacher.references.id_records[key] = row.model_copy(update={"snapshot_id": "v2"})
    assert not checked(prepared_release)["claims"]
    teacher.references.id_records[key] = row
    teacher.review_flags[key] = {"runtime_policy": "explanation_only"}
    assert not checked(prepared_release)["claims"]


def test_research_context_permission_and_exact_scope_are_required(prepared_release):
    teacher, plan, _, _ = prepared_release
    unit = teacher.units[0]
    records = teacher.references.id_records
    facet = plan.facets[0]
    assert not prepared_support(facet.model_copy(update={"scope": "in pregnancy"}), unit, records)
    key = unit["citation_ids"][0]
    teacher.metadata[key].update(material_type="research", study_type="test", study_context="Study context absent from prepared text", limitations="Synthetic limitations")
    assert not checked(prepared_release)["claims"]
    teacher.metadata[key] = {}
    records[key] = records[key].model_copy(update={"permission_basis": {}})
    assert not checked(prepared_release)["claims"]


@pytest.mark.parametrize("limitations,accepted", [(["Synthetic study limitation"], True), ([], False), ([None], False), (None, False)])
def test_research_limitations_follow_existing_list_schema(prepared_release, limitations, accepted):
    teacher, plan, _, _ = prepared_release
    unit = copy.deepcopy(teacher.units[0])
    records = teacher.references.id_records
    key = unit["citation_ids"][0]
    context = "Synthetic study context."
    records[key].text = context + " " + records[key].text
    unit["text"] = context + " " + unit["text"]
    unit["source_hashes"][key] = records[key].content_hash()
    unit["prepared_text_sha256"] = hashlib.sha256(unit["text"].encode()).hexdigest()
    metadata = {key: {"material_type": "research", "study_type": "test", "study_context": context, "limitations": limitations}}
    assert prepared_support(plan.facets[0], unit, records, metadata) is accepted


def test_budget_and_conflicts_preserve_whole_unit(prepared_release):
    teacher, plan, evidence, _ = prepared_release
    records = teacher.references.id_records
    result = compose(plan, evidence, records, max_chars=10, prepared_units=teacher.units)
    assert not result["claims"]
    evidence.facets[0].state = "contradictory"
    result = compose(plan, evidence, records, prepared_units=teacher.units)
    assert result["structured_answer"]["sections"][0]["state"] == "contradictory"
    assert not checked(prepared_release, result)["task_completion"]


def test_prepared_review_never_bypasses_medical_policy(prepared_release):
    teacher, plan, evidence, _ = prepared_release
    unit = copy.deepcopy(teacher.units[0])
    unit["text"] += " You should take 10 mg daily."
    unit["prepared_text_sha256"] = hashlib.sha256(unit["text"].encode()).hexdigest()
    result = compose(plan, evidence, teacher.references.id_records, prepared_units=[unit])
    assert not result["claims"]


def test_hidden_prepared_section_cannot_count_as_displayed_coverage(prepared_release):
    result = copy.deepcopy(prepared_release[3])
    result["structured_answer"]["sections"][0]["claim_indices"] = []
    answer = checked(prepared_release, result)
    assert answer["coverage_status"] == "partial" and not answer["task_completion"]


def allow_exact_prepared_hold(fixture):
    teacher, plan, evidence, result = fixture
    key = teacher.units[0]["citation_ids"][0]
    teacher.review_flags[key] = {
        "runtime_policy": "explanation_only", "content_sha256": teacher.references.id_records[key].content_hash(),
        "reason": "Synthetic raw source wording hold", "clinical_review": False,
        "allowed_explanation_ids": [teacher.units[0]["id"]],
    }
    result.clear()
    result.update(compose(plan, evidence, teacher.references.id_records, prepared_units=teacher.units,
                          source_metadata=teacher.metadata, review_flags=teacher.review_flags))
    return key


def test_explicit_hold_whitelist_admits_only_exact_prepared_text(prepared_release):
    teacher, plan, evidence, result = prepared_release
    key = allow_exact_prepared_hold(prepared_release)
    teacher.metadata[key]["runtime_policy"] = "explanation_only"
    assert checked(prepared_release)["task_completion"]
    composed = compose(plan, evidence, teacher.references.id_records, prepared_units=teacher.units,
                       source_metadata=teacher.metadata, review_flags=teacher.review_flags)
    assert composed["claims"] == result["claims"]
    assert composed["citations"][0]["source_review_notice"] == teacher.review_flags[key]["reason"]
    assert composed["citations"][0]["excerpt"] == teacher.references.id_records[key].text
    missing_notice = copy.deepcopy(composed)
    missing_notice["citations"][0].pop("source_review_notice")
    assert not checked(prepared_release, missing_notice)["claims"]
    forged_notice = copy.deepcopy(composed)
    forged_notice["citations"][0]["source_review_notice"] = "Clinically reviewed and corrected"
    assert not checked(prepared_release, forged_notice)["claims"]
    # A whitelisted correction does not release the held original quotation.
    raw = copy.deepcopy(result)
    raw.pop("prepared_claim_evidence")
    raw["claims"][0]["text"] = teacher.references.id_records[key].text
    assert not checked(prepared_release, raw)["claims"]
    altered = copy.deepcopy(result)
    altered["claims"][0]["text"] += " Extra text."
    assert not checked(prepared_release, altered)["claims"]


@pytest.mark.parametrize("field,value", [
    ("runtime_policy", "exclude"), ("content_sha256", "b" * 64),
    ("allowed_explanation_ids", ["some-other-unit"]), ("allowed_explanation_ids", []),
    ("clinical_review", True), ("reason", ""),
])
def test_hold_whitelist_cannot_override_other_holds_or_versions(prepared_release, field, value):
    teacher = prepared_release[0]
    key = allow_exact_prepared_hold(prepared_release)
    teacher.review_flags[key][field] = value
    assert not checked(prepared_release)["claims"]


def test_source_metadata_exclude_wins_over_prepared_whitelist(prepared_release):
    teacher = prepared_release[0]
    key = allow_exact_prepared_hold(prepared_release)
    teacher.metadata[key]["runtime_policy"] = "exclude"
    assert not checked(prepared_release)["claims"]


def test_mixed_standalone_facet_visible_but_removed_comparison_axis_stays_missing(prepared_release):
    teacher, plan, evidence, _ = prepared_release
    # This mechanics plan has one axis and a standalone mechanism section.
    # Coverage uses the requested axis contract even if output hides the axis.
    mixed = plan.model_copy(update={"task": "compare", "comparison_axes": ["definition"]})
    result = compose(mixed, evidence, teacher.references.id_records, prepared_units=teacher.units)
    answer = finalize(mixed.original_question, result, teacher.units, mixed,
                      teacher.metadata, teacher.review_flags, teacher.references.id_records)
    assert answer["task_completion"]
    result["comparison"]["axes"] = [{"facet": "other", "cells": []}]
    from backend.app.services.output_validation import facet_coverage

    coverage = facet_coverage(mixed, result, teacher.metadata, teacher.references.id_records, teacher.units)
    assert {f["facet"] for f in coverage["covered_facets"]} == {"mechanism"}
    assert {f["facet"] for f in coverage["missing_facets"]} == {"definition"}
