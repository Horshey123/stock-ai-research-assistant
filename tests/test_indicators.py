import unittest
from datetime import date, timedelta

from stock_ai.indicators import calculate_market_indicators


class IndicatorTests(unittest.TestCase):
    def test_uptrend_and_valuation_percentile(self):
        start = date(2025, 1, 1)
        history = []
        for index in range(260):
            history.append(
                {
                    "date": (start + timedelta(days=index)).isoformat(),
                    "close": str(10 + index * 0.05),
                    "volume": str(1000 + index),
                    "peTTM": str(10 + index / 50),
                    "pbMRQ": str(1 + index / 500),
                }
            )

        result = calculate_market_indicators(history)

        self.assertEqual(result["trend_state"], "上升")
        self.assertEqual(result["history_rows"], 260)
        self.assertGreater(result["latest_close"], result["ma20"])
        self.assertGreaterEqual(result["pe_history_percentile"], 99)
        self.assertIsNotNone(result["annualized_volatility_percent"])

    def test_empty_history(self):
        self.assertEqual(calculate_market_indicators([]), {})

    def test_invalid_rows_are_ignored(self):
        result = calculate_market_indicators(
            [
                {"date": "2026-01-01", "close": "--"},
                {"date": "2026-01-02", "close": "12.5"},
            ]
        )
        self.assertEqual(result["history_rows"], 1)
        self.assertEqual(result["latest_close"], 12.5)


if __name__ == "__main__":
    unittest.main()

