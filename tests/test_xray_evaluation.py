"""Catch misleading scores, image-level bootstrap and unaudited test promotion."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import evaluate_xray as evaluation


def finding_rows():
    return [
        {"asset_id": str(i), "patient_group": group, "labels": {"Effusion": target},
         "findings": [{"name": "Effusion", "score": score}]}
        for i, (group, target, score) in enumerate([
            ("a", 1, .9), ("b", 1, .4), ("c", 0, .7), ("d", 0, .1),
        ])
    ]


def test_metrics_have_hand_derived_confusion_and_auc():
    report = evaluation.evaluate_findings(finding_rows(), {"Effusion": .5}, repetitions=30)
    result = report["Effusion"]
    assert result["auroc"] == .75
    assert result["auprc"] == pytest.approx(5 / 6)
    assert result["threshold_metrics"] == {
        "threshold": .5, "tp": 1, "fn": 1, "fp": 1, "tn": 1,
        "sensitivity": .5, "specificity": .5, "precision": .5,
    }
    assert result["calibrated_probability"] is None
    assert result["confidence_intervals"]["auroc"]["interval"] is None
    assert "patients" in result["confidence_intervals"]["auroc"]["reason"]


def test_unknown_labels_excluded_and_single_class_not_perfect_accuracy():
    rows = finding_rows()
    rows[0]["labels"]["Effusion"] = -1
    rows[1]["labels"]["Effusion"] = None
    result = evaluation.evaluate_findings(rows, {"Effusion": .5}, repetitions=20)["Effusion"]
    assert result["count"] == 2
    assert result["unknown_count"] == 2
    assert result["auroc"] is None
    assert result["auprc"] is None
    assert result["threshold_metrics"]["sensitivity"] is None


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -.1, 1.1])
def test_invalid_scores_never_produce_statistics(score):
    rows = finding_rows()
    rows[0]["findings"][0]["score"] = score
    with pytest.raises(ValueError, match="score"):
        evaluation.evaluate_findings(rows, {"Effusion": .5})


def test_missing_finding_not_silently_dropped():
    rows = finding_rows()
    rows[0]["findings"] = []
    with pytest.raises(ValueError, match="finding"):
        evaluation.evaluate_findings(rows, {"Effusion": .5})


def test_bootstrap_resamples_whole_patients_with_multiplicity():
    samples = list(evaluation.patient_bootstrap_indices(["a", "a", "b"], 100, 17))
    for sample in samples:
        assert list(sample).count(0) == list(sample).count(1)
        assert list(sample).count(0) + list(sample).count(2) == 2
    assert any(list(sample).count(0) == 2 for sample in samples)
    assert any(list(sample).count(2) == 2 for sample in samples)


def test_bootstrap_intervals_reproducible_for_adequate_patient_count():
    rows = finding_rows() * 10
    rows = [{**row, "patient_group": f"patient-{i}"} for i, row in enumerate(rows)]
    first = evaluation.evaluate_findings(rows, {"Effusion": .5}, repetitions=100, seed=17)
    second = evaluation.evaluate_findings(rows, {"Effusion": .5}, repetitions=100, seed=17)
    assert first == second
    interval = first["Effusion"]["confidence_intervals"]["auroc"]["interval"]
    assert interval[0] <= .75 <= interval[1]


def protocol_fixture(tmp_path):
    raw = b"assets: []\n"
    protocol = {
        "model_id": "densenet121-res224-all", "weight_sha256": "a" * 64,
        "dataset_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "thresholds": {"Cardiomegaly": .5, "Effusion": .5, "Lung Opacity": .5},
        "threshold_basis": "Upstream normalized operating point, fixed before test",
        "training_overlap": {"status": "excluded", "reviewer": "test reviewer",
                             "rationale": "independent fixture", "evidence": ["https://example.org/audit"]},
    }
    assets = [{"asset_id": "one", "sha256": "b" * 64, "patient_group": "p1", "partition": "test", "labels": {"Effusion": 1}}]
    return raw, protocol, assets


def test_protocol_requires_overlap_review_and_bound_inputs(tmp_path):
    raw, protocol, assets = protocol_fixture(tmp_path)
    evaluation.validate_protocol(protocol, assets, raw, "a" * 64)
    protocol["training_overlap"]["status"] = "unresolved"
    with pytest.raises(ValueError, match="overlap"):
        evaluation.validate_protocol(protocol, assets, raw, "a" * 64)
    protocol["training_overlap"]["status"] = "excluded"
    with pytest.raises(ValueError, match="manifest"):
        evaluation.validate_protocol(protocol, assets, raw + b"changed", "a" * 64)
    with pytest.raises(ValueError, match="weight"):
        evaluation.validate_protocol(protocol, assets, raw, "c" * 64)


def test_protocol_rejects_demo_promotion_duplicate_images_and_patient_leakage(tmp_path):
    raw, protocol, assets = protocol_fixture(tmp_path)
    assets[0]["partition"] = "demo"
    with pytest.raises(ValueError, match="test"):
        evaluation.validate_protocol(protocol, assets, raw, "a" * 64)
    assets[0]["partition"] = "test"
    assets.append({**assets[0], "asset_id": "two"})
    with pytest.raises(ValueError, match="Duplicate image"):
        evaluation.validate_protocol(protocol, assets, raw, "a" * 64)
    assets[1]["sha256"] = "c" * 64
    assets[1]["partition"] = "development"
    with pytest.raises(ValueError, match="patient|Patient"):
        evaluation.validate_protocol(protocol, assets, raw, "a" * 64)


def test_test_thresholds_must_not_be_tuned_or_nonfinite(tmp_path):
    raw, protocol, assets = protocol_fixture(tmp_path)
    protocol["thresholds"]["Effusion"] = float("nan")
    with pytest.raises(ValueError, match="threshold"):
        evaluation.validate_protocol(protocol, assets, raw, "a" * 64)


def test_failure_examples_use_predeclared_threshold():
    failures = evaluation.failure_examples(finding_rows(), {"Effusion": .5})
    assert {item["asset_id"]: item["kind"] for item in failures} == {"1": "false_negative", "2": "false_positive"}


def test_score_reliability_bins_cover_each_boundary_exactly_once():
    rows = [{"patient_group": str(i), "labels": {"Effusion": i % 2},
             "findings": [{"name": "Effusion", "score": i / 10}]} for i in range(11)]
    bins = evaluation.evaluate_findings(rows, {"Effusion": .5}, repetitions=20)["Effusion"]["research_score_reliability_bins"]
    assert [item["count"] for item in bins] == [1] * 9 + [2]


def test_empty_independent_cohort_cannot_claim_evaluation(tmp_path):
    raw, protocol, _ = protocol_fixture(tmp_path)
    with pytest.raises(ValueError, match="No evaluation assets"):
        evaluation.validate_protocol(protocol, [], raw, "a" * 64)


def test_protocol_rejects_invalid_ground_truth(tmp_path):
    raw, protocol, assets = protocol_fixture(tmp_path)
    assets[0]["labels"]["Effusion"] = "1"
    with pytest.raises(ValueError, match="label"):
        evaluation.validate_protocol(protocol, assets, raw, "a" * 64)


def test_demo_protocol_missing_overlap_status_rejected_before_inference(tmp_path):
    raw, protocol, assets = protocol_fixture(tmp_path)
    assets[0]["partition"] = "demo"
    del protocol["training_overlap"]
    with pytest.raises(ValueError, match="overlap"):
        evaluation.validate_protocol(protocol, assets, raw, "a" * 64, integration_only=True)


def run_cli(tmp_path, *, invalid_asset=False):
    weights = json.loads((evaluation.ROOT / "configs/xray_weights.json").read_text(encoding="utf-8"))
    dataset = tmp_path / "dataset.yaml"
    import yaml

    asset = {"asset_id": "missing", "sha256": "b" * 64, "patient_group": "p1", "partition": "demo",
             "path": str(tmp_path / "missing.png"), "source": "fixture", "license": "fixture", "view": "PA",
             "adult": True, "supported_input_review": True, "deidentified": True}
    dataset.write_text(yaml.safe_dump({"assets": [asset] if invalid_asset else []}), encoding="utf-8")
    raw, protocol, _ = protocol_fixture(tmp_path)
    protocol["weight_sha256"] = weights["sha256"]
    protocol["dataset_manifest_sha256"] = hashlib.sha256(dataset.read_bytes()).hexdigest()
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol) if invalid_asset else "{bad", encoding="utf-8")
    output = tmp_path / "output"
    completed = subprocess.run([sys.executable, str(Path(evaluation.__file__)), "--dataset", str(dataset),
                                "--protocol", str(protocol_path), "--output", str(output), "--integration-only", "--validate-only"],
                               cwd=evaluation.ROOT, capture_output=True, text=True, timeout=20)
    return completed, output


@pytest.mark.parametrize("invalid_asset", [False, True])
def test_cli_failed_input_and_missing_image_write_not_ready(tmp_path, invalid_asset):
    completed, output = run_cli(tmp_path, invalid_asset=invalid_asset)
    assert completed.returncode != 0
    assert "Traceback" not in completed.stderr
    assert json.loads((output / "preflight.json").read_text())["status"] == "not_ready"
    assert not (output / "summary.json").exists()


def test_cli_refuses_to_reuse_success_output_directory(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    prior = output / "summary.json"
    prior.write_text('{"status":"prior_success"}', encoding="utf-8")
    completed, _ = run_cli(tmp_path)
    assert completed.returncode != 0
    assert "new output directory" in completed.stderr.casefold()
    assert prior.read_text() == '{"status":"prior_success"}'
