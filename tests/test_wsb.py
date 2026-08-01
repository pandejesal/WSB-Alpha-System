import unittest
import pandas as pd
import numpy as np
from analytics.indicators import compute_indicators
from research.nlp_utils import extract_tickers
from strategy_generation.wsb_alpha_legacy import extract_tickers

class TestIndicators(unittest.TestCase):
    def test_compute_indicators_less_than_20(self):
        df = pd.DataFrame({"Close": [1] * 19})
        self.assertIsNone(compute_indicators(df))

    def test_compute_indicators_valid(self):
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=30)
        df = pd.DataFrame({
            "Open": np.random.randn(30) + 100,
            "High": np.random.randn(30) + 102,
            "Low": np.random.randn(30) + 98,
            "Close": np.random.randn(30) + 101,
        }, index=dates)
        res = compute_indicators(df)
        self.assertIsNotNone(res)
        self.assertIn("EMA_20", res.columns)
        self.assertIn("RSI_14", res.columns)
        self.assertIn("MACD", res.columns)

class TestNLP(unittest.TestCase):
    def test_extract_tickers_casing(self):
        text = "HE is fine, buy AAPL but not HE. I also like TSLA and gap."
        tickers = extract_tickers(text)
        self.assertIn("AAPL", tickers)
        self.assertIn("TSLA", tickers)
        self.assertNotIn("HE", tickers)
        self.assertNotIn("GAP", tickers) # lowercase 'gap' shouldn't match regex

if __name__ == '__main__':
    unittest.main()
