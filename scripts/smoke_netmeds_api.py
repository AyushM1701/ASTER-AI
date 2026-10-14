"""Verify the running UI/API bridge serves the expanded library and its gates."""

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    client = requests.Session()
    base = "http://127.0.0.1:8501/api"
    client.headers.update({"X-Aster-Client": "1", "Origin": "http://127.0.0.1:8501"})
    response = client.get(base + "/health/ready", timeout=120)
    response.raise_for_status()
    health = response.json()
    assert health["references"]["library_version"] == "aster-v2-netmeds-r2-2026-10-07"
    assert health["references"]["records"] == 266870
    response = client.post(base + "/v1/sessions", timeout=10)
    response.raise_for_status()
    client.headers["Authorization"] = "Bearer " + response.json()["token"]
    results = []
    try:
        for question, status, retailer in [
            ("What is Dolo 650 used for?", "ok", True),
            ("What is Ascoril LS Expectorant 100ml used for?", "ok", True),
            ("What is Ketocip Shampoo 100ml used for?", "ok", True),
            ("What are Ketocip Shampoo 100ml warnings?", "insufficient_evidence", False),
            ("What is Cyclopam used for?", "insufficient_evidence", False),
            ("What are Dolo 650 interactions?", "insufficient_evidence", False),
            ("Dolo 650 Tablet 500 milligrams warnings", "insufficient_evidence", False),
            ("How many mg of Dolo 650 should I take?", "unsupported_input", False),
        ]:
            response = client.post(base + "/v1/chat", json={"question": question}, timeout=300)
            response.raise_for_status()
            body = response.json()
            passed = body["status"] == status
            if retailer:
                citations = body.get("citations", [])
                passed = (
                    passed
                    and bool(citations)
                    and all(
                        citation["source_type"] == "retailer_monograph"
                        and citation["permission_basis"]["type"] == "user_attested"
                        and citation["clinical_review"] is False
                        for citation in citations
                    )
                )
                by_id = {citation["chunk_id"]: citation for citation in citations}
                passed = passed and all(
                    any(
                        " ".join(claim["text"].casefold().split())
                        == " ".join(by_id[key]["excerpt"].casefold().split())
                        for key in claim["citation_ids"]
                        if key in by_id
                    )
                    for claim in body.get("claims", [])
                )
            results.append(
                {
                    "question": question,
                    "expected_status": status,
                    "passed": passed,
                    "response": body,
                }
            )
            print(question, body["status"], passed, flush=True)
    finally:
        cleanup = client.delete(base + "/v1/sessions/current", timeout=15)
        cleanup.raise_for_status()
        client.close()
    output = ROOT / "artifacts/evaluation/netmeds-v2-final/api-smoke.json"
    output.write_text(
        json.dumps({"health": health, "results": results, "session_deleted": True}, indent=2),
        encoding="utf-8",
    )
    if not all(result["passed"] for result in results):
        raise SystemExit("Running-app smoke failed; results saved")
    print(f"{len(results)}/{len(results)} running-app checks passed")


if __name__ == "__main__":
    main()
