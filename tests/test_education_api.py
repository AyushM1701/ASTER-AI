from datetime import datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services.research_workspace import LiteratureSearch


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(Settings(_env_file=None, workspace_path=tmp_path / "education.sqlite3"))
    ) as c:
        yield c


def headers(client, key="a" * 64):
    token = client.post("/v1/sessions").json()["token"]
    return {"Authorization": "Bearer " + token, "X-Aster-Workspace": key}


def test_progress_opt_in_export_delete_and_isolation(client):
    a, b = headers(client), headers(client, "b" * 64)
    assert (
        client.post(
            "/v1/study/progress",
            headers={"Authorization": a["Authorization"]},
            json={"topic": "Osmosis", "self_assessment": "revisit"},
        ).status_code
        == 403
    )
    response = client.post(
        "/v1/study/progress",
        headers=a,
        json={
            "topic": "Osmosis",
            "self_assessment": "revisit",
            "weak_concepts": ["water movement"],
        },
    )
    assert response.status_code == 200
    item = response.json()["record"]
    assert item["attempts"] == 1 and item["grading"] == "self_assessment_only"
    assert (
        item["revisit_on"] == (datetime.now().astimezone().date() + timedelta(days=1)).isoformat()
    )
    assert client.get("/v1/study/progress", headers=b).json()["records"] == []
    assert len(client.get("/v1/study/progress", headers=headers(client)).json()["records"]) == 1
    assert (
        client.get("/v1/education/export", headers=a).json()["patient_documents_included"] is False
    )
    assert client.delete("/v1/study/progress/" + item["id"], headers=b).status_code == 404
    assert client.delete("/v1/education", headers=a).status_code == 200
    assert client.get("/v1/study/progress", headers=a).json()["records"] == []


def test_no_patient_fields_saved_as_progress(client):
    a = headers(client)
    result = client.post(
        "/v1/study/progress",
        headers=a,
        json={"topic": "Osmosis", "self_assessment": "revisit", "document_text": "Rx"},
    )
    assert result.status_code == 422
    assert (
        client.post(
            "/v1/study/progress", headers=a, json={"topic": " ", "self_assessment": "revisit"}
        ).status_code
        == 422
    )


def test_research_saved_export_and_delete(client):
    raw = {
        "hitCount": 1,
        "resultList": {
            "result": [
                {
                    "id": "123",
                    "source": "MED",
                    "title": "Oral leukoplakia study",
                    "authorString": "A Author",
                    "pubYear": "2024",
                    "abstractText": "An abstract passage.",
                }
            ]
        },
    }
    client.app.state.literature = LiteratureSearch(
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=raw)))
    )
    a, b = headers(client), headers(client, "b" * 64)
    response = client.post(
        "/v1/research/projects",
        headers=a,
        json={
            "question": "Oral leukoplakia review",
            "population": "Adults",
            "query": "oral leukoplakia",
            "public_query_confirmed": True,
        },
    )
    assert response.status_code == 200
    identity = response.json()["project"]["id"]
    assert client.get("/v1/research/projects/" + identity, headers=b).status_code == 404
    assert (
        "# Oral leukoplakia"
        in client.get(
            "/v1/research/projects/" + identity + "/export?format=markdown", headers=a
        ).text
    )
    assert (
        "@article"
        in client.get("/v1/research/projects/" + identity + "/export?format=bibtex", headers=a).text
    )
    assert (
        client.put(
            "/v1/research/projects/" + identity + "/writing",
            headers=b,
            json={"expected_revision": 1, "draft": "My unverified writing"},
        ).status_code
        == 404
    )
    saved = client.put(
        "/v1/research/projects/" + identity + "/writing",
        headers=a,
        json={"expected_revision": 1, "draft": "My unverified writing"},
    )
    assert saved.status_code == 200 and saved.json()["project"]["version"] == 2
    assert (
        client.put(
            "/v1/research/projects/" + identity + "/writing",
            headers=a,
            json={"expected_revision": 1, "draft": "Stale overwrite"},
        ).status_code
        == 409
    )
    exported = client.get(
        "/v1/research/projects/" + identity + "/export?format=markdown", headers=a
    ).text
    assert "My unverified writing" in exported and "unverified" in exported
    assert client.delete("/v1/research/projects/" + identity, headers=a).status_code == 200


def test_network_failure_does_not_save_empty_success(client):
    client.app.state.literature = LiteratureSearch(
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    )
    a = headers(client)
    r = client.post(
        "/v1/research/projects",
        headers=a,
        json={
            "question": "Oral leukoplakia review",
            "population": "Adults",
            "query": "oral leukoplakia",
            "public_query_confirmed": True,
        },
    )
    assert r.status_code == 503
    assert client.get("/v1/research/projects", headers=a).json()["projects"] == []
