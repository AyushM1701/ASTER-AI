"""Bind developer-authored evaluation questions to inspected source excerpts."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.services.retrieval import Reference  # noqa: E402
from scripts.evaluate_mbbs import validate_cases  # noqa: E402


def build(release, spec, output):
    records = {row.chunk_id: row for row in (Reference.model_validate_json(line) for line in
               (Path(release) / "records.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
    cases = json.loads(Path(spec).read_text(encoding="utf-8"))["cases"]
    for case in cases:
        keys = case.pop("reference_chunk_ids")
        case["expected_source_ids"] = sorted({records[key].source_id for key in keys})
        case["reference_evidence"] = [{"chunk_id": key, "content_sha256": records[key].content_hash(),
                                       "excerpt": records[key].text, "review_scope": "Bounded developer source comparison; no faculty review"}
                                      for key in keys]
    validate_cases(cases)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n")
    return {"cases": len(cases), "supported": sum(case["expected_status"] == "ok" for case in cases), "output": str(output)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=ROOT / "configs/mds_benchmark_spec.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.release, args.spec, args.output)))
