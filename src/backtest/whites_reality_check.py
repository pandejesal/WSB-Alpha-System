import logging

import pandas as pd


class WhitesRealityCheck:
    def __init__(self, n_bootstraps: int = 500):
        self.n_bootstraps = n_bootstraps
        self.logger = logging.getLogger(__name__)

    def test(self, benchmark_returns: pd.Series, strategy_returns_matrix: pd.DataFrame) -> dict:
        excess_returns = strategy_returns_matrix.sub(benchmark_returns, axis=0)
        mean_excess_returns = excess_returns.mean(axis=0)

        best_actual_strategy = mean_excess_returns.idxmax()
        best_actual_return = mean_excess_returns.max()  # noqa: F841 - variable intentionally unused (kept for readability/debugging or unpacked values)

        from src.backtest.validators.statistical import StatisticalValidator

        # Use the unified implementation that respects serial correlation via StationaryBootstrap
        p_value = StatisticalValidator.whites_reality_check(
            strategy_returns=strategy_returns_matrix.values,
            benchmark_returns=benchmark_returns.values,
            replications=self.n_bootstraps
        )

        return {
            "status": "PASSED" if p_value <= 0.05 else "FAILED",
            "p_value": p_value,
            "best_strategy": best_actual_strategy,
            "null_hypothesis": "The best strategy's outperformance is due to luck from data snooping."
        }
