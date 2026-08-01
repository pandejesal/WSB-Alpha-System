import os
import unittest
from src.utils.config import config

class TestConfig(unittest.TestCase):
    def test_live_trading_disabled_by_default(self):
        self.assertFalse(config.trading.live_trading_enabled, "Live trading MUST be disabled by default.")

    def test_paper_trading_enabled_by_default(self):
        self.assertTrue(config.trading.paper_trading_enabled, "Paper trading should be enabled by default.")

if __name__ == '__main__':
    unittest.main()
