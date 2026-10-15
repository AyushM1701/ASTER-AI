"""My Library: documents the user adds (articles, books, notes) as a local, searchable pack.

Files are parsed on this computer, split into page-anchored passages, embedded
with the same MiniLM encoder as the installed packs, and stored under
``<user_library_path>/library.sqlite`` (FTS5 + float16 vectors). The original
file is not kept; only its SHA-256 (for duplicate detection) and the extracted
passages. PDF pages without a usable text layer (scans, photographed chapters)
are rendered in the isolated rasteriser and machine-read with Tesseract; their
passages are stored with extraction reliability ``pdf_ocr``. ``UserLibrary`` exposes the same search surface as an installed
``Pack`` (bm25 / dense / fetch / vector) so ``LibraryStore`` can rank its
passages together with the reference library and cite them with page numbers.
"""
import hashlib
import html
import io
import json
import logging
import re
import sqlite3
import struct
import subprocess
import threading
import time
import zipfile
from pathlib import Path
from uuid import uuid4

import numpy as np

from backend.app.errors import AppError

logger = logging.getLogger("medical_ai")

CONTENT_CLASS = "user"
EVIDENCE_TYPE = "user_document"
EXTENSIONS = {".pdf": "pdf", ".txt": "text", ".md": "text", ".markdown": "text", ".docx": "docx"}
TARGET_CHARS = 900
MAX_CHARS = 1400
MIN_WORDS = 8
MAX_DOCX_XML = 60_000_000
INJECTION = re.compile(r"\b(?:ignore|override|disregard)\b.{0,60}\b(?:previous|prior|above|system)\b.{0,30}\b(?:instructions?|prompts?)\b"
                       r"|\b(?:reveal|print|exfiltrate)\b.{0,60}\b(?:system prompt|secrets?)\b", re.I)
OCR_MIN_LETTERS = 25  # fewer letters than this on a PDF page: no usable text layer, machine-read it
OCR_BATCH = 4  # pages rendered per rasteriser run
SENTENCE = re.compile(r"(?<=[.!?;:])\s+(?=[\"'(\[]?[A-Z0-9•\-–])")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def kind_for(filename, raw):
    if raw.startswith(b"%PDF-"):
        return "pdf"
    suffix = Path(filename or "").suffix.casefold()
    if suffix == ".docx" and raw.startswith(b"PK"):
        return "docx"
    if EXTENSIONS.get(suffix) == "text":
        return "text"
    raise AppError(415, "unsupported_input", "Add a PDF, Word (.docx), text (.txt) or Markdown (.md) file.")


class Cancelled(Exception):
    """The document was removed while it was being read."""


def letters(text):
    return sum(c.isalpha() for c in text)


# ------------------------------------------------------------------ extraction
def rasterise_pages(raw, numbers, timeout):
    """Render 1-based PDF pages in the isolated rasteriser; returns [(page, PIL image)]."""
    from PIL import Image

    from backend.app.services import workers

    code, stdout, error = workers.run("pdf_raster", raw, "library", ",".join(map(str, numbers)), timeout=timeout,
                                      max_output=OCR_BATCH * 40_000_000)
    if code:
        raise RuntimeError(error or "raster_failed")
    images, offset = [], 0
    while offset + 8 <= len(stdout):
        number, size = struct.unpack_from(">II", stdout, offset)
        offset += 8
        images.append((number, Image.open(io.BytesIO(stdout[offset:offset + size]))))
        offset += size
    return images


def read_scanned_pages(raw, scanned, settings, ocr, progress=None):
    """Machine-read (OCR) page blocks that have no text layer, in place, within the OCR time budget.

    Each block gets ``scan``: "read" (text replaced, ``ocr`` set), "empty", "failed" or "unread" (time limit).
    The budget is checked between pages; each Tesseract run is bounded by ``ocr_timeout_seconds``.
    """
    deadline = time.monotonic() + settings.library_ocr_timeout_seconds
    by_page = {b["page"]: b for b in scanned}
    numbers = list(by_page)
    done = 0
    for start in range(0, len(numbers), OCR_BATCH):
        batch = numbers[start:start + OCR_BATCH]
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            images = rasterise_pages(raw, batch, timeout=max(5, min(remaining, 300)))
        except (OSError, ValueError, RuntimeError, struct.error, subprocess.TimeoutExpired):
            images = []
        for number, image in images:
            if time.monotonic() > deadline:
                break
            if progress:
                progress(done, len(numbers))
            block = by_page[number]
            try:
                text = ocr.extract_printed(image)["raw_text"]
            except AppError:
                block["scan"] = "failed"
            else:
                if letters(text) >= OCR_MIN_LETTERS:
                    block.update(text=text, ocr=True, scan="read")
                else:
                    block["scan"] = "empty"  # blank page, divider or picture
            done += 1
        for number in batch:
            by_page[number].setdefault("scan", "failed" if time.monotonic() <= deadline else "unread")
    for block in scanned:
        block.setdefault("scan", "unread")
    if progress:
        progress(len(numbers), len(numbers))


