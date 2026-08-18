import unittest

import numpy as np
import pandas as pd

from src.backtest.engines.vectorbt_engine import VectorBTEngine


class TestVectorBTEngine(unittest.TestCase):
    def test_engine_executes_simulation(self):
        engine = VectorBTEngine()
        # Generate dummy data
        dates = pd.date_range("2023-01-01", periods=100)
        # Create data that will trigger MA crossovers
        prices = np.linspace(100, 150, 50).tolist() + np.linspace(150, 100, 50).tolist()
        df = pd.DataFrame({"Close": prices}, index=dates)

        res = engine.run_sim({'fast_window': 2, 'slow_window': 5}, df)
        self.assertIsInstance(res, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()
