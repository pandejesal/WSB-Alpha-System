import json

import pytest

from src.execution.paper_executor import PaperExecutor


class FakeBroker:
    def __init__(self):
        self.orders = []
        self.positions = []
        self.cash = 1000.0
        self.equity = 1000.0
    def get_positions(self):
        return self.positions
    def get_account_balance(self):
        return {"cash": self.cash, "equity": self.equity}
    def place_order(self, symbol, qty, side, order_type="market", stop_loss_price=None, reduce_only=False):
        order_id = f"fake_{len(self.orders)}"
        self.orders.append({"symbol": symbol, "qty": qty, "side": side})
        return {
            "status": "success",
            "order_id": order_id,
            "status_details": "FILLED",
            "fill_price": 150.0,
            "avg_price": 150.0,
            "fee": 0.0
        }

from unittest.mock import patch


@pytest.fixture
def setup_ops_dirs(tmp_path):
    docs_data_ops = tmp_path / "docs" / "data" / "ops"
    config_dir = tmp_path / "config"
    docs_data_ops.mkdir(parents=True)
    config_dir.mkdir(parents=True)

    with patch("src.ops.audit.os.makedirs"), \
         patch("src.ops.risk.os.makedirs"), \
         patch("src.execution.paper_executor.write_artifact") as mock_write, \
         patch("src.execution.paper_executor.PaperExecutor._load_json") as mock_load, \
         patch("src.ops.risk.KillSwitch.get_sleeve_state", return_value="off"), \
         patch("src.ops.risk.KillSwitch.get_state", return_value="off"), \
         patch("src.ops.risk.update_ops_state"), \
         patch("builtins.open") as mock_open:
        yield

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def test_paper_executor_idempotency(setup_ops_dirs, tmp_path):
    plan = {
        "run_id": "test_run_1",
        "sleeves": [{
            "id": "sleeve_1",
            "targets": [{"symbol": "AAPL", "qty": 1.0, "side": "buy"}]
        }]
    }
    def mock_load_json(path):
        if "plan.json" in path: return plan
        if "fills.json" in path: return {}
        if "orders.json" in path: return {}
        if "heartbeat.json" in path: return {}
        return {}

    broker = FakeBroker()
    executor = PaperExecutor(broker=broker)
    with patch.object(executor, '_load_json', side_effect=mock_load_json), \
         patch.object(executor, '_save_json'):
        executor.execute_plan()
        assert len(broker.orders) == 1

    def mock_load_json_second(path):
        if "plan.json" in path: return plan
        if "fills.json" in path: return {}
        if "orders.json" in path: return {"run_id": "test_run_1", "orders": [{"client_order_id": "test_run_1-sleeve_1-AAPL-0"}]}
        if "heartbeat.json" in path: return {}
        return {}

    executor = PaperExecutor(broker=broker)
    with patch.object(executor, '_load_json', side_effect=mock_load_json_second), \
         patch.object(executor, '_save_json'):
        executor.execute_plan()
        assert len(broker.orders) == 1

def test_paper_executor_global_killswitch(setup_ops_dirs):
    plan = {
        "run_id": "test_run_ks",
        "sleeves": [{
            "id": "sleeve_1",
            "targets": [{"symbol": "AAPL", "qty": 1.0, "side": "buy"}]
        }]
    }
    def mock_load_json(path):
        if "plan.json" in path: return plan
        return {}

    broker = FakeBroker()
    executor = PaperExecutor(broker=broker)
    with patch.object(executor, '_load_json', side_effect=mock_load_json), \
         patch("src.ops.risk.KillSwitch.get_state", return_value="halt_new_orders"):
        executor.execute_plan()
        assert len(broker.orders) == 0

def test_paper_executor_per_sleeve_breaker(setup_ops_dirs):
    plan = {
        "run_id": "test_run_ps",
        "sleeves": [
            {"id": "sleeve_halted", "targets": [{"symbol": "AAPL", "qty": 1.0, "side": "buy"}]},
            {"id": "sleeve_active", "targets": [{"symbol": "MSFT", "qty": 1.0, "side": "buy"}]}
        ]
    }
    def mock_load_json(path):
        if "plan.json" in path: return plan
        return {}

    def mock_get_sleeve_state(sleeve_id):
        if sleeve_id == "sleeve_halted":
            return "halt_new_orders"
        return "off"

    broker = FakeBroker()
    executor = PaperExecutor(broker=broker)
    with patch.object(executor, '_load_json', side_effect=mock_load_json), \
         patch.object(executor, '_save_json'), \
         patch("src.ops.risk.KillSwitch.get_sleeve_state", side_effect=mock_get_sleeve_state):
        executor.execute_plan()

    assert len(broker.orders) == 1
    assert broker.orders[0]["symbol"] == "MSFT"


def test_paper_executor_missing_qty(setup_ops_dirs):
    plan = {
        "run_id": "test_run_qty",
        "sleeves": [{
            "id": "sleeve_1",
            "targets": [{"symbol": "AAPL", "side": "buy"}] # No qty
        }]
    }
    def mock_load_json(path):
        if "plan.json" in path: return plan
        return {}

    broker = FakeBroker()
    executor = PaperExecutor(broker=broker)
    with patch.object(executor, '_load_json', side_effect=mock_load_json), \
         patch.object(executor, '_save_json'):
        with pytest.raises(ValueError, match="Missing quantity for order"):
            executor.execute_plan()
        assert len(broker.orders) == 0

def test_paper_executor_real_fills(setup_ops_dirs):
    plan = {
        "run_id": "test_run_fills",
        "sleeves": [{
            "id": "sleeve_1",
            "targets": [{"symbol": "AAPL", "qty": 1.0, "side": "buy"}]
        }]
    }
    def mock_load_json(path):
        if "plan.json" in path: return plan
        return {}

    broker = FakeBroker()
    executor = PaperExecutor(broker=broker)

    saved_files = {}
    def mock_save_json(path, data):
        saved_files[path] = data

    with patch.object(executor, '_load_json', side_effect=mock_load_json), \
         patch.object(executor, '_save_json', side_effect=mock_save_json):
        executor.execute_plan()

    fills = saved_files.get("docs/data/ops/fills.json")
    assert fills is not None
    assert len(fills["fills"]) == 1
    assert fills["fills"][0]["avg_px"] == 150.0
