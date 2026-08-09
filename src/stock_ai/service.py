from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from stock_ai.cache import JsonCache
from stock_ai.data_sources import AkShareSource, BaoStockSource
from stock_ai.exceptions import StockAIError
from stock_ai.indicators import calculate_market_indicators
from stock_ai.serialization import json_safe
from stock_ai.symbols import StockSymbol, parse_stock_symbol


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StockDataService:
    """Aggregate free providers into one AI-ready stock data bundle."""

    def __init__(
        self,
        cache: JsonCache | None = None,
        akshare_source: AkShareSource | None = None,
        baostock_source: BaoStockSource | None = None,
    ):
        self.cache = cache or JsonCache(PROJECT_ROOT / "data" / "cache")
        self.akshare = akshare_source or AkShareSource()
        self.baostock = baostock_source or BaoStockSource()

    @staticmethod
    def _capture(
        target: dict[str, Any],
        statuses: dict[str, Any],
        errors: list[dict[str, str]],
        key: str,
        provider: str,
        operation: Callable[[], Any],
        default: Any,
    ) -> Any:
        try:
            value = operation()
            target[key] = json_safe(value)
            statuses[key] = {
                "provider": provider,
                "status": "ok",
                "rows": len(value) if isinstance(value, list) else None,
            }
            return value
        except Exception as error:
            target[key] = default
            statuses[key] = {
                "provider": provider,
                "status": "error",
                "message": str(error),
            }
            errors.append(
                {
                    "section": key,
                    "provider": provider,
                    "message": str(error),
                }
            )
            return default

    @staticmethod
    def _merge_stock_identity(
        symbol: StockSymbol,
        company_info: dict[str, Any],
        spot: dict[str, Any],
        baostock_basic: dict[str, Any],
    ) -> dict[str, Any]:
        bs_basic = baostock_basic.get("basic", {}) if baostock_basic else {}
        bs_industry = baostock_basic.get("industry", {}) if baostock_basic else {}
        return {
            "code": symbol.code,
            "market": symbol.market,
            "exchange": symbol.exchange,
            "name": (
                company_info.get("name")
                or spot.get("name")
                or bs_basic.get("code_name")
            ),
            "industry": (
                company_info.get("industry")
                or bs_industry.get("industry")
                or bs_basic.get("industry")
            ),
            "listing_date": (
                company_info.get("listing_date")
                or bs_basic.get("ipoDate")
            ),
        }

    def build_bundle(
        self,
        raw_code: str,
        years: int = 3,
        notice_limit: int = 20,
        news_limit: int = 20,
        use_cache: bool = True,
        include_news: bool = True,
        include_reports: bool = True,
    ) -> dict[str, Any]:
        symbol = parse_stock_symbol(raw_code)
        today = date.today()
        start_date = date(today.year - years, 1, 1)
        cache_key = (
            f"{symbol.code}-{years}-{notice_limit}-{news_limit}-"
            f"{int(include_news)}-{int(include_reports)}"
        )
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                cached["cache"] = {"hit": True}
                return cached

        data: dict[str, Any] = {}
        statuses: dict[str, Any] = {}
        errors: list[dict[str, str]] = []

        baostock_basic = self._capture(
            data,
            statuses,
            errors,
            "baostock_basic",
            "baostock",
            lambda: self.baostock.fetch_stock_basic(symbol),
            {},
        )
        history = self._capture(
            data,
            statuses,
            errors,
            "history",
            "baostock",
            lambda: self.baostock.fetch_history(
                symbol,
                start_date=start_date.isoformat(),
                end_date=today.isoformat(),
            ),
            [],
        )
        annual_metrics = self._capture(
            data,
            statuses,
            errors,
            "baostock_annual_financials",
            "baostock",
            lambda: self.baostock.fetch_annual_financial_metrics(
                symbol,
                years=max(years, 3),
            ),
            [],
        )
        company_info = self._capture(
            data,
            statuses,
            errors,
            "company_info",
            "akshare",
            lambda: self.akshare.fetch_company_info(symbol),
            {},
        )
        spot = self._capture(
            data,
            statuses,
            errors,
            "market_snapshot",
            "akshare",
            lambda: self.akshare.fetch_spot(symbol),
            {},
        )
        financial_indicators = self._capture(
            data,
            statuses,
            errors,
            "financial_indicators",
            "akshare",
            lambda: self.akshare.fetch_financial_indicators(
                symbol,
                start_year=start_date.year,
            ),
            [],
        )

        if include_reports:
            financial_reports = self._capture(
                data,
                statuses,
                errors,
                "financial_reports",
                "akshare",
                lambda: self.akshare.fetch_financial_reports(symbol),
                {},
            )
        else:
            financial_reports = {}
            data["financial_reports"] = {}
            statuses["financial_reports"] = {
                "provider": "akshare",
                "status": "skipped",
            }

        notice_begin = date(today.year - 1, 1, 1).strftime("%Y%m%d")
        notices = self._capture(
            data,
            statuses,
            errors,
            "notices",
            "akshare",
            lambda: self.akshare.fetch_notices(
                symbol,
                begin_date=notice_begin,
                end_date=today.strftime("%Y%m%d"),
                limit=notice_limit,
            ),
            [],
        )

        if include_news:
            news = self._capture(
                data,
                statuses,
                errors,
                "news",
                "akshare",
                lambda: self.akshare.fetch_news(symbol, limit=news_limit),
                [],
            )
        else:
            news = []
            data["news"] = []
            statuses["news"] = {
                "provider": "akshare",
                "status": "skipped",
            }

        market_indicators = calculate_market_indicators(history)
        stock = self._merge_stock_identity(
            symbol,
            company_info,
            spot,
            baostock_basic,
        )

        bundle = {
            "schema_version": "0.1.0",
            "stock": stock,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "data_window": {
                "start_date": start_date.isoformat(),
                "end_date": today.isoformat(),
                "years": years,
            },
            "market_snapshot": spot,
            "market_indicators": market_indicators,
            "history": history,
            "financials": {
                "akshare_indicators": financial_indicators,
                "akshare_reports": financial_reports,
                "baostock_annual_metrics": annual_metrics,
            },
            "notices": notices,
            "news": news,
            "source_status": statuses,
            "errors": errors,
            "cache": {"hit": False},
            "usage_note": "数据仅用于个人研究和项目演示，不构成投资建议。",
        }

        successful_sections = sum(
            1 for status in statuses.values() if status.get("status") == "ok"
        )
        if successful_sections == 0:
            messages = "；".join(
                dict.fromkeys(error["message"] for error in errors)
            )
            raise StockAIError(f"所有数据源均获取失败：{messages}")

        if use_cache:
            self.cache.set(cache_key, bundle)
        return bundle
