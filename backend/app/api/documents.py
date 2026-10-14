import hashlib
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from backend.app.api.dependencies import owned_session
from backend.app.errors import AppError, envelope
from backend.app.schemas import Confirmation, RevisionRequest
from backend.app.services.documents import (
    Document,
    confirm,
    explain,
    parse_fields,
    require_confirmation,
)
from backend.app.services.uploads import decode_image, decoded_budget

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.post("", status_code=201)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    intent: str = Form("prescription"),
    session=Depends(owned_session),
):
    state = request.app.state
    document_id = "doc_" + uuid4().hex
    try:
        if intent not in {"prescription", "document"}:
            raise AppError(422, "unsupported_input", "Choose prescription or document intent.")
        state.sessions.reserve_upload(session, document_id)
        chunks, size = [], 0
        while chunk := await file.read(65536):
            size += len(chunk)
            if size > state.settings.max_upload_bytes:
                raise AppError(413, "unsupported_input", "Image exceeds the upload byte limit.")
            chunks.append(chunk)

        def bounded_decode(data):
            with state.compute.enter():
                state.sessions.reserve_upload(
                    session, document_id, decoded_budget(data, state.settings)
                )
                return decode_image(data, state.settings)

        raw = b"".join(chunks)
        image, preview = await run_in_threadpool(bounded_decode, raw)
        cost = size + len(preview) + image.width * image.height * 3
        with state.sessions.lock, session.lock:
            state.sessions.alive(session)
            if (
                session.byte_count
                + sum(v for key, v in session.pending_uploads.items() if key != document_id)
                + cost
                > state.settings.max_session_bytes
            ):
                raise AppError(
                    429, "busy", "Session upload limit reached. Clear the session to continue."
                )
            session.documents[document_id] = Document(document_id, image, preview, intent)
            session.documents[document_id].source_sha256 = hashlib.sha256(raw).hexdigest()
            session.byte_count += cost
            session.pending_uploads.pop(document_id, None)
        return envelope(
            "ok",
            "document",
            "Image uploaded. Extract text to begin review.",
            document_id=document_id,
            revision=0,
            state="uploaded",
        )
    finally:
        state.sessions.release_upload(session, document_id)
        await file.close()


@router.get("/{document_id}")
def document_state(request: Request, document_id: str, session=Depends(owned_session)):
    document = request.app.state.sessions.document(session, document_id)
    with document.lock:
        return document.response()


@router.get("/{document_id}/image")
def document_image(request: Request, document_id: str, session=Depends(owned_session)):
    document = request.app.state.sessions.document(session, document_id)
    return Response(document.preview, media_type="image/png")


@router.post("/{document_id}/extract")
def extract_document(request: Request, document_id: str, session=Depends(owned_session)):
    state = request.app.state
    document = state.sessions.document(session, document_id)
    with document.lock:
        if document.state in {"extracting", "classifying"}:
            raise AppError(409, "busy", "Extraction is already in progress.")
        if document.state != "uploaded" and document.fields:
            return document.response()
        document.state = "extracting"
    try:
        with state.compute.enter():
            ocr = state.ocr.extract(document.image)
        with state.sessions.lock, session.lock, document.lock:
            state.sessions.alive(session)
            document.ocr = ocr
            document.fields = parse_fields(
                ocr["raw_text"], document.intent, provenance=ocr.get("engine", "tesseract")
            )
            document.revision += 1
            document.state = "needs_confirmation"
            return document.response()
    except AppError:
        with document.lock:
            document.state = "uploaded"
        raise


@router.put("/{document_id}/confirm")
def confirm_document(
    request: Request, document_id: str, payload: Confirmation, session=Depends(owned_session)
):
    state = request.app.state
    document = state.sessions.document(session, document_id)
    with state.sessions.lock, session.lock, document.lock:
        state.sessions.alive(session)
        return confirm(document, payload)


@router.post("/{document_id}/edit")
def edit_document(
    request: Request, document_id: str, payload: RevisionRequest, session=Depends(owned_session)
):
    state = request.app.state
    document = state.sessions.document(session, document_id)
    with state.sessions.lock, session.lock, document.lock:
        state.sessions.alive(session)
        if payload.expected_revision != document.revision or document.state in {
            "extracting",
            "classifying",
        }:
            raise AppError(409, "needs_confirmation", "Reload the current document revision.")
        document.revision += 1
        document.confirmed_revision = None
        document.explanation = None
        document.state = "needs_confirmation"
        session.messages[:] = [
            m for m in session.messages if m.get("response", {}).get("context_id") != document.id
        ]
        return document.response()


@router.post("/{document_id}/explain")
def explain_document(
    request: Request, document_id: str, payload: RevisionRequest, session=Depends(owned_session)
):
    state = request.app.state
    document = state.sessions.document(session, document_id)
    with state.sessions.lock, session.lock, document.lock:
        state.sessions.alive(session)
        require_confirmation(document, payload.expected_revision)
        result = explain(document, state.references)
        document.explanation = result
        document.state = "explained"
        return result
