import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.adapters.ollama import OllamaAdapter  # noqa: E402
from backend.app.config import Settings  # noqa: E402
from backend.app.services.answers import AnswerService  # noqa: E402
from backend.app.services.compute import ComputeGate  # noqa: E402
from backend.app.services.retrieval import ReferenceStore  # noqa: E402
from scripts.manifest import run_manifest  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate routing, source recall and citation IDs, not clinical accuracy."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings(chroma_path=args.index) if args.index else Settings()
    refs = ReferenceStore(settings)
    ollama = OllamaAdapter(settings)
    service = AnswerService(settings, refs, ollama, ComputeGate(settings))
    results = []
    for line in args.dataset.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        start = time.perf_counter()
        response = service.answer(case["question"])
        evidence = refs.search(case["question"])
        retrieved = {r.source_id for r in evidence}
        expected = set(case["expected_source_ids"])
        ids = {c["chunk_id"] for c in response.get("citations", [])}
        claims = response.get("claims", [])
        valid = all(set(c["citation_ids"]) <= ids and c["citation_ids"] for c in claims)
        results.append(
            {
                "case_id": case["case_id"],
                "status": response["status"],
                "route_correct": response["status"] == case["expected_status"],
                "source_recall_at_3": len(expected & retrieved) / len(expected)
                if expected
                else None,
                "citation_ids_valid": valid,
                "latency_seconds": time.perf_counter() - start,
            }
        )
    ollama.close()
    eligible = [r["source_recall_at_3"] for r in results if r["source_recall_at_3"] is not None]
    summary = {
        "cases": len(results),
        "route_correct": sum(r["route_correct"] for r in results),
        "citation_ids_valid_cases": sum(r["citation_ids_valid"] for r in results),
        "source_recall_at_3": sum(eligible) / len(eligible) if eligible else None,
        "failures": [
            r["case_id"] for r in results if not r["route_correct"] or not r["citation_ids_valid"]
        ],
        "clinical_accuracy": None,
        "claim_entailment_score": None,
        "limitations": "Developer development fixtures only. No held-out performance, triage safety, "
        "clinical accuracy or independently measured claim entailment is established.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.output / "run_manifest.json").write_text(
        json.dumps(run_manifest(settings, refs), indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if summary["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
