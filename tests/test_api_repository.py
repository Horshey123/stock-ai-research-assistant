import tempfile
import unittest
from pathlib import Path

from stock_ai.api.database import Database
from stock_ai.api.repository import JobReportRepository
from stock_ai.api.tasks import AnalysisTaskRunner


def sample_analysis():
    return {
        "stock": {
            "code": "600519",
            "name": "测试公司",
            "industry": "测试行业",
        },
        "overall": {
            "total_score": 80,
            "rating": "关注",
            "confidence": "中",
            "summary": "测试结论",
        },
        "scorecard": {},
        "analysis": {},
        "outlook": {},
        "action_plan": {},
        "data_quality": {},
        "analysis_metadata": {
            "source_data_generated_at": "2026-07-30T10:00:00+08:00",
            "model": "fake-model",
        },
        "validation": {
            "status": "passed",
            "corrections_count": 0,
            "warnings_count": 0,
        },
        "disclaimer": "不构成投资建议。",
    }


class FakeDataService:
    def build_bundle(self, code, use_cache=True):
        return {
            "stock": {
                "code": code,
                "name": "测试公司",
                "industry": "测试行业",
            },
            "generated_at": "2026-07-30T10:00:00+08:00",
        }


class FakeAnalysisService:
    def prepare_context(self, bundle):
        return {
            "stock": bundle["stock"],
            "data_generated_at": bundle["generated_at"],
        }

    def analyze_context(self, context):
        return sample_analysis()


class RepositoryTests(unittest.TestCase):
    def test_job_and_report_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = JobReportRepository(
                Database(Path(directory) / "api.sqlite3")
            )
            repository.initialize()

            job = repository.create_job("600519")
            self.assertEqual(job["status"], "queued")
            repository.update_job(
                job["id"],
                status="analyzing",
                progress=60,
            )
            self.assertEqual(repository.get_job(job["id"])["progress"], 60)

            report = repository.create_report(
                code="600519",
                analysis=sample_analysis(),
                report_markdown="# 测试报告",
            )
            repository.update_job(
                job["id"],
                status="completed",
                progress=100,
                report_id=report["id"],
            )

            completed = repository.get_job(job["id"])
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["report_id"], report["id"])
            self.assertEqual(
                repository.latest_report("600519")["analysis"]["overall"][
                    "total_score"
                ],
                80,
            )
            self.assertEqual(len(repository.list_reports("600519")), 1)

    def test_background_runner_persists_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = JobReportRepository(Database(root / "api.sqlite3"))
            repository.initialize()
            runner = AnalysisTaskRunner(
                repository,
                artifact_root=root / "artifacts",
                data_service_factory=FakeDataService,
                analysis_service_factory=FakeAnalysisService,
            )
            job = repository.create_job("600519")

            runner.run(job["id"], "600519")

            completed = repository.get_job(job["id"])
            self.assertEqual(completed["status"], "completed")
            report = repository.get_report(completed["report_id"])
            artifact_directory = Path(report["artifact_directory"])
            self.assertTrue((artifact_directory / "raw_data.json").exists())
            self.assertTrue(
                (artifact_directory / "analysis_context.json").exists()
            )
            self.assertTrue((artifact_directory / "analysis.json").exists())
            self.assertTrue((artifact_directory / "report.md").exists())

    def test_unfinished_jobs_fail_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = JobReportRepository(
                Database(Path(directory) / "api.sqlite3")
            )
            repository.initialize()
            job = repository.create_job("600519")

            changed = repository.mark_unfinished_failed()

            self.assertEqual(changed, 1)
            self.assertEqual(repository.get_job(job["id"])["status"], "failed")


if __name__ == "__main__":
    unittest.main()

