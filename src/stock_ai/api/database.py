from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator


class Database:
    """Small SQLite connection manager safe for background-task threads."""

    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    stock_name TEXT,
                    total_score INTEGER,
                    rating TEXT,
                    analysis_json TEXT NOT NULL,
                    report_markdown TEXT NOT NULL,
                    source_generated_at TEXT,
                    artifact_directory TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_reports_code_created
                    ON reports(code, created_at DESC);

                CREATE TABLE IF NOT EXISTS analysis_jobs (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    message TEXT,
                    error TEXT,
                    report_id TEXT,
                    cache_hit INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(report_id) REFERENCES reports(id)
                        ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_code_created
                    ON analysis_jobs(code, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_jobs_status
                    ON analysis_jobs(status);
                """
            )

    def ping(self) -> bool:
        with self.connect() as connection:
            result = connection.execute("SELECT 1").fetchone()
        return bool(result and result[0] == 1)
