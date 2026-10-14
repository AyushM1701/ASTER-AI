"""Actual loopback service workflow with the synthetic sample. Never stores a token."""

import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    results = {}
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=40, trust_env=False) as client:
        ready = client.get("/health/ready")
        ready.raise_for_status()
        results["readiness"] = ready.json()["status"]
        token = client.post("/v1/sessions").json()["token"]
        headers = {"Authorization": "Bearer " + token}
        try:
            answer = client.post(
                "/v1/chat", headers=headers, json={"question": "What is asthma?"}
            ).json()
            assert answer["status"] == "ok" and answer["citations"]
            results["cited_education"] = True
            urgent = client.post(
                "/v1/chat",
                headers=headers,
                json={"question": "I don't have asthma but I cannot breathe"},
            ).json()
            assert urgent["status"] == "urgent_guidance"
            results["urgent_during_model_outage"] = True
            doc = client.post(
                "/v1/documents",
                headers=headers,
                files={
                    "file": (
                        "synthetic.png",
                        (ROOT / "data/samples/synthetic_prescription.png").read_bytes(),
                        "image/png",
                    )
                },
                data={"intent": "prescription"},
            ).json()["document_id"]
            extracted = client.post(f"/v1/documents/{doc}/extract", headers=headers).json()
            assert extracted["fields"]
            blocked = client.post(
                f"/v1/documents/{doc}/explain",
                headers=headers,
                json={"expected_revision": extracted["revision"]},
            )
            assert blocked.status_code == 409
            results["confirmation_bypass_rejected"] = True
            fields = [
                {
                    "field_id": f["field_id"],
                    "value": f["candidate_value"],
                    "status": "confirmed_by_user" if f["candidate_value"] else "unreadable",
                }
                for f in extracted["fields"]
            ]
            confirmed = client.put(
                f"/v1/documents/{doc}/confirm",
                headers=headers,
                json={
                    "expected_revision": extracted["revision"],
                    "fields": fields,
                    "confirmation_acknowledged": True,
                },
            ).json()
            explained = client.post(
                f"/v1/documents/{doc}/explain",
                headers=headers,
                json={"expected_revision": confirmed["revision"]},
            ).json()
            assert explained["status"] == "ok" and explained["citations"]
            results["real_ocr_confirm_explain"] = True
            missing = next(f for f in explained["confirmed_fields"] if f["kind"] == "duration")
            assert missing["value"] is None
            results["missing_duration_stays_null"] = True
            xray = client.post(
                "/v1/xray/analyze", headers=headers, json={"asset_id": "not-registered"}
            ).json()
            assert xray["status"] == "unsupported_input" and not xray["findings"]
            results["unregistered_imaging_rejected"] = True
        finally:
            deleted = client.delete("/v1/sessions/current", headers=headers)
            deleted.raise_for_status()
        assert client.get(f"/v1/documents/{doc}", headers=headers).status_code == 401
        results["deletion_revokes_token"] = True
    output = ROOT / "artifacts/evaluation/live-smoke.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
