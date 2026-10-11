"""Executor <-> GateEvaluator integration tests (audit findings F3/F4).

Runs PaperExecutor against a mocked broker, persists the artifacts it writes,
and feeds them into GateEvaluator.evaluate_all() — the exact integration that
was broken when the executor wrote {"sleeve": ...} and the gate expected
{"sleeve_id": ...}.
"""

import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.execution.paper_executor import PaperExecutor
from src.ops.gate_evaluator import GateEvaluator

PLAN_PATH = "docs/data/ops/plan.json"
FILLS_PATH = "docs/data/ops/fills.json"
ORDERS_PATH = "docs/data/ops/orders.json"
RECON_PATH = "docs/data/ops/recon.json"
HEARTBEAT_PATH = "docs/data/ops/heartbeat.json"


class FakeBroker:
    """Mock broker. Fills synchronously unless configured otherwise.

    Mirrors fills into positions so reconciliation has a realistic
    before/after to compare (a broker that reports positions reflects fills).
    """

    def __init__(self, fill_price=150.0, raise_on_place=False, positions_after=None, fail_second_positions=False, track_positions=True):
        self.orders = []
        self.positions = []
        self.fill_price = fill_price
        self.raise_on_place = raise_on_place
        self.positions_after = positions_after if positions_after is not None else []
        self.fail_second_positions = fail_second_positions
        self.track_positions = track_positions
        self._positions_calls = 0

    def get_positions(self):
        self._positions_calls += 1
        if self.fail_second_positions and self._positions_calls > 1:
            raise ConnectionError("positions fetch failed")
        return self.positions

    def get_account_balance(self):
        return {"cash": 10000.0, "equity": 10000.0}

    def place_order(self, symbol, qty, side, order_type="market", stop_loss_price=None, client_order_id=None):
        self.orders.append({"symbol": symbol, "qty": qty, "side": side, "client_order_id": client_order_id})
        if self.raise_on_place:
            raise TimeoutError("ambiguous outcome")
        if self.track_positions:
            step = qty if str(side).lower() == "buy" else -qty
            pos = next((p for p in self.positions if p["symbol"] == symbol), None)
            if pos is None:
                self.positions.append({"symbol": symbol, "qty": step, "market_value": step * self.fill_price})
            else:
                pos["qty"] += step
        return {
            "status": "success",
            "order_id": f"venue_{len(self.orders)}",
            "status_details": "FILLED",
            "fill_price": self.fill_price,
            "avg_price": self.fill_price,
            "fee": 0.0,
        }


def _plan(run_id="run_1", sleeves=None):
    if sleeves is None:
        sleeves = [{"id": "sleeve_a", "targets": [{"symbol": "AAPL", "qty": 1.0, "side": "buy"}]}]
    return {"run_id": run_id, "sleeves": sleeves}


@pytest.fixture
def executor_env(monkeypatch):
    """In-memory artifact store; no filesystem, no audit file."""
    store = {}

    def fake_load(self, path):
        return copy.deepcopy(store.get(path, {}))

    def fake_save(self, path, data):
        store[path] = copy.deepcopy(data)

    monkeypatch.setattr(PaperExecutor, "_load_json", fake_load)
    monkeypatch.setattr(PaperExecutor, "_save_json", fake_save)
    store[PLAN_PATH] = _plan()
    return store


def _heartbeat_artifact(days):
    history = [{"run_id": f"t-{d}", "ts": f"{d}T12:00:00Z", "status": "ok", "job": "test"} for d in days]
    return {"history": history, "latest": history[-1] if history else None}


def _trading_days(n):
    days = []
    d = datetime.now(timezone.utc) - timedelta(days=1)
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    return list(reversed(days))


