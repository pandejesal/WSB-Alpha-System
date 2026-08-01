import unittest
from src.backtest.vectorbt_engine import VectorBTEngine
import pandas as pd
import numpy as np

class MockStrategy:
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['signal'] = 0
        df.iloc[0, df.columns.get_loc('signal')] = 1
        df.iloc[-1, df.columns.get_loc('signal')] = -1
        return df

class TestVectorBTEngine(unittest.TestCase):
    def test_engine_executes_simulation(self):
        engine = VectorBTEngine()
        # Generate dummy data
        dates = pd.date_range("2023-01-01", periods=10)
        df = pd.DataFrame({"Close": np.linspace(100, 110, 10)}, index=dates)

        res = engine.run_backtest(df, MockStrategy())
        self.assertEqual(res["status"], "success")
        self.assertIn("total_return", res["metrics"])
        self.assertGreater(res["metrics"]["total_return"], 0)

if __name__ == '__main__':
    unittest.main()
