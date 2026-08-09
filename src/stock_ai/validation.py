from __future__ import annotations

import copy
import re
from typing import Any

from stock_ai.serialization import to_float


SCORE_LIMITS = {
    "fundamental": 30,
    "growth": 20,
    "valuation": 20,
    "trend": 15,
    "risk_control": 15,
}

MA_LABELS = ("ma20", "ma60", "ma120")


def _format_number(value: float | None) -> str:
    if value is None:
        return "未知"
    return f"{value:.2f}"


def _percentile_band(value: float | None) -> str:
    if value is None:
        return "未知"
    if value <= 20:
        return "历史较低区间"
    if value >= 80:
        return "历史较高区间"
    return "历史中间区间"


def build_verified_facts(context: dict[str, Any]) -> dict[str, Any]:
    """Generate deterministic facts that the model must not contradict."""
    indicators = context.get("market_indicators", {})
    if not isinstance(indicators, dict):
        indicators = {}

    close = to_float(indicators.get("latest_close"))
    moving_averages: dict[str, dict[str, Any]] = {}
    relation_parts: list[str] = []
    for key in MA_LABELS:
        value = to_float(indicators.get(key))
        if close is None or value is None:
            relation = "unknown"
            relation_text = "关系未知"
        elif close > value:
            relation = "above"
            relation_text = "高于"
        elif close < value:
            relation = "below"
            relation_text = "低于"
        else:
            relation = "equal"
            relation_text = "基本持平"
        label = key.upper()
        moving_averages[label] = {
            "value": value,
            "close_relation": relation,
            "close_relation_text": relation_text,
        }
        if value is not None:
            relation_parts.append(
                f"{relation_text}{label}({_format_number(value)})"
            )

    if close is None:
        market_position_summary = "最新收盘价未知，无法校验均线位置。"
    elif relation_parts:
        market_position_summary = (
            f"最新收盘价{_format_number(close)}，"
            + "、".join(relation_parts)
            + "。"
        )
    else:
        market_position_summary = (
            f"最新收盘价{_format_number(close)}，均线数据不足。"
        )

    pe = to_float(indicators.get("pe_ttm"))
    pe_percentile = to_float(indicators.get("pe_history_percentile"))
    pb = to_float(indicators.get("pb_mrq"))
    pb_percentile = to_float(indicators.get("pb_history_percentile"))
    change_1y = to_float(indicators.get("change_1y_percent"))

    statuses = context.get("data_quality", {}).get("source_status", {})
    if not isinstance(statuses, dict):
        statuses = {}
    missing_sections = [
        str(key)
        for key, status in statuses.items()
        if status not in {"ok", "skipped"}
    ]

    return {
        "latest_trade_date": indicators.get("latest_trade_date"),
        "market_position": {
            "latest_close": close,
            "moving_averages": moving_averages,
            "summary": market_position_summary,
        },
        "valuation": {
            "pe_ttm": pe,
            "pe_history_percentile": pe_percentile,
            "pe_band": _percentile_band(pe_percentile),
            "pb_mrq": pb,
            "pb_history_percentile": pb_percentile,
            "pb_band": _percentile_band(pb_percentile),
        },
        "performance": {
            "change_1y_percent": change_1y,
            "direction": (
                "上涨"
                if change_1y is not None and change_1y > 0
                else "下跌"
                if change_1y is not None and change_1y < 0
                else "持平"
                if change_1y == 0
                else "未知"
            ),
        },
        "data_availability": {
            "missing_or_failed_sections": missing_sections,
            "market_snapshot_available": bool(context.get("market_snapshot")),
        },
    }


