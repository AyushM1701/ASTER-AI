from tests import test_workflows
from tests.test_workflows import session

client = test_workflows.client


def test_plain_text_report_terms_are_not_personal_interpretation(client):
    r = client.post(
        "/v1/chat",
        headers=session(client),
        json={"question": "Explain this blood report: Hemoglobin: 8 g/dL; Glucose: 200 mg/dL"},
    ).json()
    assert r["status"] == "ok"
    assert r["report_explanation"]["scope"] == "terminology_only"
    assert len(r["report_explanation"]["terms"]) == 2
    assert r["report_explanation"]["values_interpreted"] is False
    assert "anemia" not in " ".join(c["text"] for c in r["claims"]).lower()
    assert r["validation"]["clinical_review"] == "pending"


def test_every_report_line_is_accounted_for(client):
    r = client.post(
        "/v1/chat",
        headers=session(client),
        json={"question": "Explain this report: Hb: 12; Creatinine: 4"},
    ).json()
    assert r["status"] == "partial" and r["task_completion"] is False
    assert r["unsupported_parts"] == ["Creatinine: 4"]


def test_unknown_report_abstains_and_diagnosis_stays_blocked(client):
    h = session(client)
    r = client.post(
        "/v1/chat", headers=h, json={"question": "Explain this report: Creatinine: 4"}
    ).json()
    assert r["status"] == "insufficient_evidence"
    r = client.post(
        "/v1/chat",
        headers=h,
        json={"question": "Explain this report: Hb: 8. Diagnose me with anemia."},
    ).json()
    assert not r.get("report_explanation")
