"""Check the running UI bridge, active library and representative chat routes."""
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    client = requests.Session()
    base = "http://127.0.0.1:8501/api"
    client.headers.update({"X-Aster-Client": "1", "Origin": "http://127.0.0.1:8501"})
    health = client.get(base + "/health/ready", timeout=30)
    health.raise_for_status()
    metadata = health.json()
    assert metadata["references"]["library_version"] == "aster-v2-2026-10-07"
    assert metadata["references"]["records"] == 250
    token = client.post(base + "/v1/sessions", timeout=10).json()["token"]
    client.headers["Authorization"] = "Bearer " + token
    results = []
    try:
        for question, expected in [
            ("What causes low haemoglobin?", "ok"),
            ("What is Calpol used for in India?", "ok"),
            ("Calpol 120 500mg warnings", "insufficient_evidence"),
            ("How many mg of metformin should I take?", "unsupported_input"),
            ("catalogue: Ascoril LS Syrup", "insufficient_evidence"),
        ]:
            response = client.post(base + "/v1/chat", json={"question": question}, timeout=300)
            response.raise_for_status()
            body = response.json()
            results.append({"question": question, "expected": expected, "passed": body["status"] == expected, "response": body})
    finally:
        client.delete(base + "/v1/sessions/current", timeout=10)
        client.close()
    path = ROOT / "artifacts/evaluation/knowledge-v2-numpy/api-smoke.json"
    path.write_text(json.dumps({"health": metadata, "results": results}, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(results), "passed": sum(r["passed"] for r in results),
                      "library": metadata["references"]["library_version"]}, indent=2))
    if not all(r["passed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
