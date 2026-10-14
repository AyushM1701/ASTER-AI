"""Explicitly saved educational records; never temporary patient documents."""

import json
import sqlite3
from pathlib import Path
from threading import RLock


class WorkspaceStore:
    def __init__(self, path: Path, max_records=100):
        self.path = Path(path)
        self.max_records = max_records
        self.lock = RLock()

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS records (owner TEXT, kind TEXT, id TEXT, body TEXT, PRIMARY KEY(owner, kind, id))"
        )
        return conn

    def list(self, owner, kind):
        with self.lock:
            if not self.path.exists():
                return []
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT body FROM records WHERE owner=? AND kind=? ORDER BY id", (owner, kind)
                ).fetchall()
            return [json.loads(row[0]) for row in rows]

    def get(self, owner, kind, identity):
        with self.lock:
            if not self.path.exists():
                return None
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT body FROM records WHERE owner=? AND kind=? AND id=?",
                    (owner, kind, identity),
                ).fetchone()
            return json.loads(row[0]) if row else None

    def put(self, owner, kind, identity, value):
        body = json.dumps(value, ensure_ascii=False)
        if kind not in {"study", "research"} or len(body.encode()) > 2_000_000:
            raise ValueError("Unsupported or oversized educational record")
        with self.lock, self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM records WHERE owner=? AND kind=?", (owner, kind)
            ).fetchone()[0]
            exists = conn.execute(
                "SELECT 1 FROM records WHERE owner=? AND kind=? AND id=?", (owner, kind, identity)
            ).fetchone()
            if count >= self.max_records and not exists:
                raise ValueError("Local workspace is full; export or delete old records")
            conn.execute(
                "INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?)", (owner, kind, identity, body)
            )

    def delete(self, owner, kind, identity):
        with self.lock:
            if not self.path.exists():
                return False
            with self._connect() as conn:
                return (
                    conn.execute(
                        "DELETE FROM records WHERE owner=? AND kind=? AND id=?",
                        (owner, kind, identity),
                    ).rowcount
                    > 0
                )

    def clear(self, owner):
        with self.lock:
            if self.path.exists():
                with self._connect() as conn:
                    conn.execute("DELETE FROM records WHERE owner=?", (owner,))
