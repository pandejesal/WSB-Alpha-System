import unittest
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.alpha.indicators import compute_indicators

class TestIndicators(unittest.TestCase):
    def setUp(self):
        # Create dummy data of at least 20 rows
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=25)
        data = {
            "Open": np.random.uniform(100, 110, 25),
            "High": np.random.uniform(110, 120, 25),
            "Low": np.random.uniform(90, 100, 25),
            "Close": np.random.uniform(100, 110, 25)
        }
        self.df = pd.DataFrame(data, index=dates)

    def test_compute_indicators(self):
        result_df = compute_indicators(self.df)
        self.assertIsNotNone(result_df)

        # Check required columns are present
        required_cols = ["EMA_20", "RSI_14", "MACD", "HA_Close", "GK_Vol"]
        for col in required_cols:
            self.assertIn(col, result_df.columns, f"{col} missing from results")

        # Check they have non-null values
        for col in required_cols:
            self.assertTrue(result_df[col].notna().any(), f"{col} is entirely null")

if __name__ == '__main__':
    unittest.main()
