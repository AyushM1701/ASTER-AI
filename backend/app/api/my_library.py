"""My Library: add, list and remove the user's own reference documents.

Files are read and indexed on this computer; nothing is sent anywhere. The
original file is discarded after indexing (only extracted passages and a hash
are kept) and is searched alongside the installed library in later answers.
"""
from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from backend.app.api.dependencies import owned_session
from backend.app.errors import AppError, envelope

router = APIRouter(prefix="/v1/library/documents", tags=["my-library"])
NOTICE = ("Documents in My Library stay on this computer and are used to answer your later questions, with page "
          "citations. Aster has not reviewed them, so answers are only as reliable as the documents you add.")


def user_library(request):
    grounded = getattr(request.app.state, "grounded", None)
    if grounded is None or grounded.library.user is None:
        raise AppError(404, "unsupported_input", "My Library needs the reference library engine, which is not enabled in this configuration.")
    return grounded.library


def listing(library, settings, message=""):
    return envelope("ok", "my_library", message or NOTICE, documents=library.user.documents(), summary=library.user.summary(),
                    limits={"max_bytes": settings.max_library_upload_bytes, "max_pages": settings.max_library_pages,
                            "max_documents": settings.max_library_documents, "formats": ["pdf", "docx", "txt", "md"]})


@router.get("")
def documents(request: Request, session=Depends(owned_session)):
    return listing(user_library(request), request.app.state.settings)


@router.post("", status_code=202)
async def add(request: Request, filename: str = "", title: str = "", rights_confirmed: bool = False, session=Depends(owned_session)):
    state = request.app.state
    library = user_library(request)
    if not rights_confirmed:
        raise AppError(422, "unsupported_input", "Confirm that you may keep a personal study copy of this document.")
    limit = state.settings.max_library_upload_bytes
    try:
        declared = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared = 0
    if declared > limit:
        raise AppError(413, "unsupported_input", f"Files for My Library can be up to {limit // 1_048_576} MB.")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > limit:
            raise AppError(413, "unsupported_input", f"Files for My Library can be up to {limit // 1_048_576} MB.")
    if not raw:
        raise AppError(422, "unsupported_input", "The file is empty.")
    # Hashing a 100 MB book and the duplicate check would otherwise stall every other request.
    document = await run_in_threadpool(library.user.submit, bytes(raw), filename[:255], title[:200], state.settings,
                                       lambda: library.encoder, ocr=getattr(state, "ocr", None))
    return envelope("ok", "my_library", "Adding “" + document["title"] + "” to My Library. Large books and scanned pages "
                    "(which are machine-read) can take a few minutes.", document=document)


@router.get("/{doc_id}")
def document(request: Request, doc_id: str, session=Depends(owned_session)):
    found = user_library(request).user.document(doc_id)
    if found is None:
        raise AppError(404, "unsupported_input", "This document is not in My Library.")
    return envelope("ok", "my_library", "", document=found)


@router.delete("/{doc_id}")
def remove(request: Request, doc_id: str, session=Depends(owned_session)):
    library = user_library(request)
    if not library.user.delete(doc_id):
        raise AppError(404, "unsupported_input", "This document is not in My Library.")
    return listing(library, request.app.state.settings, "Removed from My Library. Its passages will no longer be used in answers.")
