import unittest
import pandas as pd
import numpy as np
from strategy_generation.strategy_man_ahl import ManAHLStrategy
from strategy_generation.strategy_wsb_alpha import WSBAlphaStrategy

class TestStrategies(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=200)
        self.df = pd.DataFrame({
            "Open": np.random.randn(200) + 100,
            "High": np.random.randn(200) + 105,
            "Low": np.random.randn(200) + 95,
            "Close": np.random.randn(200) + 100,
            "Volume": np.random.randint(100, 1000, 200)
        }, index=dates)

    def test_man_ahl_strategy(self):
        strategy = ManAHLStrategy(windows=[5, 10], vol_window=20)
        df_res = strategy.generate_signals(self.df.copy())
        self.assertIn('signal', df_res.columns)
        self.assertTrue(set(df_res['signal'].unique()).issubset({-1, 0, 1}))

    def test_wsb_alpha_strategy(self):
        strategy = WSBAlphaStrategy()
        df_res = strategy.generate_signals(self.df.copy())
        self.assertIn('signal', df_res.columns)
        self.assertTrue(set(df_res['signal'].unique()).issubset({-1, 0, 1}))
