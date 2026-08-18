import json
import logging
import os
from datetime import datetime, timedelta, timezone

from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

class HeartbeatManager:
    """
    Writes docs/data/ops/heartbeat.json every run.
    Detects staleness (>2 missed runs -> WARN alert).
    Preserves existing plan.json heartbeat schema format.
    """
    def __init__(self, filepath: str = "docs/data/ops/heartbeat.json"):
        self.filepath = filepath

    def write_heartbeat(self, run_id: str, status: str = "ok") -> None:
        """
        Writes the heartbeat artifact.
        """
        payload = {
            "run_id": run_id,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": status
        }
        try:
            write_artifact(self.filepath, payload)
            logger.info(f"Heartbeat written: {payload}")
        except Exception as e:  # noqa: BLE001 - Catching Exception to log error
            logger.error(f"Failed to write heartbeat: {e}")

    def check_staleness(self) -> bool:
        """
        Returns True if the heartbeat is stale (>2 missed runs).
        Assuming runs are every 24h, 2 missed runs = ~48 hours.
        For safety and based on business days, we'll check if the timestamp is > 48h old.
        Returns False if not stale or file missing (to prevent alert storms on new setups).
        """
        if not os.path.exists(self.filepath):
            # If the file doesn't exist, we haven't run yet or it's a fresh system.
            # Don't trigger a staleness WARN immediately.
            return False

        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)

            ts_str = data.get("ts", "")
            if not ts_str:
                return False

            # Parse ISO8601 with Z
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

            # Use timezone-aware now to match
            now = datetime.now(timezone.utc)

            # > 2 missed runs (e.g. 48 hours for daily run)
            return (now - ts) > timedelta(hours=48)
        except Exception as e:  # noqa: BLE001 - Fail gracefully if JSON is corrupt
            logger.error(f"Failed to parse heartbeat for staleness: {e}")
            return False
