from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from stock_ai.api.database import Database


ACTIVE_STATUSES = (
    "queued",
    "fetching_data",
    "preparing_context",
    "analyzing",
    "validating",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row_dict(row) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class JobReportRepository:
    """Persist analysis jobs and reports without an external database server."""

    JOB_UPDATE_FIELDS = {
        "status",
        "progress",
        "message",
        "error",
        "report_id",
        "cache_hit",
    }

    def __init__(self, database: Database):
        self.database = database

    def initialize(self) -> None:
        self.database.initialize()

    def ping(self) -> bool:
        return self.database.ping()

    def create_job(
        self,
        code: str,
        *,
        status: str = "queued",
        progress: int = 0,
        message: str = "任务已创建，等待执行。",
        report_id: str | None = None,
        cache_hit: bool = False,
    ) -> dict[str, Any]:
        job_id = uuid4().hex
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_jobs (
                    id, code, status, progress, message, error, report_id,
                    cache_hit, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    code,
                    status,
                    max(0, min(100, int(progress))),
                    message,
                    report_id,
                    int(cache_hit),
                    now,
                    now,
                ),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM analysis_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        result = _row_dict(row)
        if result is not None:
            result["cache_hit"] = bool(result.get("cache_hit"))
        return result

    def find_active_job(self, code: str) -> dict[str, Any] | None:
        placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
        with self.database.connect() as connection:
            row = connection.execute(
                f"""
                SELECT * FROM analysis_jobs
                WHERE code = ? AND status IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (code, *ACTIVE_STATUSES),
            ).fetchone()
        result = _row_dict(row)
        if result is not None:
            result["cache_hit"] = bool(result.get("cache_hit"))
        return result

    def update_job(self, job_id: str, **changes: Any) -> dict[str, Any] | None:
        selected = {
            key: value
            for key, value in changes.items()
            if key in self.JOB_UPDATE_FIELDS
        }
        if not selected:
            return self.get_job(job_id)
        if "progress" in selected:
            selected["progress"] = max(0, min(100, int(selected["progress"])))
        if "cache_hit" in selected:
            selected["cache_hit"] = int(bool(selected["cache_hit"]))
        selected["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in selected)
        values = list(selected.values()) + [job_id]
        with self.database.connect() as connection:
            connection.execute(
                f"UPDATE analysis_jobs SET {assignments} WHERE id = ?",
                values,
            )
        return self.get_job(job_id)

    def mark_unfinished_failed(self) -> int:
        placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
        now = utc_now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE analysis_jobs
                SET status = 'failed',
                    message = '服务重启，原任务未能继续。',
                    error = '服务重启导致后台任务中断。',
                    updated_at = ?
                WHERE status IN ({placeholders})
                """,
                (now, *ACTIVE_STATUSES),
            )
            return cursor.rowcount

    def create_report(
        self,
        *,
        code: str,
        analysis: dict[str, Any],
        report_markdown: str,
        artifact_directory: str | None = None,
    ) -> dict[str, Any]:
        report_id = uuid4().hex
        stock = analysis.get("stock", {})
        overall = analysis.get("overall", {})
        metadata = analysis.get("analysis_metadata", {})
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO reports (
                    id, code, stock_name, total_score, rating,
                    analysis_json, report_markdown, source_generated_at,
                    artifact_directory, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    code,
                    stock.get("name") if isinstance(stock, dict) else None,
                    (
                        overall.get("total_score")
                        if isinstance(overall, dict)
                        else None
                    ),
                    overall.get("rating") if isinstance(overall, dict) else None,
                    json.dumps(analysis, ensure_ascii=False),
                    report_markdown,
                    (
                        metadata.get("source_data_generated_at")
                        if isinstance(metadata, dict)
                        else None
                    ),
                    artifact_directory,
                    utc_now(),
                ),
            )
        return self.get_report(report_id)

    @staticmethod
    def _decode_report(row) -> dict[str, Any] | None:
        result = _row_dict(row)
        if result is None:
            return None
        result["analysis"] = json.loads(result.pop("analysis_json"))
        return result

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM reports WHERE id = ?",
                (report_id,),
            ).fetchone()
        return self._decode_report(row)

    def latest_report(
        self,
        code: str,
        *,
        max_age_hours: int | None = None,
    ) -> dict[str, Any] | None:
        parameters: list[Any] = [code]
        age_filter = ""
        if max_age_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(
                hours=max(0, max_age_hours)
            )
            age_filter = "AND created_at >= ?"
            parameters.append(cutoff.isoformat(timespec="seconds"))
        with self.database.connect() as connection:
            row = connection.execute(
                f"""
                SELECT * FROM reports
                WHERE code = ? {age_filter}
                ORDER BY created_at DESC
                LIMIT 1
                """,
                parameters,
            ).fetchone()
        return self._decode_report(row)

    def list_reports(
        self,
        code: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, code, stock_name, total_score, rating,
                       source_generated_at, artifact_directory, created_at
                FROM reports
                WHERE code = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (code, max(1, min(100, int(limit)))),
            ).fetchall()
        return [dict(row) for row in rows]

