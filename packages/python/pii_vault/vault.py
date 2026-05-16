import sqlite3
import threading
from typing import Optional


# LocalVault is the canonical name; Vault is kept as a backwards-compatible alias.
class LocalVault:
    """
    Token ↔ value store backed by SQLite.

    Thread-safe: each thread gets its own connection.
    path=":memory:" for ephemeral (tests / dev), a file path for persistence.
    """

    def __init__(self, path: str = ":memory:"):
        self._path  = path
        self._local = threading.local()

    # ── Internal ──────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(self._path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    token       TEXT PRIMARY KEY,
                    value       TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    subject_id  TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            self._local.conn = conn
        return self._local.conn

    # ── Public API ────────────────────────────────────────────────────────

    def store(
        self,
        token:       str,
        value:       str,
        entity_type: str,
        subject_id:  Optional[str] = None,
    ) -> None:
        self._conn().execute(
            "INSERT OR IGNORE INTO tokens (token, value, entity_type, subject_id) VALUES (?, ?, ?, ?)",
            (token, value, entity_type, subject_id),
        )
        self._conn().commit()

    def retrieve(self, token: str) -> Optional[str]:
        row = self._conn().execute(
            "SELECT value FROM tokens WHERE token = ?", (token,)
        ).fetchone()
        return row["value"] if row else None

    def delete_subject(self, subject_id: str) -> int:
        """Delete all tokens linked to a data subject. Returns number of rows deleted."""
        cursor = self._conn().execute(
            "DELETE FROM tokens WHERE subject_id = ?", (subject_id,)
        )
        self._conn().commit()
        return cursor.rowcount

    def list_subject(self, subject_id: str) -> list[dict]:
        rows = self._conn().execute(
            "SELECT token, entity_type, created_at FROM tokens WHERE subject_id = ?",
            (subject_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        return self._conn().execute("SELECT COUNT(*) FROM tokens").fetchone()[0]

Vault = LocalVault  # backwards-compatible alias
