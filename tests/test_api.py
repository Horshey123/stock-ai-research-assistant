import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    from stock_ai.api.main import create_app
except ImportError:
    TestClient = None
    create_app = None


def sample_analysis(code):
    return {
        "stock": {
            "code": code,
            "name": "测试公司",
            "industry": "测试行业",
        },
        "overall": {
            "total_score": 80,
            "rating": "关注",
            "confidence": "中",
            "summary": "测试结论",
        },
        "analysis_metadata": {
            "source_data_generated_at": "2026-07-30T10:00:00+08:00",
        },
    }


class ImmediateFakeRunner:
    def __init__(self, repository):
        self.repository = repository

    def run(self, job_id, code, refresh_data=False):
        report = self.repository.create_report(
            code=code,
            analysis=sample_analysis(code),
            report_markdown="# 测试报告",
        )
        self.repository.update_job(
            job_id,
            status="completed",
            progress=100,
            message="分析完成。",
            report_id=report["id"],
        )


@unittest.skipIf(
    TestClient is None,
    "需要先安装FastAPI和HTTPX后才能运行接口测试。",
)
class APITests(unittest.TestCase):
    def test_health_job_lifecycle_cache_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def runner_factory(repository, artifact_root):
                return ImmediateFakeRunner(repository)

            app = create_app(
                database_path=root / "api.sqlite3",
                artifact_root=root / "artifacts",
                runner_factory=runner_factory,
            )
            with TestClient(app) as client:
                health = client.get("/api/v1/health")
                self.assertEqual(health.status_code, 200)
                self.assertEqual(health.json()["database"], "ok")

                preflight = client.options(
                    "/api/v1/analysis-jobs",
                    headers={
                        "Origin": "https://localhost",
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "content-type,x-api-key",
                    },
                )
                self.assertEqual(preflight.status_code, 200)
                self.assertEqual(
                    preflight.headers["access-control-allow-origin"],
                    "https://localhost",
                )

                submitted = client.post(
                    "/api/v1/analysis-jobs",
                    json={
                        "code": "600519",
                        "refresh_data": False,
                        "reuse_hours": 24,
                    },
                )
                self.assertEqual(submitted.status_code, 202)
                job_id = submitted.json()["id"]

                job = client.get(f"/api/v1/analysis-jobs/{job_id}")
                self.assertEqual(job.status_code, 200)
                self.assertEqual(job.json()["status"], "completed")
                report_id = job.json()["report_id"]

                report = client.get(f"/api/v1/reports/{report_id}")
                self.assertEqual(report.status_code, 200)
                self.assertEqual(
                    report.json()["analysis"]["overall"]["total_score"],
                    80,
                )

                latest = client.get(
                    "/api/v1/stocks/600519/latest-report"
                )
                self.assertEqual(latest.status_code, 200)

                history = client.get("/api/v1/stocks/600519/reports")
                self.assertEqual(history.status_code, 200)
                self.assertEqual(len(history.json()["items"]), 1)

                cached = client.post(
                    "/api/v1/analysis-jobs",
                    json={"code": "600519"},
                )
                self.assertEqual(cached.status_code, 202)
                self.assertEqual(cached.json()["status"], "completed")
                self.assertTrue(cached.json()["cache_hit"])

    def test_rejects_unsupported_code_and_missing_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = create_app(
                database_path=root / "api.sqlite3",
                artifact_root=root / "artifacts",
                runner_factory=lambda repository, artifact_root: (
                    ImmediateFakeRunner(repository)
                ),
            )
            with TestClient(app) as client:
                invalid = client.post(
                    "/api/v1/analysis-jobs",
                    json={"code": "430047"},
                )
                self.assertEqual(invalid.status_code, 422)

                missing_job = client.get(
                    "/api/v1/analysis-jobs/not-found"
                )
                self.assertEqual(missing_job.status_code, 404)

                missing_report = client.get(
                    "/api/v1/stocks/600519/latest-report"
                )
                self.assertEqual(missing_report.status_code, 404)


if __name__ == "__main__":
    unittest.main()
