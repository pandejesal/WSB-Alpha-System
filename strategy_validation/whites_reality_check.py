import numpy as np
import pandas as pd
from typing import List
import logging

class WhitesRealityCheck:
    """
    White's Reality Check (WRC) accounts for data snooping bias by evaluating
    if the best performing strategy in a pool is genuinely better than the benchmark,
    or just the result of luck from multiple testing.
    """
    def __init__(self, n_bootstraps: int = 500):
        self.n_bootstraps = n_bootstraps
        self.logger = logging.getLogger(__name__)

    def test(self, benchmark_returns: pd.Series, strategy_returns_matrix: pd.DataFrame) -> dict:
        """
        strategy_returns_matrix: DataFrame where each column is the daily return of a strategy variant.
        benchmark_returns: Series of daily benchmark returns.
        """
        self.logger.info(f"Running White's Reality Check with {self.n_bootstraps} bootstraps on {strategy_returns_matrix.shape[1]} strategies.")

        # Calculate excess returns
        excess_returns = strategy_returns_matrix.sub(benchmark_returns, axis=0)
        mean_excess_returns = excess_returns.mean(axis=0)

        best_actual_strategy = mean_excess_returns.idxmax()
        best_actual_return = mean_excess_returns.max()

        T = len(benchmark_returns)
        bootstrap_max_returns = []

        # Simple Block Bootstrap to preserve autocorrelation (optional, using simple resample here for speed)
        for _ in range(self.n_bootstraps):
            # Sample indices with replacement
            indices = np.random.randint(0, T, T)
            # Center the bootstrap sample to the null hypothesis (mean = 0)
            centered_sample = excess_returns.iloc[indices] - mean_excess_returns

            # Find the best strategy in this centered bootstrap universe
            best_boot_return = centered_sample.mean(axis=0).max()
            bootstrap_max_returns.append(best_boot_return)

        bootstrap_max_returns = np.array(bootstrap_max_returns)

        # Calculate p-value: what % of bootstrapped max returns beat the actual best return?
        p_value = np.sum(bootstrap_max_returns >= best_actual_return) / self.n_bootstraps

        self.logger.info(f"WRC p-value: {p_value:.4f}")

        return {
            "status": "PASSED" if p_value <= 0.05 else "FAILED",
            "p_value": p_value,
            "best_strategy": best_actual_strategy,
            "null_hypothesis": "The best strategy's outperformance is due to luck from data snooping."
        }
