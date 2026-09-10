"""Risk subsystem — consolidated shim.

The canonical KillSwitch implementation lives in ``src.ops.killswitch``.
This module re-exports it for backwards compatibility and still owns
``DDTracker`` and ``update_ops_state``.
"""

# S1 DEPRECATED compatibility path: import KillSwitch from src.ops.killswitch instead.
# This re-export stays (do not delete) so existing `src.ops.risk.KillSwitch`
# references keep resolving to the canonical fail-CLOSED class; add no new uses.
from src.ops.killswitch import KillSwitch

import json
from dataclasses import dataclass, field
from pathlib import Path

METRICS_PATH = Path("runtime/metrics/risk_metrics.json")


@dataclass
class DDTracker:
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    max_daily_loss: float = 0.0

    def _load_metrics(self):
        if METRICS_PATH.exists():
            try:
                with open(METRICS_PATH) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def update(self, pnl: float):
        self.daily_pnl += pnl
        metrics = self._load_metrics()
        if pnl < 0:
            self.max_drawdown = min(self.max_drawdown, self.daily_pnl)
        metrics["daily_pnl"] = self.daily_pnl
        metrics["max_drawdown"] = self.max_drawdown
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_PATH, "w") as f:
            json.dump(metrics, f, indent=2)


def update_ops_state(state: dict):
    """Persist the unified ops state to the canonical kill-switch file.

    S2 single-writer delegate: all ops_state.yaml writes funnel through
    ``KillSwitch.set_state`` (atomic tmp + os.replace, preserves sleeves).
    There is no second writer path in this module.
    """
    ks = KillSwitch(filepath="config/ops_state.yaml")
    ks.set_state(state.get("state", "halt_new_orders"))
