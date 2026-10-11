import json
import logging
import os

from src.ops.alerts import AlertManager
from src.ops.artifacts import extract_fills, is_confirmed_fill
from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

def _planned_tickers(plan: dict) -> dict:
    """Planned tickers from either a flat 'targets' list or sleeves[].targets[]."""
    planned = {}
    for t in plan.get("targets", []):
        if isinstance(t, dict) and t.get("ticker"):
            planned[t["ticker"]] = t
    for sleeve in plan.get("sleeves", []):
        for t in sleeve.get("targets", []):
            ticker = t.get("ticker") or t.get("symbol")
            if ticker:
                planned[ticker] = t
    return planned

def run_reconciliation():
    """
    Compares docs/data/ops/plan.json targets with the broker-confirmed fills in
    docs/data/ops/fills.json.
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
                plan_targets = _planned_tickers(plan)
        except Exception as e:  # noqa: BLE001 - Catching Exception to log error
            logger.error(f"Failed to read plan.json: {e}")

    # Fills go through the canonical extractor (audit finding F3): this used to
    # assume a bare list and raised AttributeError on the wrapper format the
    # executor writes, silently reporting every planned target as missing.
    filled_tickers = set()
    fills_unreadable = False
    if os.path.exists(fills_path):
        try:
            with open(fills_path, "r") as f:
                raw = json.load(f)
            for fill in extract_fills(raw):
                if not is_confirmed_fill(fill):
                    continue
                ticker = fill.get("ticker", "UNKNOWN")
                filled_tickers.add(ticker)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to read fills.json: {e}")
            fills_unreadable = True

    mismatches = []

    # Check for planned targets that didn't get filled
    for ticker, target in plan_targets.items():
        if ticker not in filled_tickers:
            mismatches.append({"type": "missing_fill", "ticker": ticker, "target": target})

    # Check for fills that were never planned (less likely but possible)
    for ticker in filled_tickers:
        if ticker not in plan_targets and ticker != "UNKNOWN":
            mismatches.append({"type": "unplanned_fill", "ticker": ticker})

    if fills_unreadable:
        # Cannot prove clean: report unknown, not clean.
        recon_data = {
            "mismatches": mismatches,
            "status": "unknown",
            "reason": "fills.json missing or malformed",
        }
    else:
        recon_data = {
            "mismatches": mismatches,
            "status": "clean" if not mismatches else "mismatch",
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
