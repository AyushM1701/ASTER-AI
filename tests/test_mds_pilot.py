"""Evaluation integrity checks, not medical accuracy tests."""
import importlib.util
import json
from collections import Counter

import pytest


def pilot():
    spec = importlib.util.find_spec("scripts.mds_pilot")
    assert spec is not None, "The versioned pilot/lock tooling has not been implemented"
    from scripts import mds_pilot
    return mds_pilot


def test_pilot_distribution_and_no_answer_keys():
    rows = pilot().candidate_prompts()
    assert len(rows) == 150
    assert len({r["case_id"] for r in rows}) == 150
    assert sorted(Counter(r["family"] for r in rows).values()) == [15] * 10
    assert len({r["operation"] for r in rows}) >= 5
    assert set(r["difficulty"] for r in rows) == {"basic", "intermediate", "advanced"}
    assert all("reference_answer" not in r for r in rows)
    assert all(r["independent_unseen"] is False for r in rows)


def test_lock_binds_prompts_and_source_bytes_and_cannot_overwrite(tmp_path):
    p = pilot()
    release = tmp_path / "release"
    release.mkdir()
    (release / "records.jsonl").write_text("{}\n")
    (release / "manifest.json").write_text(json.dumps({"version": "fixture", "files": {}}))
    folder = tmp_path / "bank"
    p.lock_bank(folder, release)
    p.verify_bank(folder, release)
    with pytest.raises(FileExistsError):
        p.lock_bank(folder, release)
    (folder / "candidate-prompts.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="prompt"):
        p.verify_bank(folder, release)


def test_source_change_invalidates_snapshot(tmp_path):
    p = pilot()
    release = tmp_path / "release"
    release.mkdir()
    (release / "records.jsonl").write_text("{}\n")
    (release / "manifest.json").write_text('{"version":"fixture", "files":{}}')
    p.lock_bank(tmp_path / "bank", release)
    (release / "records.jsonl").write_text('{"changed":true}\n')
    with pytest.raises(ValueError, match="source"):
        p.verify_bank(tmp_path / "bank", release)


def test_family_and_near_duplicate_leakage_is_explicit():
    p = pilot()
    rows = [{"case_id": "a", "family": "oral", "question": "Define oral epithelium", "split": "development"},
            {"case_id": "b", "family": "oral", "question": "Define oral epithelium!", "split": "holdout"}]
    report = p.audit_overlap(rows, [{"question": "Define oral epithelium."}])
    assert report["family_split_leakage"]
    assert report["cross_split_near_duplicates"]
    assert report["source_derived_example_overlap"]


def test_citation_resolution_rejects_forged_coordinates():
    p = pilot()
    records = {"x": {"chunk_id": "x", "source_id": "source", "section": "A", "text": "Exact evidence."}}
    good = {"claims": [{"text": "Exact evidence.", "citation_ids": ["x"]}],
            "citations": [{"chunk_id": "x", "source_id": "source", "section": "B", "excerpt": "Exact evidence."}]}
    score = p.score_response({"case_id": "test", "question": "Define oral epithelium", "expected_facets": []}, good, records)
    assert score["citation_resolution"] == {"numerator": 0, "denominator": 1}
    assert score["claim_support_flags"]["numerator"] == 1


def test_empty_metrics_are_unknown_not_perfect():
    report = pilot().summarize([])
    assert report["metrics"]["citation_resolution"]["rate"] is None
    assert report["independent_clinical_review"] == "pending_F03"
    assert report["multi_turn_success"]["rate"] is None


def test_published_citation_schema_resolves_without_optional_source_id():
    p = pilot()
    row = {"chunk_id": "x", "source_id": "source", "section": "A", "text": "Exact evidence.", "snapshot_id": "v1"}
    response = {"claims": [{"text": row["text"], "citation_ids": ["x"]}],
                "citations": [{"chunk_id": "x", "section": "A", "excerpt": row["text"], "snapshot_id": "v1"}]}
    score = p.score_response({"case_id": "test", "question": "Define oral epithelium", "expected_facets": []}, response, {"x": row})
    assert score["citation_resolution"] == {"numerator": 1, "denominator": 1}
    assert score["claim_support_flags"] == {"numerator": 0, "denominator": 1}


def test_duplicate_id_does_not_hide_forged_coordinate():
    p = pilot()
    row = {"chunk_id": "x", "source_id": "source", "section": "A", "text": "Exact evidence."}
    response = {"claims": [{"text": row["text"], "citation_ids": ["x"]}],
                "citations": [{"chunk_id": "x", "section": "A", "excerpt": row["text"]},
                              {"chunk_id": "x", "section": "FORGED", "excerpt": row["text"]}]}
    score = p.score_response({"case_id": "test", "question": "test", "expected_facets": []}, response, {"x": row})
    assert score["citation_resolution"] == {"numerator": 1, "denominator": 2}
    assert score["claim_support_flags"]["numerator"] == 1


def test_stale_source_hash_cannot_count_as_facet_coverage():
    p = pilot()
    text = "Exact evidence."
    row = {"chunk_id": "x", "source_id": "source", "section": "A", "text": text, "snapshot_id": "v1"}
    response = {"claims": [{"text": text, "citation_ids": ["x"]}],
                "citations": [{"chunk_id": "x", "section": "A", "excerpt": text}],
                "claim_evidence": [{"claim_index": 0, "topic_id": "oral_epithelium", "facet": "definition",
                                    "span": {"chunk_id": "x", "section": "A", "snapshot_id": "v1", "start": 0,
                                             "end": len(text), "text_sha256": p.digest(text.encode()), "source_sha256": "0" * 64}}]}
    case = {"case_id": "test", "question": "Define oral epithelium", "expected_facets": [{"topic_id": "oral_epithelium", "facet": "definition"}]}
    assert p.score_response(case, response, {"x": row})["facet_coverage"] == {"numerator": 0, "denominator": 1}


def test_real_cpu_api_route_returns_coverage_without_inference(tmp_path):
    from fastapi.testclient import TestClient

    from backend.app.config import Settings
    from backend.app.main import create_app
    with TestClient(create_app(Settings(_env_file=None, enable_teaching=True,
                          enable_mds_pipeline=True, teaching_backend="lexical",
                          enable_general_chat=False, answer_mode="extractive",
                          workspace_path=tmp_path / "eval.sqlite3"))) as client:
        token = client.post("/v1/sessions").json()["token"]
        result = client.post("/v1/chat", headers={"Authorization": "Bearer " + token},
                             json={"question": "Define oral epithelium and its layers", "audience": "study"})
        assert result.status_code == 200
        assert result.json()["coverage_status"] in {"complete", "partial", "insufficient_evidence", "blocked"}