def _below_claim(text: str, label: str) -> bool:
    patterns = (
        rf"(?:低于|小于)\s*{label}",
        rf"{label}(?:\s*[（(][^）)]*[）)])?"
        rf"[^，。；;\n]{{0,30}}(?:下方|之下)",
        rf"(?:未能|未|没有|尚未)(?:有效)?(?:突破|站上)"
        rf"[^，。；;\n]{{0,8}}{label}",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _above_claim(text: str, label: str) -> bool:
    patterns = (
        rf"(?:高于|大于)\s*{label}",
        rf"{label}(?:\s*[（(][^）)]*[）)])?"
        rf"[^，。；;\n]{{0,12}}(?:上方|之上)",
        rf"(?:已经|已|成功)(?:有效)?(?:突破|站上)[^。；;\n]{{0,8}}{label}",
        rf"(?:当前|股价|价格|收盘价)[^。；;\n]{{0,12}}"
        rf"(?<!未)(?<!没有)(?<!尚未)(?:突破|站上)[^。；;\n]{{0,8}}{label}",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _sentence_conflicts(
    sentence: str,
    moving_averages: dict[str, Any],
) -> list[str]:
    conditional_markers = (
        "若",
        "如果",
        "一旦",
        "除非",
        "有望",
        "可能",
        "预计",
        "挑战",
        "目标",
        "需要",
        "需确认",
        "能否",
        "无法",
    )
    if any(marker in sentence for marker in conditional_markers):
        return []
    conflicts: list[str] = []
    for label, item in moving_averages.items():
        if not isinstance(item, dict) or label.lower() not in sentence.lower():
            continue
        relation = item.get("close_relation")
        if relation == "above" and _below_claim(sentence, label):
            conflicts.append(label)
        elif relation == "below" and _above_claim(sentence, label):
            conflicts.append(label)
    return conflicts


def _correct_market_text(
    text: str,
    moving_averages: dict[str, Any],
    canonical_summary: str,
) -> tuple[str, list[dict[str, Any]]]:
    parts = re.split(r"([。！？；;，,\n])", text)
    corrected_parts: list[str] = []
    corrections: list[dict[str, Any]] = []
    for index in range(0, len(parts), 2):
        sentence = parts[index]
        separator = parts[index + 1] if index + 1 < len(parts) else ""
        conflicts = _sentence_conflicts(sentence, moving_averages)
        if conflicts:
            replacement = canonical_summary.rstrip("。")
            corrections.append(
                {
                    "code": "moving_average_relation",
                    "affected_indicators": conflicts,
                    "original": sentence.strip(),
                    "corrected": replacement,
                }
            )
            corrected_parts.extend([replacement, separator or "。"])
        else:
            corrected_parts.extend([sentence, separator])
    return "".join(corrected_parts), corrections


def _walk_and_correct_text(
    value: Any,
    *,
    path: str,
    moving_averages: dict[str, Any],
    canonical_summary: str,
    corrections: list[dict[str, Any]],
) -> Any:
    if isinstance(value, str):
        corrected, found = _correct_market_text(
            value,
            moving_averages,
            canonical_summary,
        )
        for item in found:
            item["path"] = path
            corrections.append(item)
        return corrected
    if isinstance(value, list):
        return [
            _walk_and_correct_text(
                item,
                path=f"{path}[{index}]",
                moving_averages=moving_averages,
                canonical_summary=canonical_summary,
                corrections=corrections,
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            key: _walk_and_correct_text(
                item,
                path=f"{path}.{key}" if path else str(key),
                moving_averages=moving_averages,
                canonical_summary=canonical_summary,
                corrections=corrections,
            )
            for key, item in value.items()
            if key not in {"validation", "verified_facts"}
        }
    return value


def validate_and_correct_report(
    report: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Validate deterministic claims and return a corrected report copy."""
    corrected_report = copy.deepcopy(report)
    facts = context.get("verified_facts")
    if not isinstance(facts, dict):
        facts = build_verified_facts(context)

    corrections: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    checks: list[dict[str, Any]] = []

    stock = context.get("stock", {})
    if isinstance(stock, dict):
        expected_stock = {
            "code": stock.get("code"),
            "name": stock.get("name"),
            "industry": stock.get("industry"),
        }
        if corrected_report.get("stock") != expected_stock:
            corrections.append(
                {
                    "code": "stock_identity",
                    "path": "stock",
                    "original": corrected_report.get("stock"),
                    "corrected": expected_stock,
                }
            )
            corrected_report["stock"] = expected_stock
            checks.append({"code": "stock_identity", "status": "corrected"})
        else:
            checks.append({"code": "stock_identity", "status": "passed"})

    scorecard = corrected_report.get("scorecard")
    total = 0
    valid_scores = True
    if not isinstance(scorecard, dict):
        valid_scores = False
        warnings.append(
            {
                "code": "scorecard_missing",
                "message": "报告缺少评分明细，无法校验综合评分。",
            }
        )
    else:
        for key, maximum in SCORE_LIMITS.items():
            item = scorecard.get(key)
            if not isinstance(item, dict):
                valid_scores = False
                warnings.append(
                    {
                        "code": "score_missing",
                        "message": f"缺少{key}评分。",
                    }
                )
                continue
            try:
                original_score = item.get("score")
                score = int(round(float(original_score)))
            except (TypeError, ValueError):
                valid_scores = False
                warnings.append(
                    {
                        "code": "score_invalid",
                        "message": f"{key}评分不是有效数字。",
                    }
                )
                continue
            clamped_score = max(0, min(maximum, score))
            if clamped_score != score:
                corrections.append(
                    {
                        "code": "score_range",
                        "path": f"scorecard.{key}.score",
                        "original": original_score,
                        "corrected": clamped_score,
                    }
                )
                item["score"] = clamped_score
            total += clamped_score

    overall = corrected_report.get("overall")
    if valid_scores and isinstance(overall, dict):
        original_total = overall.get("total_score")
        try:
            reported_total = int(round(float(original_total)))
        except (TypeError, ValueError):
            reported_total = None
        if reported_total != total:
            corrections.append(
                {
                    "code": "score_total",
                    "path": "overall.total_score",
                    "original": original_total,
                    "corrected": total,
                }
            )
            overall["total_score"] = total
            checks.append({"code": "score_total", "status": "corrected"})
        else:
            checks.append({"code": "score_total", "status": "passed"})
    elif not isinstance(overall, dict):
        warnings.append(
            {
                "code": "overall_missing",
                "message": "报告缺少综合结论结构。",
            }
        )

    market_position = facts.get("market_position", {})
    moving_averages = market_position.get("moving_averages", {})
    canonical_summary = str(market_position.get("summary", ""))
    text_corrections: list[dict[str, Any]] = []
    if isinstance(moving_averages, dict) and canonical_summary:
        corrected_report = _walk_and_correct_text(
            corrected_report,
            path="",
            moving_averages=moving_averages,
            canonical_summary=canonical_summary,
            corrections=text_corrections,
        )
    corrections.extend(text_corrections)
    checks.append(
        {
            "code": "moving_average_relation",
            "status": "corrected" if text_corrections else "passed",
            "fact": canonical_summary,
        }
    )

    data_availability = facts.get("data_availability", {})
    if isinstance(data_availability, dict):
        missing = data_availability.get("missing_or_failed_sections", [])
        if missing:
            warnings.append(
                {
                    "code": "source_data_missing",
                    "message": "以下数据模块缺失或失败："
                    + "、".join(str(item) for item in missing),
                }
            )

    analysis = corrected_report.get("analysis")
    technical = analysis.get("technical", {}) if isinstance(analysis, dict) else {}
    if isinstance(technical, dict) and canonical_summary:
        evidence = technical.get("evidence")
        if not isinstance(evidence, list):
            evidence = []
        if canonical_summary not in evidence:
            evidence.insert(0, canonical_summary)
        technical["evidence"] = evidence

    corrected_report["verified_facts"] = facts
    if corrections:
        status = "corrected"
    elif warnings:
        status = "warning"
    else:
        status = "passed"
    corrected_report["validation"] = {
        "version": "0.1.0",
        "status": status,
        "checks": checks,
        "corrections_count": len(corrections),
        "corrections": corrections,
        "warnings_count": len(warnings),
        "warnings": warnings,
        "note": "程序仅校验可确定的数字和逻辑关系，主观判断仍需人工复核。",
    }
    return corrected_report
