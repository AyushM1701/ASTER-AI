"""Check actual local chat routing and teaching source context on synthetic inputs."""

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_curricula import digest  # noqa: E402
from scripts.evaluate_teaching_precision import cases_from, inspect_fit  # noqa: E402

SCOPE_CASES = [
    "For kidney failure, explain osmosis",
    "For an MBBS student with kidney failure, explain osmosis",
    "Explain diffusion and osmosis in kidney failure",
    "Compare diffusion and osmosis in kidney failure",
    "Explain diffusion and osmosis for children with kidney failure",
    "Compare diffusion and osmosis for dialysis",
    "Explain diffusion and osmosis under hypoxic conditions",
    "Explain depression investigations",
    "Explain schizophrenia diagnostic assessment",
    "What is the difference between diffusion and osmosis for dialysis?",
    "Differences between diffusion and osmosis for dialysis",
    "For kidney failure, what is osmosis?",
    "For kidney failure, tell me about osmosis",
    "Compare mean and median for kidney failure",
    "What is the difference between mean and median in liver disease?",
]


def run(output):
    if output.exists():
        raise FileExistsError(output)
    cases = cases_from(json.loads((ROOT / "data/evaluation/teaching_precision_v1.json").read_text()))
    prior = json.loads((ROOT / "artifacts/evaluation/precision-v1/live-precision-and-regression.json").read_text(encoding="utf-8"))
    regressions = [r for r in prior["results"] if r["group"] == "existing_bridge"]
    rows = []
    with httpx.Client(base_url="http://127.0.0.1:8501", timeout=120, trust_env=False,
                      headers={"X-Aster-Client": "1", "Origin": "http://127.0.0.1:8501"}) as client:
        health = client.get("/api/health/ready")
        health.raise_for_status()
        token = client.post("/api/v1/sessions").json()["token"]
        headers = {"Authorization": "Bearer " + token}
        try:
            for case in cases:
                reply = client.post("/api/v1/chat", headers=headers, json={"question": case["question"]})
                answer = reply.json()
                expected = dict(case)
                if case["status"] == "not_handled":
                    expected["status"] = "insufficient_evidence"
                check = inspect_fit(expected, answer)
                if case["id"] == "brand-boundary":
                    # This fixture asserts bypass of teaching, not refusal of a
                    # recognised medicine. Product notes cannot prove osmosis.
                    check = {"pass": not answer.get("teaching_version") and bool(answer.get("citations"))
                             and any(c.get("source_type") == "retailer_monograph" for c in answer["citations"])
                             and all(c.get("source_type") in {"retailer_monograph", "unverified_secondary"} for c in answer["citations"]),
                             "interpretation": "Medicine identity routing only; mixed-question completeness is not established."}
                rows.append(dict(id=case["id"], question=case["question"], answer=answer, check=check, http_status=reply.status_code))
            for row in regressions:
                reply = client.post("/api/v1/chat", headers=headers, json={"question": row["question"]})
                answer = reply.json()
                rows.append(dict(id=row["id"], question=row["question"], answer=answer, http_status=reply.status_code,
                                 check={"pass": answer.get("status") == row["answer"]["status"], "interpretation": "Existing routing regression only."}))
            for number, question in enumerate(SCOPE_CASES):
                reply = client.post("/api/v1/chat", headers=headers, json={"question": question})
                answer = reply.json()
                rows.append(dict(id=f"review-scope-{number}", question=question, answer=answer, http_status=reply.status_code,
                                 check={"pass": answer.get("status") == "insufficient_evidence"}))
        finally:
            deleted = client.delete("/api/v1/sessions/current", headers=headers).is_success
    report = dict(cases=len(rows), passed=sum(r["check"]["pass"] and r["http_status"] == 200 for r in rows),
                  clinical_accuracy=None, faculty_review="pending", session_deleted=deleted,
                  health_teaching=health.json().get("teaching"),
                  runtime_hashes={p: digest(ROOT / p) for p in ["backend/app/services/teaching.py", "backend/app/services/teaching_query.py", "backend/app/services/answers.py"]},
                  interpretation=f"66 teaching context/boundary probes, 34 prior routing probes and {len(SCOPE_CASES)} review-scope probes. Mixed medicine case checks routing only, not completeness. No medical accuracy score.",
                  results=rows)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(cases=report["cases"], passed=report["passed"], deleted=deleted,
                          failures=[dict(id=r["id"], status=r["answer"].get("status")) for r in rows if not r["check"]["pass"]])))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.output)
