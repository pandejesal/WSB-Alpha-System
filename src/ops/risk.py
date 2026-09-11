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
import os  # retained: tests patch src.ops.risk.os.makedirs; do not remove
from dataclasses import dataclass, field
from pathlib import Path

METRICS_PATH = Path("runtime/metrics/risk_metrics.json")


@dataclass
class DDTracker:
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    max_daily_loss: float = 0.0
    metrics_file: str = "docs/data/ops/metrics.json"
    hwm: dict = field(default_factory=dict)
    dd_from_hwm: dict = field(default_factory=dict)

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

    def check_and_update_breaker(self, sleeve_id: str, current_equity: float, model_dd: float) -> bool:
        """Update HWM and DD. Returns True if DD breaches 1.5x model_dd. Fail-closed safe.

        Restored (B1b dropped it, breaking paper_executor live path): HWM ratchets up,
        DD measured from HWM, breach at 1.5x model limit. Non-positive equity -> False
        (no position, nothing to halt).
        """
        if current_equity <= 0:
            return False
        current_hwm = self.hwm.get(sleeve_id, current_equity)
        if current_equity > current_hwm:
            self.hwm[sleeve_id] = current_equity
            self.dd_from_hwm[sleeve_id] = 0.0
            return False
        dd = (current_hwm - current_equity) / current_hwm
        self.dd_from_hwm[sleeve_id] = dd
        return dd > (1.5 * model_dd)


def update_ops_state(sleeve_id: str, status: str, state_file: str = "config/ops_state.yaml"):
    """Set per-sleeve status without modifying the global state (atomic tmp+replace).

    Restored original (sleeve_id, status) signature (B1b changed it to a dict form that
    broke paper_executor.py:115). For global state changes use KillSwitch.set_state
    (S2 single-writer, sleeve-preserving).
    """
    import tempfile

    import yaml

    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    if "sleeves" not in data:
        data["sleeves"] = {}
    data["sleeves"][sleeve_id] = status
    parent = os.path.dirname(state_file)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=parent or ".")
    with os.fdopen(fd, "w") as f:
        yaml.dump(data, f)
    os.replace(temp_path, state_file)
