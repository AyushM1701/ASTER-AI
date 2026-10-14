from contextvars import ContextVar
from uuid import uuid4

REQUEST_ID = ContextVar("request_id", default="")
POLICY_VERSION = "research-policy-v1"
SCOPE = (
    "For education and local research. This app cannot diagnose, prescribe, "
    "calculate a personal dose, or confirm that an X-ray is normal."
)


def envelope(status="ok", route="system", message="", **data):
    return {
        "request_id": REQUEST_ID.get() or str(uuid4()),
        "route": route,
        "status": status,
        "message": message,
        "policy_version": POLICY_VERSION,
        "warnings": [],
        "claims": [],
        "citations": [],
        "limitations": [SCOPE],
        **data,
    }


class AppError(Exception):
    def __init__(self, code, status, message, *, reason_code=None):
        self.code, self.status, self.message = code, status, message
        self.reason_code = reason_code
