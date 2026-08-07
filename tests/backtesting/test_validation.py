import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from src.backtest import validation

class TestValidation(unittest.TestCase):
    @patch("src.backtest.validation.load_base_data")
    @patch("src.backtest.validation.rb.run_backtest")
    def test_validation_main_execution(self, mock_run_backtest, mock_load_data):
        # Setup dummy data
        dates = pd.date_range("2023-01-01", periods=100)
        spy_close = pd.Series(np.linspace(100, 110, 100), index=dates)

        df = pd.DataFrame({
            "Open": np.linspace(100, 110, 100),
            "High": np.linspace(101, 111, 100),
            "Low": np.linspace(99, 109, 100),
            "Close": np.linspace(100, 110, 100)
        }, index=dates)
        stock_dfs = {"AAPL": df}

        posts_df = pd.DataFrame({
            "ticker": ["AAPL"] * 10,
            "post_date": dates[:10],
            "score": [0.5] * 10
        })

        mock_load_data.return_value = (posts_df, stock_dfs, spy_close)

        # Setup dummy trades for rb.run_backtest
        trades_df = pd.DataFrame({
            "ticker": ["AAPL"] * 5,
            "post_date": dates[:5],
            "return": [0.01, -0.005, 0.02, 0.01, -0.01]
        })
        mock_run_backtest.return_value = trades_df

        # Lower NUM_PERMUTATIONS for speed in testing
        original_num = validation.NUM_PERMUTATIONS
        validation.NUM_PERMUTATIONS = 2

        # Should execute without raising any exceptions
        try:
            with patch("matplotlib.pyplot.savefig"):  # Prevent file write
                validation.main()
        finally:
            validation.NUM_PERMUTATIONS = original_num

if __name__ == "__main__":
    unittest.main()
