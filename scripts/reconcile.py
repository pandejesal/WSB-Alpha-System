import json
import logging
import os
import sys
from datetime import datetime, timezone

from src.ops.alerts import Alerts
from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

PLAN_FILE = "docs/data/ops/plan.json"
FILLS_FILE = "docs/data/ops/fills.json"
RECON_FILE = "docs/data/ops/reconciliation.json"

def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting reconciliation process...")

    alerts = Alerts()

    if not os.path.exists(PLAN_FILE):
        logger.warning(f"{PLAN_FILE} not found. Skipping reconciliation.")
        return

    if not os.path.exists(FILLS_FILE):
        logger.warning(f"{FILLS_FILE} not found. Assuming 0 fills.")
        fills_data = []
    else:
        try:
            with open(FILLS_FILE, "r") as f:
                fills_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading fills: {e}")
            fills_data = []

    try:
        with open(PLAN_FILE, "r") as f:
            plan_data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading plan: {e}")
        return

    targets = plan_data.get("targets", [])
    attribution = plan_data.get("attribution", {})

    # Simple reconciliation: compare planned notional vs filled notional
    planned_notional = {}
    for target in targets:
        ticker = target.get("ticker")
        planned_notional[ticker] = planned_notional.get(ticker, 0.0) + target.get("notional", 0.0)

    filled_notional = {}
    for fill in fills_data:
        ticker = fill.get("ticker")
        try:
            qty = float(fill.get("filled_qty", 0.0))
            price = float(fill.get("filled_avg_price", 0.0))
            notional = qty * price
            filled_notional[ticker] = filled_notional.get(ticker, 0.0) + notional
        except (ValueError, TypeError):
            logger.error(f"Invalid fill data for {ticker}: {fill}")

    mismatches = []
    all_tickers = set(planned_notional.keys()).union(set(filled_notional.keys()))

    for ticker in all_tickers:
        planned = planned_notional.get(ticker, 0.0)
        filled = filled_notional.get(ticker, 0.0)
        if abs(planned - filled) > 5.0: # $5 tolerance
            mismatches.append({
                "ticker": ticker,
                "planned_notional": planned,
                "filled_notional": filled,
                "diff": planned - filled
            })

    # Pro-rata attribution
    sleeve_pnl_deltas = {}
    for ticker, filled_amt in filled_notional.items():
        if ticker in attribution:
            ticker_attr = attribution[ticker]
            for sleeve_id, pct in ticker_attr.items():
                if sleeve_id not in sleeve_pnl_deltas:
                    sleeve_pnl_deltas[sleeve_id] = {"notional_filled": 0.0}
                sleeve_pnl_deltas[sleeve_id]["notional_filled"] += filled_amt * pct

    recon_data = {
        "mismatches": mismatches,
        "sleeve_attribution": sleeve_pnl_deltas,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    write_artifact(RECON_FILE, recon_data)

    if mismatches:
        msg = f"Reconciliation Mismatch detected in {len(mismatches)} tickers.\\n"
        for m in mismatches[:3]:
            msg += f"- {m['ticker']}: Planned ${m['planned_notional']:.2f}, Filled ${m['filled_notional']:.2f}\\n"
        alerts.send_critical(msg)
    else:
        logger.info("Reconciliation successful with no major mismatches.")

if __name__ == "__main__":
    main()