def _gate_data(fills_doc, recon_status="clean"):
    """Assemble gate inputs from executor artifacts (gate reads docs/data layout).

    The gate's G7 input (docs/data/ops/reconciliation.json) is produced by
    scripts/reconcile.py; the executor's own recon.json carries the same
    status contract, so the executor run's status drives this mapping.
    """
    return {
        "fills": fills_doc["fills"],
        "sharpe": {"ci_lower": 0.5},
        "permutation": {"p_value": 0.5},
        "heartbeats": _heartbeat_artifact(_trading_days(7)),
        "rehearsal": {"restored": True},
        "reconciliation": {"status": recon_status},
    }


def test_executor_artifact_feeds_gate_evaluator(executor_env):
    """F3: executor writes the wrapper + sleeve_id; the gate counts real trades."""
    sleeve_targets = [{"symbol": f"T{i}", "qty": 1.0, "side": "buy"} for i in range(55)]
    executor_env[PLAN_PATH] = _plan(sleeves=[{"id": "sleeve_a", "targets": sleeve_targets}])

    broker = FakeBroker()
    PaperExecutor(broker=broker).execute_plan()

    fills_doc = executor_env[FILLS_PATH]
    assert len(fills_doc["fills"]) == 55
    assert all(f["sleeve_id"] == "sleeve_a" for f in fills_doc["fills"])
    assert all(f["status"] == "FILLED" for f in fills_doc["fills"])

    results = GateEvaluator().evaluate_all(_gate_data(fills_doc))
    assert results["G1"] is True   # >= 50 confirmed trades
    assert results["G2"] is True   # >= 10 per sleeve
    assert results["details"]["G1"]["trades"] == 55
    assert results["details"]["G2"]["per_sleeve"] == {"sleeve_a": 55}

    # The reconciliation artifact is honest and clean.
    recon = executor_env[RECON_PATH]
    assert recon["status"] == "clean"
    assert recon["mismatches"] == []

def test_client_order_id_reaches_broker(executor_env):
    """F4: the idempotency key is passed to the broker, not just kept locally."""
    broker = FakeBroker()
    PaperExecutor(broker=broker).execute_plan()
    assert len(broker.orders) == 1
    assert broker.orders[0]["client_order_id"] == "run_1-sleeve_a-AAPL-0"


def test_submission_is_not_recorded_as_fill(executor_env):
    """F4: broker-acknowledged-but-unfilled orders stay out of fills.json."""
    broker = FakeBroker(fill_price=None)
    # fill_price=None with an ack status means "submitted, not filled"
    def place(symbol, qty, side, order_type="market", stop_loss_price=None, client_order_id=None):
        broker.orders.append({"symbol": symbol, "client_order_id": client_order_id})
        return {"status": "success", "order_id": "v1", "status_details": "SUBMITTED"}
    broker.place_order = place

    PaperExecutor(broker=broker).execute_plan()

    fills_doc = executor_env[FILLS_PATH]
    assert fills_doc["fills"] == []  # no fill recorded
    orders = executor_env[ORDERS_PATH]["orders"]
    assert len(orders) == 1 and orders[0]["status"] == "SUBMITTED"

    results = GateEvaluator().evaluate_all(_gate_data(fills_doc))
    assert results["G1"] is False  # submissions never count toward gates
    assert executor_env[HEARTBEAT_PATH]["unconfirmed_orders"] == 1


def test_ambiguous_outcome_not_retried_and_not_clean(executor_env):
    """F4: an exception mid-call yields UNKNOWN, no resubmission, recon != clean."""
    broker = FakeBroker(raise_on_place=True)
    PaperExecutor(broker=broker).execute_plan()

    orders = executor_env[ORDERS_PATH]["orders"]
    assert len(orders) == 1 and orders[0]["status"] == "UNKNOWN"
    assert executor_env[FILLS_PATH]["fills"] == []

    # Simulated restart/re-run: the persisted UNKNOWN intent blocks resubmission.
    broker2 = FakeBroker()
    PaperExecutor(broker=broker2).execute_plan()
    assert broker2.orders == []  # never blindly retried
    assert len(broker.orders) == 1  # original never succeeded twice

    recon = executor_env[RECON_PATH]
    assert recon["status"] != "clean"
    assert any(m["type"] == "unconfirmed_orders" for m in recon["mismatches"])

    results = GateEvaluator().evaluate_all(_gate_data(executor_env[FILLS_PATH], recon_status="mismatch"))
    assert results["G7"] is False  # gate data must reflect a non-clean recon


