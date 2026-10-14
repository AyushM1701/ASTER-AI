from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import owned_session
from backend.app.errors import AppError, envelope
from backend.app.schemas import XrayRequest

router = APIRouter(prefix="/v1/xray", tags=["research imaging"])


@router.get("/assets")
def xray_assets(request: Request, session=Depends(owned_session)):
    service = request.app.state.xray
    return envelope(assets=service.list_assets(), setup=service.health())


@router.post("/analyze")
def xray_analyze(request: Request, payload: XrayRequest, session=Depends(owned_session)):
    state = request.app.state
    result = state.xray.analyze(payload)
    with state.sessions.lock, session.lock:
        state.sessions.alive(session)
        if result["status"] == "ok":
            result_id = "xray_" + uuid4().hex
            result["result_id"] = result_id
            session.results[result_id] = result
            if len(session.results) > 10:
                session.results.pop(next(iter(session.results)))
    return result


@router.get("/results/{result_id}")
def xray_result(request: Request, result_id: str, session=Depends(owned_session)):
    if result_id not in session.results:
        raise AppError(404, "unsupported_input", "Result not available in this session.")
    return session.results[result_id]
