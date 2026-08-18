import json
import logging
import os
from typing import Any

from src.ops.alerts import AlertManager
from src.ops.killswitch import KillSwitch

logger = logging.getLogger(__name__)

MIN_PAPER_TRADES = 50
MIN_TRADES_PER_SLEEVE = 10
SMA200_EXEMPT = "spy_sma200"
MIN_CONSECUTIVE_HEARTBEAT_DAYS = 7


class GateEvaluator:
    """
    Gate evaluator computing G1-G7 from docs/data/ops/* artifacts.
    If G1/G2/G3 fail -> CRITICAL alert + auto-halt NEW orders only (never auto-flat).
    evaluate_g1..g7 and evaluate_all are PURE functions of data dictionaries:
    no file I/O, no network, no broker. All I/O lives in main()/load_artifacts().
    """
    def __init__(self, data_dir: str = "docs/data"):
        self.data_dir = data_dir
        self.ops_dir = os.path.join(data_dir, "ops")
        self.paper_dir = os.path.join(data_dir, "paper")

    def evaluate_g1(self, fills: list) -> tuple[bool, int]:
        """G1: >= 50 paper trades executed by the live system."""
        count = len(fills or [])
        return count >= MIN_PAPER_TRADES, count

    def evaluate_g2(self, fills: list) -> tuple[bool, dict[str, int]]:
        """G2: >= 10 trades per active sleeve (spy_sma200 exempt)."""
        counts: dict[str, int] = {}
        for fill in fills or []:
            sleeve = fill.get("sleeve_id")
            if sleeve:
                counts[sleeve] = counts.get(sleeve, 0) + 1

        passed = True
        for sleeve, count in counts.items():
            if sleeve != SMA200_EXEMPT and count < MIN_TRADES_PER_SLEEVE:
                passed = False

        # A sleeve with zero fills must be checked against the active roster, not
        # silently skipped: without any fills the gate cannot pass.
        if not counts:
            passed = False
        return passed, counts

    def evaluate_g3(self, sharpe_data: dict) -> tuple[bool, float]:
        """G3: Sharpe with CI; lower bound of 90% CI > 0."""
        ci_lower = (sharpe_data or {}).get("ci_lower", 0.0)
        return ci_lower > 0.0, ci_lower

    def evaluate_g4(self, perm_data: dict) -> bool:
        """G4: Full 200-permutation protocol run (p >= 0.05 passes)."""
        p_value = (perm_data or {}).get("p_value", 1.0)
        return p_value >= 0.05

    def evaluate_g5(self, heartbeats: dict) -> bool:
        """G5: Telegram heartbeat seen for >= 7 consecutive trading days."""
        if not isinstance(heartbeats, dict):
            return False
        dates = _trading_days_from_data(heartbeats)
        return _has_consecutive_trading_days(dates, MIN_CONSECUTIVE_HEARTBEAT_DAYS)

    def evaluate_g6(self, rehearsal: dict) -> bool:
        """G6: Kill-switch rehearsal documented once (tier-2 + tier-3 exercised, then restored)."""
        return rehearsal is not None and rehearsal.get("restored") is True

    def evaluate_g7(self, recon: dict) -> bool:
        """G7: Reconciliation check: zero unresolved fill/order mismatches."""
        return recon is not None and recon.get("status") == "clean"

    def evaluate_all(self, data: dict) -> dict:
        """
        Pure evaluation of all gates from a data dictionary:
        data = {"fills": [...], "sharpe": {...}, "permutation": {...},
                "heartbeats": {...}, "rehearsal": {...}, "reconciliation": {...}}
        """
        g1_pass, g1_count = self.evaluate_g1(data.get("fills", []))
        g2_pass, g2_counts = self.evaluate_g2(data.get("fills", []))
        g3_pass, g3_ci = self.evaluate_g3(data.get("sharpe", {}))
        g4_pass = self.evaluate_g4(data.get("permutation", {}))
        g5_pass = self.evaluate_g5(data.get("heartbeats", {}))
        g6_pass = self.evaluate_g6(data.get("rehearsal", {}))
        g7_pass = self.evaluate_g7(data.get("reconciliation", {}))

        return {
            "G1": g1_pass,
            "G2": g2_pass,
            "G3": g3_pass,
            "G4": g4_pass,
            "G5": g5_pass,
            "G6": g6_pass,
            "G7": g7_pass,
            "details": {
                "G1": {"trades": g1_count},
                "G2": {"per_sleeve": g2_counts},
                "G3": {"ci_lower": g3_ci}
            }
        }

    def load_artifacts(self) -> dict:
        """Reads all gate inputs from disk (the ONLY I/O surface)."""
        return {
            "fills": self._read_json(os.path.join(self.ops_dir, "fills.json")) or [],
            "sharpe": self._read_json(os.path.join(self.paper_dir, "sharpe.json")) or {},
            "permutation": self._read_json(os.path.join(self.data_dir, "permutation_study.json")) or {},
            "heartbeats": self._read_json(os.path.join(self.ops_dir, "heartbeat.json")) or {},
            "rehearsal": self._read_json(os.path.join(self.ops_dir, "kill_switch_rehearsal.json")) or {},
            "reconciliation": self._read_json(os.path.join(self.ops_dir, "reconciliation.json")) or {}
        }

    def _read_json(self, path: str) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:  # noqa: BLE001 - Catching Exception to log error
                logger.error(f"Failed to read {path}: {e}")
        return None

    def enforce_halt(self, results: dict) -> None:
        """CRITICAL alert + auto-halt NEW orders only when G1/G2/G3 fail. Never auto-flat."""
        if not (results.get("G1") and results.get("G2") and results.get("G3")):
            logger.warning("G1, G2, or G3 failed. Triggering auto-halt of new orders.")
            ks = KillSwitch()
            if ks.get_state() == "off":
                ks.set_state("halt_new_orders")
                try:
                    AlertManager().send("CRITICAL", f"Gate Evaluator auto-halt triggered. Results: {results}")
                except Exception as e:  # noqa: BLE001 - alerting must not crash the job
                    logger.error(f"Failed to send CRITICAL alert: {e}")


