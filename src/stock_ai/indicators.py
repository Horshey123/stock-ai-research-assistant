import math
from statistics import pstdev
from typing import Any

from stock_ai.serialization import to_float


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _rounded(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _percentile_rank(values: list[float], current: float | None) -> float | None:
    if current is None or not values:
        return None
    usable = [value for value in values if value > 0]
    if not usable:
        return None
    rank = sum(1 for value in usable if value <= current) / len(usable) * 100
    return rank


def calculate_market_indicators(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate deterministic trend, risk and valuation features."""
    rows: list[dict[str, Any]] = []
    for record in history:
        close = to_float(record.get("close"))
        if close is None or close <= 0:
            continue
        rows.append(
            {
                "date": str(record.get("date", "")),
                "close": close,
                "volume": to_float(record.get("volume")),
                "pe": to_float(record.get("peTTM")),
                "pb": to_float(record.get("pbMRQ")),
            }
        )
    rows.sort(key=lambda row: row["date"])
    if not rows:
        return {}

    closes = [row["close"] for row in rows]
    volumes = [row["volume"] for row in rows if row["volume"] is not None]
    latest = rows[-1]

    def moving_average(window: int) -> float | None:
        if len(closes) < window:
            return None
        return _mean(closes[-window:])

    ma20 = moving_average(20)
    ma60 = moving_average(60)
    ma120 = moving_average(120)

    log_returns = [
        math.log(current / previous)
        for previous, current in zip(closes, closes[1:])
        if previous > 0 and current > 0
    ]
    volatility = (
        pstdev(log_returns[-252:]) * math.sqrt(252) * 100
        if len(log_returns) >= 2
        else None
    )

    peak = closes[0]
    max_drawdown = 0.0
    for close in closes:
        peak = max(peak, close)
        drawdown = (close / peak - 1) * 100
        max_drawdown = min(max_drawdown, drawdown)

    change_1y = None
    if len(closes) >= 2:
        base_index = max(0, len(closes) - 253)
        base = closes[base_index]
        change_1y = (closes[-1] / base - 1) * 100 if base > 0 else None

    if ma20 is not None and ma60 is not None:
        if closes[-1] > ma20 > ma60:
            trend = "上升"
        elif closes[-1] < ma20 < ma60:
            trend = "下降"
        else:
            trend = "震荡"
    else:
        trend = "数据不足"

    recent_volume = _mean(volumes[-5:]) if len(volumes) >= 5 else None
    baseline_volume = _mean(volumes[-25:-5]) if len(volumes) >= 25 else None
    volume_ratio = (
        recent_volume / baseline_volume
        if recent_volume is not None and baseline_volume not in (None, 0)
        else None
    )

    pe_values = [row["pe"] for row in rows if row["pe"] is not None and row["pe"] > 0]
    pb_values = [row["pb"] for row in rows if row["pb"] is not None and row["pb"] > 0]

    return {
        "latest_trade_date": latest["date"],
        "latest_close": _rounded(latest["close"]),
        "ma20": _rounded(ma20),
        "ma60": _rounded(ma60),
        "ma120": _rounded(ma120),
        "trend_state": trend,
        "change_1y_percent": _rounded(change_1y, 2),
        "annualized_volatility_percent": _rounded(volatility, 2),
        "max_drawdown_percent": _rounded(max_drawdown, 2),
        "recent_volume_ratio_5_to_20": _rounded(volume_ratio, 2),
        "pe_ttm": _rounded(latest["pe"]),
        "pe_history_percentile": _rounded(
            _percentile_rank(pe_values, latest["pe"]),
            2,
        ),
        "pb_mrq": _rounded(latest["pb"]),
        "pb_history_percentile": _rounded(
            _percentile_rank(pb_values, latest["pb"]),
            2,
        ),
        "history_rows": len(rows),
    }

