"""Local web presentation and bounded, same-origin bridge to the research API."""

import re
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.app.paths import install_root
from frontend.client import BASE

ROOT = install_root()
WEB = ROOT / "frontend/web"
MAX_BODY = 11 * 1024 * 1024
# My Library accepts whole books; the API enforces the configured limit.
MAX_LIBRARY_BODY = 250 * 1024 * 1024
API_PATH = re.compile(
    r"(?:health/ready|v1/(?:library/(?:status|update|documents(?:/[A-Za-z0-9_-]{1,80})?)|education(?:/export)?|study/(?:topics|curriculum|source-inventory|progress(?:/[A-Za-z0-9_-]{1,80})?)|research/projects(?:/[A-Za-z0-9_-]{1,80}(?:/(?:export|writing))?)?|sessions(?:/current)?|chat|papers(?:/[A-Za-z0-9_-]{1,80}(?:/(?:confirm|reopen))?)?|attachments(?:/[A-Za-z0-9_-]{1,80}/(?:classify|xray))?|documents/[A-Za-z0-9_-]{1,80}(?:/(?:image|confirm|edit|explain|extract|fields/[A-Za-z0-9_-]{1,80}/crop))?))\Z"
)


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(
        base_url=BASE, timeout=httpx.Timeout(330, connect=3), trust_env=False
    ) as client:
        app.state.client = client
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])


@app.middleware("http")
async def browser_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
        "img-src 'self' blob:; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
async def index():
    return FileResponse(WEB / "index.html")


@app.get("/_stcore/health")
async def health():
    # Retain the launcher's UI probe URL across the presentation migration.
    return PlainTextResponse("ok")


@app.get("/sample-prescription")
async def sample():
    return FileResponse(ROOT / "data/samples/synthetic_prescription.png", media_type="image/png")


def error(message, status):
    return JSONResponse({"status": "error", "message": message}, status_code=status)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    if not API_PATH.fullmatch(path):
        return error("This API route is not available in the workspace.", 404)
    # A custom header forces cross-site browser requests to preflight; no CORS
    # permission is granted. Origin is checked as a second independent gate.
    expected_origin = f"{request.url.scheme}://{request.headers['host']}"
    if request.headers.get("x-aster-client") != "1" or request.headers.get(
        "origin", expected_origin
    ) != expected_origin:
        return error("Open this workspace directly to send requests.", 403)
    limit = MAX_LIBRARY_BODY if path == "v1/library/documents" else MAX_BODY
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        return error("Invalid request size.", 400)
    if length < 0 or length > limit:
        return error("File exceeds the upload limit.", 413)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return error("File exceeds the upload limit.", 413)
        chunks.append(chunk)
    headers = {
        key: request.headers[key]
        for key in ("authorization", "content-type", "x-aster-workspace")
        if key in request.headers
    }
    try:
        upstream = await request.app.state.client.request(
            request.method, "/" + path, params=request.query_params, content=b"".join(chunks), headers=headers
        )
    except httpx.HTTPError:
        return error("The local API is unavailable. Refresh connections and retry.", 503)
    return Response(
        upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


app.mount("/assets", StaticFiles(directory=WEB), name="assets")
