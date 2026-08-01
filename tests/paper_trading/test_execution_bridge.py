import unittest
from paper_trading.execution_bridge import ExecutionBridge
from brokers.alpaca_broker import AlpacaBroker
from risk.position_sizer import PositionSizer
from risk.circuit_breakers import CircuitBreaker

class TestExecutionBridge(unittest.TestCase):
    def test_bridge_execution_flow(self):
        # Using mock objects intrinsically initialized in these classes
        broker = AlpacaBroker()
        sizer = PositionSizer()
        cb = CircuitBreaker()

        bridge = ExecutionBridge(broker, sizer, cb)

        # Simulating a buy signal for AAPL at $150 with an ATR of $5
        res = bridge.execute_signal("AAPL", signal=1, entry_price=150.0, atr=5.0)

        self.assertEqual(res["status"], "executed")
        self.assertIn("broker_response", res)
        self.assertEqual(res["broker_response"]["status"], "success")

    def test_bridge_circuit_breaker_halt(self):
        broker = AlpacaBroker()
        sizer = PositionSizer()
        # Extremely tight circuit breaker to force a halt
        cb = CircuitBreaker(max_drawdown_pct=0.0001)

        bridge = ExecutionBridge(broker, sizer, cb)
        bridge.peak_equity = 200.0
        # Will pull $100 mock balance, triggering 50% drawdown > 0.01% max

        res = bridge.execute_signal("AAPL", signal=1, entry_price=150.0, atr=5.0)

        self.assertEqual(res["status"], "rejected")
        self.assertIn("EMERGENCY HALT", res["reason"])

if __name__ == '__main__':
    unittest.main()
