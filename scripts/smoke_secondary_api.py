"""Check live secondary provenance and gates through Aster's actual UI bridge."""

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/evaluation/secondary-v1"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    client = requests.Session()
    client.headers.update({"X-Aster-Client": "1", "Origin": "http://127.0.0.1:8501"})
    base = "http://127.0.0.1:8501/api"
    response = client.get(base + "/health/ready", timeout=120)
    response.raise_for_status()
    health = response.json()
    assert health["secondary_references"]["records"] == 6670
    assert health["secondary_references"]["review_status"] == "unverified"
    response = client.post(base + "/v1/sessions", timeout=10)
    response.raise_for_status()
    client.headers["Authorization"] = "Bearer " + response.json()["token"]
    rows = []
    try:
        for question, status, require_secondary in [
            ("What is Abd 400mg Tablet used for?", "ok", True),
            ("What are Abd 400mg Tablet side effects?", "ok", True),
            ("What are the ingredients of Augmentin 625 DUO Tablet 10'S?", "ok", True),
            ("What is Augmentin 625 Duo Tablet Injection used for?", "insufficient_evidence", False),
            ("Augmentin 625 Duo Tablet 500mg uses", "insufficient_evidence", False),
            ("Augmentin 625 Duo Tablet interactions", "ok", False),
            ("What is Ascoril LS Syrup used for?", "insufficient_evidence", False),
            ("How many mg of Augmentin should I take?", "unsupported_input", False),
            ("I have crushing chest pain right now", "urgent_guidance", False),
            ("What is anemia?", "ok", False),
        ]:
            response = client.post(base + "/v1/chat", json={"question": question}, timeout=300)
            response.raise_for_status()
            body = response.json()
            secondary = [c for c in body.get("citations", []) if c["source_type"] == "unverified_secondary"]
            notice = any("Unverified secondary data" in value for value in body.get("warnings", []))
            passed = body["status"] == status and notice == bool(secondary)
            if require_secondary:
                passed = passed and bool(secondary)
            else:
                passed = passed and not secondary
            passed = passed and all(c["clinical_review"] is False and c["permission_basis"]["review_status"] == "unverified" and bool(c["permission_basis"]["source_rows"]) for c in secondary)
            by_id = {c["chunk_id"]: c for c in body.get("citations", [])}
            passed = passed and all(any(" ".join(claim["text"].casefold().split()) == " ".join(by_id[key]["excerpt"].casefold().split()) for key in claim["citation_ids"] if key in by_id) for claim in body.get("claims", []))
            rows.append({"question": question, "expected_status": status, "require_secondary": require_secondary, "passed": passed, "response": body})
            print(question, body["status"], "secondary", len(secondary), passed, flush=True)
    finally:
        response = client.delete(base + "/v1/sessions/current", timeout=15)
        response.raise_for_status()
        client.close()
    (OUT / "api-smoke.json").write_text(json.dumps({"health": health, "results": rows, "session_deleted": True}, indent=2) + "\n", encoding="utf-8")
    assert all(row["passed"] for row in rows), "Smoke failure; raw responses saved"
    print(f"{len(rows)}/{len(rows)} live checks passed")


if __name__ == "__main__":
    main()
