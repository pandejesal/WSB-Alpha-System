import unittest
import pandas as pd
import numpy as np
from walk_forward.walk_forward_engine import WalkForwardValidator
from strategy_validation.whites_reality_check import WhitesRealityCheck

class TestAdvancedValidation(unittest.TestCase):
    def test_walk_forward(self):
        df = pd.DataFrame({"Close": np.random.randn(500)}, index=pd.date_range("2020-01-01", periods=500))
        validator = WalkForwardValidator(train_window_days=100, test_window_days=20)

        def mock_eval(df_slice):
            return df_slice["Close"].mean()

        res = validator.validate(df, mock_eval)
        self.assertIn("status", res)
        self.assertIn("windows_tested", res)
        self.assertGreater(res["windows_tested"], 0)

    def test_whites_reality_check(self):
        np.random.seed(42)
        benchmark = pd.Series(np.random.normal(0.0001, 0.01, 100))
        # 3 garbage strategies, 1 slightly good one
        strategies = pd.DataFrame({
            "S1": np.random.normal(-0.0001, 0.01, 100),
            "S2": np.random.normal(0.0000, 0.01, 100),
            "S3": np.random.normal(0.0002, 0.01, 100),
            "S4_Good": np.random.normal(0.005, 0.01, 100) # Unlikely to be just luck
        })

        wrc = WhitesRealityCheck(n_bootstraps=100)
        res = wrc.test(benchmark, strategies)
        self.assertIn("p_value", res)
        self.assertEqual(res["best_strategy"], "S4_Good")
        self.assertEqual(res["status"], "PASSED")

if __name__ == '__main__':
    unittest.main()
