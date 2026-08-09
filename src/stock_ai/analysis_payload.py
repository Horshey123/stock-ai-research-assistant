from __future__ import annotations

from typing import Any

from stock_ai.serialization import repair_mojibake


HISTORY_FIELDS = (
    "date",
    "close",
    "pctChg",
    "volume",
    "amount",
    "turn",
    "peTTM",
    "pbMRQ",
)

ANNUAL_METRIC_FIELDS = (
    "period",
    "pubDate",
    "statDate",
    "profit.roeAvg",
    "profit.npMargin",
    "profit.gpMargin",
    "profit.netProfit",
    "profit.epsTTM",
    "profit.MBRevenue",
    "growth.YOYEquity",
    "growth.YOYAsset",
    "growth.YOYNI",
    "growth.YOYEPSBasic",
    "growth.YOYPNI",
    "balance.currentRatio",
    "balance.quickRatio",
    "balance.cashRatio",
    "balance.YOYLiability",
    "balance.liabilityToAsset",
    "balance.assetToEquity",
    "cash_flow.CFOToOR",
    "cash_flow.CFOToNP",
    "cash_flow.CFOToGr",
)

FINANCIAL_INDICATOR_TOKENS = (
    "日期",
    "每股收益",
    "每股经营性现金流",
    "销售净利率",
    "销售毛利率",
    "净资产收益率",
    "主营业务收入增长率",
    "净利润增长率",
    "总资产增长率",
    "应收账款周转率",
    "存货周转率",
    "流动比率",
    "速动比率",
    "资产负债率",
)

REPORT_FIELD_TOKENS = (
    "报告日",
    "更新日期",
    "货币资金",
    "应收票据",
    "应收账款",
    "存货",
    "流动资产合计",
    "非流动资产合计",
    "资产总计",
    "短期借款",
    "长期借款",
    "流动负债合计",
    "非流动负债合计",
    "负债合计",
    "股东权益",
    "营业总收入",
    "营业收入",
    "营业总成本",
    "营业成本",
    "营业利润",
    "利润总额",
    "净利润",
    "基本每股收益",
    "经营活动产生的现金流量净额",
    "投资活动产生的现金流量净额",
    "筹资活动产生的现金流量净额",
    "现金及现金等价物净增加额",
    "销售商品、提供劳务收到的现金",
)


def _compact_record(
    record: dict[str, Any],
    *,
    exact_fields: tuple[str, ...] = (),
    field_tokens: tuple[str, ...] = (),
) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in record.items():
        key_text = str(key)
        if value in (None, ""):
            continue
        if key_text in exact_fields or any(
            token in key_text for token in field_tokens
        ):
            compact[key_text] = value
    return compact


def _latest_rows(rows: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    usable = [row for row in rows if isinstance(row, dict)]
    return usable[:limit]


def _recent_history(rows: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    usable = [row for row in rows if isinstance(row, dict)]
    selected = usable[-limit:]
    return [
        _compact_record(row, exact_fields=HISTORY_FIELDS)
        for row in selected
    ]


def _compact_reports(
    reports: Any,
    periods_per_report: int,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(reports, dict):
        return {}
    compact: dict[str, list[dict[str, Any]]] = {}
    for report_name, rows in reports.items():
        if str(report_name).endswith("_error") or not isinstance(rows, list):
            continue
        selected = []
        for row in _latest_rows(rows, periods_per_report):
            item = _compact_record(row, field_tokens=REPORT_FIELD_TOKENS)
            if item:
                selected.append(item)
        compact[str(report_name)] = selected
    return compact


def _compact_notices(rows: Any, limit: int) -> list[dict[str, Any]]:
    fields = ("代码", "名称", "公告标题", "公告类型", "公告日期", "网址")
    return [
        _compact_record(row, exact_fields=fields)
        for row in _latest_rows(rows, limit)
    ]


def _compact_news(rows: Any, limit: int) -> list[dict[str, Any]]:
    fields = ("关键词", "新闻标题", "新闻内容", "发布时间", "文章来源", "新闻链接")
    compact: list[dict[str, Any]] = []
    for row in _latest_rows(rows, limit):
        item = _compact_record(row, exact_fields=fields)
        content = item.get("新闻内容")
        if isinstance(content, str) and len(content) > 300:
            item["新闻内容"] = content[:300] + "..."
        compact.append(item)
    return compact


def build_analysis_context(
    bundle: dict[str, Any],
    *,
    history_points: int = 60,
    financial_periods: int = 8,
    report_periods: int = 4,
    notice_limit: int = 8,
    news_limit: int = 8,
) -> dict[str, Any]:
    """Build a small, evidence-focused payload for the language model."""
    cleaned = repair_mojibake(bundle)
    financials = cleaned.get("financials", {})
    if not isinstance(financials, dict):
        financials = {}

    annual_rows = []
    for row in _latest_rows(
        financials.get("baostock_annual_metrics"),
        financial_periods,
    ):
        item = _compact_record(row, exact_fields=ANNUAL_METRIC_FIELDS)
        if item:
            annual_rows.append(item)

    indicator_rows = []
    for row in _latest_rows(
        financials.get("akshare_indicators"),
        financial_periods,
    ):
        item = _compact_record(row, field_tokens=FINANCIAL_INDICATOR_TOKENS)
        if item:
            indicator_rows.append(item)

    statuses = cleaned.get("source_status", {})
    data_quality = {
        str(key): value.get("status")
        for key, value in statuses.items()
        if isinstance(value, dict)
    } if isinstance(statuses, dict) else {}

    return {
        "context_schema_version": "0.1.0",
        "stock": cleaned.get("stock", {}),
        "data_generated_at": cleaned.get("generated_at"),
        "data_window": cleaned.get("data_window", {}),
        "market_snapshot": cleaned.get("market_snapshot", {}),
        "market_indicators": cleaned.get("market_indicators", {}),
        "recent_daily_history": _recent_history(
            cleaned.get("history"),
            max(1, history_points),
        ),
        "financials": {
            "annual_metrics": annual_rows,
            "detailed_indicators": indicator_rows,
            "reports": _compact_reports(
                financials.get("akshare_reports"),
                max(1, report_periods),
            ),
        },
        "recent_notices": _compact_notices(
            cleaned.get("notices"),
            max(1, notice_limit),
        ),
        "recent_news": _compact_news(
            cleaned.get("news"),
            max(1, news_limit),
        ),
        "data_quality": {
            "source_status": data_quality,
            "known_errors": cleaned.get("errors", []),
            "rule": "缺失数据必须标记为未知，不得猜测或补造。",
        },
    }