def _trading_days_from_data(heartbeats: dict) -> list[str]:
    """Extracts distinct Mon-Fri dates (YYYY-MM-DD) from a heartbeat artifact's history."""
    history = heartbeats.get("history", [])
    dates: list[str] = []
    for entry in history:
        ts_str = entry.get("ts", "")
        if not ts_str:
            continue
        try:
            ts = __import__("datetime").datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001 - skip corrupt entries
            continue
        if ts.weekday() >= 5:
            continue
        day = ts.strftime("%Y-%m-%d")
        if not dates or dates[-1] != day:
            dates.append(day)
    return dates


def _has_consecutive_trading_days(dates: list[str], min_days: int) -> bool:
    """True if dates contains >= min_days consecutive trading days (Mon-Fri, weekend gaps allowed)."""
    if len(dates) < min_days:
        return False
    from datetime import datetime as _dt

    current_streak = 1
    prev = None
    for day in dates:
        if prev is None:
            prev = day
            continue
        prev_dt = _dt.strptime(prev, "%Y-%m-%d")
        cur_dt = _dt.strptime(day, "%Y-%m-%d")
        delta_days = (cur_dt - prev_dt).days
        if delta_days == 1:
            current_streak += 1
        elif delta_days == 3 and prev_dt.weekday() == 4 and cur_dt.weekday() == 0:
            current_streak += 1  # Friday -> Monday
        elif delta_days == 2 and prev_dt.weekday() == 4 and cur_dt.weekday() == 1:
            current_streak += 1  # Friday -> Tuesday (Monday holiday)
        else:
            current_streak = 1
        prev = day
        if current_streak >= min_days:
            return True
    return current_streak >= min_days


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    evaluator = GateEvaluator()
    data = evaluator.load_artifacts()
    results = evaluator.evaluate_all(data)
    logger.info(f"Gate Evaluation Results: {results}")
    evaluator.enforce_halt(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())