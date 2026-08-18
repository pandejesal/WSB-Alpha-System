import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.backtest.engines.vectorbt_engine import VectorBTEngine
from src.backtest.validators.statistical import StatisticalValidator
from src.risk.portfolio_optimization import PortfolioOptimizer


class TestQuantPhase3(unittest.TestCase):

    def test_t1_execution_rule(self):
        engine = VectorBTEngine()

        signals_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01 14:00:00', '2023-01-02 09:30:00'])
        })

        ohlcv_df = pd.DataFrame() # not strictly needed for the isolated method right now

        processed = engine.apply_t1_execution_rule(signals_df, ohlcv_df)

        # Check T+1 logic: execution should be next day stripped of time
        expected_exec_dates = pd.to_datetime(['2023-01-02', '2023-01-03'])

        for i in range(len(processed)):
            self.assertEqual(processed.iloc[i]['execution_date'], expected_exec_dates[i])
            self.assertTrue(processed.iloc[i]['execution_date'] > processed.iloc[i]['timestamp'])

    def test_whites_reality_check(self):
        np.random.seed(42)
        # Mock random strategy returns (mean 0)
        num_strats = 5
        n_days = 252
        random_strats = np.random.normal(0, 0.01, (n_days, num_strats))

        # Benchmark
        benchmark = np.random.normal(0, 0.01, n_days)

        p_val = StatisticalValidator.whites_reality_check(random_strats, benchmark, replications=100)

        # Because strategies are just random noise, p-value should generally not be significant
        # (p-value shouldn't be very small, meaning we fail to reject the null that best strat is just luck)
        # We can't guarantee a strict bound due to randomness, but it should be a valid float
        self.assertIsInstance(p_val, float)
        self.assertTrue(0.0 <= p_val <= 1.0)

        # We can also test with a strategy that clearly outperforms
        good_strat = benchmark + 0.05
        p_val_good = StatisticalValidator.whites_reality_check(good_strat, benchmark, replications=100)
        self.assertLess(p_val_good, 0.05) # Should be significant

    def test_portfolio_cvar_allocator(self):
        np.random.seed(42)
        returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 100),
            'MSFT': np.random.normal(0.001, 0.015, 100),
            'GOOG': np.random.normal(0.001, 0.025, 100),
            'NVDA': np.random.normal(0.002, 0.04, 100)
        })

        optimizer = PortfolioOptimizer(risk_measure='CVaR')
        weights = optimizer.optimize_cvar(returns, max_weight=0.25, min_cash=0.10)

        self.assertFalse(weights.empty)

        total_weight = weights.sum()
        # Due to floating point math, check if it's close to 0.90
        self.assertAlmostEqual(total_weight, 0.90, places=4)

        # Check max weight constraint
        max_alloc = weights.max()
        self.assertLessEqual(max_alloc, 0.2501)

    def test_portfolio_erc_allocator(self):
        np.random.seed(42)
        returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 100),
            'MSFT': np.random.normal(0.001, 0.015, 100),
            'GOOG': np.random.normal(0.001, 0.025, 100)
        })

        optimizer = PortfolioOptimizer(risk_measure='CVaR')
        weights = optimizer.optimize_erc(returns, max_weight=0.25, min_cash=0.10)

        self.assertFalse(weights.empty)
        total_weight = weights.sum()
        self.assertAlmostEqual(total_weight, 0.90, places=4)

if __name__ == '__main__':
    unittest.main()
