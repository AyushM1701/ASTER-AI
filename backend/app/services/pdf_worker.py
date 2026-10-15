"""Isolated, bounded selectable-text PDF parser. No network or disk writes.

This file is executed directly by the local Python runtime with isolated
imports. Output is bounded JSON; parser exceptions never contain source text.
"""

import io
import json
import logging
import os
import sys
import warnings

MAX_BYTES = 20_971_520
MEMORY_BYTES = 536_870_912
# "library" mode reads whole books for My Library: larger bounds, tolerant parsing.
LIBRARY_MAX_BYTES = 262_144_000
LIBRARY_MEMORY_BYTES = 2_147_483_648
_job = None


def bound_memory(memory_bytes=MEMORY_BYTES):
    global _job
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", wintypes.DWORD), ("minimum", ctypes.c_size_t),
                        ("maximum", ctypes.c_size_t), ("active", wintypes.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                        ("scheduling", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.SetInformationJobObject.restype = wintypes.BOOL
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        _job = kernel.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x100 | 0x2000  # Process memory; kill on final job-handle close.
        limits.process_memory = memory_bytes
        if (not _job or not kernel.SetInformationJobObject(_job, 9, ctypes.byref(limits), ctypes.sizeof(limits))
                or not kernel.AssignProcessToJobObject(_job, kernel.GetCurrentProcess())):
            raise RuntimeError("resource_bound_unavailable")
    elif os.name == "posix":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    else:
        raise RuntimeError("resource_bound_unavailable")


def main():
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")
    try:
        library = len(sys.argv) > 3 and sys.argv[3] == "library"
        bound_memory(LIBRARY_MEMORY_BYTES if library else MEMORY_BYTES)
        from pypdf import PdfReader

        page_limit, character_limit = int(sys.argv[1]), int(sys.argv[2])
        max_pages, max_characters, max_bytes = (5000, 20_000_000, LIBRARY_MAX_BYTES) if library else (100, 500000, MAX_BYTES)
        if not 1 <= page_limit <= max_pages or not 1000 <= character_limit <= max_characters:
            raise ValueError("invalid_limits")
        raw = sys.stdin.buffer.read(max_bytes + 1)
        if not raw.startswith(b"%PDF-") or len(raw) > max_bytes:
            raise ValueError("invalid_pdf")
        reader = PdfReader(io.BytesIO(raw), strict=not library)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= page_limit:
            raise ValueError("unsupported_pdf")
        if not library:
            catalogue = reader.trailer["/Root"]
            names = catalogue.get("/Names", {})
            if hasattr(names, "get_object"):
                names = names.get_object()
            if "/OpenAction" in catalogue or "/AA" in catalogue or "/JavaScript" in names or "/EmbeddedFiles" in names:
                raise ValueError("active_content_not_supported")
        # Library mode only extracts text; actions and scripts are never run, and
        # real books routinely carry /OpenAction, so they are not rejected there.
        pages, characters = [], 0
        for page in reader.pages:
            if not library and "/AA" in page:
                raise ValueError("active_content_not_supported")
            try:
                text = (page.extract_text() or "").strip()
            except Exception:
                if not library:
                    raise
                text = ""  # one damaged page should not lose a whole book
            if library:
                text = text.replace("\ufffd", "").replace("\x00", "")
            characters += len(text)
            if characters > character_limit or "\ufffd" in text or "\x00" in text:
                raise ValueError("unreadable_or_oversized_text")
            pages.append(text)
        # Library mode reports image-only pages as empty text; the caller machine-reads them (OCR).
        if not library and sum(character.isalpha() for text in pages for character in text) < 30:
            raise ValueError("selectable_text_unavailable")
        print(json.dumps({"status": "ok", "pages": pages}, ensure_ascii=True), flush=True)
    except Exception:
        print(json.dumps({"status": "unsupported_pdf"}), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
