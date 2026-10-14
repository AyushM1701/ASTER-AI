import asyncio
import importlib.util
import logging
import sys
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from backend.app.adapters.ocr import OCRAdapter
from backend.app.adapters.ollama import OllamaAdapter
from backend.app.api import attachments, chat, documents, education, papers, sessions, xray
from backend.app.config import Settings
from backend.app.errors import REQUEST_ID, AppError, envelope
from backend.app.services.answers import AnswerService
from backend.app.services.compute import ComputeGate
from backend.app.services.research_workspace import LiteratureSearch
from backend.app.services.retrieval import ReferenceStore
from backend.app.services.secondary_references import SecondaryReferenceStore
from backend.app.services.sessions import SessionStore
from backend.app.services.teaching import TeachingStore
from backend.app.services.workspaces import WorkspaceStore
from backend.app.services.xray import XrayService

logger = logging.getLogger("medical_ai")


def create_app(settings=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings
        app.state.sessions = SessionStore(settings)
        app.state.workspaces = WorkspaceStore(settings.workspace_path)
        app.state.literature = LiteratureSearch()
        app.state.compute = ComputeGate(settings)
        app.state.references = ReferenceStore(settings)
        app.state.secondary_references = SecondaryReferenceStore(settings)
        app.state.teaching = TeachingStore(settings)
        app.state.ollama = OllamaAdapter(settings)
        app.state.ocr = OCRAdapter(settings, vision=app.state.ollama)
        app.state.answers = AnswerService(
            settings,
            app.state.references,
            app.state.ollama,
            app.state.compute,
            secondary=app.state.secondary_references,
            teaching=app.state.teaching,
        )
        app.state.xray = XrayService(settings, app.state.compute, app.state.references)

        async def cleanup():
            while True:
                await asyncio.sleep(min(30, settings.session_ttl_seconds))
                await run_in_threadpool(app.state.sessions.purge)

        task = asyncio.create_task(cleanup())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        app.state.ollama.close()
        app.state.references.close()
        app.state.teaching.close()
        for session in list(app.state.sessions.sessions.values()):
            app.state.sessions.delete(session)

    app = FastAPI(title="Aster Medical Research", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def request_metadata(request, call_next):
        request_id = str(uuid4())
        token = REQUEST_ID.set(request_id)
        started = time.monotonic()
        try:
            limit = (
                settings.max_upload_bytes + 65536
                if request.url.path in {"/v1/documents", "/v1/attachments", "/v1/papers"}
                else 65536
            )
            declared = request.headers.get("content-length")
            if declared and (not declared.isdigit() or int(declared) > limit):
                response = JSONResponse(
                    envelope("unsupported_input", message="Request body exceeds the size limit."),
                    status_code=413,
                )
            else:
                if request.method in {"POST", "PUT", "PATCH"}:
                    original_receive = request._receive
                    consumed = 0

                    async def limited_receive():
                        nonlocal consumed
                        message = await original_receive()
                        consumed += len(message.get("body", b""))
                        if consumed > limit:
                            raise AppError(
                                413, "unsupported_input", "Request body exceeds the size limit."
                            )
                        return message

                    request._receive = limited_receive
                try:
                    response = await call_next(request)
                except AppError as exc:
                    response = JSONResponse(
                        envelope(exc.status, message=exc.message), status_code=exc.code
                    )
                except Exception:
                    response = JSONResponse(
                        envelope("error", message="Operation failed. Retry or check local setup."),
                        status_code=500,
                    )
            response.headers["X-Request-ID"] = request_id
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            route = request.scope.get("route")
            logger.info(
                "route=%s status=%s latency_ms=%d request_id=%s",
                getattr(route, "path", "unmatched"),
                response.status_code,
                int((time.monotonic() - started) * 1000),
                request_id,
            )
            return response
        finally:
            REQUEST_ID.reset(token)

    @app.exception_handler(AppError)
    async def known_error(request, exc):
        from backend.app.services.output_validation import finalize

        return JSONResponse(
            finalize("", envelope(exc.status, message=exc.message, **({"transport_error": {"upstream_status_code": exc.code}} if exc.code in {502, 503} else {}))),
            status_code=exc.code,
            headers={"Retry-After": "5"} if exc.status == "busy" else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            envelope("unsupported_input", message="Request fields are missing or invalid."),
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            envelope("unsupported_input", message="Request could not be accepted."),
            status_code=exc.status_code,
        )

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        refs = app.state.references
        ollama = (
            app.state.ollama.ready()
            if settings.answer_mode == "ollama"
            else {"available": None, "required": False}
        )
        available = bool(refs.records) and (settings.answer_mode != "ollama" or ollama["available"])
        if settings.enable_teaching and app.state.teaching.error:
            available = False
        return JSONResponse(
            {
                "status": "ready" if available else "unavailable",
                "answer_mode": settings.answer_mode,
                "references": refs.manifest(),
                "secondary_references": app.state.secondary_references.manifest(),
                "teaching": app.state.teaching.manifest(),
                "patient_information": app.state.answers.patient.manifest(),
                "ollama": ollama,
                "ocr": {
                    "available": app.state.ocr.ready(),
                    "engine": "tesseract",
                    "handwriting_enabled": settings.enable_handwriting_ocr,
                    "handwriting_model": settings.vision_model
                    if settings.enable_handwriting_ocr
                    else None,
                },
                "attachment_classifier": app.state.ollama.ready(settings.vision_model),
                "general_chat": settings.enable_general_chat and settings.answer_mode == "ollama",
                "provisional_education": {"enabled": settings.enable_educational_model_knowledge and settings.answer_mode == "ollama", "source_verified": False, "counts_toward_source_coverage": False},
                "xray": app.state.xray.health(),
                "network": "local_inference_optional_public_literature_search" if settings.enable_research_search else "local_only",
                "research_search": {"enabled": settings.enable_research_search, "provider": "Europe PMC", "public_query_confirmation_required": True},
                "private_papers": {"enabled": not getattr(sys, "frozen", False) and importlib.util.find_spec("pypdf") is not None, "temporary": True,
                                   "confirmation_required": True, "analysis": "exact_excerpts_partial_appraisal",
                                   "max_pages": settings.max_paper_pages},
                "release": getattr(app.state, "release_info", None),
            },
            status_code=200 if available else 503,
        )

    for router in (sessions.router, chat.router, documents.router, xray.router, attachments.router, education.router, papers.router):
        app.include_router(router)
    return app


app = create_app()
