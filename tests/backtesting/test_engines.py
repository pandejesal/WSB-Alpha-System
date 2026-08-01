import unittest
from backtesting.vectorbt_engine import VectorBTEngine
import pandas as pd

class TestVectorBTEngine(unittest.TestCase):
    def test_engine_initializes(self):
        engine = VectorBTEngine()
        df = pd.DataFrame({"close": [100, 101, 102]})
        res = engine.run_backtest(df, None)
        self.assertIn("status", res)

if __name__ == '__main__':
    unittest.main()
