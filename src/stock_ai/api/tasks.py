from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from stock_ai.analysis_service import StockAnalysisService
from stock_ai.api.repository import JobReportRepository
from stock_ai.report import render_markdown_report
from stock_ai.service import PROJECT_ROOT, StockDataService


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)


def _safe_error_message(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    for variable_name in ("DEEPSEEK_API_KEY",):
        secret = os.getenv(variable_name)
        if secret:
            message = message.replace(secret, "***")
    return message[:1000]


class AnalysisTaskRunner:
    """Run the existing stock pipeline behind a persistent job record."""

    def __init__(
        self,
        repository: JobReportRepository,
        *,
        artifact_root: Path | None = None,
        max_concurrent: int = 1,
        data_service_factory: Callable[[], StockDataService] | None = None,
        analysis_service_factory: Callable[[], StockAnalysisService] | None = None,
    ):
        self.repository = repository
        self.artifact_root = (
            Path(artifact_root)
            if artifact_root is not None
            else PROJECT_ROOT / "data" / "api" / "artifacts"
        )
        self.semaphore = threading.Semaphore(max(1, max_concurrent))
        self.data_service_factory = data_service_factory or StockDataService
        self.analysis_service_factory = (
            analysis_service_factory or StockAnalysisService
        )

    def run(self, job_id: str, code: str, refresh_data: bool = False) -> None:
        self.repository.update_job(
            job_id,
            status="queued",
            progress=5,
            message="等待后台分析资源。",
        )
        with self.semaphore:
            try:
                self.repository.update_job(
                    job_id,
                    status="fetching_data",
                    progress=15,
                    message="正在获取股票行情、财务、公告和新闻。",
                )
                bundle = self.data_service_factory().build_bundle(
                    code,
                    use_cache=not refresh_data,
                )

                self.repository.update_job(
                    job_id,
                    status="preparing_context",
                    progress=45,
                    message="正在提取关键数据并计算确定性事实。",
                )
                analysis_service = self.analysis_service_factory()
                context = analysis_service.prepare_context(bundle)

                self.repository.update_job(
                    job_id,
                    status="analyzing",
                    progress=60,
                    message="正在调用DeepSeek生成股票研究报告。",
                )
                analysis = analysis_service.analyze_context(context)

                self.repository.update_job(
                    job_id,
                    status="validating",
                    progress=85,
                    message="正在校验评分、均线关系和数据缺失。",
                )
                report_markdown = render_markdown_report(analysis)
                timestamp = datetime.now().astimezone().strftime(
                    "%Y%m%d-%H%M%S"
                )
                artifact_directory = (
                    self.artifact_root
                    / code
                    / f"{timestamp}-{job_id[:8]}"
                )
                artifact_directory.mkdir(parents=True, exist_ok=True)
                _write_json(artifact_directory / "raw_data.json", bundle)
                _write_json(
                    artifact_directory / "analysis_context.json",
                    context,
                )
                _write_json(artifact_directory / "analysis.json", analysis)
                (artifact_directory / "report.md").write_text(
                    report_markdown,
                    encoding="utf-8",
                )

                report = self.repository.create_report(
                    code=code,
                    analysis=analysis,
                    report_markdown=report_markdown,
                    artifact_directory=str(artifact_directory.resolve()),
                )
                self.repository.update_job(
                    job_id,
                    status="completed",
                    progress=100,
                    message="分析完成。",
                    report_id=report["id"],
                    error=None,
                )
            except Exception as error:
                self.repository.update_job(
                    job_id,
                    status="failed",
                    progress=100,
                    message="分析失败。",
                    error=_safe_error_message(error),
                )

