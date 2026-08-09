import unittest

from stock_ai.analysis_payload import build_analysis_context
from stock_ai.deepseek_client import DeepSeekClient
from stock_ai.prompts import build_analysis_messages
from stock_ai.report import render_markdown_report
from stock_ai.serialization import repair_mojibake_text


class AnalysisPayloadTests(unittest.TestCase):
    def test_repairs_mojibake_and_limits_large_sections(self):
        bundle = {
            "stock": {"code": "600519", "name": "贵州茅台"},
            "generated_at": "2026-07-27T12:00:00+08:00",
            "data_window": {"start_date": "2023-01-01"},
            "market_indicators": {"trend_state": "震荡"},
            "history": [
                {"date": f"2026-01-{index:02d}", "close": str(index)}
                for index in range(1, 80)
            ],
            "financials": {
                "akshare_indicators": [
                    {"ÈÕÆÚ": "2025-12-31", "¾»×Ê²úÊÕÒæÂÊ(%)": 20}
                ],
                "akshare_reports": {},
                "baostock_annual_metrics": [],
            },
            "notices": [
                {"¹«¸æ±êÌâ": "年度报告", "¹«¸æÈÕÆÚ": "2026-03-01"}
            ],
            "news": [
                {"ÐÂÎÅ±êÌâ": "测试新闻", "ÐÂÎÅÄÚÈÝ": "内容" * 400}
            ],
            "source_status": {},
            "errors": [],
        }

        context = build_analysis_context(bundle)

        self.assertEqual(len(context["recent_daily_history"]), 60)
        self.assertEqual(
            context["financials"]["detailed_indicators"][0]["日期"],
            "2025-12-31",
        )
        self.assertEqual(context["recent_notices"][0]["公告标题"], "年度报告")
        self.assertLessEqual(
            len(context["recent_news"][0]["新闻内容"]),
            303,
        )

    def test_builds_messages_with_json_schema(self):
        messages = build_analysis_messages(
            {"stock": {"code": "600519", "name": "贵州茅台"}}
        )
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("total_score", messages[1]["content"])
        self.assertIn("600519", messages[1]["content"])

    def test_repairs_known_gbk_latin1_text(self):
        self.assertEqual(repair_mojibake_text("ÈÕÆÚ"), "日期")
        self.assertEqual(repair_mojibake_text("正常中文"), "正常中文")
        self.assertEqual(repair_mojibake_text("https://example.com"), "https://example.com")


class DeepSeekClientTests(unittest.TestCase):
    def test_calls_compatible_endpoint_and_parses_report(self):
        captured = {}

        def fake_transport(endpoint, payload, headers, timeout):
            captured.update(
                endpoint=endpoint,
                payload=payload,
                headers=headers,
                timeout=timeout,
            )
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"overall":{"total_score":999},'
                                '"scorecard":{'
                                '"fundamental":{"score":25},'
                                '"growth":{"score":15},'
                                '"valuation":{"score":18},'
                                '"trend":{"score":12},'
                                '"risk_control":{"score":10}'
                                "}}"
                            )
                        }
                    }
                ],
                "usage": {"total_tokens": 100},
            }

        client = DeepSeekClient(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="deepseek-v4-pro",
            timeout=30,
            transport=fake_transport,
        )
        report, usage = client.generate_analysis(
            [{"role": "user", "content": "test"}]
        )

        self.assertEqual(
            captured["endpoint"],
            "https://api.example.com/v1/chat/completions",
        )
        self.assertEqual(captured["payload"]["model"], "deepseek-v4-pro")
        self.assertEqual(
            captured["payload"]["response_format"],
            {"type": "json_object"},
        )
        self.assertEqual(report["overall"]["total_score"], 999)
        self.assertEqual(usage["total_tokens"], 100)

    def test_renders_readable_markdown(self):
        markdown = render_markdown_report(
            {
                "stock": {
                    "code": "600519",
                    "name": "贵州茅台",
                    "industry": "白酒",
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
            }
        )
        self.assertIn("# 贵州茅台（600519）AI投资研究报告", markdown)
        self.assertIn("测试结论", markdown)
        self.assertIn("不构成投资建议", markdown)


if __name__ == "__main__":
    unittest.main()
