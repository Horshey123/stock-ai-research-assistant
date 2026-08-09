import tempfile
import unittest
from pathlib import Path

from stock_ai.cache import JsonCache


class CacheTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = JsonCache(Path(directory))
            cache.set("600519-3", {"stock": {"code": "600519"}})
            value = cache.get("600519-3")
            self.assertEqual(value["stock"]["code"], "600519")


if __name__ == "__main__":
    unittest.main()

