"""Reproducible narrow public literature pilot; no medical accuracy score."""

import argparse
import json
import time
from pathlib import Path

import httpx

from backend.app.services.research_workspace import (
    LiteratureSearch,
    ResearchRequest,
    export_markdown,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/evaluation/product-scope-2026-10-11")
    )
    parser.add_argument(
        "--journeys",
        action="store_true",
        help="Probe the running local API instead of searching literature",
    )
    args = parser.parse_args()
    if args.journeys:
        return journeys(args.output)
    request = ResearchRequest(
        question="Malignant transformation risk in adults with oral leukoplakia",
        population="Adults with oral leukoplakia",
        article_type="narrative review",
        query='TITLE_ABS:"oral leukoplakia" AND TITLE_ABS:"malignant transformation" AND OPEN_ACCESS:Y',
        inclusion="Human adult observational studies and reviews; manually screen each record.",
        exclusion="Case reports; nonhuman studies; manual screening pending.",
        limit=10,
        inspect_full_text=True,
        public_query_confirmed=True,
    )
    project = LiteratureSearch().search(request)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "oral-pathology-pilot.json").write_text(
        json.dumps(project, indent=2), encoding="utf-8"
    )
    (args.output / "oral-pathology-pilot.md").write_text(export_markdown(project), encoding="utf-8")
    print(
        json.dumps(
            {
                "papers": len(project["papers"]),
                "full_text": sum(
                    p["access"] == "permitted_full_text_inspected" for p in project["papers"]
                ),
                "evidence_rows": len(project["evidence_table"]),
                "validation": project["validation"],
            }
        )
    )


def journeys(output):
    patient = [
        "Why does my tooth hurt?",
        "What is a headache?",
        "What is fever?",
        "What causes a sore throat?",
        "What could abdominal pain mean?",
        "What is epithelium?",
        "What does blood pressure mean?",
        "Explain this report: Hb: 12 g/dL",
        "Explain this report: Glucose: 110 mg/dL",
        "What is metformin hydrochloride immediate-release tablet used for?",
    ]
    student = [
        "epithelium",
        "dental pulp",
        "periodontal ligament",
        "cementum",
        "junctional epithelium",
        "salivary glands",
        "amelogenesis",
        "H&E staining",
        "immunohistochemistry",
        "tissue fixation",
    ]
    probes = [("understand", q) for q in patient] + [
        ("study", "What is " + topic + "?") for topic in student
    ]
    probes += [("study", "Ask me a viva question on " + topic) for topic in student]
    probes += [
        ("study", q)
        for q in [
            "Compare dental pulp and cementum",
            "Compare osmosis and diffusion",
            "Explain the mechanism of amelogenesis",
            "Review my answer on epithelium: It covers surfaces.",
            "Apply dental pulp to a fictional case",
        ]
    ]
    results = []
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=45, trust_env=False) as client:
        token = client.post("/v1/sessions").json()["token"]
        headers = {"Authorization": "Bearer " + token}
        try:
            capabilities = client.get("/v1/study/topics", headers=headers).json()
            for audience, question in probes:
                before = time.monotonic()
                response = client.post(
                    "/v1/chat",
                    headers=headers,
                    json={"question": question, "audience": audience, "task_explicit": True},
                )
                results.append(
                    dict(
                        audience=audience,
                        question=question,
                        http_status=response.status_code,
                        latency_ms=round((time.monotonic() - before) * 1000),
                        response=response.json(),
                    )
                )
        finally:
            client.delete("/v1/sessions/current", headers=headers)
    report = dict(
        scope="10 patient + 10 student topics, 10 viva activities, 5 operation probes",
        medical_accuracy=None,
        qualified_review="pending",
        patient_comprehension="not_measured",
        capabilities=capabilities,
        results=results,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "patient-student-journeys.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "probes": len(results),
                "http_failures": sum(r["http_status"] != 200 for r in results),
                "statuses": {
                    s: sum(r["response"]["status"] == s for r in results)
                    for s in sorted({r["response"]["status"] for r in results})
                },
                "medical_accuracy": None,
            }
        )
    )


if __name__ == "__main__":
    main()
