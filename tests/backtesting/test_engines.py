import sys
import unittest

import numpy as np
import pandas as pd
import pytest

from src.backtest.engines.vectorbt_engine import VectorBTEngine


class TestVectorBTEngine(unittest.TestCase):
    @pytest.mark.skipif(sys.version_info >= (3, 13), reason="VectorBT+numba incompatible with Python 3.13 (TypingError non-precise array(pyobject)) - requires Python 3.11/3.12")
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
