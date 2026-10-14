import argparse
import hashlib
import importlib.metadata
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.adapters.xray_model import XrayAdapter  # noqa: E402
from backend.app.config import Settings  # noqa: E402
from backend.app.errors import AppError  # noqa: E402
from backend.app.services.xray import validate_asset  # noqa: E402

LABELS = ("Cardiomegaly", "Effusion", "Lung Opacity")


def validate_protocol(protocol, assets, dataset_bytes, weight_hash, integration_only=False):
    if protocol.get("model_id") != XrayAdapter.model_id or protocol.get("weight_sha256") != weight_hash:
        raise ValueError("Protocol model/weight binding changed")
    if protocol.get("dataset_manifest_sha256") != hashlib.sha256(dataset_bytes).hexdigest():
        raise ValueError("Protocol dataset manifest binding changed")
    thresholds = protocol.get("thresholds", {})
    if set(thresholds) != set(LABELS) or not protocol.get("threshold_basis"):
        raise ValueError("Every finding needs a predeclared threshold and its basis")
    if any(type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 1 for value in thresholds.values()):
        raise ValueError("Invalid threshold")
    overlap = protocol.get("training_overlap")
    if not isinstance(overlap, dict) or overlap.get("status") not in {"excluded", "unresolved", "integration_only", "known_source_overlap"}:
        raise ValueError("Protocol requires an explicit training overlap status")
    if not integration_only and (overlap.get("status") != "excluded" or not all(overlap.get(key) for key in ("reviewer", "rationale", "evidence"))):
        raise ValueError("Independent evaluation requires a documented training overlap exclusion review")
    if not assets:
        raise ValueError("No evaluation assets; independent performance has not been measured")
    hashes, ids, groups = set(), set(), defaultdict(set)
    for asset in assets:
        if not asset.get("patient_group"):
            raise ValueError("Missing patient grouping")
        groups[asset["patient_group"]].add(asset.get("partition"))
        if asset.get("sha256") in hashes:
            raise ValueError("Duplicate image hash in evaluation manifest")
        if asset.get("asset_id") in ids:
            raise ValueError("Duplicate asset ID")
        hashes.add(asset.get("sha256"))
        ids.add(asset.get("asset_id"))
        for label, value in asset.get("labels", {}).items():
            if label not in LABELS or (value is not None and (type(value) is not int or value not in {-1, 0, 1})):
                raise ValueError("Invalid or unmapped ground-truth label")
    if any(len(partitions) > 1 for partitions in groups.values()):
        raise ValueError("Patient grouping overlaps partitions")
    expected = {"demo"} if integration_only else {"test"}
    if any(asset.get("partition") not in expected for asset in assets):
        raise ValueError("Use test-only assets, or demo-only assets with --integration-only")


def patient_bootstrap_indices(groups, repetitions, seed):
    members = defaultdict(list)
    for index, group in enumerate(groups):
        members[group].append(index)
    keys = sorted(members)
    rng = np.random.default_rng(seed)
    for _ in range(repetitions):
        sampled = rng.integers(0, len(keys), len(keys))
        yield np.array([index for choice in sampled for index in members[keys[choice]]], dtype=int)


def metric_values(targets, scores, threshold):
    from sklearn.metrics import average_precision_score, roc_auc_score

    both = len(set(targets)) == 2
    decisions = scores >= threshold
    positive = targets == 1
    tp = int(np.sum(positive & decisions))
    fn = int(np.sum(positive & ~decisions))
    fp = int(np.sum(~positive & decisions))
    tn = int(np.sum(~positive & ~decisions))
    return {
        "auroc": float(roc_auc_score(targets, scores)) if both else None,
        "auprc": float(average_precision_score(targets, scores)) if both else None,
        "threshold_metrics": {
            "threshold": threshold, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "sensitivity": tp / (tp + fn) if tp + fn else None,
            "specificity": tn / (tn + fp) if tn + fp else None,
            "precision": tp / (tp + fp) if tp + fp else None,
        },
    }


def finding_pairs(rows, label):
    pairs = []
    for row in rows:
        findings = [finding for finding in row["findings"] if finding["name"] == label]
        if len(findings) != 1:
            raise ValueError("Missing or duplicate model finding")
        score = findings[0]["score"]
        if type(score) not in {int, float} or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Invalid model score")
        target = row.get("labels", {}).get(label)
        if target is not None and (type(target) is not int or target not in {-1, 0, 1}):
            raise ValueError("Invalid ground-truth label")
        if target in {0, 1}:
            pairs.append((target, score, row["patient_group"]))
    return pairs


