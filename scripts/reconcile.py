import json
import logging
import os

from src.ops.alerts import AlertManager
from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

def run_reconciliation():
    """
    Compares docs/data/ops/plan.json targets with docs/data/ops/fills.json.
    Logs mismatches to docs/data/ops/reconciliation.json.
    Sends CRITICAL alert on any mismatch.
    """
    am = AlertManager()

    plan_path = "docs/data/ops/plan.json"
    fills_path = "docs/data/ops/fills.json"
    recon_path = "docs/data/ops/reconciliation.json"

    plan_targets = {}
    if os.path.exists(plan_path):
        try:
            with open(plan_path, "r") as f:
                plan = json.load(f)
                for t in plan.get("targets", []):
                    # In a real system, you might compare side/qty. We do a simple ticker check.
                    plan_targets[t["ticker"]] = t
        except Exception as e:  # noqa: BLE001 - Catching Exception to log error
            logger.error(f"Failed to read plan.json: {e}")

    filled_tickers = set()
    if os.path.exists(fills_path):
        try:
            with open(fills_path, "r") as f:
                fills = json.load(f)
                for fill in fills:
                    # Depending on schema, handle ticker extraction
                    ticker = fill.get("ticker", "UNKNOWN")
                    filled_tickers.add(ticker)
        except Exception as e:  # noqa: BLE001 - Catching Exception to log error
            logger.error(f"Failed to read fills.json: {e}")

    mismatches = []

    # Check for planned targets that didn't get filled
    for ticker, target in plan_targets.items():
        if ticker not in filled_tickers:
            mismatches.append({"type": "missing_fill", "ticker": ticker, "target": target})

    # Check for fills that were never planned (less likely but possible)
    for ticker in filled_tickers:
        if ticker not in plan_targets and ticker != "UNKNOWN":
            mismatches.append({"type": "unplanned_fill", "ticker": ticker})

    recon_data = {
        "mismatches": mismatches,
        "status": "clean" if not mismatches else "mismatch"
    }

    try:
        write_artifact(recon_path, recon_data)
        logger.info(f"Reconciliation written: {recon_data}")
    except Exception as e:  # noqa: BLE001 - Catching Exception to log error
        logger.error(f"Failed to write recon: {e}")

    if mismatches:
        am.send("CRITICAL", f"Reconciliation mismatch detected:\n{json.dumps(mismatches, indent=2)}")
        logger.warning("Reconciliation mismatches found and alerted.")
    else:
        logger.info("Reconciliation clean. No mismatches.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_reconciliation()
