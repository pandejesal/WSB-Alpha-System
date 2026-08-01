import pandas as pd
import numpy as np
from typing import Callable, Dict, Any, List
import logging

class WalkForwardValidator:
    """
    Implements rolling Walk-Forward Optimization (WFO) to test strategy robustness
    and parameter stability across out-of-sample time periods.
    """
    def __init__(self, train_window_days: int = 252, test_window_days: int = 63):
        self.train_window = train_window_days
        self.test_window = test_window_days
        self.logger = logging.getLogger(__name__)

    def validate(self, df: pd.DataFrame, strategy_eval_func: Callable) -> Dict[str, Any]:
        """
        Rolls through the dataset. The strategy_eval_func should take a dataframe
        and return the evaluation metric (e.g. Profit Factor, Sharpe).
        """
        if len(df) < self.train_window + self.test_window:
            self.logger.warning("Insufficient data for walk-forward validation.")
            return {"status": "FAILED", "reason": "Insufficient data"}

        test_metrics = []

        # Simple anchored or rolling walk-forward. We use rolling here.
        start_idx = 0
        while start_idx + self.train_window + self.test_window <= len(df):
            train_df = df.iloc[start_idx : start_idx + self.train_window]
            test_df = df.iloc[start_idx + self.train_window : start_idx + self.train_window + self.test_window]

            # In a full WFO, we would optimize parameters on train_df.
            # Here we evaluate the robustness of a *static* parameter set across OOS windows.
            try:
                metric = strategy_eval_func(test_df)
                test_metrics.append(metric)
            except Exception as e:
                self.logger.error(f"Strategy evaluation failed during walk-forward: {e}")
                return {"status": "FAILED", "reason": f"Evaluation error: {e}"}

            start_idx += self.test_window

        if not test_metrics:
            return {"status": "FAILED", "reason": "No valid test windows evaluated"}

        avg_metric = np.mean(test_metrics)
        consistency = np.std(test_metrics) / (avg_metric + 1e-9)

        self.logger.info(f"Walk-Forward complete. Avg Metric: {avg_metric:.3f}, Consistency: {consistency:.3f}")

        return {
            "status": "PASSED" if avg_metric > 0 else "FAILED", # Replace with actual threshold logic
            "average_metric": avg_metric,
            "consistency_score": consistency,
            "windows_tested": len(test_metrics)
        }
