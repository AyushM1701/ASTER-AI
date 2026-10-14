from fastapi import Request

from backend.app.errors import AppError


def owned_session(request: Request):
    value = request.headers.get("Authorization", "")
    if not value.startswith("Bearer ") or len(value) > 200:
        raise AppError(401, "error", "Start a session before using the workspace.")
    return request.app.state.sessions.get(value[7:])
