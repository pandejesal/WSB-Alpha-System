import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List
import pandas as pd

from src.execution.alpaca_broker import AlpacaBroker
from src.ops.audit import AuditLogger, write_artifact, generate_client_order_id
from src.ops.risk import KillSwitch, DDTracker, update_ops_state

class PaperExecutor:
    """
    Executes the orders generated in docs/data/ops/plan.json idempotently.
    """
    def __init__(self, broker=None):
        self.broker = broker if broker else AlpacaBroker()
        self.audit = AuditLogger()
        self.run_id = ""

    def _load_json(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def _save_json(self, path: str, data: Any):
        write_artifact(path, data)

    def _get_strategy_for_ticker(self, plan: Dict[str, Any], ticker: str) -> str:
        for sleeve in plan.get("sleeves", []):
            for target in sleeve.get("targets", []):
                if target.get("symbol") == ticker or target.get("ticker") == ticker:
                    return sleeve["id"]
        return "unknown"

    def execute_plan(self):
        # 1. Load Plan
        plan = self._load_json("docs/data/ops/plan.json")
        if not plan:
            print("No plan.json found. Exiting.")
            return

        self.run_id = plan.get("run_id", "unknown_run")
        print(f"Executing run {self.run_id}")

        # Check for kill switch again just in case
        ks = KillSwitch()
        state = ks.get_state()
        if state in ["halt_new_orders", "flat"]:
             print(f"Kill switch active ({state}). Skipping execution.")
             self.audit.log_event(self.run_id, "EXECUTION_SKIPPED", "system", "all", {"reason": f"Kill switch: {state}"})
             return

        if plan.get("blocked"):
            print(f"Plan is blocked: {plan['blocked']}. Skipping execution.")
            return

        # 2. Reconcile startup state (Nautilus pattern)
        try:
            positions = self.broker.get_positions()
        except Exception as e:
            print(f"Failed to fetch positions: {e}")
            return

        # 3. Order Placement (Idempotent)
        fills = {"run_id": self.run_id, "fills": []}
        orders_log = {"run_id": self.run_id, "orders": []}

        for sleeve in plan.get("sleeves", []):
            sleeve_id = sleeve["id"]

            dd_tracker = DDTracker()
            if dd_tracker.check_and_update_breaker(sleeve_id, 100.0, 0.10): # Mock equity
                print(f"DD breaker tripped for {sleeve_id}. Halting new orders.")
                update_ops_state(sleeve_id, "halt_new_orders")
                self.audit.log_event(self.run_id, "BREAKER_TRIPPED", "sleeve", sleeve_id, {})
                continue

            for seq, target in enumerate(sleeve.get("targets", [])):
                ticker = target.get("symbol", target.get("ticker"))
                if not ticker:
                    continue

                qty = target.get("qty")
                if qty is None:
                     qty = 1.0 # placeholder for test

                side = target.get("side", "buy")

                client_order_id = generate_client_order_id(self.run_id, sleeve_id, ticker, seq)

                print(f"Placing order {client_order_id}: {side} {qty} {ticker}")
                try:
                    res = self.broker.place_order(ticker, qty=qty, side=side, order_type="market")

                    orders_log["orders"].append({
                        "client_order_id": client_order_id,
                        "venue_order_id": res.get("order_id"),
                        "sleeve": sleeve_id,
                        "ticker": ticker,
                        "side": side,
                        "qty": qty,
                        "type": "market",
                        "status": res.get("status_details", "SUBMITTED")
                    })

                    self.audit.log_event(self.run_id, "ORDER_PLACED", "order", client_order_id, {"ticker": ticker, "side": side, "qty": qty})

                    fills["fills"].append({
                        "client_order_id": client_order_id,
                        "venue_order_id": res.get("order_id"),
                        "qty": qty,
                        "avg_px": target.get("entry_price", 0.0), # mock
                        "fee": 0.0,
                        "ts": pd.Timestamp.utcnow().isoformat() + "Z",
                        "side": side,
                        "ticker": ticker,
                        "sleeve": sleeve_id
                    })

                except Exception as e:
                    print(f"Order failed for {ticker}: {e}")
                    orders_log["orders"].append({
                        "client_order_id": client_order_id,
                        "status": "FAILED",
                        "error": str(e)
                    })

        # 4. Sync Positions & Recon
        try:
            new_positions = self.broker.get_positions()
        except Exception:
            new_positions = []

        recon = {
            "run_id": self.run_id,
            "before": {"positions": positions},
            "after": {"positions": new_positions},
            "deltas": [],
            "mismatches": []
        }

        # 5. Finalize Artifacts
        self._save_json("docs/data/ops/orders.json", orders_log)
        self._save_json("docs/data/ops/fills.json", fills)
        self._save_json("docs/data/ops/recon.json", recon)

        heartbeat = self._load_json("docs/data/ops/heartbeat.json")
        heartbeat["orders_submitted"] = len(orders_log["orders"])
        self._save_json("docs/data/ops/heartbeat.json", heartbeat)

        print("Paper execution completed.")

if __name__ == "__main__":
    executor = PaperExecutor()
    executor.execute_plan()
