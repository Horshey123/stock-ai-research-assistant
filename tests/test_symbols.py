import unittest

from stock_ai.exceptions import InvalidStockCodeError
from stock_ai.symbols import parse_stock_symbol


class StockSymbolTests(unittest.TestCase):
    def test_shanghai_stock(self):
        symbol = parse_stock_symbol("600519")
        self.assertEqual(symbol.market, "sh")
        self.assertEqual(symbol.baostock_code, "sh.600519")
        self.assertEqual(symbol.sina_code, "sh600519")

    def test_shenzhen_stock(self):
        symbol = parse_stock_symbol("000333")
        self.assertEqual(symbol.market, "sz")
        self.assertEqual(symbol.baostock_code, "sz.000333")

    def test_code_can_include_separator(self):
        symbol = parse_stock_symbol("SH-688981")
        self.assertEqual(symbol.code, "688981")
        self.assertEqual(symbol.market, "sh")

    def test_rejects_beijing_stock(self):
        with self.assertRaises(InvalidStockCodeError):
            parse_stock_symbol("920001")

    def test_rejects_non_stock_security(self):
        with self.assertRaises(InvalidStockCodeError):
            parse_stock_symbol("510300")


if __name__ == "__main__":
    unittest.main()

