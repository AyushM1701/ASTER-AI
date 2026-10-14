import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.adapters.ocr import OCRAdapter  # noqa: E402
from backend.app.config import Settings  # noqa: E402
from backend.app.services.documents import parse_fields  # noqa: E402
from backend.app.services.retrieval import ReferenceStore  # noqa: E402
from backend.app.services.uploads import decode_image  # noqa: E402
from scripts.manifest import run_manifest  # noqa: E402


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, first in enumerate(a, 1):
        current = [i]
        for j, second in enumerate(b, 1):
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (first != second))
            )
        previous = current
    return previous[-1]


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate actual transcription against synthetic ground truth."
    )
    parser.add_argument(
        "--image", type=Path, default=ROOT / "data/samples/synthetic_prescription.png"
    )
    parser.add_argument(
        "--truth", type=Path, default=ROOT / "data/samples/synthetic_ground_truth.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings()
    adapter = OCRAdapter(settings)
    image, _ = decode_image(args.image.read_bytes(), settings)
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    start = time.perf_counter()
    ocr = adapter.extract(image)
    latency = time.perf_counter() - start

    def normalize(text):
        return " ".join(text.split())

    actual, expected = normalize(ocr["raw_text"]), normalize(truth["raw_text"])
    fields = {f["kind"]: f["candidate_value"] for f in parse_fields(ocr["raw_text"])}
    summary = {
        "cases": 1,
        "character_error_rate": edit_distance(expected, actual) / max(len(expected), 1),
        "word_error_rate": edit_distance(expected.split(), actual.split())
        / max(len(expected.split()), 1),
        "critical_field_exact_match": {
            key: fields.get(key) == value for key, value in truth["fields"].items()
        },
        "latency_seconds": latency,
        "hallucinated_missing_duration": fields.get("duration") is not None,
        "limitations": "One clear printed synthetic sample. No handwriting reliability or population accuracy claim.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.output / "run_manifest.json").write_text(
        json.dumps(run_manifest(settings, ReferenceStore(settings)), indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
