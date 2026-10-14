"""Owned temporary PDF upload/review. Raw bodies avoid multipart disk spooling."""

import hashlib
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from backend.app.api.dependencies import owned_session
from backend.app.errors import AppError, envelope
from backend.app.schemas import RevisionRequest
from backend.app.services.papers import Paper, extract_pdf

router = APIRouter(prefix="/v1/papers", tags=["private-papers"])


class PaperConfirmation(RevisionRequest):
    extraction_reviewed: Literal[True]


def owned_paper(session, identity):
    with session.lock:
        paper = session.papers.get(identity)
        if paper is None:
            raise AppError(404, "unsupported_input", "Paper is not available in this session.")
        return paper


@router.post("", status_code=201)
async def upload(request: Request, private_analysis_authorized: bool = False, session=Depends(owned_session)):
    state = request.app.state
    if not private_analysis_authorized:
        raise AppError(422, "unsupported_input", "Confirm permission for private analysis of this paper.")
    if request.headers.get("content-type", "").split(";", 1)[0] not in {"application/pdf", "application/octet-stream"}:
        raise AppError(415, "unsupported_input", "Send a PDF body for private analysis.")
    identity = "paper_" + uuid4().hex
    try:
        state.sessions.reserve_upload(session, identity)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > state.settings.max_upload_bytes:
                raise AppError(413, "unsupported_input", "PDF exceeds the upload limit.")
        state.sessions.reserve_upload(session, identity, len(raw))

        def parse():
            with state.compute.enter():
                return extract_pdf(bytes(raw), state.settings)

        pages = await run_in_threadpool(parse)
        cost = len(raw) + sum(4 * len(text) for text in pages)
        with state.sessions.lock, session.lock:
            state.sessions.alive(session)
            state.sessions.reserve_upload(session, identity, cost)
            paper = Paper(identity, hashlib.sha256(raw).hexdigest(), pages, authorized=True, cost=cost)
            session.papers[identity] = paper
            session.byte_count += cost
            session.pending_uploads.pop(identity, None)
            return paper.response()
    finally:
        state.sessions.release_upload(session, identity)


@router.get("/{identity}")
def state(request: Request, identity: str, session=Depends(owned_session)):
    with request.app.state.sessions.lock, session.lock:
        request.app.state.sessions.alive(session)
        paper = owned_paper(session, identity)
        with paper.lock:
            return paper.response()


@router.post("/{identity}/confirm")
def confirm(request: Request, identity: str, payload: PaperConfirmation, session=Depends(owned_session)):
    with request.app.state.sessions.lock, session.lock:
        request.app.state.sessions.alive(session)
        paper = owned_paper(session, identity)
        with paper.lock:
            return paper.confirm(payload.expected_revision)


@router.post("/{identity}/reopen")
def reopen(request: Request, identity: str, payload: RevisionRequest, session=Depends(owned_session)):
    with request.app.state.sessions.lock, session.lock:
        request.app.state.sessions.alive(session)
        paper = owned_paper(session, identity)
        with paper.lock:
            if payload.expected_revision != paper.revision:
                raise AppError(409, "needs_confirmation", "Reload the current paper revision.")
            paper.revision += 1
            paper.confirmed_revision = None
            session.messages[:] = [message for message in session.messages if message.get("response", {}).get("context_id") != identity]
            return paper.response()


@router.delete("/{identity}")
def delete(request: Request, identity: str, session=Depends(owned_session)):
    with request.app.state.sessions.lock, session.lock:
        request.app.state.sessions.alive(session)
        paper = owned_paper(session, identity)
        with paper.lock:
            paper.wipe()
            session.papers.pop(identity)
            session.byte_count -= paper.cost
            session.messages[:] = [message for message in session.messages if message.get("response", {}).get("context_id") != identity]
            return envelope("ok", "private_paper_review", "Private paper and its server analysis context deleted.", document_id=identity)
