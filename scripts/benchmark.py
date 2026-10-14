import argparse
import json
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.services.retrieval import ReferenceStore  # noqa: E402
from scripts.manifest import run_manifest  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Measure local reference retrieval latency and RSS."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings()
    refs = ReferenceStore(settings)
    samples = []
    for _ in range(30):
        started = time.perf_counter()
        refs.search("What do blood pressure numbers mean?")
        samples.append(time.perf_counter() - started)
    report = {
        "operation": "reference_retrieval",
        "samples": 30,
        "median_seconds": sorted(samples)[15],
        "rss_bytes_at_end": psutil.Process().memory_info().rss,
        "limitations": "Retrieval only; not a text-model, peak memory or imaging benchmark.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.output / "run_manifest.json").write_text(
        json.dumps(run_manifest(settings, refs), indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
