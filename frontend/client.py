import os
from urllib.parse import urlsplit

import httpx

BASE = os.environ.get("MEDICAL_API_URL", "http://127.0.0.1:8000").rstrip("/")
url = urlsplit(BASE)
if url.hostname not in {"localhost", "127.0.0.1", "::1"} or url.scheme != "http" or url.username:
    raise ValueError("UI API URL must be loopback HTTP")


def call(method, path, token=None, **kwargs):
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        with httpx.Client(timeout=httpx.Timeout(200, connect=3), trust_env=False) as client:
            response = client.request(method, BASE + path, headers=headers, **kwargs)
        body = response.json()
        body["_http_status"] = response.status_code
        return body
    except (httpx.HTTPError, ValueError):
        return {
            "status": "error",
            "message": "The local API is unavailable. Run start.ps1, then refresh status.",
            "_http_status": 503,
        }
