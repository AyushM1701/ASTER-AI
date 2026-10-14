"""Benchmark provenance and assessment-integrity tests, not medical answer keys."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
from shutil import copytree

import pytest

from scripts.evaluate_mds_supplied import (
    cases_from_bank,
    prepared_identity_signals,
    task_shape_signals,
)
from scripts.mds_supplied_contracts import (
    DEFAULT_BANK,
    SPECIALTIES,
    digest,
    lock_bank,
    read_rows,
    verify_bank,
)


def test_supplied_bank_preserves_every_specialty_and_conversation_turn():
    manifest = verify_bank()
    cases = cases_from_bank(DEFAULT_BANK)
    assert manifest["case_count"] == len(cases) == 89
    assert sum(len(c["turns"]) for c in cases) == manifest["supplied_turn_count"] == 93
    assert len({c["case_id"] for c in cases}) == 89
    for specialty in SPECIALTIES:
        rows = [c for c in cases if c["case_id"].startswith(specialty + "-")]
        assert len(rows) == 6
        assert {c["task_shape"] for c in rows} == {
            "explanation", "mechanism", "comparison", "educational_case" if specialty != "public_health" else "public_health_case",
            "long_answer", "interactive_viva",
        }
    assert manifest["files"]["inputs/oral-pathology.txt"] == "e5a95584efcacc3bf5342c7fcb64607d4a5fc6df20c2aed60640c1e4147362cc"
    assert manifest["files"]["inputs/all-specialties.txt"] == "8040c785c80feeaae3eab164711b786fd8fd8de8547797e22a12c84b32ac5439"
    assert all(c["clinical_reference_answer"] is None and not c["independent_unseen"] for c in cases)


def test_input_bytes_question_spelling_and_bounded_sources_are_hash_locked(tmp_path):
    bank = tmp_path / "bank"
    copytree(DEFAULT_BANK, bank)
    verify_bank(bank)
    # Changing one question byte is a broken lock even if the JSON still parses.
    path = bank / "supplied.jsonl"
    path.write_bytes(path.read_bytes().replace(b"oral epithelium", b"oral epitheliUm", 1))
    with pytest.raises(ValueError, match="Locked bank bytes changed"):
        verify_bank(bank)


def test_manifest_edit_cannot_silently_update_a_question_lock(tmp_path):
    bank = tmp_path / "bank"
    copytree(DEFAULT_BANK, bank)
    path = bank / "manifest.json"
    path.write_bytes(path.read_bytes().replace(b'"case_count": 89', b'"case_count": 88'))
    with pytest.raises(ValueError, match="manifest"):
        verify_bank(bank)


def test_lock_creation_refuses_to_overwrite_existing_artifacts(tmp_path):
    bank = tmp_path / "bank"
    oral, all_specialties = (DEFAULT_BANK / "inputs" / n for n in ("oral-pathology.txt", "all-specialties.txt"))
    lock_bank(bank, oral, all_specialties)
    original = (bank / "supplied.jsonl").read_bytes()
    with pytest.raises(FileExistsError):
        lock_bank(bank, oral, all_specialties)
    assert (bank / "supplied.jsonl").read_bytes() == original


def test_progressive_turns_keep_different_requested_scope_and_conditional_grading():
    cases = {c["case_id"]: c for c in read_rows(DEFAULT_BANK / "supplied.jsonl")}
    apoptosis = cases["oral-29"]
    assert len(apoptosis["turns"]) == 2
    assert "simple language" in apoptosis["turns"][0]["question"]
    assert "postgraduate detail without repeating" in apoptosis["turns"][1]["question"]
    assert {f["facet"] for f in apoptosis["turn_content_contracts"][0]} == {"molecular_features"}
    assert {f["facet"] for f in apoptosis["turn_content_contracts"][1]} == {"intrinsic_pathway", "extrinsic_pathway"}
    implant = cases["cross-E"]
    assert len(implant["turns"]) == 4
    assert implant["turns"][3]["question"].startswith("After I answer,")
    assert implant["turn_content_contracts"][2:] == [[], []]
    assert "not a learner answer" in implant["conditional_turn_note"]


def test_multipart_facets_stay_with_their_requested_subject():
    cases = {c["case_id"]: c for c in read_rows(DEFAULT_BANK / "supplied.jsonl")}
    inflammation = {(f["topic_id"], f["facet"]) for f in cases["oral-20"]["expected_content_facets"]}
    assert ("local:chronic_periapical_inflammation", "mechanism") in inflammation
    assert ("radicular_cyst", "histopathology") in inflammation
    assert ("radicular_cyst", "mechanism") not in inflammation
    fibrosis = {(f["topic_id"], f["facet"]) for f in cases["oral-28"]["expected_content_facets"]}
    assert ("local:oral_submucous_fibrosis", "mechanism") in fibrosis
    assert ("local:oral_lichen_planus", "mechanism") not in fibrosis
    assert len(cases["oral-28"]["separate_parts"]) == 3


def test_related_paraphrases_are_disclosed_and_do_not_claim_independence():
    variations = read_rows(DEFAULT_BANK / "variations.jsonl")
    assert len(variations) == 18
    distribution = Counter(c["specialties"][0] for c in variations)
    assert distribution == Counter({specialty: 2 for specialty in SPECIALTIES})
    assert all(c["split"] == "related_development_variation" and not c["independent_unseen"] for c in variations)
    assert all(digest(c["question"].encode()) == c["question_sha256"] for c in variations)


def test_shape_presence_never_becomes_a_clinical_completeness_score():
    signals = task_shape_signals({"task_shape": "comparison_table", "turns": [{}]},
                                 {"coverage_status": "complete", "comparison": {"axes": [{"facet": "histology", "cells": [{"topic_id": "a", "claim_indices": []}, {"topic_id": "b", "claim_indices": []}]}], "rows": []}}, 1)
    assert signals["structured_comparison_present"] is True
    assert signals["comparison_cells_require_human_review"] is True
    assert signals["clinical_accuracy"] is None
    assert signals["clinical_completeness"] is None


def test_axis_cell_table_is_recognized_with_no_legacy_rows_or_evidence():
    response = {"comparison": {"entities": ["a", "b"], "rows": [], "axes": [
        {"facet": "definition", "cells": [{"topic_id": "a", "claim_indices": []}, {"topic_id": "b", "claim_indices": []}]},
    ]}}
    signals = task_shape_signals({"task_shape": "comparison", "turns": [{}]}, response, 1)
    assert signals["structured_comparison_present"] is True
    assert signals["clinical_completeness"] is None
    response["comparison"]["axes"] = []
    assert task_shape_signals({"task_shape": "comparison", "turns": [{}]}, response, 1)["structured_comparison_present"] is False


def test_attachment_context_and_original_message_are_separately_retained():
    cases = {c["case_id"]: c for c in read_rows(DEFAULT_BANK / "supplied.jsonl")}
    case = cases["oral-21"]
    assert not case["question"].startswith("fictional")
    assert case["educational_context_origin"] == "attachment_level_4_introduction"
    assert "fictional postgraduate educational cases" in case["context_instruction"]
    source_lines = (DEFAULT_BANK / "inputs/oral-pathology.txt").read_text(encoding="utf-8-sig").splitlines()
    assert case["origin"]["source_line"] == source_lines[case["origin"]["line_number"] - 1]
    assert Path(DEFAULT_BANK / "inputs/oral-pathology.txt").is_file()


def prepared_fixture():
    """Synthetic provenance-only text; never inserted in a production source pack."""
    from backend.app.services.retrieval import Reference

    row = Reference(source_id="synthetic", title="Synthetic evaluator test", publisher="Test fixture",
                    jurisdiction="Global", section="Test section", source_date="2026-10-01",
                    retrieved_date="2026-10-12", snapshot_id="synthetic-v1", source_type="teaching",
                    url="https://opentextbc.ca/synthetic/", text="Synthetic original complete evidence with an explicit limitation.",
                    topics=["test topic"], keywords=["synthetic"], clinical_review=False,
                    permission_basis={"type": "open_license", "approved_host": "opentextbc.ca",
                                      "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                                      "snapshot_sha256": "a" * 64, "clinical_review": False})
    row.chunk_id = row.stable_id()
    binding = {"topic_id": "local:test_topic", "facet": "structure", "scope": ""}
    text = "Synthetic bounded explanation retains its explicit limitation."
    unit = {"id": "synthetic-unit", "text": text, "prepared_text_sha256": digest(text.encode()),
            "citation_ids": [row.chunk_id], "source_hashes": {row.chunk_id: row.content_hash()},
            "review_status": "developer_reviewed", "reviewer": "Synthetic provenance test",
            "clinical_review": False, "qualifications": ["explicit limitation"], "facet_bindings": [binding]}
    pointer = {"claim_index": 0, "prepared_id": unit["id"], **binding,
               "prepared_text_sha256": unit["prepared_text_sha256"], "source_hashes": unit["source_hashes"]}
    response = {"claims": [{"text": text, "citation_ids": [row.chunk_id]}], "citations": [row.citation()],
                "prepared_claim_evidence": [pointer]}
    case = {"expected_facets": [{"topic_id": binding["topic_id"], "facet": binding["facet"]}]}
    return case, response, {row.chunk_id: row.model_dump()}, [unit], {}, {}


def test_prepared_claim_resolves_only_against_actual_trusted_unit_identity():
    score = prepared_identity_signals(*prepared_fixture())
    assert score["valid_claim_indices"] == [0]
    assert score["requested_prepared_facet_signal"] == {"numerator": 1, "denominator": 1}
    assert score["semantic_support"] is None and score["clinical_accuracy"] is None


@pytest.mark.parametrize("forgery", ["claim_text", "parent_hash", "pointer_scope", "citation_section", "duplicate_citation", "output_only_unit"])
def test_prepared_provenance_forgery_cannot_count_as_explanation_availability(forgery):
    case, response, records, units, metadata, flags = deepcopy(prepared_fixture())
    if forgery == "claim_text":
        response["claims"][0]["text"] += " Invented detail."
    elif forgery == "parent_hash":
        # Forging both output and trusted-looking unit cannot bind a stale parent.
        key = units[0]["citation_ids"][0]
        units[0]["source_hashes"][key] = "0" * 64
        response["prepared_claim_evidence"][0]["source_hashes"][key] = "0" * 64
    elif forgery == "pointer_scope":
        response["prepared_claim_evidence"][0]["scope"] = "in children"
    elif forgery == "citation_section":
        response["citations"][0]["section"] = "Forged section"
    elif forgery == "duplicate_citation":
        response["citations"].append(deepcopy(response["citations"][0]))
    else:
        units = []
    score = prepared_identity_signals(case, response, records, units, metadata, flags)
    assert score["valid_claim_indices"] == []
    assert score["requested_prepared_facet_signal"]["numerator"] == 0
    assert score["clinical_completeness"] is None


def test_source_hold_requires_exact_unit_exception_and_displayed_notice():
    case, response, records, units, metadata, flags = prepared_fixture()
    key = units[0]["citation_ids"][0]
    flag = {"runtime_policy": "explanation_only", "content_sha256": units[0]["source_hashes"][key],
            "clinical_review": False, "reason": "Synthetic source wording hold", "allowed_explanation_ids": []}
    flags[key] = flag
    response["citations"][0]["source_review_notice"] = flag["reason"]
    assert prepared_identity_signals(case, response, records, units, metadata, flags)["valid_claim_indices"] == []
    flag["allowed_explanation_ids"] = [units[0]["id"]]
    assert prepared_identity_signals(case, response, records, units, metadata, flags)["valid_claim_indices"] == [0]
