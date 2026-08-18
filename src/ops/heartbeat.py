import argparse
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

MAX_HISTORY_ENTRIES = 60


class HeartbeatManager:
    """
    Writes docs/data/ops/heartbeat.json every run (with rolling history).
    Detects staleness (>2 missed runs -> WARN alert).
    Preserves the plan.json heartbeat schema via the 'latest' object.
    """
    def __init__(self, filepath: str = "docs/data/ops/heartbeat.json"):
        self.filepath = filepath

    def _load(self) -> dict:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except Exception as e:  # noqa: BLE001 - fail gracefully on corrupt file
                logger.error(f"Failed to parse heartbeat file: {e}")
        return {"history": [], "latest": None}

    def write_heartbeat(self, run_id: str, status: str = "ok", job: str = "") -> None:
        """
        Appends a heartbeat entry to the rolling history and updates 'latest'.
        """
        data = self._load()
        history = data.get("history", []) if isinstance(data, dict) else []

        entry = {
            "run_id": run_id,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": status,
            "job": job
        }
        history.append(entry)
        history = history[-MAX_HISTORY_ENTRIES:]

        payload = {
            "history": history,
            "latest": entry
        }
        try:
            write_artifact(self.filepath, payload)
            logger.info(f"Heartbeat written: {entry}")
        except Exception as e:  # noqa: BLE001 - Catching Exception to log error
            logger.error(f"Failed to write heartbeat: {e}")

    def check_staleness(self) -> bool:
        """
        Returns True if the heartbeat is stale (>2 missed runs).
        Assumes runs every 24h; 2 missed runs = ~48 hours.
        Returns False if the file is missing or unparseable (avoid alert storms on fresh setups).
        """
        data = self._load()
        if not isinstance(data, dict):
            return False
        latest = data.get("latest") or (data.get("history") or [None])[-1]
        if not latest and data.get("ts"):
            latest = data  # legacy single-object format
        if not latest:
            return False

        ts_str = latest.get("ts", "")
        if not ts_str:
            return False

        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - ts) > timedelta(hours=48)
        except Exception as e:  # noqa: BLE001 - Fail gracefully if timestamp corrupt
            logger.error(f"Failed to parse heartbeat timestamp for staleness: {e}")
            return False

    def trading_day_history(self) -> list[str]:
        """
        Returns the list of distinct trading-day dates (YYYY-MM-DD, Mon-Fri only)
        present in the heartbeat history, oldest first. Used by the G5 gate.
        """
        data = self._load()
        if not isinstance(data, dict):
            return []
        history = data.get("history", [])
        dates = []
        for entry in history:
            ts_str = entry.get("ts", "")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001 - skip corrupt entries
                continue
            if ts.weekday() >= 5:
                continue
            day = ts.strftime("%Y-%m-%d")
            if not dates or dates[-1] != day:
                dates.append(day)
        return dates

    def has_consecutive_trading_days(self, min_days: int = 7) -> bool:
        """
        True if the heartbeat history contains >= min_days consecutive trading days.
        """
        dates = self.trading_day_history()
        if len(dates) < min_days:
            return False

        current_streak = 1
        prev = None
        for day in dates:
            if prev is None:
                prev = day
                continue
            prev_dt = datetime.strptime(prev, "%Y-%m-%d")
            cur_dt = datetime.strptime(day, "%Y-%m-%d")
            delta_days = (cur_dt - prev_dt).days

            if delta_days == 1:
                current_streak += 1
            elif delta_days == 3 and prev_dt.weekday() == 4 and cur_dt.weekday() == 0:
                # Friday -> Monday (weekend gap)
                current_streak += 1
            elif delta_days == 2 and prev_dt.weekday() == 4 and cur_dt.weekday() == 1:
                # Friday -> Tuesday (Monday holiday)
                current_streak += 1
            else:
                current_streak = 1
            prev = day
            if current_streak >= min_days:
                return True
        return current_streak >= min_days


def main() -> int:
    parser = argparse.ArgumentParser(description="Write an ops heartbeat entry and check staleness.")
    parser.add_argument("--job", default="unknown", help="Job name producing this heartbeat")
    args = parser.parse_args()

    mgr = HeartbeatManager()
    run_id = f"{args.job}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    mgr.write_heartbeat(run_id=run_id, status="ok", job=args.job)

    if mgr.check_staleness():
        logger.warning("Heartbeat is STALE: >2 missed runs detected")
        try:
            from src.ops.alerts import AlertManager
            AlertManager().send("WARN", "Heartbeat staleness detected: more than 2 runs missed.")
        except Exception as e:  # noqa: BLE001 - alerting must never crash the workflow
            logger.error(f"Failed to send staleness WARN alert: {e}")
        return 2
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())