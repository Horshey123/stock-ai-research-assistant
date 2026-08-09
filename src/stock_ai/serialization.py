import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _chinese_character_count(text: str) -> int:
    return sum(1 for character in text if "\u3400" <= character <= "\u9fff")


def repair_mojibake_text(text: str) -> str:
    """Repair common GBK text that was mistakenly decoded as Latin-1.

    Some AKShare upstream responses can contain column names such as ``ÈÕÆÚ``
    instead of ``日期``. Correct UTF-8 Chinese, ASCII, URLs and numbers remain
    unchanged.
    """
    if not text or all(ord(character) < 128 for character in text):
        return text
    try:
        candidate = text.encode("latin1").decode("gb18030")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    if _chinese_character_count(candidate) > _chinese_character_count(text):
        return candidate
    return text


def repair_mojibake(value: Any) -> Any:
    """Recursively repair mojibake in mapping keys and string values."""
    if isinstance(value, str):
        return repair_mojibake_text(value)
    if isinstance(value, dict):
        return {
            repair_mojibake_text(str(key)): repair_mojibake(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [repair_mojibake(item) for item in value]
    if isinstance(value, tuple):
        return tuple(repair_mojibake(item) for item in value)
    return value


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    try:
        result = value != value
        return bool(result)
    except Exception:
        return False


def json_safe(value: Any) -> Any:
    """Recursively convert common pandas/numpy values into JSON-safe values."""
    if is_missing(value):
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def to_float(value: Any) -> float | None:
    if is_missing(value):
        return None
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("%", "")
        if not cleaned or cleaned in {"-", "--", "None", "nan"}:
            return None
        value = cleaned
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def dataframe_records(frame, limit: int | None = None) -> list[dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return []
    selected = frame.head(limit) if limit else frame
    return [
        repair_mojibake(json_safe(record))
        for record in selected.to_dict(orient="records")
    ]
