import unittest

import pandas as pd

from stock_ai.data_sources.akshare_source import AkShareSource
from stock_ai.data_sources.baostock_source import BaoStockSource
from stock_ai.symbols import parse_stock_symbol


class FakeBaoResult:
    error_code = "0"
    error_msg = "success"

    def __init__(self, rows):
        self.rows = rows

    def get_data(self):
        return pd.DataFrame(self.rows)


class FakeBaoModule:
    def login(self):
        return FakeBaoResult([])

    def logout(self):
        return FakeBaoResult([])

    def query_stock_basic(self, code):
        return FakeBaoResult([{"code": code, "code_name": "测试公司"}])

    def query_stock_industry(self, code):
        return FakeBaoResult([{"code": code, "industry": "制造业"}])

    def query_history_k_data_plus(self, code, fields, **kwargs):
        return FakeBaoResult(
            [
                {
                    "date": "2026-07-24",
                    "code": code,
                    "close": "10.50",
                    "volume": "10000",
                    "peTTM": "15.2",
                    "pbMRQ": "2.1",
                }
            ]
        )

    def _financial(self, code, year, quarter):
        return FakeBaoResult(
            [
                {
                    "code": code,
                    "pubDate": f"{year}-03-31",
                    "statDate": f"{year}-12-31",
                    "metric": "1.0",
                }
            ]
        )

    query_profit_data = _financial
    query_growth_data = _financial
    query_balance_data = _financial
    query_cash_flow_data = _financial


class FakeAkModule:
    def stock_individual_info_em(self, symbol):
        return pd.DataFrame(
            [
                {"item": "股票简称", "value": "测试公司"},
                {"item": "行业", "value": "制造业"},
                {"item": "上市时间", "value": "20100101"},
            ]
        )

    def stock_sh_a_spot_em(self):
        return pd.DataFrame(
            [
                {
                    "代码": "600519",
                    "名称": "测试公司",
                    "最新价": 10.5,
                    "涨跌幅": 1.2,
                    "市盈率-动态": 15.2,
                    "市净率": 2.1,
                    "总市值": 100000,
                    "流通市值": 80000,
                }
            ]
        )

    def stock_sz_a_spot_em(self):
        return pd.DataFrame()

    def stock_financial_analysis_indicator(self, symbol, start_year):
        return pd.DataFrame(
            [
                {
                    "日期": "2025-12-31",
                    "销售毛利率(%)": 30.0,
                    "净资产收益率(%)": 12.0,
                }
            ]
        )

    def stock_financial_report_sina(self, stock, symbol):
        return pd.DataFrame(
            [
                {
                    "报告日": "20251231",
                    "营业收入": 1000,
                    "净利润": 100,
                    "资产总计": 2000,
                    "负债合计": 500,
                    "经营活动产生的现金流量净额": 120,
                }
            ]
        )

    def stock_individual_notice_report(
        self, security, symbol, begin_date, end_date
    ):
        return pd.DataFrame(
            [
                {
                    "代码": security,
                    "名称": "测试公司",
                    "公告标题": "年度报告",
                    "公告类型": "财务报告",
                    "公告日期": "2026-03-01",
                    "网址": "https://example.com/report",
                }
            ]
        )

    def stock_news_em(self, symbol):
        return pd.DataFrame(
            [
                {
                    "关键词": symbol,
                    "新闻标题": "测试新闻",
                    "新闻内容": "测试内容",
                    "发布时间": "2026-07-24",
                    "文章来源": "测试来源",
                    "新闻链接": "https://example.com/news",
                }
            ]
        )


class DataSourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.symbol = parse_stock_symbol("600519")

    def test_baostock_adapter(self):
        source = BaoStockSource(module=FakeBaoModule())
        basic = source.fetch_stock_basic(self.symbol)
        history = source.fetch_history(
            self.symbol,
            start_date="2026-01-01",
            end_date="2026-07-27",
        )
        financials = source.fetch_annual_financial_metrics(self.symbol, years=1)

        self.assertEqual(basic["industry"]["industry"], "制造业")
        self.assertEqual(history[0]["close"], "10.50")
        self.assertTrue(financials)

    def test_akshare_adapter(self):
        source = AkShareSource(module=FakeAkModule())

        self.assertEqual(
            source.fetch_company_info(self.symbol)["name"],
            "测试公司",
        )
        self.assertEqual(source.fetch_spot(self.symbol)["pe_dynamic"], 15.2)
        self.assertTrue(source.fetch_financial_indicators(self.symbol, 2024))
        self.assertTrue(source.fetch_financial_reports(self.symbol))
        self.assertTrue(
            source.fetch_notices(
                self.symbol,
                begin_date="20260101",
                end_date="20260727",
            )
        )
        self.assertTrue(source.fetch_news(self.symbol))


if __name__ == "__main__":
    unittest.main()

