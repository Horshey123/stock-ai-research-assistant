from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


JobStatus = Literal[
    "queued",
    "fetching_data",
    "preparing_context",
    "analyzing",
    "validating",
    "completed",
    "failed",
]


class AnalysisJobRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        examples=["600519"],
    )
    refresh_data: bool = False
    reuse_hours: int = Field(default=24, ge=0, le=168)


class JobResponse(BaseModel):
    id: str
    code: str
    status: JobStatus
    progress: int
    message: str | None = None
    error: str | None = None
    report_id: str | None = None
    cache_hit: bool = False
    created_at: str
    updated_at: str
    poll_url: str
    result_url: str | None = None


class ReportSummary(BaseModel):
    id: str
    code: str
    stock_name: str | None = None
    total_score: int | None = None
    rating: str | None = None
    source_generated_at: str | None = None
    created_at: str


class ReportResponse(ReportSummary):
    analysis: dict[str, Any]
    report_markdown: str


class ReportListResponse(BaseModel):
    code: str
    items: list[ReportSummary]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]
    version: str
    deepseek_configured: bool

