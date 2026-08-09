from dataclasses import dataclass

from stock_ai.exceptions import InvalidStockCodeError


@dataclass(frozen=True)
class StockSymbol:
    code: str
    market: str

    @property
    def baostock_code(self) -> str:
        return f"{self.market}.{self.code}"

    @property
    def sina_code(self) -> str:
        return f"{self.market}{self.code}"

    @property
    def exchange(self) -> str:
        return "SSE" if self.market == "sh" else "SZSE"


def parse_stock_symbol(raw_code: str) -> StockSymbol:
    """Normalize a six-digit Shanghai/Shenzhen A-share code."""
    code = "".join(character for character in str(raw_code).strip() if character.isdigit())
    if len(code) != 6:
        raise InvalidStockCodeError("股票代码必须是6位数字，例如 600519 或 000333。")

    if code.startswith(("600", "601", "603", "605", "688", "689")):
        market = "sh"
    elif code.startswith(("000", "001", "002", "003", "300", "301")):
        market = "sz"
    elif code.startswith(("4", "8", "920")):
        raise InvalidStockCodeError("首版暂不支持北交所股票，请先使用沪深A股。")
    else:
        raise InvalidStockCodeError(
            f"{code} 不在首版支持的沪深A股代码范围内。"
        )

    return StockSymbol(code=code, market=market)
