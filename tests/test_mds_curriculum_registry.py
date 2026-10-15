import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.mds_curriculum import registry
from tests.mds_fixtures import make_teacher


@pytest.mark.local  # needs licensed source packs that are not committed
def test_registry_binds_existing_national_amendment_scope_without_readiness_claims():
    data = registry()
    assert len(data["families"]) == 12 and len(data["specialties"]) == 9
    assert data["national_assessment_register"]["verified_snapshot_count"] >= 4
    assert data["topics"][0]["curriculum_topic_ids"]
    assert all(not t["ready_tasks"] for t in data["topics"])
    assert data["curriculum"]["university_overlay"] == "not_requested_national_only"


def test_curriculum_endpoint_is_session_owned_and_reports_only_actual_sources(tmp_path):
    teacher, _ = make_teacher(tmp_path, [("apoptosis", "Apoptosis", "Apoptosis is a synthetic bounded definition for this mechanics fixture with qualified source limitations.")])
    with TestClient(create_app(teacher.settings)) as client:
        assert client.get("/v1/study/curriculum").status_code == 401
        headers = {"Authorization": "Bearer " + client.post("/v1/sessions").json()["token"]}
        response = client.get("/v1/study/curriculum", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["source_set_version"] == "synthetic-v1"
        assert all(t["qualified_clinical_review"] == "pending" for t in data["topics"])


def test_registry_does_not_claim_verified_missing_or_tampered_snapshot(tmp_path, monkeypatch):
    import backend.app.services.mds_curriculum as curriculum

    fake = tmp_path / "scope.json"
    fake.write_text(json.dumps({"version": "test", "sources": [{"id": "official", "path": "missing.pdf", "sha256": hashlib.sha256(b"expected").hexdigest()}], "items": []}))
    monkeypatch.setattr(curriculum, "NATIONAL_REGISTER", fake)
    data = curriculum.registry()
    assert data["national_assessment_register"]["verified_snapshot_count"] == 0
    assert data["national_assessment_register"]["integrity_status"] == "unavailable_or_changed"


def test_curriculum_route_is_available_through_owned_web_bridge():
    import httpx

    from tests.test_webserver import web_client

    received = []

    def handler(request):
        received.append(request)
        return httpx.Response(200, json={"status": "ok", "readiness": "Declared scope"})

    with web_client(handler) as client:
        result = client.get("/api/v1/study/curriculum", headers={"X-Aster-Client": "1", "Authorization": "Bearer owned-token"})
    assert result.status_code == 200
    assert received[0].headers["authorization"] == "Bearer owned-token"
    assert received[0].url.path == "/v1/study/curriculum"
