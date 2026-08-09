import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from stock_ai.cache import JsonCache
from stock_ai.service import StockDataService


class FakeBaoSource:
    def fetch_stock_basic(self, symbol):
        return {
            "basic": {"code_name": "测试公司", "ipoDate": "2010-01-01"},
            "industry": {"industry": "制造业"},
        }

    def fetch_history(self, symbol, start_date, end_date):
        start = date(2025, 1, 1)
        return [
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "close": str(10 + index * 0.02),
                "volume": str(10000 + index),
                "peTTM": str(15 + index / 100),
                "pbMRQ": str(2 + index / 1000),
            }
            for index in range(260)
        ]

    def fetch_annual_financial_metrics(self, symbol, years):
        return [{"period": "2025-12-31", "profit.roeAvg": "12.0"}]


class FakeAkSource:
    def fetch_company_info(self, symbol):
        return {
            "code": symbol.code,
            "name": "测试公司",
            "industry": "制造业",
            "listing_date": "20100101",
        }

    def fetch_spot(self, symbol):
        return {"code": symbol.code, "name": "测试公司", "latest_price": 15.2}

    def fetch_financial_indicators(self, symbol, start_year):
        return [{"日期": "2025-12-31", "净资产收益率(%)": 12.0}]

    def fetch_financial_reports(self, symbol):
        return {"利润表": [{"报告日": "20251231", "营业收入": 1000}]}

    def fetch_notices(self, symbol, begin_date, end_date, limit):
        return [{"公告标题": "年度报告", "公告日期": "2026-03-01"}]

    def fetch_news(self, symbol, limit):
        return [{"新闻标题": "测试新闻", "发布时间": "2026-07-24"}]


class ServiceTests(unittest.TestCase):
    def test_builds_and_caches_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            service = StockDataService(
                cache=JsonCache(Path(directory)),
                akshare_source=FakeAkSource(),
                baostock_source=FakeBaoSource(),
            )
            first = service.build_bundle("600519")
            second = service.build_bundle("600519")

            self.assertEqual(first["stock"]["name"], "测试公司")
            self.assertEqual(first["market_indicators"]["trend_state"], "上升")
            self.assertFalse(first["cache"]["hit"])
            self.assertTrue(second["cache"]["hit"])
            self.assertFalse(first["errors"])


if __name__ == "__main__":
    unittest.main()

