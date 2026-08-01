import unittest
import pandas as pd
import numpy as np
from backtesting.custom_engine import CustomEngine

class MockStrategy:
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['signal'] = 1
        return df

class TestCustomEngine(unittest.TestCase):
    def test_custom_engine_execution(self):
        engine = CustomEngine()
        dates = pd.date_range("2023-01-01", periods=20)
        df = pd.DataFrame({
            "Open": np.linspace(100, 110, 20),
            "High": np.linspace(101, 111, 20),
            "Low": np.linspace(99, 109, 20),
            "Close": np.linspace(100, 110, 20)
        }, index=dates)

        res = engine.run_backtest(df, MockStrategy())
        self.assertEqual(res["status"], "success")
        self.assertIn("Cumulative_Return", res["portfolio"].columns)
