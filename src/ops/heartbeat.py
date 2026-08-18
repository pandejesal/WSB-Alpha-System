import json
import logging
import os
import argparse
from datetime import datetime, timezone

from src.ops.audit import write_artifact
from src.ops.alerts import Alerts

logger = logging.getLogger(__name__)

HEARTBEAT_FILE = "docs/data/ops/heartbeat.json"

def write_heartbeat(job_name: str, status: str = "ok") -> None:
    """
    Appends a heartbeat to docs/data/ops/heartbeat.json.
    """
    data = {"history": []}
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            pass

    history = data.get("history", [])

    # We maintain a list of heartbeats (e.g. max 100)
    entry = {
        "job_name": job_name,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status
    }
    history.append(entry)

    if len(history) > 1000:
        history = history[-1000:]

    data["history"] = history
    # Keep top-level keys for backward compatibility if any
    data["ts"] = entry["ts"]
    data["status"] = entry["status"]

    try:
        write_artifact(HEARTBEAT_FILE, data)
        logger.info(f"Heartbeat written for job {job_name} with status {status}")
    except Exception as e:
        logger.error(f"Failed to write heartbeat: {e}")

def check_staleness() -> bool:
    """
    Detects if the heartbeat is stale (> 2 missed runs based on daily schedule).
    Since it's daily, 2 missed runs > 2 days (48 hours).
    Returns True if stale, False otherwise.
    """
    if not os.path.exists(HEARTBEAT_FILE):
        logger.warning(f"Heartbeat file {HEARTBEAT_FILE} does not exist.")
        return True # Considered stale if it doesn't exist

    try:
        with open(HEARTBEAT_FILE, "r") as f:
            data = json.load(f)

        history = data.get("history", [])
        if len(history) < 2:
            return False # Not enough history to be stale, or just started

        # Get the second to last entry (the one BEFORE the one we just wrote)
        # to see if there was a gap BEFORE this current run.
        last_entry = history[-2]
        ts_str = last_entry.get("ts")
        if not ts_str:
            return True

        ts_str = ts_str.replace("Z", "+00:00")
        last_ts = datetime.fromisoformat(ts_str)
        now = datetime.now(timezone.utc)

        diff = now - last_ts
        if diff.total_seconds() > 48 * 3600:
            logger.warning(f"Heartbeat is stale: previous run was {diff.total_seconds() / 3600:.1f} hours ago.")
            return True

        return False
    except Exception as e:
        logger.error(f"Error reading heartbeat file: {e}")
        return True

        last_entry = history[-1]
        ts_str = last_entry.get("ts")
        if not ts_str:
            return True

        # Parse ISO format. Handle Z.
        ts_str = ts_str.replace("Z", "+00:00")
        last_ts = datetime.fromisoformat(ts_str)
        now = datetime.now(timezone.utc)

        diff = now - last_ts
        if diff.total_seconds() > 48 * 3600:
            logger.warning(f"Heartbeat is stale: last run was {diff.total_seconds() / 3600:.1f} hours ago.")
            return True

        return False
    except Exception as e:
        logger.error(f"Error reading heartbeat file: {e}")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Heartbeat generator")
    parser.add_argument("--job", type=str, required=True, help="Name of the job generating the heartbeat")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    write_heartbeat(args.job)

    if check_staleness():
        alerts = Alerts()
        alerts.send_warn(f"Heartbeat is stale (> 48h). Alert triggered by job: {args.job}")
