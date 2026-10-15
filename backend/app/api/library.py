"""Reference library status and opt-in updates.

Updates are only checked when the user asks. The request downloads a signed
manifest and signed, hash-pinned packs from the release host; no questions,
documents or images are sent. New packs are activated only after signature,
hash and quality checks pass; the previous selection stays as last-known-good.
"""
import threading

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from backend.app.errors import AppError, envelope

router = APIRouter(prefix="/v1/library", tags=["library"])
UPDATE_URL = "https://github.com/AyushM1701/ASTER-AI/releases/latest/download/library-latest.json"
_update_lock = threading.Lock()


class UpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    network_consent: bool
    include_noncommercial: bool = True


@router.get("/status")
def status(request: Request):
    grounded = getattr(request.app.state, "grounded", None)
    if grounded is None:
        raise AppError(404, "unsupported_input", "The reference library is not used in this configuration.")
    return envelope(library=grounded.library.manifest(), update_source=UPDATE_URL,
                    message="Updates are checked only when you ask. No questions or documents are sent.")


def fetch_manifest(url):
    import httpx

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        raw = client.get(url).raise_for_status().content
        signature = client.get(url + ".sig").raise_for_status().text
    return raw, signature


@router.post("/update")
def update(request: Request, payload: UpdateRequest):
    state = request.app.state
    grounded = getattr(state, "grounded", None)
    if grounded is None:
        raise AppError(404, "unsupported_input", "The reference library is not used in this configuration.")
    if not payload.network_consent:
        raise AppError(422, "unsupported_input", "Confirm that Aster may contact the release server to check for updates.")
    if not _update_lock.acquire(blocking=False):
        raise AppError(409, "busy", "A library update is already running.")
    try:
        from aster_library import install
        from aster_release.setup_engine import fetch

        url = getattr(state.settings, "library_update_url", None) or UPDATE_URL
        # A loopback update source (tests / LAN mirror) is accepted only when it is the configured URL.
        mirror = url.rsplit("/", 1)[0] if url.startswith(("http://127.0.0.1", "http://localhost")) else None
        try:
            raw, signature = fetch_manifest(url)
            manifest = install.verify_update_manifest(raw, signature)
        except install.InstallError as exc:
            raise AppError(502, "error", str(exc)) from exc
        except Exception as exc:
            raise AppError(503, "error", "The update server could not be reached. Aster keeps working with the installed library.") from exc
        current = {p["pack_id"] for p in grounded.library.manifest()["packs"]}
        editions = ("core", "nc") if payload.include_noncommercial else ("core",)
        wanted = [p["pack_id"] for p in manifest["packs"] if p["edition"] in editions]
        if set(wanted) == current:
            return envelope(message="The installed library is already the latest version.", library=grounded.library.manifest())

        def downloader(link, dest, sha256, size):
            fetch([link], dest, sha256, size, mirror=mirror)

        root = state.settings.library_root
        try:
            activated = install.apply_update(root, manifest, downloader, editions=editions)
        except install.InstallError as exc:
            raise AppError(422, "error", "The update failed its checks and was not installed: " + str(exc)) from exc
        from backend.app.services.library import LibraryStore

        refreshed = LibraryStore(root, encoder_path=state.settings.embedding_path,
                                 reranker_path=state.settings.rerank_model_path)
        if refreshed.status != "ready":
            install.rollback(root)
            raise AppError(500, "error", "The updated library could not be loaded and the previous library was restored.")
        old, grounded.library = grounded.library, refreshed
        grounded.verifier.set_entities(refreshed.generic_names())
        old.close()
        return envelope(message="Library updated to " + ", ".join(activated) + ".", library=refreshed.manifest())
    finally:
        _update_lock.release()
