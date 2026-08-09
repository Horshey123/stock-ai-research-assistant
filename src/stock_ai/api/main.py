from __future__ import annotations

import os
import secrets
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from stock_ai import __version__
from stock_ai.api.database import Database
from stock_ai.api.repository import JobReportRepository
from stock_ai.api.schemas import (
    AnalysisJobRequest,
    HealthResponse,
    JobResponse,
    ReportListResponse,
    ReportResponse,
)
from stock_ai.api.tasks import AnalysisTaskRunner
from stock_ai.exceptions import InvalidStockCodeError
from stock_ai.service import PROJECT_ROOT
from stock_ai.symbols import parse_stock_symbol


RunnerFactory = Callable[
    [JobReportRepository, Path],
    AnalysisTaskRunner,
]


def _require_api_token(
    x_api_key: Annotated[
        str | None,
        Header(alias="X-API-Key"),
    ] = None,
) -> None:
    expected_token = os.getenv("STOCK_AI_API_TOKEN", "").strip()
    if not expected_token:
        return
    if not x_api_key or not secrets.compare_digest(
        x_api_key,
        expected_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问令牌无效。",
        )


def _job_response(job: dict[str, Any]) -> dict[str, Any]:
    report_id = job.get("report_id")
    return {
        **job,
        "poll_url": f"/api/v1/analysis-jobs/{job['id']}",
        "result_url": (
            f"/api/v1/reports/{report_id}" if report_id else None
        ),
    }


def _report_response(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key != "artifact_directory"
    }


def create_app(
    *,
    database_path: Path | None = None,
    artifact_root: Path | None = None,
    runner_factory: RunnerFactory | None = None,
) -> FastAPI:
    resolved_database_path = (
        Path(database_path)
        if database_path is not None
        else PROJECT_ROOT / "data" / "api" / "stock_ai.sqlite3"
    )
    resolved_artifact_root = (
        Path(artifact_root)
        if artifact_root is not None
        else PROJECT_ROOT / "data" / "api" / "artifacts"
    )
    repository = JobReportRepository(Database(resolved_database_path))
    runner = (
        runner_factory(repository, resolved_artifact_root)
        if runner_factory is not None
        else AnalysisTaskRunner(
            repository,
            artifact_root=resolved_artifact_root,
        )
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository.initialize()
        repository.mark_unfinished_failed()
        app.state.repository = repository
        app.state.analysis_runner = runner
        yield

    app = FastAPI(
        title="股票AI研究助手 API",
        description=(
            "提交A股代码，后台获取数据、调用DeepSeek、校验结果并保存报告。"
        ),
        version=__version__,
        lifespan=lifespan,
    )

    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "STOCK_AI_CORS_ORIGINS",
            (
                "http://localhost,https://localhost,capacitor://localhost,"
                "http://127.0.0.1:5173,http://localhost:5173"
            ),
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": "股票AI研究助手 API",
            "health": "/api/v1/health",
            "docs": "/docs",
        }

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> dict[str, Any]:
        if not repository.ping():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库不可用。",
            )
        return {
            "status": "ok",
            "database": "ok",
            "version": __version__,
            "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY")),
        }

    @app.post(
        "/api/v1/analysis-jobs",
        response_model=JobResponse,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(_require_api_token)],
    )
    def create_analysis_job(
        request: AnalysisJobRequest,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        try:
            symbol = parse_stock_symbol(request.code)
        except InvalidStockCodeError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        if not request.refresh_data and request.reuse_hours > 0:
            existing_report = repository.latest_report(
                symbol.code,
                max_age_hours=request.reuse_hours,
            )
            if existing_report is not None:
                job = repository.create_job(
                    symbol.code,
                    status="completed",
                    progress=100,
                    message="已复用近期分析报告。",
                    report_id=existing_report["id"],
                    cache_hit=True,
                )
                return _job_response(job)

        active_job = repository.find_active_job(symbol.code)
        if active_job is not None:
            return _job_response(active_job)

        job = repository.create_job(symbol.code)
        background_tasks.add_task(
            runner.run,
            job["id"],
            symbol.code,
            request.refresh_data,
        )
        return _job_response(job)

    @app.get(
        "/api/v1/analysis-jobs/{job_id}",
        response_model=JobResponse,
        dependencies=[Depends(_require_api_token)],
    )
    def get_analysis_job(job_id: str) -> dict[str, Any]:
        job = repository.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到该分析任务。",
            )
        return _job_response(job)

    @app.get(
        "/api/v1/reports/{report_id}",
        response_model=ReportResponse,
        dependencies=[Depends(_require_api_token)],
    )
    def get_report(report_id: str) -> dict[str, Any]:
        report = repository.get_report(report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到该分析报告。",
            )
        return _report_response(report)

    @app.get(
        "/api/v1/stocks/{code}/latest-report",
        response_model=ReportResponse,
        dependencies=[Depends(_require_api_token)],
    )
    def get_latest_report(code: str) -> dict[str, Any]:
        try:
            symbol = parse_stock_symbol(code)
        except InvalidStockCodeError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        report = repository.latest_report(symbol.code)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该股票还没有分析报告。",
            )
        return _report_response(report)

    @app.get(
        "/api/v1/stocks/{code}/reports",
        response_model=ReportListResponse,
        dependencies=[Depends(_require_api_token)],
    )
    def list_stock_reports(
        code: str,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> dict[str, Any]:
        try:
            symbol = parse_stock_symbol(code)
        except InvalidStockCodeError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        return {
            "code": symbol.code,
            "items": repository.list_reports(symbol.code, limit=limit),
        }

    return app


app = create_app()
