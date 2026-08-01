import numpy as np
import pandas as pd
import logging

class WhitesRealityCheck:
    def __init__(self, n_bootstraps: int = 500):
        self.n_bootstraps = n_bootstraps
        self.logger = logging.getLogger(__name__)

    def test(self, benchmark_returns: pd.Series, strategy_returns_matrix: pd.DataFrame) -> dict:
        excess_returns = strategy_returns_matrix.sub(benchmark_returns, axis=0)
        mean_excess_returns = excess_returns.mean(axis=0)

        best_actual_strategy = mean_excess_returns.idxmax()
        best_actual_return = mean_excess_returns.max()

        T = len(benchmark_returns)
        bootstrap_max_returns = []
        for _ in range(self.n_bootstraps):
            indices = np.random.randint(0, T, T)
            centered_sample = excess_returns.iloc[indices] - mean_excess_returns
            best_boot_return = centered_sample.mean(axis=0).max()
            bootstrap_max_returns.append(best_boot_return)

        bootstrap_max_returns = np.array(bootstrap_max_returns)
        p_value = np.sum(bootstrap_max_returns >= best_actual_return) / self.n_bootstraps

        return {
            "status": "PASSED" if p_value <= 0.05 else "FAILED",
            "p_value": p_value,
            "best_strategy": best_actual_strategy,
            "null_hypothesis": "The best strategy's outperformance is due to luck from data snooping."
        }
