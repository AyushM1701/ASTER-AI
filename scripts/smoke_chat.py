"""Real local-model integration demonstrations, not clinical performance tests."""

import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = {
        "scope": "Small integration demonstrations; no clinical or population accuracy claim."
    }
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=330, trust_env=False) as client:
        health = client.get("/health/ready").json()
        assert health["status"] == "ready", health
        report["model"] = health["ollama"]
        token = client.post("/v1/sessions").json()["token"]
        auth = {"Authorization": "Bearer " + token}
        try:
            for name, question in [
                ("general_text", "Explain quantum entanglement in two sentences."),
                ("source_backed_text", "What is asthma?"),
            ]:
                started = time.monotonic()
                response = client.post("/v1/chat", headers=auth, json={"question": question})
                body = response.json()
                assert body["status"] == "ok", body
                if name == "general_text":
                    assert body["answer"] and not body["citations"]
                else:
                    assert body["claims"] and body["citations"]
                report[name] = {"seconds": round(time.monotonic() - started, 2), "result": body}
                print(name, "passed", flush=True)
            for name, path, expected in [
                (
                    "synthetic_prescription",
                    ROOT / "data/samples/synthetic_prescription.png",
                    "prescription",
                ),
                (
                    "cc0_chest_routing",
                    ROOT / "artifacts/evaluation/classification/cc0-chest-routing-960.png",
                    "xray",
                ),
            ]:
                started = time.monotonic()
                body = client.post(
                    "/v1/attachments",
                    headers=auth,
                    files={"file": ("attachment.png", path.read_bytes(), "image/png")},
                ).json()
                assert (body.get("classification") or {}).get("kind") == expected, body
                if expected == "prescription":
                    assert body["status"] == "needs_confirmation" and body["fields"]
                    confirmed = client.put(
                        f"/v1/documents/{body['document_id']}/confirm",
                        headers=auth,
                        json={
                            "expected_revision": body["revision"],
                            "confirmation_acknowledged": True,
                            "fields": [
                                {
                                    "field_id": f["field_id"],
                                    "value": f["candidate_value"],
                                    "status": "confirmed_by_user"
                                    if f["candidate_value"]
                                    else "unreadable",
                                }
                                for f in body["fields"]
                            ],
                        },
                    ).json()
                    explained = client.post(
                        f"/v1/documents/{body['document_id']}/explain",
                        headers=auth,
                        json={"expected_revision": confirmed["revision"]},
                    ).json()
                    assert explained["status"] == "ok" and explained["citations"]
                    assert (
                        next(f for f in confirmed["fields"] if f["kind"] == "duration")["value"]
                        is None
                    )
                    report["confirmation_explanation"] = {"passed": True, "missing_duration": None}
                else:
                    assert (
                        not body.get("findings")
                        and body["imaging_result"]["status"] == "unsupported_input"
                    )
                report[name] = {"seconds": round(time.monotonic() - started, 2), "result": body}
                print(name, "passed", flush=True)
        finally:
            client.delete("/v1/sessions/current", headers=auth)
    (ROOT / "artifacts/evaluation/chat-live-smoke.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("All local-model integration demonstrations passed.", flush=True)


if __name__ == "__main__":
    main()
