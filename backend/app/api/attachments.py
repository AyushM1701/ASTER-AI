from fastapi import APIRouter, Depends, File, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.app.api.dependencies import owned_session
from backend.app.api.documents import upload
from backend.app.errors import AppError, envelope
from backend.app.schemas import XrayRequest
from backend.app.services.documents import parse_fields

router = APIRouter(prefix="/v1/attachments", tags=["chat attachments"])


def classify_attachment(request, document_id, session):
    state = request.app.state
    document = state.sessions.document(session, document_id)
    with document.lock:
        if document.state == "classifying":
            raise AppError(409, "busy", "This attachment is already being classified.")
        if document.classification:
            if document.classification["kind"] == "prescription":
                result = document.response()
                result.update(
                    classification=document.classification,
                    classification_model=state.settings.vision_model,
                )
                return result
            return document.attachment_response
        if document.state != "uploaded":
            raise AppError(
                409,
                "busy",
                "This document is already in another workflow. Attach a new image to classify it.",
            )
        document.state = "classifying"
    try:
        with state.compute.enter():
            classification = state.ollama.classify(document.image).model_dump()
            ocr = (
                state.ocr.extract(document.image)
                if classification["kind"] == "prescription"
                else {}
            )
        imaging_result = None
        if classification["kind"] == "xray":
            asset = next(
                (a for a in state.xray.assets.values() if a["sha256"] == document.source_sha256),
                None,
            )
            if asset:
                try:
                    imaging_result = state.xray.analyze(XrayRequest(asset_id=asset["asset_id"]))
                except AppError as exc:
                    imaging_result = envelope(exc.status, "xray", exc.message)
                except (ValueError, RuntimeError, OSError, KeyError):
                    imaging_result = envelope(
                        "error",
                        "xray",
                        "Research inference failed validation. Check the imaging model setup; no scores were displayed.",
                    )
            else:
                imaging_result = envelope(
                    "unsupported_input",
                    "xray",
                    "I identified an X-ray image. Research scoring requires a reviewed adult AP/PA chest image and verified weights. This upload has no reviewed registration, so I cannot provide scores or a diagnosis.",
                )
        with state.sessions.lock, session.lock, document.lock:
            state.sessions.alive(session)
            document.classification = classification
            document.confirmed_revision = None
            document.explanation = None
            document.revision += 1
            document.intent = classification["kind"]
            document.ocr = ocr
            document.fields = (
                parse_fields(
                    ocr.get("raw_text", ""),
                    "prescription",
                    provenance=ocr.get("engine", "tesseract"),
                )
                if document.intent == "prescription"
                else []
            )
            document.state = (
                "needs_confirmation" if document.intent == "prescription" else "classified"
            )
            if document.intent == "prescription":
                result = document.response()
                result["message"] = (
                    "I identified a prescription document and extracted its text. Compare and confirm it below before I explain it."
                )
            else:
                result = envelope(
                    "ok" if document.intent == "xray" else "unsupported_input",
                    "xray" if document.intent == "xray" else "attachment",
                    "I identified an X-ray image."
                    if document.intent == "xray"
                    else "I could not route this image to a prescription or X-ray workflow. Attach a clearer prescription or X-ray image.",
                    document_id=document.id,
                    fields=[],
                    revision=document.revision,
                    imaging_result=imaging_result,
                )
            result["classification"] = classification
            result["classification_model"] = state.settings.vision_model
            result["warnings"].append(
                "Attachment classification is an experimental routing decision, not clinical validation."
            )
            document.attachment_response = result
            return result
    except AppError as exc:
        with state.sessions.lock, session.lock, document.lock:
            state.sessions.alive(session)
            document.state = "uploaded"
        return envelope(
            exc.status,
            "attachment",
            exc.message,
            document_id=document_id,
            fields=[],
            classification=None,
        )
    finally:
        with document.lock:
            if document.state == "classifying":
                document.state = "uploaded"


@router.post("", status_code=201)
async def attach(request: Request, file: UploadFile = File(...), session=Depends(owned_session)):
    result = await upload(request, file, "document", session)
    return await run_in_threadpool(classify_attachment, request, result["document_id"], session)


@router.post("/{document_id}/classify")
def retry(request: Request, document_id: str, session=Depends(owned_session)):
    return classify_attachment(request, document_id, session)