def evaluate_findings(rows, thresholds, repetitions=1000, seed=17):
    if not 20 <= repetitions <= 10000:
        raise ValueError("Use 20 to 10000 bootstrap repetitions")
    results = {}
    for label, threshold in thresholds.items():
        if type(threshold) not in {int, float} or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("Invalid threshold")
        pairs = finding_pairs(rows, label)
        targets = np.array([pair[0] for pair in pairs], dtype=int)
        scores = np.array([pair[1] for pair in pairs])
        groups = [pair[2] for pair in pairs]
        result = metric_values(targets, scores, threshold)
        samples = defaultdict(list)
        names = ("auroc", "auprc", "sensitivity", "specificity", "precision")
        patient_count = len(set(groups))
        if patient_count >= 20:
            for indices in patient_bootstrap_indices(groups, repetitions, seed):
                measured = metric_values(targets[indices], scores[indices], threshold)
                for name in names:
                    value = measured.get(name, measured["threshold_metrics"].get(name))
                    if value is not None:
                        samples[name].append(value)
        intervals = {}
        for name in names:
            point = result.get(name, result["threshold_metrics"].get(name))
            valid = len(samples[name])
            reason = None
            if point is None:
                reason = "Undefined for this cohort/class denominator"
            elif patient_count < 20:
                reason = "Fewer than 20 distinct patients; interval withheld"
            elif valid < math.ceil(.8 * repetitions):
                reason = "Fewer than 80% of patient-bootstrap replicates defined"
            intervals[name] = {
                "interval": np.quantile(samples[name], [.025, .975]).tolist() if reason is None else None,
                "valid_replicates": valid, "reason": reason,
            }
        bins = []
        bin_indices = np.minimum((scores * 10).astype(int), 9)
        for index in range(10):
            mask = bin_indices == index
            bins.append({"lower": index / 10, "upper": (index + 1) / 10, "count": int(mask.sum()),
                         "mean_research_score": float(scores[mask].mean()) if mask.any() else None,
                         "observed_positive_fraction": float(targets[mask].mean()) if mask.any() else None})
        result.update({
            "count": len(pairs), "unknown_count": len(rows) - len(pairs),
            "patient_count": patient_count, "positive_count": int(targets.sum()),
            "negative_count": int(len(targets) - targets.sum()),
            "confidence_intervals": intervals, "bootstrap_unit": "patient",
            "research_score_reliability_bins": bins,
            "calibration": None, "calibrated_probability": None,
            "auprc_method": "average_precision",
        })
        results[label] = result
    return results


def failure_examples(rows, thresholds):
    failures = []
    for label, threshold in thresholds.items():
        finding_pairs(rows, label)  # Validate all scores before collecting examples.
        for row in rows:
            target = row.get("labels", {}).get(label)
            if target not in {0, 1}:
                continue
            score = next(f["score"] for f in row["findings"] if f["name"] == label)
            if int(score >= threshold) != target:
                failures.append({"asset_id": row["asset_id"], "patient_group": row["patient_group"],
                                 "finding": label, "target": target, "score": score, "threshold": threshold,
                                 "kind": "false_positive" if target == 0 else "false_negative"})
    return failures