def test_intent_persisted_before_broker_call(executor_env):
    """F4: a crash between intent-persist and broker-call still blocks retry."""
    broker = FakeBroker()

    def save_then_crash(self, path, data):
        # Persist the intent record FIRST (like a durable write), then crash.
        if path == ORDERS_PATH:
            executor_env[path] = json.loads(json.dumps(data))
            raise KeyboardInterrupt("simulated crash after intent persisted")
        executor_env[path] = json.loads(json.dumps(data))

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(PaperExecutor, "_save_json", save_then_crash)
        with pytest.raises(KeyboardInterrupt):
            PaperExecutor(broker=broker).execute_plan()

    # The broker was NOT reached (intent precedes the call) and the intent
    # record exists durably.
    assert broker.orders == []
    intent = executor_env[ORDERS_PATH]["orders"]
    assert len(intent) == 1 and intent[0]["status"] == "SUBMITTING"

    # Restart/retry: the persisted intent blocks resubmission.
    broker2 = FakeBroker()
    PaperExecutor(broker=broker2).execute_plan()
    assert broker2.orders == []


def test_position_fetch_failure_yields_unknown_not_clean(executor_env):
    """F4: recon is unknown (not empty-clean) when the after-fetch fails."""
    broker = FakeBroker(fail_second_positions=True)
    PaperExecutor(broker=broker).execute_plan()
    recon = executor_env[RECON_PATH]
    assert recon["status"] == "unknown"
    assert any(m["type"] == "positions_fetch_failed" for m in recon["mismatches"])


def test_paper_executor_refuses_live_broker(executor_env):
    """F2: an injected live-configured broker is a hard error."""
    class LiveBroker(FakeBroker):
        is_paper = False

    with pytest.raises(RuntimeError, match="paper broker"):
        PaperExecutor(broker=LiveBroker())


def test_paper_executor_refuses_live_config(executor_env, monkeypatch):
    """F2: live trading enabled in config is a hard error for the paper path."""
    import src.execution.paper_executor as pe

    class _Trading:
        live_trading_enabled = True

    class _Wrapper:
        trading = _Trading()

    # The executor binds `config` at import time — patch its own reference.
    monkeypatch.setattr(pe, "config", _Wrapper())
    with pytest.raises(RuntimeError, match="refuses to run"):
        PaperExecutor()


def test_duplicate_order_id_skipped(executor_env):
    """F4: an existing local record for the same client_order_id blocks resubmission."""
    broker = FakeBroker()
    PaperExecutor(broker=broker).execute_plan()
    assert len(broker.orders) == 1

    # Second run against the same persisted artifacts (retry/restart).
    broker2 = FakeBroker()
    PaperExecutor(broker=broker2).execute_plan()
    assert broker2.orders == []


def test_reconciliation_detects_position_mismatch(executor_env):
    """F4: a position the fills do not explain is reported as a mismatch."""
    class DriftingBroker(FakeBroker):
        """Positions change in a way the run's fills do not explain."""
        def __init__(self):
            super().__init__()
            self._calls = 0

        def get_positions(self):
            self._calls += 1
            if self._calls <= 1:
                return []  # before
            return [{"symbol": "AAPL", "qty": 1.0, "market_value": 150.0},
                    {"symbol": "XYZ", "qty": 9.0, "market_value": 900.0}]  # after: unexplained XYZ

    PaperExecutor(broker=DriftingBroker()).execute_plan()
    recon = executor_env[RECON_PATH]
    assert recon["status"] == "mismatch"
    symbols = {m["symbol"] for m in recon["mismatches"] if m["type"] == "position_mismatch"}
    assert "XYZ" in symbols  # unexpected position detected, not silently clean
