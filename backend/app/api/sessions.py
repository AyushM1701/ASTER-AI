from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import owned_session
from backend.app.errors import envelope

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


@router.post("", status_code=201)
def create_session(request: Request):
    state = request.app.state
    token = state.sessions.create()
    return envelope(
        token=token,
        expires_in_seconds=state.settings.session_ttl_seconds,
        hard_lifetime_seconds=state.settings.session_hard_ttl_seconds,
        message="Temporary local session created.",
    )


@router.delete("/current")
def clear_session(request: Request, session=Depends(owned_session)):
    request.app.state.sessions.delete(session)
    return envelope(message="Session and derived state deleted.")
