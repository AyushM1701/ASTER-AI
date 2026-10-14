import hashlib
import secrets
import threading
import time
from dataclasses import dataclass, field

from backend.app.errors import AppError


@dataclass
class Session:
    key: str
    created: float
    touched: float
    documents: dict = field(default_factory=dict)
    papers: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)
    byte_count: int = 0
    pending_uploads: dict = field(default_factory=dict)
    viva: dict = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)


class SessionStore:
    def __init__(self, settings, clock=time.monotonic):
        self.settings, self.clock = settings, clock
        self.sessions = {}
        self.lock = threading.RLock()

    @staticmethod
    def key(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def expired(self, session):
        now = self.clock()
        return (
            now - session.touched >= self.settings.session_ttl_seconds
            or now - session.created >= self.settings.session_hard_ttl_seconds
        )

    def purge(self):
        with self.lock:
            for key, session in list(self.sessions.items()):
                if self.expired(session):
                    self.sessions.pop(key, None)
                    # A worker may still hold a reference. Wipe before releasing it.
                    with session.lock:
                        session.documents.clear()
                        for paper in session.papers.values():
                            paper.wipe()
                        session.papers.clear()
                        session.results.clear()
                        session.messages.clear()
                        session.byte_count = 0
                        session.pending_uploads.clear()
                        session.viva.clear()

    def create(self):
        self.purge()
        with self.lock:
            if len(self.sessions) >= self.settings.max_active_sessions:
                raise AppError(429, "busy", "Session capacity reached. Clear an existing session.")
            token = secrets.token_urlsafe(32)
            key = self.key(token)
            now = self.clock()
            self.sessions[key] = Session(key, now, now)
            return token

    def get(self, token, touch=True):
        self.purge()
        with self.lock:
            session = self.sessions.get(self.key(token))
            if session is None:
                raise AppError(401, "error", "Session expired or unavailable. Start a new session.")
            if touch:
                session.touched = self.clock()
            return session

    def alive(self, session):
        with self.lock:
            if self.sessions.get(session.key) is not session or self.expired(session):
                raise AppError(401, "error", "Session expired or was cleared during processing.")

    def delete(self, session):
        with self.lock:
            self.sessions.pop(session.key, None)
        with session.lock:
            session.documents.clear()
            for paper in session.papers.values():
                paper.wipe()
            session.papers.clear()
            session.results.clear()
            session.messages.clear()
            session.byte_count = 0
            session.pending_uploads.clear()
            session.viva.clear()

    def reserve_upload(self, session, upload_id, cost=0):
        with self.lock, session.lock:
            self.alive(session)
            pending_count = len(session.pending_uploads) + (
                upload_id not in session.pending_uploads
            )
            others = sum(v for key, v in session.pending_uploads.items() if key != upload_id)
            if (
                len(session.documents) + len(session.papers) + pending_count > self.settings.max_documents_per_session
                or session.byte_count + others + cost > self.settings.max_session_bytes
            ):
                raise AppError(
                    429, "busy", "Session upload limit reached. Clear the session to continue."
                )
            session.pending_uploads[upload_id] = cost

    def release_upload(self, session, upload_id):
        with session.lock:
            session.pending_uploads.pop(upload_id, None)

    @staticmethod
    def document(session, document_id):
        with session.lock:
            document = session.documents.get(document_id)
            if document is None:
                raise AppError(404, "unsupported_input", "Document not found in this session.")
            return document
