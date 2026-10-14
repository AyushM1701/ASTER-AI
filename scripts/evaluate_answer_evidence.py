"""Evaluate saved synthetic responses and export a small blank review pack."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from backend.app.services.medical_evaluation import evaluate_claims


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("responses", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    content = args.responses.read_bytes()
    rows = json.loads(content)
    cases = [{"case_id": hashlib.sha256((str(i) + row["question"]).encode()).hexdigest()[:16],
              "question": row["question"], "answer": row["response"],
              "automated": evaluate_claims(row["response"])} for i, row in enumerate(rows) if "response" in row]
    report = {"input_sha256": hashlib.sha256(content).hexdigest(), "cases": cases,
              "clinical_review": "pending", "medical_accuracy": None,
              "note": "Exact passage checks do not evaluate prepared paraphrases or the truth of sources."}
    args.output.joinpath("evidence-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with args.output.joinpath("review-scores-blank.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case_id", "reviewer", "qualifications", "independent_reference", "correctness", "completeness", "applicability", "clarity", "serious_error", "adjudication", "review_date"])
        writer.writeheader()
        writer.writerows({"case_id": case["case_id"]} for case in cases)
    args.output.joinpath("review-instructions.md").write_text(
        "# Independent review\n\nOnly qualified humans enter their own assessments. Scores and identities are blank. "
        "Use an independent reference; record correctness, completeness, applicability and clarity from 0 (unacceptable) "
        "to 4 (fully satisfactory), serious errors and disagreements. An abstention is not a factual answer. "
        "Credentials require separate verification. This export cannot establish qualified clinical review. "
        "Use the existing curriculum_audit.py import-scores workflow for its own compatible packs; this small pack is a separate developer export. "
        "Do not import its CSV into an incompatible schema or auto-fill scores. Source material remains subject to its terms.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
