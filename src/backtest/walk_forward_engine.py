import logging
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd


class WalkForwardValidator:
    def __init__(self, train_window_days: int = 252, test_window_days: int = 63):
        self.train_window = train_window_days
        self.test_window = test_window_days
        self.logger = logging.getLogger(__name__)

    def validate(self, df: pd.DataFrame, strategy_eval_func: Callable) -> dict[str, Any]:
        if len(df) < self.train_window + self.test_window:
            self.logger.warning("Insufficient data for walk-forward validation.")
            return {"status": "FAILED", "reason": "Insufficient data"}

        test_metrics = []
        start_idx = 0
        while start_idx + self.train_window + self.test_window <= len(df):
            test_df = df.iloc[start_idx + self.train_window : start_idx + self.train_window + self.test_window]
            try:
                metric = strategy_eval_func(test_df)
                test_metrics.append(metric)
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                return {"status": "FAILED", "reason": f"Evaluation error: {e}"}
            start_idx += self.test_window

        if not test_metrics:
            return {"status": "FAILED"}

        avg_metric = np.mean(test_metrics)
        consistency = np.std(test_metrics) / (avg_metric + 1e-9)
        return {
            "status": "PASSED" if avg_metric > 0 else "FAILED",
            "average_metric": avg_metric,
            "consistency_score": consistency,
            "windows_tested": len(test_metrics)
        }
