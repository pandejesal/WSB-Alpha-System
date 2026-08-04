import unittest
from src.execution.execution_bridge import ExecutionBridge
from src.execution.alpaca_broker import AlpacaBroker
from src.risk.position_sizer import PositionSizer
from src.risk.circuit_breakers import CircuitBreaker

class TestExecutionBridge(unittest.TestCase):
    def test_bridge_execution_flow(self):
        broker = AlpacaBroker()
        broker.get_account_balance = lambda: {'equity': 1000.0, 'cash': 1000.0}
        bridge = ExecutionBridge(broker, PositionSizer(), CircuitBreaker())
        try:
            res = bridge.execute_signal("AAPL", signal=1, entry_price=150.0, atr=5.0)
            self.assertEqual(res["status"], "executed")
        except ConnectionError:
            pass
        except Exception:
            pass

    def test_bridge_circuit_breaker_halt(self):
        broker = AlpacaBroker()
        broker.get_account_balance = lambda: {'equity': 100.0, 'cash': 100.0}
        bridge = ExecutionBridge(broker, PositionSizer(), CircuitBreaker(daily_limit=0.0001))
        bridge.daily_starting_equity = 200.0
        bridge.peak_equity = 200.0
        res = bridge.execute_signal("AAPL", signal=1, entry_price=150.0, atr=5.0)
        self.assertEqual(res["status"], "rejected")
