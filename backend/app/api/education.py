"""Local educational persistence requires an independent opt-in capability."""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from pydantic import Field, field_validator

from backend.app.api.dependencies import owned_session
from backend.app.errors import AppError
from backend.app.schemas import StrictModel
from backend.app.services.research_workspace import ResearchRequest, export_bibtex, export_markdown
from backend.app.services.study import StudyRecord

router = APIRouter(prefix="/v1", tags=["educational workspace"])


@router.get("/study/topics")
def study_topics(request: Request, session=Depends(owned_session)):
    from backend.app.services.study_operations import topic_capabilities

    return {"status": "ok", **topic_capabilities(request.app.state.teaching)}


@router.get("/study/curriculum")
def study_curriculum(request: Request, session=Depends(owned_session)):
    from backend.app.services.mds_curriculum import registry

    teacher = request.app.state.teaching
    return {"status": "ok", **registry(), "source_set_version": teacher.version,
            "available_source_records": len(teacher.records),
            "readiness": "Declared scope only; query responses compute actual facet coverage."}


@router.get("/study/source-inventory")
def source_inventory(session=Depends(owned_session)):
    import json

    from backend.app.paths import install_root

    path = install_root() / "configs/medical_source_inventory.v2.json"
    return {"status": "ok", **json.loads(path.read_text(encoding="utf-8"))}


def workspace_owner(request: Request, session=Depends(owned_session)):
    key = request.headers.get("X-Aster-Workspace", "")
    if not re.fullmatch(r"[a-f0-9]{64}", key):
        raise AppError(
            403, "unsupported_input", "Enable local educational saving before using saved work."
        )
    return hashlib.sha256(key.encode()).hexdigest()


class ProgressInput(StudyRecord):
    weak_concepts: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=10
    )

    @field_validator("topic")
    @classmethod
    def valid_topic(cls, value):
        if not value.strip():
            raise ValueError("Topic must not be empty")
        return value.strip()


class WritingInput(StrictModel):
    expected_revision: int = Field(ge=1)
    draft: str = Field(max_length=30000)


def put(store, owner, kind, identity, value):
    try:
        store.put(owner, kind, identity, value)
    except ValueError as exc:
        raise AppError(413, "unsupported_input", str(exc)) from exc


@router.get("/study/progress")
def progress(request: Request, owner=Depends(workspace_owner)):
    return {"status": "ok", "records": request.app.state.workspaces.list(owner, "study")}


@router.post("/study/progress")
def save_progress(request: Request, payload: ProgressInput, owner=Depends(workspace_owner)):
    store = request.app.state.workspaces
    identity = hashlib.sha256(" ".join(payload.topic.casefold().split()).encode()).hexdigest()[:24]
    now = datetime.now(timezone.utc)
    with store.lock:
        old = store.get(owner, "study", identity) or {}
        attempt = dict(
            timestamp=now.isoformat(),
            self_assessment=payload.self_assessment,
            weak_concepts=payload.weak_concepts,
        )
        record = dict(
            id=identity,
            topic=payload.topic,
            attempts=old.get("attempts", 0) + 1,
            self_assessment=payload.self_assessment,
            weak_concepts=payload.weak_concepts,
            history=[*old.get("history", []), attempt][-20:],
            updated_at=now.isoformat(),
            revisit_on=(
                now.astimezone() + timedelta(days=1 if payload.self_assessment == "revisit" else 7)
            )
            .date()
            .isoformat(),
            grading="self_assessment_only",
            clinical_review="pending",
        )
        put(store, owner, "study", identity, record)
    return {"status": "ok", "record": record}


@router.delete("/study/progress/{identity}")
def delete_progress(request: Request, identity: str, owner=Depends(workspace_owner)):
    if not request.app.state.workspaces.delete(owner, "study", identity):
        raise AppError(
            404, "unsupported_input", "Saved topic is not available in your local workspace."
        )
    return {"status": "ok"}


@router.get("/education/export")
def educational_export(request: Request, owner=Depends(workspace_owner)):
    store = request.app.state.workspaces
    return {
        "status": "ok",
        "schema_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "study": store.list(owner, "study"),
        "research": store.list(owner, "research"),
        "patient_documents_included": False,
        "retention": "Until explicitly deleted; downloaded exports are separate.",
    }


@router.delete("/education")
def clear_education(request: Request, owner=Depends(workspace_owner)):
    request.app.state.workspaces.clear(owner)
    return {
        "status": "ok",
        "message": "Saved educational work deleted. Temporary patient sessions are managed separately.",
    }


@router.post("/research/projects")
def create_project(request: Request, payload: ResearchRequest, owner=Depends(workspace_owner)):
    if not request.app.state.settings.enable_research_search:
        raise AppError(
            503, "unsupported_input", "Online literature search is disabled in this installation."
        )
    try:
        project = request.app.state.literature.search(payload)
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise AppError(
            503,
            "error",
            "Literature retrieval failed or returned invalid evidence. No project was saved; retry or revise the public query.",
        ) from exc
    put(request.app.state.workspaces, owner, "research", project["id"], project)
    return {"status": "ok", "project": project}


@router.get("/research/projects")
def projects(request: Request, owner=Depends(workspace_owner)):
    return {
        "status": "ok",
        "projects": [
            {k: p[k] for k in ("id", "question", "created_at", "task_completion")}
            for p in request.app.state.workspaces.list(owner, "research")
        ],
    }


def get_project(request, owner, identity):
    project = request.app.state.workspaces.get(owner, "research", identity)
    if not project:
        raise AppError(
            404, "unsupported_input", "Research project is not available in your local workspace."
        )
    return project


@router.get("/research/projects/{identity}")
def project(request: Request, identity: str, owner=Depends(workspace_owner)):
    return {"status": "ok", "project": get_project(request, owner, identity)}


@router.put("/research/projects/{identity}/writing")
def save_writing(
    request: Request, identity: str, payload: WritingInput, owner=Depends(workspace_owner)
):
    store = request.app.state.workspaces
    with store.lock:
        value = get_project(request, owner, identity)
        if value["version"] != payload.expected_revision:
            raise AppError(
                409,
                "needs_confirmation",
                "This project changed. Reopen it before saving; keep a copy of your draft.",
            )
        value.update(
            version=value["version"] + 1,
            user_draft=payload.draft,
            user_draft_status="unverified_user_writing",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        put(store, owner, "research", identity, value)
    return {"status": "ok", "project": value}


@router.get("/research/projects/{identity}/export")
def project_export(
    request: Request, identity: str, format: str = "markdown", owner=Depends(workspace_owner)
):
    value = get_project(request, owner, identity)
    if format == "json":
        return value
    if format not in {"markdown", "bibtex"}:
        raise AppError(422, "unsupported_input", "Choose markdown, bibtex or json export.")
    return PlainTextResponse(
        export_markdown(value) if format == "markdown" else export_bibtex(value)
    )


@router.delete("/research/projects/{identity}")
def delete_project(request: Request, identity: str, owner=Depends(workspace_owner)):
    if not request.app.state.workspaces.delete(owner, "research", identity):
        raise AppError(
            404, "unsupported_input", "Research project is not available in your local workspace."
        )
    return {"status": "ok"}
