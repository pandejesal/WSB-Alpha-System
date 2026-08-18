import json
import os
from typing import Any

import pandas as pd

from src.execution.alpaca_broker import AlpacaBroker
from src.ops.audit import AuditLogger, generate_client_order_id, write_artifact
from src.ops.risk import DDTracker, KillSwitch, update_ops_state
from src.risk.position_sizing import MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT


class PaperExecutor:
    """
    Executes the orders generated in docs/data/ops/plan.json idempotently.
    """
    def __init__(self, broker=None):
        self.broker = broker if broker else AlpacaBroker()
        self.audit = AuditLogger()
        self.run_id = ""

    def _load_json(self, path: str) -> dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def _save_json(self, path: str, data: Any):
        write_artifact(path, data)

    def _get_strategy_for_ticker(self, plan: dict[str, Any], ticker: str) -> str:
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
        fills = self._load_json("docs/data/ops/fills.json")
        if not fills or fills.get("run_id") != self.run_id:
            fills = {"run_id": self.run_id, "fills": []}

        orders_log = self._load_json("docs/data/ops/orders.json")
        if not orders_log or orders_log.get("run_id") != self.run_id:
            orders_log = {"run_id": self.run_id, "orders": []}

        existing_order_ids = {o.get("client_order_id") for o in orders_log.get("orders", []) if o.get("client_order_id")}

        account_balance = self.broker.get_account_balance()
        cash = account_balance.get("cash", 0.0)

        position_map = {p["symbol"]: p for p in positions}

        for sleeve in plan.get("sleeves", []):
            sleeve_id = sleeve["id"]

            # Check if this specific sleeve is halted
            sleeve_state = ks.get_sleeve_state(sleeve_id)
            if sleeve_state == "halt_new_orders":
                print(f"Sleeve {sleeve_id} is halted. Skipping its orders.")
                continue

            sleeve_targets = sleeve.get("targets", [])

            # Calculate REAL per-sleeve equity using the current positions and a proportional cash slice
            sleeve_position_value = 0.0
            for target in sleeve_targets:
                ticker = target.get("symbol", target.get("ticker"))
                if ticker in position_map:
                    # In a fully shared position setup, we'd pro-rate this.
                    # For simplicity of real data, we take the position's market value.
                    sleeve_position_value += position_map[ticker].get("market_value", 0.0)

            # Assume equal cash allocation per active sleeve if doing 7 sleeves
            num_sleeves = len(plan.get("sleeves", []))
            sleeve_cash = cash / num_sleeves if num_sleeves > 0 else 0.0

            sleeve_equity = sleeve_position_value + sleeve_cash

            # Define MODEL_DD from constants module instead of literal/class attribute.
            model_dd = MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT
            dd_tracker = DDTracker()
            if dd_tracker.check_and_update_breaker(sleeve_id, sleeve_equity, model_dd):
                print(f"DD breaker tripped for {sleeve_id}. Halting new orders.")
                update_ops_state(sleeve_id, "halt_new_orders")
                self.audit.log_event(self.run_id, "BREAKER_TRIPPED", "sleeve", sleeve_id, {"sleeve_equity": sleeve_equity})
                continue

            for seq, target in enumerate(sleeve_targets):
                ticker = target.get("symbol", target.get("ticker"))
                if not ticker:
                    continue

                client_order_id = generate_client_order_id(self.run_id, sleeve_id, ticker, seq)

                # Defect 1: Idempotency
                if client_order_id in existing_order_ids:
                    print(f"Order {client_order_id} already exists. Skipping (idempotency).")
                    self.audit.log_event(self.run_id, "EXECUTION_SKIPPED_ORDER", "order", client_order_id, {"reason": "duplicate"})
                    continue

                qty = target.get("qty")
                # Defect 3: No Placeholder Qty
                if qty is None:
                    print(f"Skipping {client_order_id}: missing qty.")
                    self.audit.log_event(self.run_id, "ORDER_SKIPPED", "order", client_order_id, {"reason": "missing_qty"})
                    continue

                side = target.get("side", "buy")

                print(f"Placing order {client_order_id}: {side} {qty} {ticker}")
                try:
                    res = self.broker.place_order(ticker, qty=qty, side=side, order_type="market")

                    status_details = res.get("status_details", "SUBMITTED")

                    orders_log["orders"].append({
                        "client_order_id": client_order_id,
                        "venue_order_id": res.get("order_id"),
                        "sleeve": sleeve_id,
                        "ticker": ticker,
                        "side": side,
                        "qty": qty,
                        "type": "market",
                        "status": status_details
                    })

                    existing_order_ids.add(client_order_id)

                    self.audit.log_event(self.run_id, "ORDER_PLACED", "order", client_order_id, {"ticker": ticker, "side": side, "qty": qty})

                    # Defect 4: Real Fills
                    fill_price = res.get("fill_price") or res.get("avg_price")

                    # If we don't have a fill price synchronously, some venues might return it asynchronously.
                    # We still record what we have.
                    fill_record = {
                        "client_order_id": client_order_id,
                        "venue_order_id": res.get("order_id"),
                        "qty": qty,
                        "fee": res.get("fee", 0.0),
                        "ts": pd.Timestamp.utcnow().isoformat() + "Z",
                        "side": side,
                        "ticker": ticker,
                        "sleeve": sleeve_id
                    }

                    if fill_price is not None:
                        fill_record["avg_px"] = float(fill_price)
                        fill_record["status"] = "FILLED"
                    else:
                        fill_record["status"] = status_details

                    fills["fills"].append(fill_record)

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
