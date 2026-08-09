from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Any

from stock_ai.exceptions import DataSourceError, MissingDependencyError
from stock_ai.serialization import dataframe_records, json_safe
from stock_ai.symbols import StockSymbol


HISTORY_FIELDS = (
    "date,code,open,high,low,close,preclose,volume,amount,adjustflag,"
    "turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST"
)


class BaoStockSource:
    """BaoStock adapter for stable daily history and annual ratios."""

    name = "baostock"

    def __init__(self, module=None):
        self._module = module

    @property
    def bs(self):
        if self._module is None:
            try:
                import baostock as baostock_module
            except ImportError as error:
                raise MissingDependencyError(
                    "缺少 baostock，请执行：python -m pip install baostock"
                ) from error
            self._module = baostock_module
        return self._module

    @contextmanager
    def session(self):
        login_result = self.bs.login()
        if getattr(login_result, "error_code", "-1") != "0":
            raise DataSourceError(
                f"BaoStock登录失败：{getattr(login_result, 'error_msg', '未知错误')}"
            )
        try:
            yield
        finally:
            self.bs.logout()

    @staticmethod
    def _result_frame(result, label: str):
        if getattr(result, "error_code", "-1") != "0":
            raise DataSourceError(
                f"BaoStock {label}失败：{getattr(result, 'error_msg', '未知错误')}"
            )
        try:
            return result.get_data()
        except Exception as error:
            raise DataSourceError(f"BaoStock {label}结果无法转换为表格。") from error

    def fetch_stock_basic(self, symbol: StockSymbol) -> dict[str, Any]:
        with self.session():
            result = self.bs.query_stock_basic(code=symbol.baostock_code)
            frame = self._result_frame(result, "股票基础信息")
            industry_result = self.bs.query_stock_industry(code=symbol.baostock_code)
            industry_frame = self._result_frame(industry_result, "行业信息")
        basic = dataframe_records(frame, limit=1)
        industry = dataframe_records(industry_frame, limit=1)
        return {
            "basic": basic[0] if basic else {},
            "industry": industry[0] if industry else {},
        }

    def fetch_history(
        self,
        symbol: StockSymbol,
        start_date: str,
        end_date: str,
        adjustflag: str = "2",
    ) -> list[dict[str, Any]]:
        with self.session():
            result = self.bs.query_history_k_data_plus(
                symbol.baostock_code,
                HISTORY_FIELDS,
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag=adjustflag,
            )
            frame = self._result_frame(result, "历史行情")
        if frame is None or getattr(frame, "empty", True):
            return []
        frame = frame.sort_values("date")
        return dataframe_records(frame)

    def fetch_annual_financial_metrics(
        self,
        symbol: StockSymbol,
        years: int = 4,
    ) -> list[dict[str, Any]]:
        current_year = date.today().year
        combined: dict[str, dict[str, Any]] = {}
        queries = (
            ("profit", self.bs.query_profit_data),
            ("growth", self.bs.query_growth_data),
            ("balance", self.bs.query_balance_data),
            ("cash_flow", self.bs.query_cash_flow_data),
        )

        with self.session():
            for year in range(current_year - years, current_year + 1):
                for query_name, query in queries:
                    result = query(code=symbol.baostock_code, year=year, quarter=4)
                    frame = self._result_frame(result, f"{query_name}财务指标")
                    for record in dataframe_records(frame):
                        period = str(
                            record.get("statDate")
                            or record.get("pubDate")
                            or f"{year}-Q4"
                        )
                        target = combined.setdefault(
                            period,
                            {
                                "period": period,
                                "code": symbol.code,
                                "source_year": year,
                            },
                        )
                        for key, value in record.items():
                            if key in {"code", "pubDate", "statDate"}:
                                target.setdefault(key, value)
                            else:
                                target[f"{query_name}.{key}"] = json_safe(value)

        return sorted(
            combined.values(),
            key=lambda record: str(record.get("period", "")),
            reverse=True,
        )

