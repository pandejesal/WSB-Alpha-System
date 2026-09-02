import os
import unittest
from src.utils.config import config

class TestConfig(unittest.TestCase):
    def test_live_trading_disabled_by_default(self):
        self.assertFalse(config.trading.live_trading_enabled, "Live trading MUST be disabled by default.")

    def test_paper_trading_enabled_by_default(self):
        self.assertTrue(config.trading.paper_trading_enabled, "Paper trading should be enabled by default.")

    def test_benchmark_spider_defaults(self):
        bs = config.benchmark_spider
        self.assertTrue(bs.enabled, "Benchmark spider should be enabled by default.")
        self.assertEqual(bs.symbol, "SPY", "Benchmark symbol should be SPY.")
        self.assertEqual(bs.lookback_days, 252, "Lookback should be 252 trading days.")
        self.assertAlmostEqual(bs.min_sharpe_ratio, 0.5, msg="Min Sharpe ratio should be 0.5.")
        self.assertAlmostEqual(bs.max_drawdown_pct, 0.15, msg="Max drawdown should be 0.15.")

    def test_benchmark_spider_accessible_from_config(self):
        self.assertTrue(hasattr(config, 'benchmark_spider'), "ConfigWrapper should expose benchmark_spider.")

if __name__ == '__main__':
    unittest.main()