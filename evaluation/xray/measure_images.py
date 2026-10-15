"""Measure gate signals and classifier scores for local evaluation images.

    python evaluation/xray/measure_images.py --root D:/aster-eval/xray --out D:/aster-eval/xray/measurements.jsonl
"""
import argparse
import json
import random
from pathlib import Path

from PIL import Image

from backend.app.adapters.xray_onnx import OnnxXray, preprocess
from backend.app.services.uploads import quality_measurements

ROOT = Path(__file__).resolve().parents[2]


def load(path, max_side=2048):
    image = Image.open(path)
    if image.mode in {"I;16", "I", "I;16B"}:
        import numpy as np
        array = np.asarray(image, dtype=np.float32)
        lo, hi = np.percentile(array, 0.5), np.percentile(array, 99.5)
        image = Image.fromarray(np.clip((array - lo) / max(hi - lo, 1) * 255, 0, 255).astype("uint8"))
    image = image.convert("RGB")
    image.thumbnail((max_side, max_side))
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    model = OnnxXray(ROOT / "configs/xray_gates.json", ROOT / "data/models/xray")
    items = []
    for entry in json.loads((root / "nlm_manifest.json").read_text(encoding="utf-8")):
        adult = entry["age_years"] is None or entry["age_years"] >= 18
        items.append({**entry, "group": f"{entry['dataset']}_{'adult' if adult else 'child'}", "expected": "accept" if adult else "reject_age"})
    for entry in json.loads((root / "commons" / "manifest.json").read_text(encoding="utf-8")):
        items.append({**entry, "file": "commons/" + entry["file"], "dataset": "commons"})
    for name in ("00000001_000.png", "00000002_000.png"):
        items.append({"file": str(ROOT / "data/xray/nih-v3" / name), "dataset": "nih_demo", "group": "nih_demo", "expected": "accept"})
    rng = random.Random(1014)
    done = set()
    out = Path(args.out)
    if out.exists():
        done = {json.loads(line)["file"] for line in out.read_text(encoding="utf-8").splitlines() if line.strip()}
    with out.open("a", encoding="utf-8") as handle:
        for item in items:
            item["split"] = "calibration" if rng.random() < 0.5 else "test"
            if item["file"] in done:
                continue
            path = Path(item["file"]) if Path(item["file"]).is_absolute() else root / item["file"]
            if not path.exists():
                continue
            try:
                image = load(path)
            except Exception as exc:
                item["error"] = str(exc)
                handle.write(json.dumps(item) + "\n")
                continue
            quality = quality_measurements(image)
            item["quality"] = {k: v for k, v in quality.items() if k != "semantics"}
            tensor = preprocess(image)
            item["gates"] = model.measure(image, tensor)
            item["scores"] = model.all_scores(image, tensor)
            handle.write(json.dumps(item) + "\n")
            handle.flush()
            print(item["group"], item["file"][-40:], round(item["gates"]["ae_error"], 4), round(item["gates"]["frontal_probability"], 3), flush=True)


if __name__ == "__main__":
    main()
