"""Choose X-ray gate thresholds on the calibration split; report on the test split.

    python evaluation/xray/calibrate_gates.py --measurements D:/aster-eval/xray/measurements.jsonl --write

Groups: in-scope = adult frontal chest radiographs (Montgomery adults, Shenzhen adults,
NIH demo). Out-of-scope = Commons lateral chest, dental panoramic, hand, skull, head CT,
brain MRI, photos. Shenzhen children are out of scope by age; image gates are not
expected to catch them (the adult attestation does), and that limit is reported.
Commons "X-rays of the chest" are mixed views without view labels and are reported only.
"""
import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
IN_SCOPE = {"montgomery_adult", "shenzhen_adult", "nih_demo"}
OUT_SCOPE = {"chest_lateral", "dental_panoramic", "hand_xray", "skull_xray", "head_ct", "brain_mri", "photo"}


def accepted(item, t):
    g, q = item["gates"], item["quality"]
    return (min(q["width"], q["height"]) >= t["min_side"] and t["aspect_min"] <= q["aspect_ratio"] <= t["aspect_max"]
            and q["dynamic_range"] >= t["min_dynamic_range"] and q["saturation_fraction"] <= t["max_saturation"]
            and g["colourfulness"] <= t["max_colourfulness"] and g["ae_error"] <= t["max_ae_error"]
            and g["frontal_probability"] >= t["min_frontal_probability"])


def rates(items, t):
    out = {}
    for group in sorted({i["group"] for i in items}):
        members = [i for i in items if i["group"] == group]
        out[group] = {"n": len(members), "accepted": sum(accepted(i, t) for i in members)}
        out[group]["accept_rate"] = round(out[group]["accepted"] / len(members), 3)
    inside = [i for i in items if i["group"] in IN_SCOPE]
    outside = [i for i in items if i["group"] in OUT_SCOPE]
    summary = {"in_scope_accept_rate": round(np.mean([accepted(i, t) for i in inside]), 3) if inside else None,
               "out_of_scope_reject_rate": round(1 - np.mean([accepted(i, t) for i in outside]), 3) if outside else None,
               "in_scope_n": len(inside), "out_of_scope_n": len(outside)}
    return summary, out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurements", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    items = [json.loads(line) for line in Path(args.measurements).read_text(encoding="utf-8").splitlines() if line.strip()]
    items = [i for i in items if "gates" in i]
    config_path = ROOT / "configs/xray_gates.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    base = dict(config["thresholds"])
    calibration = [i for i in items if i["split"] == "calibration"]
    test = [i for i in items if i["split"] == "test"]
    inside = [i for i in calibration if i["group"] in IN_SCOPE]
    # Fix quality thresholds, then pick AE and view thresholds that keep >= 97% of in-scope calibration images.
    ae_values = sorted(i["gates"]["ae_error"] for i in inside)
    best = None
    for ae in np.quantile(ae_values, [0.95, 0.97, 0.98, 0.99, 1.0]) * np.array([1.0, 1.0, 1.0, 1.05, 1.1]):
        for view in (0.3, 0.5, 0.7, 0.8, 0.9):
            t = {**base, "max_ae_error": float(round(ae, 5)), "min_frontal_probability": view}
            summary, _ = rates(calibration, t)
            if summary["in_scope_accept_rate"] is None or summary["in_scope_accept_rate"] < 0.97:
                continue
            key = (summary["out_of_scope_reject_rate"], summary["in_scope_accept_rate"])
            if best is None or key > best[0]:
                best = (key, t)
    chosen = best[1] if best else base
    cal_summary, cal_groups = rates(calibration, chosen)
    test_summary, test_groups = rates(test, chosen)
    children = [i for i in test + calibration if i["group"] == "shenzhen_child"]
    result = {
        "thresholds": chosen, "calibration": {"summary": cal_summary, "groups": cal_groups},
        "test": {"summary": test_summary, "groups": test_groups},
        "pediatric_image_gate_accept_rate": round(np.mean([accepted(i, chosen) for i in children]), 3) if children else None,
        "pediatric_note": "Children's chest X-rays are generally accepted by image gates; pediatric exclusion relies on the "
                          "required adult attestation. No age model is shipped.",
        "data": "Montgomery and Shenzhen (NLM; local evaluation only, not redistributed), Wikimedia Commons (licence per file), "
                "NIH ChestX-ray14 demo image (CC0). Random 50/50 file-level split (seed 1014); one image per patient in NLM sets.",
    }
    print(json.dumps(result, indent=2))
    out = ROOT / "evaluation/xray/gate-calibration.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.write:
        config["thresholds"] = chosen
        config["calibration"] = {"status": "calibrated_on_public_data", "date": "2026-10-15",
                                 "report": "evaluation/xray/gate-calibration.json",
                                 "test_in_scope_accept_rate": test_summary["in_scope_accept_rate"],
                                 "test_out_of_scope_reject_rate": test_summary["out_of_scope_reject_rate"]}
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
