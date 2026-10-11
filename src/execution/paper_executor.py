import json
import os
from datetime import datetime, timezone
from typing import Any

from src.execution.alpaca_broker import AlpacaBroker
from src.ops.alerts import AlertManager
from src.ops.artifacts import (
    AMBIGUOUS_ORDER_STATUSES,
    CONFIRMED_FILL_STATUSES,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_PARTIAL,
    ORDER_STATUS_SUBMITTED,
    ORDER_STATUS_SUBMITTING,
    ORDER_STATUS_UNKNOWN,
    RECON_STATUS_CLEAN,
    RECON_STATUS_MISMATCH,
    RECON_STATUS_UNKNOWN,
    make_fill_record,
)
from src.ops.audit import AuditLogger, generate_client_order_id, write_artifact
from src.ops.killswitch import KillSwitch
from src.ops.risk import DDTracker, update_ops_state
from src.risk.position_sizing import MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT
from src.utils.config import config

FILLS_PATH = "docs/data/ops/fills.json"
ORDERS_PATH = "docs/data/ops/orders.json"
RECON_PATH = "docs/data/ops/recon.json"
HEARTBEAT_PATH = "docs/data/ops/heartbeat.json"

# Broker status_details strings that mean "received, not yet filled".
_ACK_STATUSES = {"SUBMITTED", "ACCEPTED", "PENDING_NEW", "NEW", "ACCEPTED_FOR_BIDDING", "HELD", "PENDING"}
# Broker status_details strings that mean "partially filled".
_PARTIAL_STATUSES = {"PARTIAL", "PARTIALLY_FILLED", "FILLED_PARTIAL"}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PaperExecutor:
    """
    Executes the orders generated in docs/data/ops/plan.json idempotently.

    Audit findings addressed:
    - F1/F3: fills.json uses the canonical schema in src/ops/artifacts.py
      (sleeve_id key; only broker-confirmed fills recorded in fills.json,
      submissions live in orders.json).
    - F2: paper-only. The default broker is constructed with paper=True and a
      live trading configuration is a hard error — a paper run can never be
      routed to a live endpoint by a shared flag.
    - F4: order intent is persisted BEFORE the broker call; outcomes are a
      real state machine (SUBMITTING/SUBMITTED/PARTIAL/FILLED/.../UNKNOWN);
      ambiguous outcomes are never blindly retried; reconciliation derives
      deltas from before/after positions and reports unknown on failure.
    """

    def __init__(self, broker=None):
        if broker is None:
            # Paper-only by construction (F2): explicit paper=True ignores the
            # LIVE_TRADING_ENABLED flag at the broker layer.
            if config.trading.live_trading_enabled:
                raise RuntimeError(
                    "PaperExecutor refuses to run: live trading is enabled in config. "
                    "Paper execution must never route to a live endpoint."
                )
            self.broker = AlpacaBroker(paper=True)
        else:
            self.broker = broker
        if getattr(self.broker, "is_paper", True) is False:
            raise RuntimeError("PaperExecutor requires a paper broker (is_paper=False was supplied).")
        self.audit = AuditLogger()
        self.run_id = ""

    def _load_json(self, path: str) -> dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def _save_json(self, path: str, data: Any):
        write_artifact(path, data)

    def _load_run_scoped(self, path: str, list_key: str) -> dict:
        """Load a run-scoped artifact, normalizing legacy/bare shapes."""
        doc = self._load_json(path)
        if not isinstance(doc, dict) or doc.get("run_id") != self.run_id:
            return {"run_id": self.run_id, list_key: []}
        if not isinstance(doc.get(list_key), list):
            return {"run_id": self.run_id, list_key: []}
        return doc

    def _get_strategy_for_ticker(self, plan: dict[str, Any], ticker: str) -> str:
        for sleeve in plan.get("sleeves", []):
            for target in sleeve.get("targets", []):
                if target.get("symbol") == ticker or target.get("ticker") == ticker:
                    return sleeve["id"]
        return "unknown"

    def _map_broker_status(self, res: dict) -> tuple[str, float | None]:
        """Broker response -> (order status, fill price or None)."""
        fill_price = res.get("fill_price") or res.get("avg_price")
        raw = str(res.get("status_details", "") or "").upper()
        if fill_price is not None:
            return ORDER_STATUS_FILLED, float(fill_price)
        if raw in _PARTIAL_STATUSES:
            return ORDER_STATUS_PARTIAL, None
        if raw in _ACK_STATUSES:
            return ORDER_STATUS_SUBMITTED, None
        if not raw:
            return ORDER_STATUS_UNKNOWN, None
        return ORDER_STATUS_UNKNOWN, None

    def _find_order(self, orders: list[dict], client_order_id: str) -> dict | None:
        for o in orders:
            if o.get("client_order_id") == client_order_id:
                return o
        return None

    def _reconcile_ambiguous_orders(self, orders_log: dict, fills: dict) -> None:
        """Query the broker for orders whose outcome is unknown before deciding
        anything. If the broker cannot answer, the entry stays ambiguous and is
        never resubmitted (fail closed)."""
        getter = getattr(self.broker, "get_order", None)
        if getter is None:
            return
        for order in orders_log.get("orders", []):
            if order.get("status") not in AMBIGUOUS_ORDER_STATUSES:
                continue
            client_order_id = order.get("client_order_id")
            try:
                res = getter(client_order_id)
            except Exception as e:  # noqa: BLE001 - lookup failure keeps ambiguity
                self.audit.log_event(self.run_id, "ORDER_LOOKUP_FAILED", "order", client_order_id, {"error": str(e)})
                continue
            if not res:
                continue
            status, px = self._map_broker_status(res)
            order["venue_order_id"] = res.get("order_id", order.get("venue_order_id"))
            order["status"] = status
            if status in CONFIRMED_FILL_STATUSES and px is not None and not any(
                f.get("client_order_id") == client_order_id for f in fills["fills"]
            ):
                fills["fills"].append(make_fill_record(
                    client_order_id=client_order_id,
                    sleeve_id=order.get("sleeve_id", "unknown"),
                    ticker=order.get("ticker", ""),
                    side=order.get("side", ""),
                    qty=order.get("qty", 0.0),
                    status=ORDER_STATUS_FILLED,
                    avg_px=px,
                    venue_order_id=res.get("order_id"),
                    ts=_utcnow_iso(),
                ))

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
        if state in ["halt_new_orders", "halt_only", "flat"]:
             print(f"Kill switch active ({state}). Skipping execution.")
             self.audit.log_event(self.run_id, "EXECUTION_SKIPPED", "system", "all", {"reason": f"Kill switch: {state}"})
             return

        if plan.get("blocked"):
            print(f"Plan is blocked: {plan['blocked']}. Skipping execution.")
            return

        # 2. Reconcile startup state (Nautilus pattern)
        # Snapshot defensively: brokers may return a live/mutable list.
        try:
            positions = [dict(p) for p in self.broker.get_positions()]
        except Exception as e:  # noqa: BLE001 - broker failure must abort the run
            print(f"Failed to fetch positions: {e}")
            return

        # 3. Order Placement (Idempotent)
        fills = self._load_run_scoped(FILLS_PATH, "fills")
        orders_log = self._load_run_scoped(ORDERS_PATH, "orders")

        existing_order_ids = {o.get("client_order_id") for o in orders_log.get("orders", []) if o.get("client_order_id")}

        # Resolve any previously ambiguous orders first (never blind-retry).
        self._reconcile_ambiguous_orders(orders_log, fills)

        account_balance = self.broker.get_account_balance()
        cash = account_balance.get("cash", 0.0)

        position_map = {p["symbol"]: p for p in positions}

        for sleeve in plan.get("sleeves", []):
            sleeve_id = sleeve["id"]

            # Check if this specific sleeve is halted
            sleeve_state = ks.get_sleeve_state(sleeve_id)
            if sleeve_state in ["halt_new_orders", "halt_only", "flat"]:
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

                # Defect 1: Idempotency — local record of any prior submission
                # (including ambiguous ones) blocks resubmission for this ID.
                if client_order_id in existing_order_ids:
                    print(f"Order {client_order_id} already exists. Skipping (idempotency).")
                    self.audit.log_event(self.run_id, "EXECUTION_SKIPPED_ORDER", "order", client_order_id, {"reason": "duplicate"})
                    continue

                qty = target.get("qty")
                if qty is None:
                    print(f"Failing fast on {client_order_id}: missing qty.")
                    self.audit.log_event(self.run_id, "ORDER_FAILED", "order", client_order_id, {"reason": "missing_qty"})
                    raise ValueError(f"Missing quantity for order {client_order_id}")

                side = target.get("side", "buy")

                print(f"Placing order {client_order_id}: {side} {qty} {ticker}")

                # Persist intent BEFORE the broker call so a crash after
                # submission still blocks the idempotent retry (F4).
                order_entry = {
                    "client_order_id": client_order_id,
                    "venue_order_id": None,
                    "sleeve_id": sleeve_id,
                    "ticker": ticker,
                    "side": side,
                    "qty": qty,
                    "type": "market",
                    "status": ORDER_STATUS_SUBMITTING,
                    "ts": _utcnow_iso(),
                }
                orders_log["orders"].append(order_entry)
                existing_order_ids.add(client_order_id)
                self._save_json(ORDERS_PATH, orders_log)

                try:
                    res = self.broker.place_order(
                        ticker, qty=qty, side=side, order_type="market",
                        client_order_id=client_order_id,
                    )

                    status, fill_price = self._map_broker_status(res)
                    order_entry["venue_order_id"] = res.get("order_id")
                    order_entry["status"] = status
                    self._save_json(ORDERS_PATH, orders_log)
                    self.audit.log_event(
                        self.run_id, "ORDER_PLACED", "order", client_order_id,
                        {"ticker": ticker, "side": side, "qty": qty, "status": status},
                    )

                    # Defect 4: only broker-confirmed fills enter fills.json.
                    if fill_price is not None:
                        fills["fills"].append(make_fill_record(
                            client_order_id=client_order_id,
                            sleeve_id=sleeve_id,
                            ticker=ticker,
                            side=side,
                            qty=qty,
                            status=ORDER_STATUS_FILLED,
                            avg_px=fill_price,
                            venue_order_id=res.get("order_id"),
                            fee=res.get("fee", 0.0) or 0.0,
                            ts=_utcnow_iso(),
                        ))
                    elif status not in CONFIRMED_FILL_STATUSES:
                        self.audit.log_event(
                            self.run_id, "ORDER_NOT_FILLED", "order", client_order_id,
                            {"status": status},
                        )

                except Exception as e:  # noqa: BLE001 - outcome is genuinely ambiguous
                    # The broker may have accepted the order; mark UNKNOWN and
                    # never resubmit within or across runs.
                    order_entry["status"] = ORDER_STATUS_UNKNOWN
                    order_entry["error"] = str(e)
                    self._save_json(ORDERS_PATH, orders_log)
                    print(f"Order outcome UNKNOWN for {client_order_id}: {e}")
                    self.audit.log_event(
                        self.run_id, "ORDER_UNKNOWN", "order", client_order_id,
                        {"ticker": ticker, "side": side, "qty": qty, "error": str(e)},
                    )

        # 4. Sync Positions & Recon (F4: real deltas, honest status)
        recon = self._build_reconciliation(positions, fills["fills"], orders_log["orders"])

        # 5. Finalize Artifacts
        self._save_json(ORDERS_PATH, orders_log)
        self._save_json(FILLS_PATH, fills)
        self._save_json(RECON_PATH, recon)

        heartbeat = self._load_json(HEARTBEAT_PATH)
        if not isinstance(heartbeat, dict):
            heartbeat = {}
        heartbeat["orders_submitted"] = len(orders_log["orders"])
        heartbeat["unconfirmed_orders"] = len([
            o for o in orders_log["orders"]
            if o.get("status") in AMBIGUOUS_ORDER_STATUSES or o.get("status") == ORDER_STATUS_UNKNOWN
        ])
        self._save_json(HEARTBEAT_PATH, heartbeat)

        if recon["status"] != RECON_STATUS_CLEAN:
            try:
                AlertManager().send("WARN", f"Reconciliation not clean for run {self.run_id}: {recon['status']}")
            except Exception as e:  # noqa: BLE001 - alerting must not crash the job
                print(f"Failed to send reconciliation alert: {e}")

        print("Paper execution completed.")

    def _build_reconciliation(self, positions_before: list[dict], fills: list[dict], orders: list[dict]) -> dict:
        """Compare broker positions before/after this run against the positions
        the run's confirmed fills imply. A fetch failure yields status=unknown,
        never clean."""
        before_map = {p.get("symbol"): float(p.get("qty", 0.0) or 0.0) for p in positions_before}
        expected = dict(before_map)

        for fill in fills:
            if str(fill.get("status", "")).upper() not in CONFIRMED_FILL_STATUSES:
                continue
            symbol = fill.get("ticker")
            qty = float(fill.get("qty", 0.0) or 0.0)
            if symbol is None:
                continue
            step = qty if str(fill.get("side", "buy")).lower() == "buy" else -qty
            expected[symbol] = expected.get(symbol, 0.0) + step

        try:
            after_positions = [dict(p) for p in self.broker.get_positions()]
        except Exception as e:  # noqa: BLE001 - honest unknown, not empty-clean
            print(f"Reconciliation position fetch failed: {e}")
            return {
                "run_id": self.run_id,
                "ts": _utcnow_iso(),
                "before": {"positions": positions_before},
                "after": {"positions": []},
                "deltas": [],
                "mismatches": [{"type": "positions_fetch_failed", "error": str(e)}],
                "status": RECON_STATUS_UNKNOWN,
            }

        after_map = {p.get("symbol"): float(p.get("qty", 0.0) or 0.0) for p in after_positions}

        deltas = []
        mismatches = []
        for symbol in sorted(set(before_map) | set(after_map) | set(expected)):
            b = before_map.get(symbol, 0.0)
            a = after_map.get(symbol, 0.0)
            e = expected.get(symbol, 0.0)
            if abs(a - b) > 1e-9:
                deltas.append({"symbol": symbol, "before_qty": b, "after_qty": a, "expected_qty": e, "delta": a - b})
            if abs(a - e) > 1e-9:
                mismatches.append({"type": "position_mismatch", "symbol": symbol, "expected_qty": e, "actual_qty": a})

        unconfirmed = [
            o.get("client_order_id") for o in orders
            if o.get("status") in AMBIGUOUS_ORDER_STATUSES or o.get("status") == ORDER_STATUS_UNKNOWN
        ]
        if unconfirmed:
            mismatches.append({"type": "unconfirmed_orders", "client_order_ids": unconfirmed})

        status = RECON_STATUS_CLEAN if not mismatches else RECON_STATUS_MISMATCH
        return {
            "run_id": self.run_id,
            "ts": _utcnow_iso(),
            "before": {"positions": positions_before},
            "after": {"positions": after_positions},
            "deltas": deltas,
            "mismatches": mismatches,
            "status": status,
        }


if __name__ == "__main__":
    executor = PaperExecutor()
    executor.execute_plan()
