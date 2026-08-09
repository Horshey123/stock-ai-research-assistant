from __future__ import annotations

from datetime import date
from typing import Any

from stock_ai.exceptions import DataSourceError, MissingDependencyError
from stock_ai.retry import retry_call
from stock_ai.serialization import dataframe_records, json_safe, to_float
from stock_ai.symbols import StockSymbol


REPORT_FIELDS = {
    "资产负债表": [
        "报告日",
        "更新日期",
        "货币资金",
        "应收账款",
        "存货",
        "流动资产合计",
        "资产总计",
        "短期借款",
        "长期借款",
        "流动负债合计",
        "负债合计",
        "所有者权益合计",
        "股东权益合计",
    ],
    "利润表": [
        "报告日",
        "更新日期",
        "营业总收入",
        "营业收入",
        "营业总成本",
        "营业成本",
        "营业利润",
        "利润总额",
        "净利润",
        "归属于母公司",
        "基本每股收益",
    ],
    "现金流量表": [
        "报告日",
        "更新日期",
        "经营活动产生的现金流量净额",
        "投资活动产生的现金流量净额",
        "筹资活动产生的现金流量净额",
        "现金及现金等价物净增加额",
        "销售商品、提供劳务收到的现金",
    ],
}

INDICATOR_FIELDS = [
    "日期",
    "每股收益",
    "每股经营性现金流",
    "销售毛利率",
    "销售净利率",
    "净资产收益率",
    "主营业务收入增长率",
    "净利润增长率",
    "总资产增长率",
    "应收账款周转率",
    "存货周转率",
    "流动比率",
    "速动比率",
    "资产负债率",
]


