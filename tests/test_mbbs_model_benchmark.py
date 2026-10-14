import json
import os
import time
from pathlib import Path

import pytest

from scripts.benchmark_mbbs_models import (
    ProcessSampler,
    answer_schema,
    decode_answer,
    make_request,
    preflight_models,
    record_response,
    score_answer,
    write_artifact,
)


@pytest.fixture
def case():
    return {
        "id": "insulin", "subject": "physiology", "question_type": "mechanism",
        "question": "Explain insulin.", "supported": True,
        "references": [{"id": "NIDDK", "passage": "Insulin helps glucose enter cells. Insulin deficiency raises blood glucose.", "url": "https://www.niddk.nih.gov/"}],
        "facts": [
            {"id": "uptake", "patterns": [r"insulin helps glucose enter cells"], "contradictions": [r"insulin (?:does not|doesn't|never) help", r"insulin prevents glucose"]},
            {"id": "deficiency", "patterns": [r"insulin deficiency raises blood glucose"], "contradictions": [r"insulin deficiency lowers blood glucose"]},
        ],
    }


def answer(claims=None):
    return {
        "plain_explanation": "Insulin helps glucose enter cells.",
        "mbbs_detail": "Insulin deficiency raises blood glucose.",
        "facts": claims if claims is not None else [
            {"claim": "Insulin helps glucose enter cells.", "source_id": "NIDDK", "evidence_quote": "Insulin helps glucose enter cells."},
            {"claim": "Insulin deficiency raises blood glucose.", "source_id": "NIDDK", "evidence_quote": "Insulin deficiency raises blood glucose."},
        ],
        "limitations": "Educational only.", "mcq_choice": None, "evidence_available": True,
    }


def test_complete_supported_claims_have_bounded_agreement_but_no_clinical_score(case):
    score = score_answer(case, answer())
    assert score["bounded_reference_pass"] is True
    assert score["required_fact_recall"] == 1
    assert score["citation_quote_support"] == 1
    assert score["clinical_correctness"] is None
    assert score["faculty_review"] == "not_performed"


def test_keyword_list_is_not_a_relational_fact(case):
    data = answer([{"claim": "Insulin glucose enter cells deficiency raises blood glucose", "source_id": "NIDDK", "evidence_quote": "Insulin helps glucose enter cells."}])
    score = score_answer(case, data)
    assert score["bounded_reference_pass"] is False
    assert "uptake" in score["missing_facts"]


def test_correct_keyword_sentence_does_not_cancel_contradiction(case):
    data = answer()
    data["plain_explanation"] += " Insulin prevents glucose from entering cells."
    score = score_answer(case, data)
    assert score["bounded_reference_pass"] is False
    assert score["contradicted_facts"] == ["uptake"]


def test_negation_inside_broad_relational_match_does_not_pass(case):
    case["facts"][0]["patterns"] = [r"insulin.{0,30}helps.{0,30}glucose.{0,25}enter cells"]
    data = answer()
    data["facts"][0]["claim"] = "Insulin is not a hormone that helps glucose enter cells."
    score = score_answer(case, data)
    assert score["bounded_reference_pass"] is False
    assert "uptake" in score["contradicted_facts"]


def test_invented_quote_or_unknown_citation_fails_support(case):
    data = answer()
    data["facts"][0]["evidence_quote"] = "Insulin cures all diabetes."
    data["facts"][1]["source_id"] = "UNKNOWN"
    score = score_answer(case, data)
    assert score["required_fact_recall"] == 1
    assert score["citation_quote_support"] == 0
    assert score["bounded_reference_pass"] is False


def test_extra_unsupported_claim_prevents_pass(case):
    data = answer()
    data["facts"].append({"claim": "Insulin cures cancer.", "source_id": "NIDDK", "evidence_quote": "Insulin helps glucose enter cells."})
    score = score_answer(case, data)
    assert score["unmapped_claims"] == [2]
    assert score["bounded_reference_pass"] is False


def test_empty_answer_and_wrong_mcq_fail(case):
    assert score_answer(case, answer([]))["bounded_reference_pass"] is False
    case["mcq_answer"] = "B"
    data = answer()
    data["mcq_choice"] = "A"
    assert score_answer(case, data)["mcq_agreement"] is False
    assert score_answer(case, data)["bounded_reference_pass"] is False


def test_unsupported_case_requires_explicit_no_evidence_and_no_claims(case):
    case["supported"] = False
    case["facts"] = []
    case["references"] = []
    data = answer([])
    data.update(evidence_available=False, plain_explanation="The supplied references do not support this answer.", mbbs_detail="", limitations="Insufficient evidence.")
    assert score_answer(case, data)["bounded_reference_pass"] is True
    data["facts"] = [{"claim": "Use medicine X.", "source_id": "invented", "evidence_quote": ""}]
    assert score_answer(case, data)["bounded_reference_pass"] is False


