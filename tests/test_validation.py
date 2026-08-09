import unittest

from stock_ai.report import render_markdown_report
from stock_ai.validation import (
    build_verified_facts,
    validate_and_correct_report,
)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "stock": {
                "code": "600519",
                "name": "贵州茅台",
                "industry": "白酒",
            },
            "market_snapshot": {},
            "market_indicators": {
                "latest_trade_date": "2026-07-24",
                "latest_close": 100,
                "ma20": 90,
                "ma60": 95,
                "ma120": 110,
                "change_1y_percent": -5,
                "pe_ttm": 20,
                "pe_history_percentile": 10,
                "pb_mrq": 5,
                "pb_history_percentile": 15,
            },
            "data_quality": {
                "source_status": {
                    "history": "ok",
                    "market_snapshot": "error",
                }
            },
        }

    def _wrong_report(self):
        return {
            "stock": {
                "code": "000001",
                "name": "错误名称",
                "industry": "未知",
            },
            "overall": {
                "total_score": 99,
                "rating": "关注",
                "confidence": "中",
                "summary": "股价尚未突破MA60和MA120，趋势偏弱。",
            },
            "scorecard": {
                "fundamental": {"score": 25, "reason": "测试"},
                "growth": {"score": 15, "reason": "测试"},
                "valuation": {"score": 18, "reason": "测试"},
                "trend": {
                    "score": 10,
                    "reason": "股价低于MA60，但低于MA120。",
                },
                "risk_control": {"score": 10, "reason": "测试"},
            },
            "analysis": {
                "technical": {
                    "conclusion": "当前仍在MA60和MA120之下。",
                    "evidence": [],
                    "risks": ["若股价无法突破MA60，可能重新走弱。"],
                }
            },
            "outlook": {
                "scenarios": [
                    {
                        "expected_direction": "有望挑战MA120并进入140元以上区间。"
                    }
                ]
            },
            "action_plan": {},
            "data_quality": {},
        }

    def test_builds_deterministic_market_facts(self):
        facts = build_verified_facts(self.context)

        self.assertEqual(
            facts["market_position"]["moving_averages"]["MA60"][
                "close_relation"
            ],
            "above",
        )
        self.assertEqual(
            facts["market_position"]["moving_averages"]["MA120"][
                "close_relation"
            ],
            "below",
        )
        self.assertEqual(facts["valuation"]["pe_band"], "历史较低区间")
        self.assertEqual(facts["performance"]["direction"], "下跌")

    def test_corrects_score_identity_and_ma_contradictions(self):
        validated = validate_and_correct_report(
            self._wrong_report(),
            self.context,
        )

        self.assertEqual(validated["stock"]["code"], "600519")
        self.assertEqual(validated["overall"]["total_score"], 78)
        self.assertEqual(validated["validation"]["status"], "corrected")
        self.assertGreaterEqual(
            validated["validation"]["corrections_count"],
            3,
        )
        self.assertNotIn(
            "股价低于MA60",
            validated["scorecard"]["trend"]["reason"],
        )
        self.assertEqual(
            validated["analysis"]["technical"]["risks"][0],
            "若股价无法突破MA60，可能重新走弱。",
        )
        self.assertEqual(
            validated["outlook"]["scenarios"][0]["expected_direction"],
            "有望挑战MA120并进入140元以上区间。",
        )
        self.assertIn(
            "高于MA60(95.00)",
            validated["verified_facts"]["market_position"]["summary"],
        )
        self.assertEqual(
            validated["analysis"]["technical"]["evidence"][0],
            validated["verified_facts"]["market_position"]["summary"],
        )

    def test_markdown_shows_validation_results(self):
        validated = validate_and_correct_report(
            self._wrong_report(),
            self.context,
        )
        markdown = render_markdown_report(validated)

        self.assertIn("## 程序校验", markdown)
        self.assertIn("发现并自动修正", markdown)
        self.assertIn("确定性行情事实", markdown)


if __name__ == "__main__":
    unittest.main()