class AkShareSource:
    """AKShare adapter with small, explicit responses for the AI layer."""

    name = "akshare"

    def __init__(self, module=None):
        self._module = module

    @property
    def ak(self):
        if self._module is None:
            try:
                import akshare as akshare_module
            except ImportError as error:
                raise MissingDependencyError(
                    "缺少 akshare，请执行：python -m pip install -U akshare"
                ) from error
            self._module = akshare_module
        return self._module

    @staticmethod
    def _select_columns(frame, wanted_tokens: list[str], max_columns: int = 32):
        selected: list[str] = []
        for column in frame.columns:
            column_text = str(column)
            if any(token in column_text for token in wanted_tokens):
                selected.append(column)
            if len(selected) >= max_columns:
                break
        if not selected:
            return frame
        return frame.loc[:, selected]

    @staticmethod
    def _info_records_to_dict(frame) -> dict[str, Any]:
        if frame is None or getattr(frame, "empty", True):
            return {}
        if "item" in frame.columns and "value" in frame.columns:
            return {
                str(row["item"]): json_safe(row["value"])
                for _, row in frame.iterrows()
            }
        return {"raw": dataframe_records(frame)}

    def fetch_company_info(self, symbol: StockSymbol) -> dict[str, Any]:
        frame = retry_call(
            lambda: self.ak.stock_individual_info_em(symbol=symbol.code)
        )
        raw = self._info_records_to_dict(frame)
        return {
            "code": symbol.code,
            "market": symbol.market,
            "exchange": symbol.exchange,
            "name": raw.get("股票简称") or raw.get("名称"),
            "industry": raw.get("行业"),
            "listing_date": raw.get("上市时间") or raw.get("上市日期"),
            "total_shares": to_float(raw.get("总股本")),
            "floating_shares": to_float(raw.get("流通股")),
            "raw": raw,
        }

    def fetch_spot(self, symbol: StockSymbol) -> dict[str, Any]:
        if symbol.market == "sh":
            frame = retry_call(self.ak.stock_sh_a_spot_em)
        else:
            frame = retry_call(self.ak.stock_sz_a_spot_em)
        if frame is None or getattr(frame, "empty", True) or "代码" not in frame.columns:
            raise DataSourceError("AKShare实时行情返回空数据。")
        match = frame[frame["代码"].astype(str).str.zfill(6) == symbol.code]
        if match.empty:
            raise DataSourceError(f"AKShare实时行情中没有找到 {symbol.code}。")
        row = match.iloc[0].to_dict()
        return {
            "code": symbol.code,
            "name": json_safe(row.get("名称")),
            "latest_price": to_float(row.get("最新价")),
            "change_percent": to_float(row.get("涨跌幅")),
            "open": to_float(row.get("今开")),
            "high": to_float(row.get("最高")),
            "low": to_float(row.get("最低")),
            "previous_close": to_float(row.get("昨收")),
            "volume": to_float(row.get("成交量")),
            "amount": to_float(row.get("成交额")),
            "turnover_rate": to_float(row.get("换手率")),
            "volume_ratio": to_float(row.get("量比")),
            "pe_dynamic": to_float(row.get("市盈率-动态")),
            "pb": to_float(row.get("市净率")),
            "total_market_cap": to_float(row.get("总市值")),
            "floating_market_cap": to_float(row.get("流通市值")),
            "source_time": date.today().isoformat(),
        }

    def fetch_financial_indicators(
        self,
        symbol: StockSymbol,
        start_year: int,
        limit_periods: int = 16,
    ) -> list[dict[str, Any]]:
        frame = retry_call(
            lambda: self.ak.stock_financial_analysis_indicator(
                symbol=symbol.code,
                start_year=str(start_year),
            )
        )
        if frame is None or getattr(frame, "empty", True):
            return []
        if "日期" in frame.columns:
            frame = frame.sort_values("日期", ascending=False)
        selected = self._select_columns(frame, INDICATOR_FIELDS)
        return dataframe_records(selected, limit=limit_periods)

    def fetch_financial_reports(
        self,
        symbol: StockSymbol,
        limit_periods: int = 8,
    ) -> dict[str, list[dict[str, Any]]]:
        reports: dict[str, list[dict[str, Any]]] = {}
        ak = self.ak
        for report_name, fields in REPORT_FIELDS.items():
            try:
                frame = retry_call(
                    lambda name=report_name: ak.stock_financial_report_sina(
                        stock=symbol.sina_code,
                        symbol=name,
                    )
                )
                if frame is None or getattr(frame, "empty", True):
                    reports[report_name] = []
                    continue
                selected = self._select_columns(frame, fields)
                reports[report_name] = dataframe_records(selected, limit=limit_periods)
            except Exception as error:
                reports[report_name] = []
                reports[f"{report_name}_error"] = str(error)
        return reports

    def fetch_notices(
        self,
        symbol: StockSymbol,
        begin_date: str,
        end_date: str,
        category: str = "全部",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        frame = retry_call(
            lambda: self.ak.stock_individual_notice_report(
                security=symbol.code,
                symbol=category,
                begin_date=begin_date,
                end_date=end_date,
            )
        )
        if frame is None or getattr(frame, "empty", True):
            return []
        if "公告日期" in frame.columns:
            frame = frame.sort_values("公告日期", ascending=False)
        columns = [
            column
            for column in ("代码", "名称", "公告标题", "公告类型", "公告日期", "网址")
            if column in frame.columns
        ]
        return dataframe_records(frame.loc[:, columns], limit=limit)

    def fetch_news(
        self,
        symbol: StockSymbol,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        frame = retry_call(lambda: self.ak.stock_news_em(symbol=symbol.code))
        if frame is None or getattr(frame, "empty", True):
            return []
        if "发布时间" in frame.columns:
            frame = frame.sort_values("发布时间", ascending=False)
        columns = [
            column
            for column in ("关键词", "新闻标题", "新闻内容", "发布时间", "文章来源", "新闻链接")
            if column in frame.columns
        ]
        records = dataframe_records(frame.loc[:, columns], limit=limit)
        for record in records:
            content = record.get("新闻内容")
            if isinstance(content, str) and len(content) > 500:
                record["新闻内容"] = content[:500] + "..."
        return records