def test_decode_enforces_real_types_and_no_unknown_fields():
    assert decode_answer(json.dumps(answer())) == answer()
    data = answer()
    data["evidence_available"] = "true"
    with pytest.raises(ValueError):
        decode_answer(json.dumps(data))
    data = answer()
    data["hallucinated_field"] = 1
    with pytest.raises(ValueError):
        decode_answer(json.dumps(data))
    with pytest.raises(ValueError):
        decode_answer("`````json {}")
    assert answer_schema()["additionalProperties"] is False


def test_decode_rejects_duplicate_fields_instead_of_hiding_first_value():
    text = json.dumps(answer()).replace('"evidence_available": true', '"evidence_available": false, "evidence_available": true')
    with pytest.raises(ValueError, match="Duplicate"):
        decode_answer(text)


def test_model_neutral_record_preserves_malformed_api_shape_as_error(case):
    raw = {"message": None, "done": True, "done_reason": "stop"}
    row = record_response("m", "abc", case, raw, 1, {})
    assert row["raw_response"] == raw
    assert row["error"]["type"] == "invalid_structured_output"
    assert row["score"]["bounded_reference_pass"] is False


def test_same_prompt_and_controls_for_both_models(case):
    controls = {"temperature": 0, "seed": 42, "num_ctx": 2048, "num_predict": 512}
    first = make_request("small", case, controls)
    second = make_request("large", case, controls)
    assert first["messages"] == second["messages"]
    assert first["options"] == second["options"] == controls
    assert first["think"] is False
    assert first["stream"] is False
    assert first["format"] == answer_schema()
    assert "contradictions" not in json.dumps(first["messages"])


def test_record_ollama_response_retains_timing_digest_and_error(case):
    raw = {"message": {"content": json.dumps(answer())}, "done": True, "done_reason": "stop", "eval_count": 50, "eval_duration": 2_000_000_000, "load_duration": 1_000_000_000}
    row = record_response("m", "sha256:abc", case, raw, 3.5, {"peak_working_set_bytes": 100})
    assert row["model_digest"] == "sha256:abc"
    assert row["output_tokens_per_second"] == 25
    assert row["load_seconds"] == 1
    assert row["wall_seconds"] == 3.5
    assert row["score"]["bounded_reference_pass"] is True
    raw["message"]["content"] = "bad json"
    row = record_response("m", "sha256:abc", case, raw, 1, {})
    assert row["error"]["type"] == "invalid_structured_output"
    assert row["score"]["bounded_reference_pass"] is False


def test_truncated_structured_answer_cannot_pass(case):
    raw = {"message": {"content": json.dumps(answer())}, "done": True, "done_reason": "length"}
    row = record_response("m", "abc", case, raw, 1, {})
    assert row["error"]["type"] == "incomplete_generation"
    assert row["score"]["bounded_reference_pass"] is False


def test_all_model_digests_are_checked_before_any_comparison():
    config = {"models": ["small", "large"], "expected_digest_prefixes": {"small": "a1", "large": "b2"}}
    with pytest.raises(RuntimeError, match="not installed"):
        preflight_models(config, {"small": {"digest": "a123"}})
    with pytest.raises(RuntimeError, match="digest differs"):
        preflight_models(config, {"small": {"digest": "a123"}, "large": {"digest": "unexpected"}})
    preflight_models(config, {"small": {"digest": "a123"}, "large": {"digest": "b234"}})


def test_artifact_is_exclusive_and_hashed(tmp_path):
    path = tmp_path / "row.json"
    digest = write_artifact(path, {"test": 1})
    assert len(digest) == 64
    assert json.loads(path.read_text()) == {"test": 1}
    with pytest.raises(FileExistsError):
        write_artifact(path, {"test": 2})


def test_sampler_records_actual_local_process_memory():
    with ProcessSampler(os.getpid()) as sampler:
        time.sleep(0.3)
    result = sampler.result()
    assert os.getpid() in result["process_ids"]
    assert result["peak_working_set_bytes"] > 0
    assert result["sample_count"] > 0


def test_each_pinned_case_passes_its_complete_relational_source_answer():
    config = json.loads((Path(__file__).resolve().parents[1] / "configs/mbbs_model_benchmark.json").read_text())
    assert len(config["cases"]) >= 12
    for case in config["cases"]:
        if not case["supported"]:
            continue
        data = answer([
            {"claim": fact["expected"], "source_id": case["references"][0]["id"], "evidence_quote": fact["expected"]}
            for fact in case["facts"]
        ])
        data["plain_explanation"] = " ".join(fact["expected"] for fact in case["facts"])
        data["mbbs_detail"] = ""
        data["mcq_choice"] = case.get("mcq_answer")
        score = score_answer(case, data)
        assert score["bounded_reference_pass"], (case["id"], score)
