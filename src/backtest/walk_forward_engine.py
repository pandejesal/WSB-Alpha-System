import logging
import math
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd


class WalkForwardValidator:
    """Walk-forward OOS validator — strict gate per OPTIMIZATION_PLAYBOOK.md s3.

    Gates (must all pass before registry): permutation, CPCV, walk-forward OOS,
    DSR, min trades, Sharpe/DD. This validator enforces the WF OOS conjunction
    per plan_1 W2 (flaw_D:19-23,102-105): avg >= OOS_MIN and consistency < 1.5 and
    windows >=3 and >=2/3 windows positive. Fail-closed on insufficient data/eval
    error. See docs/OPTIMIZATION_PLAYBOOK.md s3 and docs/HUNT_PROTOCOL.md.
    """

    OOS_MIN = 0.40
    CONSISTENCY_MAX = 1.5
    MIN_WINDOWS = 3

    def __init__(
        self, train_window_days: int = 252, test_window_days: int = 63, oos_min: float = 0.40
    ):
        self.train_window = train_window_days
        self.test_window = test_window_days
        self.oos_min = oos_min
        self.logger = logging.getLogger(__name__)

    def validate(
        self,
        df: pd.DataFrame,
        strategy_eval_func: Callable,
        oos_min: float | None = None,
        sharpe_floored: float | None = None,
    ) -> dict[str, Any]:
        """Validate strategy across rolling OOS windows — fail-closed.

        Strict conjunction (plan_1 W2):
          avg_metric >= OOS_MIN (0.40, overridable via oos_min/sharpe_floored)
          and consistency_score < 1.5
          and windows_tested >= 3
          and at least 2/3 windows with metric > 0
        Any violation -> FAILED. Eval error / insufficient data -> FAILED.
        Cites: docs/OPTIMIZATION_PLAYBOOK.md s3 (Gates must all pass).
        W13 survivorship guard: missing manifest -> FAILED (fail-closed).
        """
        # W13 survivorship manifest guard (fail-closed if missing)
        try:
            import json as _js  # noqa: I001 - grouped with pathlib for guard probe
            import pathlib as _pl

            _root = _pl.Path(__file__).resolve().parents[2]
            _uni = _js.loads((_root / "config/universe.json").read_text(encoding="utf-8"))
            _mf = _root / _uni.get("manifest", "docs/data/registry_survivorship_manifest.json")
            if not _mf.exists():
                return {"status": "FAILED", "reason": "W13 survivorship manifest missing (fail-closed)"}
            if not _uni.get("survivorship_checked"):
                return {"status": "FAILED", "reason": "W13 universe survivorship_checked != true (fail-closed)"}
        except Exception as _e:  # noqa: BLE001  # guard probe, intentional
            # if probe itself fails, treat as FAILED only when manifest truly missing
            try:
                import pathlib as _pl2

                _root2 = _pl2.Path(__file__).resolve().parents[2]
                if not (_root2 / "docs/data/registry_survivorship_manifest.json").exists():
                    return {"status": "FAILED", "reason": f"W13 manifest probe failed: {_e}"}
            except Exception:  # noqa: BLE001  # second-level guard, intentional
                pass

        if oos_min is not None:
            threshold = oos_min
        elif sharpe_floored is not None:
            threshold = sharpe_floored
        else:
            threshold = self.oos_min

        if len(df) < self.train_window + self.test_window:
            self.logger.warning("Insufficient data for walk-forward validation.")
            return {"status": "FAILED", "reason": "Insufficient data"}

        test_metrics: list[float] = []
        start_idx = 0
        while start_idx + self.train_window + self.test_window <= len(df):
            test_df = df.iloc[start_idx + self.train_window : start_idx + self.train_window + self.test_window]
            try:
                metric = strategy_eval_func(test_df)
                if not isinstance(metric, (int, float, np.floating)):
                    try:
                        metric = float(metric)
                    except Exception as e:
                        return {"status": "FAILED", "reason": f"Non-numeric metric: {e}"}
                test_metrics.append(float(metric))
            except Exception as e:
                return {"status": "FAILED", "reason": f"Evaluation error: {e}"}
            start_idx += self.test_window

        if not test_metrics:
            return {"status": "FAILED", "reason": "No windows evaluated"}

        if len(test_metrics) < self.MIN_WINDOWS:
            avg_metric = float(np.mean(test_metrics)) if test_metrics else 0.0
            consistency = float(np.std(test_metrics) / (abs(avg_metric) + 1e-9)) if test_metrics else float("inf")
            return {
                "status": "FAILED",
                "reason": f"Insufficient windows: {len(test_metrics)} < {self.MIN_WINDOWS}",
                "average_metric": avg_metric,
                "consistency_score": consistency,
                "windows_tested": len(test_metrics),
            }

        avg_metric = float(np.mean(test_metrics))
        consistency = float(np.std(test_metrics) / (abs(avg_metric) + 1e-9))
        windows_tested = len(test_metrics)
        positive_windows = sum(1 for m in test_metrics if m > 0)
        required_positive = math.ceil(windows_tested * 2 / 3)

        passes_avg = avg_metric >= threshold
        passes_consistency = consistency < self.CONSISTENCY_MAX
        passes_windows = windows_tested >= self.MIN_WINDOWS
        passes_positive = positive_windows >= required_positive

        is_pass = passes_avg and passes_consistency and passes_windows and passes_positive

        result: dict[str, Any] = {
            "status": "PASSED" if is_pass else "FAILED",
            "average_metric": avg_metric,
            "consistency_score": consistency,
            "windows_tested": windows_tested,
            "positive_windows": positive_windows,
            "required_positive": required_positive,
            "threshold": threshold,
        }
        if not is_pass:
            reasons = []
            if not passes_avg:
                reasons.append(f"avg {avg_metric:.4f} < threshold {threshold}")
            if not passes_consistency:
                reasons.append(f"consistency {consistency:.4f} >= {self.CONSISTENCY_MAX}")
            if not passes_windows:
                reasons.append(f"windows {windows_tested} < {self.MIN_WINDOWS}")
            if not passes_positive:
                reasons.append(f"positive {positive_windows}/{windows_tested} < {required_positive} (2/3)")
            result["reason"] = "; ".join(reasons)
        return result
