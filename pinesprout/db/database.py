"""SQLite-backed storage for PineSprout run history.

Every meaningful CLI action (lint, format, analyze, generate, upgrade) is
recorded so users can review history with ``pinesprout history``. The
database lives at ``~/.pinesprout/pinesprout.db`` by default, or at the
path given by the ``PINESPROUT_DB`` environment variable — handy for tests.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path.home() / ".pinesprout" / "pinesprout.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    target TEXT,
    created_at TEXT NOT NULL,
    summary TEXT,
    details_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_command ON runs(command);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);
"""


def get_db_path() -> Path:
    override = os.environ.get("PINESPROUT_DB")
    return Path(override) if override else DEFAULT_DB_PATH


@dataclass
class RunRecord:
    id: int
    command: str
    target: str | None
    created_at: str
    summary: str | None
    details: dict[str, Any]


class Database:
    """Thin, explicit wrapper around sqlite3 for PineSprout's history table."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_run(
        self,
        command: str,
        target: str | None = None,
        summary: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO runs (command, target, created_at, summary, details_json) VALUES (?, ?, ?, ?, ?)",
                (
                    command,
                    target,
                    datetime.now(UTC).isoformat(),
                    summary,
                    json.dumps(details or {}),
                ),
            )
            return int(cur.lastrowid) if cur.lastrowid is not None else -1

    def recent_runs(self, limit: int = 20, command: str | None = None) -> list[RunRecord]:
        with self._connect() as conn:
            if command:
                rows = conn.execute(
                    "SELECT * FROM runs WHERE command = ? ORDER BY id DESC LIMIT ?",
                    (command, limit),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

        return [
            RunRecord(
                id=row["id"],
                command=row["command"],
                target=row["target"],
                created_at=row["created_at"],
                summary=row["summary"],
                details=json.loads(row["details_json"] or "{}"),
            )
            for row in rows
        ]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM runs")