def main():
    parser = argparse.ArgumentParser(
        description="Offline per-label evaluation of permitted test assets."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--bootstrap-repetitions", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--cpu-threads", type=int, choices=range(1, 9), default=2)
    parser.add_argument("--integration-only", action="store_true", help="Demo inference only; withhold diagnostic metrics")
    parser.add_argument("--validate-only", action="store_true", help="Check protocol before model loading")
    args = parser.parse_args()
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("Output already exists; use a new output directory to preserve prior results")
    try:
        if not 20 <= args.bootstrap_repetitions <= 10000:
            raise ValueError("Use 20 to 10000 bootstrap repetitions")
        settings = Settings(xray_manifest=args.dataset.resolve())
        dataset_bytes = args.dataset.read_bytes()
        assets = yaml.safe_load(dataset_bytes)["assets"]
        protocol_bytes = args.protocol.read_bytes()
        protocol = json.loads(protocol_bytes)
        weight_manifest = json.loads(settings.xray_weights_manifest.read_text(encoding="utf-8"))
        validate_protocol(protocol, assets, dataset_bytes, weight_manifest["sha256"], args.integration_only)
        for asset in assets:
            validate_asset(asset, settings)
        weight_path = Path(weight_manifest["weights_path"])
        if not weight_path.is_absolute():
            weight_path = settings.xray_weights_manifest.parent / weight_path
        if hashlib.sha256(weight_path.read_bytes()).hexdigest() != weight_manifest["sha256"]:
            raise ValueError("Checkpoint hash mismatch")
    except (AppError, OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as error:
        reason = error.message if isinstance(error, AppError) else str(error)
        (args.output / "preflight.json").write_text(json.dumps({"status": "not_ready", "reason": reason, "diagnostic_metrics": None}, indent=2), encoding="utf-8")
        parser.error(reason)
    tracked_files = [args.dataset, args.protocol, settings.xray_weights_manifest, Path(__file__),
                     ROOT / "backend/app/adapters/xray_model.py", ROOT / "backend/app/services/xray.py"]
    tracked_files.extend(path for path in (ROOT / "requirements.lock.txt", ROOT / "requirements-xray.lock.txt", ROOT / "requirements.txt") if path.is_file())
    (args.output / "run_manifest.json").write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "arguments": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "files": [{"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in tracked_files],
        "packages": {name: importlib.metadata.version(name) for name in ("torch", "torchxrayvision", "numpy", "scikit-learn", "Pillow", "PyYAML")},
        "checkpoint_sha256": weight_manifest["sha256"],
    }, indent=2), encoding="utf-8")
    (args.output / "preflight.json").write_text(json.dumps({"status": "ready", "assets": len(assets)}, indent=2), encoding="utf-8")
    if args.validate_only:
        print("Protocol, image and checkpoint preflight passed; no inference/evaluation performed.")
        return
    try:
        run_inference(args, settings, assets, protocol, protocol_bytes, dataset_bytes)
    except (AppError, OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        reason = error.message if isinstance(error, AppError) else str(error)
        (args.output / "summary.json").write_text(json.dumps({"status": "failed", "reason": reason, "metrics": None}, indent=2), encoding="utf-8")
        parser.error(str(error))


def run_inference(args, settings, assets, protocol, protocol_bytes, dataset_bytes):
    import torch

    torch.set_num_threads(args.cpu_threads)
    model = XrayAdapter(settings)
    outputs = []
    for asset in assets:
        image, _, _ = validate_asset(asset, settings)
        started = time.perf_counter()
        findings = model.predict(image)
        outputs.append(
            {
                "asset_id": asset["asset_id"],
                "patient_group": asset["patient_group"],
                "labels": asset.get("labels", {}),
                "findings": findings,
                "inference_seconds": time.perf_counter() - started,
                "weight_sha256": model.weight_hash,
            }
        )
    metrics = None if args.integration_only else evaluate_findings(outputs, protocol["thresholds"], args.bootstrap_repetitions, args.seed)
    (args.output / "predictions.json").write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    (args.output / "summary.json").write_text(
        json.dumps(
            {
                "metrics": metrics,
                "status": "integration_only" if args.integration_only else "research_benchmark",
                "assets": len(outputs), "patients": len({row["patient_group"] for row in outputs}),
                "bootstrap_repetitions": args.bootstrap_repetitions, "seed": args.seed,
                "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
                "dataset_manifest_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
                "weight_sha256": model.weight_hash, "preprocessing_version": model.preprocessing_version,
                "score_semantics": model.score_semantics, "training_overlap": protocol["training_overlap"],
                "limitations": ["Research benchmark, not clinical validation.",
                                "Overlap review is documented evidence, not automatic proof of complete training provenance.",
                                "Thresholds are predeclared research operating points, not clinically validated decisions.",
                                "Reliability bins describe research scores; no probability calibration is fitted.",
                                "20-patient/80%-replicate interval rules are engineering guards, not adequate-study-size guarantees."],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (args.output / "failure_examples.json").write_text(json.dumps([] if args.integration_only else failure_examples(outputs, protocol["thresholds"]), indent=2), encoding="utf-8")
    print(json.dumps({"status": "integration_only" if args.integration_only else "research_benchmark", "metrics": metrics, "assets": len(outputs)}, indent=2))


if __name__ == "__main__":
    main()
