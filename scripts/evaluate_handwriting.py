"""Evaluate local OCR against frozen English word labels and synthetic scan variants."""

import argparse
import csv
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.adapters.ocr import OCRAdapter  # noqa: E402
from backend.app.adapters.ollama import OllamaAdapter  # noqa: E402
from backend.app.config import Settings  # noqa: E402
from backend.app.services.documents import parse_fields  # noqa: E402
from scripts.evaluate_ocr import edit_distance  # noqa: E402


def normalize(text):
    return " ".join(text.split()).casefold()


def score(expected, actual):
    expected, actual = normalize(expected), normalize(actual)
    abstained = not actual or "[unreadable]" in actual or actual == "unreadable"
    return {
        "exact": actual == expected,
        "character_errors": edit_distance(expected, actual),
        "reference_characters": len(expected),
        "word_errors": edit_distance(expected.split(), actual.split()),
        "reference_words": len(expected.split()),
        "abstained": abstained,
        "wrong_non_abstained": bool(expected) and not abstained and actual != expected,
    }


def aggregate(rows, key):
    scored = [r[key] for r in rows]
    chars = sum(r["reference_characters"] for r in scored)
    words = sum(r["reference_words"] for r in scored)
    latencies = [r["latency_seconds"] for r in scored]
    accepted = sum(not r["abstained"] for r in scored)
    correct = sum(r["exact"] for r in scored)
    return {
        "cases": len(rows),
        "exact_matches": correct,
        "exact_match_rate": correct / len(rows),
        "character_error_rate": sum(r["character_errors"] for r in scored) / chars
        if chars
        else None,
        "word_error_rate": sum(r["word_errors"] for r in scored) / words if words else None,
        "abstentions": sum(r["abstained"] for r in scored),
        "wrong_non_abstained": sum(r["wrong_non_abstained"] for r in scored),
        "non_abstained_cases": accepted,
        "correct_among_non_abstained": sum(r["exact"] and not r["abstained"] for r in scored)
        / accepted
        if accepted
        else None,
        "median_latency_seconds": statistics.median(latencies),
        "max_latency_seconds": max(latencies),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings(enable_handwriting_ocr=True)
    vision = OllamaAdapter(settings)
    adapter = OCRAdapter(settings, vision=vision)
    labels_path = ROOT / "data/evaluation/handwriting-bd/testing_labels.csv"
    labels = {
        r["IMAGE"]: r["MEDICINE_NAME"]
        for r in csv.DictReader(labels_path.open(encoding="utf-8-sig"))
    }
    cases = []
    for path in sorted(labels_path.parent.glob("*.png"), key=lambda p: int(p.stem)):
        cases.append(
            (path.stem, "human_word", Image.open(path).convert("RGB"), labels[path.name], path)
        )
    source = Image.open(ROOT / "data/samples/synthetic_prescription.png").convert("RGB")
    truth = json.loads(
        (ROOT / "data/samples/synthetic_ground_truth.json").read_text(encoding="utf-8")
    )
    variants = {
        "clear": source.copy(),
        "rotated_3deg": source.rotate(3, expand=True, fillcolor="white"),
        "half_resolution": source.resize((source.width // 2, source.height // 2)),
        "blur_radius_1": source.filter(ImageFilter.GaussianBlur(1)),
        "low_contrast_0.35": ImageEnhance.Contrast(source).enhance(0.35),
        "severe_blur_6": source.filter(ImageFilter.GaussianBlur(6)),
        "blank_control": Image.new("RGB", source.size, "white"),
    }
    fixtures = args.output / "synthetic-fixtures"
    fixtures.mkdir(exist_ok=True)
    for name, image in variants.items():
        path = fixtures / (name + ".png")
        image.save(path)
        cases.append(
            (
                name,
                "synthetic_scan",
                image,
                "" if name == "blank_control" else truth["raw_text"],
                path,
            )
        )
    rows = []
    try:
        for case_id, cohort, image, expected, path in cases:
            started = time.perf_counter()
            printed = adapter.extract_printed(image)
            printed_seconds = time.perf_counter() - started
            started = time.perf_counter()
            selected = adapter.extract(image)
            seconds = time.perf_counter() - started
            row = {
                "case_id": case_id,
                "cohort": cohort,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "image_size": list(image.size),
                "expected": expected,
                "tesseract": {
                    **score(expected, printed["raw_text"]),
                    "latency_seconds": printed_seconds,
                    "raw_text": printed["raw_text"],
                },
                "hybrid": {
                    **score(expected, selected["raw_text"]),
                    "latency_seconds": seconds,
                    **selected,
                },
            }
            if cohort == "synthetic_scan":
                fields = {
                    f["kind"]: f["candidate_value"]
                    for f in parse_fields(selected["raw_text"], provenance=selected["engine"])
                }
                expected_fields = (
                    {k: None for k in truth["fields"]} if not expected else truth["fields"]
                )
                row["critical_field_exact_match"] = {
                    k: fields.get(k) == v for k, v in expected_fields.items()
                }
                row["candidate_fields"] = fields
            rows.append(row)
            (args.output / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
            print(
                cohort,
                case_id,
                selected["engine"],
                repr(selected["raw_text"][:80]),
                "exact",
                row["hybrid"]["exact"],
                flush=True,
            )
    finally:
        vision.close()
    summary = {
        "model": settings.vision_model,
        "normalization": "case-fold and collapse whitespace; punctuation and spelling retained",
        "handwriting": {
            key: aggregate([r for r in rows if r["cohort"] == "human_word"], key)
            for key in ("tesseract", "hybrid")
        },
        "synthetic_scans": {
            key: aggregate([r for r in rows if r["cohort"] == "synthetic_scan"], key)
            for key in ("tesseract", "hybrid")
        },
        "unique_human_labels": len({r["expected"] for r in rows if r["cohort"] == "human_word"}),
        "limitations": "Small public word-crop development probe, not full prescription or independent clinical validation. Initial 12 consecutive crops plus first example of every third class in label-file order. No labels passed to the model. Synthetic transformations are engineering fixtures, not doctor handwriting. Errors and abstentions are counted, not corrected from vocabulary.",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