def plural(count, word):
    return f"{count} {word}" + ("" if count == 1 else "s")


def scan_note(blocks, settings):
    """Plain-language summary of machine-read pages for the document listing (None for ordinary text)."""
    counts = {state: sum(b.get("scan") == state for b in blocks) for state in ("read", "failed", "unread", "missing")}
    if not any(counts.values()):
        return None
    parts = []
    if counts["read"]:
        parts.append(f"{plural(counts['read'], 'scanned page')} machine-read (OCR); check words and numbers against your original.")
    if counts["failed"]:
        parts.append(f"{plural(counts['failed'], 'scanned page')} could not be read.")
    if counts["unread"]:
        parts.append(f"{plural(counts['unread'], 'scanned page')} not read within the "
                     f"{max(1, settings.library_ocr_timeout_seconds // 60)}-minute limit; split the file to add the rest.")
    if counts["missing"]:
        parts.append(f"{plural(counts['missing'], 'scanned page')} skipped: the text reader (Tesseract) is missing. "
                     "Choose Repair in Aster setup.")
    return " ".join(parts)


def extract_pdf(raw, settings, ocr=None, progress=None):
    from backend.app.services import workers

    try:
        code, stdout, _ = workers.run("pdf_text", raw, settings.max_library_pages, settings.max_library_characters, "library",
                                      timeout=settings.library_parse_timeout_seconds,
                                      max_output=4 * settings.max_library_characters + 1_000_000)
        parsed = json.loads(stdout) if not code else {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        parsed = {}
    pages = parsed.get("pages") if parsed.get("status") == "ok" else None
    if not isinstance(pages, list) or not pages or any(not isinstance(text, str) for text in pages):
        raise AppError(422, "quality_rejected", "This PDF could not be read. Use an unencrypted PDF "
                       f"of at most {settings.max_library_pages} pages.")
    blocks = [{"page": number, "heading": None, "text": text} for number, text in enumerate(pages, 1)]
    scanned = [b for b in blocks if letters(b["text"]) < OCR_MIN_LETTERS]
    if not scanned:
        return blocks
    if ocr is None or not ocr.ready():
        if len(scanned) == len(blocks):
            raise AppError(422, "quality_rejected", "This PDF is scanned (it has no selectable text) and the text reader "
                           "(Tesseract) is missing. Choose Repair in Aster setup, then add the file again.")
        for block in scanned:
            block["scan"] = "missing"
        return blocks
    read_scanned_pages(raw, scanned, settings, ocr, progress)
    return blocks


def decode_text(raw):
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def extract_text(raw):
    """Plain text / Markdown: Markdown headings become sections; no page numbers."""
    text = decode_text(raw).replace("\r\n", "\n").replace("\x00", "")
    blocks, heading, lines = [], None, []

    def flush():
        body = "\n".join(lines).strip()
        if body:
            blocks.append({"page": None, "heading": heading, "text": body})
        lines.clear()

    for line in text.split("\n"):
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            flush()
            heading = match[1].strip()[:160]
        else:
            lines.append(line)
    flush()
    return blocks


def extract_docx(raw):
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > MAX_DOCX_XML:
                raise ValueError("oversized")
            xml = archive.read(info).decode("utf-8", "replace")
    except (KeyError, ValueError, zipfile.BadZipFile, OSError):
        raise AppError(422, "quality_rejected", "This Word file could not be read. Save it as .docx (not .doc) and try again.") from None
    blocks, heading, lines = [], None, []
    for paragraph in re.finditer(r"<w:p[ >].*?</w:p>|<w:p/>", xml, re.S):
        body = paragraph[0]
        words = "".join(html.unescape(t) for t in re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", body))
        words = re.sub(r"\s+", " ", words).strip()
        if not words:
            continue
        if re.search(r'<w:pStyle w:val="(?:Heading\d|Title)"', body):
            if lines:
                blocks.append({"page": None, "heading": heading, "text": "\n".join(lines)})
                lines = []
            heading = words[:160]
        else:
            lines.append(words)
    if lines:
        blocks.append({"page": None, "heading": heading, "text": "\n".join(lines)})
    return blocks


CONTROL = re.compile(r"[\ud800-\udfff\x00-\x08\x0b\x0c\x0e-\x1f\x7f�]")


def extract(raw, filename, settings, ocr=None, progress=None):
    kind = kind_for(filename, raw)
    blocks = extract_pdf(raw, settings, ocr, progress) if kind == "pdf" else extract_docx(raw) if kind == "docx" else extract_text(raw)
    for block in blocks:
        # PDF text layers can carry lone surrogates and control bytes the tokenizer rejects.
        block["text"] = CONTROL.sub("", block["text"])
    characters = sum(len(b["text"]) for b in blocks)
    if characters > settings.max_library_characters:
        raise AppError(413, "unsupported_input", "This document has more text than My Library accepts in one file. Split it and add the parts.")
    if sum(letters(b["text"]) for b in blocks) < 30:
        if any(b.get("scan") for b in blocks):
            raise AppError(422, "quality_rejected", "No readable text was found. The scanned pages could not be machine-read; "
                           "try a sharper, straight, well-lit scan.")
        raise AppError(422, "quality_rejected", "No readable text was found in this file.")
    return kind, blocks


# -------------------------------------------------------------------- chunking
def heading_line(line):
    """A short title-like line (PDF running text has no markup)."""
    words = line.split()
    if not 1 <= len(words) <= 12 or len(line) > 90 or line.endswith((".", ",", ";")) or not re.search(r"[A-Za-z]{3}", line):
        return False
    if re.match(r"^(?:fig(?:ure)?|table|plate|chart|box)\.?\s*\d", line, re.I) or re.search(r",\s*\d+(?:[-–]\d+)?$", line):
        return False  # figure/table captions and back-of-book index entries
    if re.match(r"^(?:chapter|section|part|unit)\s+[\dIVXL]+\b", line, re.I) or re.match(r"^\d+(?:\.\d+){0,3}\.?\s+[A-Z]", line):
        return True
    letters = [w for w in words if w[:1].isalpha()]
    return bool(letters) and (line.isupper() or sum(w[:1].isupper() for w in letters) / len(letters) >= 0.75) and len(words) >= 2


def index_like(paragraph):
    """Back-of-book index / contents text ("beam search, 547 beam width, 547") matches every query but teaches nothing."""
    locators = len(re.findall(r"[A-Za-z)],\s*\d{1,4}(?:[-–]\d{1,4})?\b|\.{3,}\s*\d{1,4}\b", paragraph))
    return locators >= 3 and locators > 0.08 * len(paragraph.split())


def clean_page(text):
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join hyphenated line breaks
    return [line.strip() for line in text.split("\n")]


def chunks(blocks):
    """Yield (page, section, text) passages of ~900 characters within one page/section."""
    heading = None
    part = 0
    for block in blocks:
        if block["page"] is None:
            part += 1
            heading = block["heading"] or heading
        paragraphs, current = [], []
        for line in clean_page(block["text"]):
            if not line:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
            elif block["page"] is not None and heading_line(line) and not current:
                heading = re.sub(r"\s+", " ", line)[:160]
            else:
                current.append(line)
        if current:
            paragraphs.append(" ".join(current))
        paragraphs = [p for p in paragraphs if not index_like(p)]
        # Text inside documents is untrusted; drop instruction-like sentences, keep the rest of the page.
        sentences = [s for p in paragraphs for s in SENTENCE.split(re.sub(r"\s+", " ", p).strip()) if s and not INJECTION.search(s)]
        if block["page"] is not None:
            location = f"p. {block['page']}"
        else:
            location = f"part {part}"
        section = f"{heading} · {location}" if heading else location.capitalize()
        buffer = ""
        for sentence in sentences:
            while len(sentence) > MAX_CHARS:  # tables / run-on extraction: hard wrap at a space
                cut = sentence.rfind(" ", 0, MAX_CHARS)
                cut = cut if cut > MAX_CHARS // 2 else MAX_CHARS
                if buffer:
                    yield block["page"], section, buffer
                    buffer = ""
                yield block["page"], section, sentence[:cut].strip()
                sentence = sentence[cut:].strip()
            if buffer and len(buffer) + 1 + len(sentence) > TARGET_CHARS:
                yield block["page"], section, buffer
                buffer = ""
            buffer = (buffer + " " + sentence).strip()
        if buffer:
            yield block["page"], section, buffer


def passages(blocks):
    machine_read = {b["page"] for b in blocks if b.get("ocr")}
    out = []
    for page, section, text in chunks(blocks):
        if len(text.split()) < MIN_WORDS:
            continue
        out.append({"page": page, "section": section, "text": text, "ocr": page in machine_read})
    return out


# ---------------------------------------------------------------------- store
class UserLibrary:
    """Local, writable pack of the user's own documents (Pack-compatible search surface)."""

    pack_id = "my-library"
    edition = "user"

    def __init__(self, root, *, max_documents=300, clock=time.time):
        self.root = Path(root)
        self.path = self.root / "library.sqlite"
        self.max_documents = max_documents
        self.clock = clock
        self.lock = threading.RLock()
        self.db = None
        self.vectors = np.zeros((0, 384), dtype=np.float16)
        self.rowids = np.zeros(0, dtype=np.int64)
        self.position = {}
        self.jobs = {}
        if self.path.exists():
            self._open()
            self.db.execute("UPDATE documents SET status='failed', error='Processing was interrupted when Aster closed. Add the file again.' "
                            "WHERE status='processing'")
            self.db.execute("DELETE FROM units WHERE doc_id IN (SELECT doc_id FROM documents WHERE status='failed')")
            self.db.commit()
            self._reload()

    # ------------------------------------------------------------- storage
    def _open(self):
        if self.db is not None:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, title TEXT, filename TEXT, kind TEXT, sha256 TEXT,
                bytes INTEGER, pages INTEGER, units INTEGER DEFAULT 0, added TEXT, status TEXT, progress REAL DEFAULT 0, error TEXT,
                note TEXT);
            CREATE TABLE IF NOT EXISTS units (rowid INTEGER PRIMARY KEY, unit_id TEXT UNIQUE, doc_id TEXT, title TEXT, section TEXT,
                text TEXT, page INTEGER, kind TEXT, acquired TEXT, vector BLOB);
            CREATE INDEX IF NOT EXISTS units_doc ON units(doc_id);
            CREATE VIRTUAL TABLE IF NOT EXISTS units_fts USING fts5(title, section, text, content='units', content_rowid='rowid',
                tokenize='porter unicode61 remove_diacritics 2');
            CREATE TRIGGER IF NOT EXISTS units_ai AFTER INSERT ON units BEGIN
                INSERT INTO units_fts(rowid, title, section, text) VALUES (new.rowid, new.title, new.section, new.text); END;
            CREATE TRIGGER IF NOT EXISTS units_ad AFTER DELETE ON units BEGIN
                INSERT INTO units_fts(units_fts, rowid, title, section, text) VALUES ('delete', old.rowid, old.title, old.section, old.text); END;
        """)
        if "note" not in {row[1] for row in db.execute("PRAGMA table_info(documents)")}:
            db.execute("ALTER TABLE documents ADD COLUMN note TEXT")  # libraries created before scanned-page support
        self.db = db

    def _reload(self):
        with self.lock:
            rows = self.db.execute("SELECT u.rowid, u.vector FROM units u JOIN documents d ON d.doc_id = u.doc_id "
                                   "WHERE d.status = 'ready' ORDER BY u.rowid").fetchall()
            if rows:
                self.rowids = np.array([r[0] for r in rows], dtype=np.int64)
                self.vectors = np.vstack([np.frombuffer(r[1], dtype=np.float16) for r in rows])
            else:
                self.rowids = np.zeros(0, dtype=np.int64)
                self.vectors = np.zeros((0, 384), dtype=np.float16)
            self.position = {int(r): i for i, r in enumerate(self.rowids)}

    def close(self):
        with self.lock:
            if self.db is not None:
                self.db.close()
                self.db = None

    @property
    def units(self):
        return len(self.rowids)

    # ------------------------------------------------------ Pack interface
    def bm25(self, match, limit=80, classes=None):
        if not match or not self.units or (classes and CONTENT_CLASS not in classes):
            return []
        with self.lock:
            try:
                rows = self.db.execute(
                    "SELECT units_fts.rowid, bm25(units_fts, 3.0, 1.5, 1.0) AS s FROM units_fts WHERE units_fts MATCH ? "
                    "ORDER BY s LIMIT ?", (match, limit * 2)).fetchall()
            except sqlite3.OperationalError:
                return []
        return [(rowid, -score) for rowid, score in rows if rowid in self.position][:limit]

    def rows_with_class(self, rowids, classes):
        return set(rowids) if CONTENT_CLASS in classes else set()

    def dense(self, vector, limit=80):
        with self.lock:
            matrix, rowids = self.vectors, self.rowids
        if not len(rowids):
            return []
        scores = np.asarray(matrix @ vector.astype(np.float16), dtype=np.float32)
        top = np.argsort(-scores)[:limit] if len(scores) <= limit else np.argpartition(-scores, limit)[:limit]
        top = top[np.argsort(-scores[top])]
        return [(int(rowids[i]), float(scores[i])) for i in top]

    def vector(self, rowid):
        with self.lock:
            return np.asarray(self.vectors[self.position[rowid]], dtype=np.float32)

    def fetch(self, rowids):
        from backend.app.services.library import Hit

        if not rowids:
            return {}
        marks = ",".join("?" * len(rowids))
        with self.lock:
            rows = self.db.execute(f"SELECT rowid, unit_id, doc_id, title, section, text, kind, acquired FROM units "
                                   f"WHERE rowid IN ({marks})", list(rowids)).fetchall()
        return {row[0]: Hit(row[1], row[2], row[3], row[4], row[5], CONTENT_CLASS, EVIDENCE_TYPE, "user_provided", "",
                            "My Library", "", "", row[7] or "", "full_text", "user_provided", "text", row[6] or "",
                            pack_id=self.pack_id, edition=self.edition) for row in rows}

    # --------------------------------------------------------- documents
    def _document(self, row):
        keys = ("doc_id", "title", "filename", "kind", "sha256", "bytes", "pages", "units", "added", "status", "progress", "error", "note")
        return dict(zip(keys, row, strict=True))

    def documents(self):
        with self.lock:
            if self.db is None:
                return []
            rows = self.db.execute("SELECT doc_id, title, filename, kind, sha256, bytes, pages, units, added, status, progress, error, note "
                                   "FROM documents ORDER BY added DESC").fetchall()
        return [self._document(r) for r in rows]

    def document(self, doc_id):
        with self.lock:
            if self.db is None:
                return None
            row = self.db.execute("SELECT doc_id, title, filename, kind, sha256, bytes, pages, units, added, status, progress, error, note "
                                  "FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        return self._document(row) if row else None

    def summary(self):
        documents = self.documents()
        return {"documents": sum(d["status"] == "ready" for d in documents), "units": self.units,
                "processing": sum(d["status"] == "processing" for d in documents)}

    def submit(self, raw, filename, title, settings, encoder_source, on_ready=None, ocr=None):
        """Register a document and index it in the background. Returns its record.

        ``ocr`` (an ``OCRAdapter``) machine-reads PDF pages that have no text layer.
        """
        digest = sha256(raw)
        kind_for(filename, raw)  # fail fast on an unsupported type, before any record exists
        title = re.sub(r"\s+", " ", title or "").strip()[:200] or Path(filename or "Untitled").stem[:200] or "Untitled"
        with self.lock:
            self._open()
            duplicate = self.db.execute("SELECT title, status FROM documents WHERE sha256 = ? AND status != 'failed'", (digest,)).fetchone()
            if duplicate:
                raise AppError(409, "unsupported_input", f"This file is already in My Library as “{duplicate[0]}”.")
            count = self.db.execute("SELECT COUNT(*) FROM documents WHERE status != 'failed'").fetchone()[0]
            if count >= self.max_documents:
                raise AppError(409, "unsupported_input", f"My Library holds up to {self.max_documents} documents. Remove some before adding more.")
            doc_id = "mylib_" + uuid4().hex[:16]
            added = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.clock()))
            self.db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, NULL, 0, ?, 'processing', 0, NULL, NULL)",
                            (doc_id, title, Path(filename or "").name[:200], None, digest, len(raw), added))
            self.db.execute("DELETE FROM documents WHERE sha256 = ? AND status = 'failed'", (digest,))
            self.db.commit()
        worker = threading.Thread(target=self._ingest, args=(doc_id, raw, filename, title, added, settings, encoder_source, on_ready, ocr),
                                  name="my-library-" + doc_id, daemon=True)
        self.jobs[doc_id] = worker
        worker.start()
        return self.document(doc_id)

    def _progress(self, doc_id, value, **fields):
        with self.lock:
            if self.db is None:
                return
            sets = ", ".join(["progress = ?", *[f"{k} = ?" for k in fields]])
            self.db.execute(f"UPDATE documents SET {sets} WHERE doc_id = ?", (value, *fields.values(), doc_id))
            self.db.commit()

    def _reading(self, doc_id, done, total):
        """OCR progress: the first 60% of the bar, one step per scanned page."""
        if self.document(doc_id) is None:
            raise Cancelled
        self._progress(doc_id, 0.6 * done / max(total, 1), note=f"Machine-reading scanned pages · {min(done + 1, total)} of {total}")

    def _ingest(self, doc_id, raw, filename, title, added, settings, encoder_source, on_ready, ocr=None):
        from aster_library.index import embedding_text

        try:
            kind, blocks = extract(raw, filename, settings, ocr, lambda done, total: self._reading(doc_id, done, total))
            del raw
            found = passages(blocks)
            if not found:
                raise AppError(422, "quality_rejected", "No usable passages were found in this file.")
            pages = max((b["page"] or 0) for b in blocks) or None
            begin = 0.6 if any(b.get("scan") for b in blocks) else 0.1
            self._progress(doc_id, begin, kind=kind, pages=pages, note=scan_note(blocks, settings))
            encoder = encoder_source()
            vectors = []
            for start in range(0, len(found), 64):
                if self.document(doc_id) is None:
                    return  # removed while processing
                batch = found[start:start + 64]
                vectors.append(encoder.encode([embedding_text({"title": title, **p}) for p in batch]))
                self._progress(doc_id, begin + (0.95 - begin) * min(1.0, (start + len(batch)) / len(found)))
            matrix = np.vstack(vectors).astype(np.float16)
            with self.lock:
                if self.document(doc_id) is None:
                    return
                self.db.executemany(
                    "INSERT INTO units (unit_id, doc_id, title, section, text, page, kind, acquired, vector) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(f"{doc_id}_{i:05d}", doc_id, title, p["section"], p["text"], p["page"],
                      "pdf_ocr" if p["ocr"] else kind + "_text", added[:10], matrix[i].tobytes())
                     for i, p in enumerate(found)])
                self.db.execute("UPDATE documents SET status = 'ready', progress = 1, units = ? WHERE doc_id = ?", (len(found), doc_id))
                self.db.commit()
                self._reload()
            logger.info("my-library: indexed %s (%d passages)", doc_id, len(found))
            if on_ready:
                on_ready()
        except Cancelled:
            return
        except AppError as exc:
            self._fail(doc_id, exc.message)
        except Exception as exc:  # never leave a document stuck in "processing"
            logger.exception("my-library: indexing failed")
            self._fail(doc_id, f"Indexing failed ({type(exc).__name__}). Try again or add a different copy of the file.")
        finally:
            self.jobs.pop(doc_id, None)

    def _fail(self, doc_id, message):
        with self.lock:
            if self.db is None:
                return
            self.db.execute("DELETE FROM units WHERE doc_id = ?", (doc_id,))
            self.db.execute("UPDATE documents SET status = 'failed', error = ?, note = NULL WHERE doc_id = ?", (message[:400], doc_id))
            self.db.commit()

    def delete(self, doc_id):
        with self.lock:
            if self.document(doc_id) is None:
                return False
            self.db.execute("DELETE FROM units WHERE doc_id = ?", (doc_id,))
            self.db.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            self.db.commit()
            self._reload()
        return True

    def wait(self, doc_id, timeout=None):
        """Test helper: block until a background indexing job finishes."""
        job = self.jobs.get(doc_id)
        if job is not None:
            job.join(timeout)
        return self.document(doc_id)
