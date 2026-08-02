import unittest
from src.risk.position_sizer import PositionSizer
from src.risk.circuit_breakers import CircuitBreaker

class TestRiskEngine(unittest.TestCase):
    def test_position_sizer(self):
        sizer = PositionSizer(base_risk_pct=0.02, max_notional_leverage=1.0)
        res = sizer.calculate_size(account_equity=100.0, entry_price=50.0, atr=2.0, stop_loss_atr_multiplier=2.0, confidence_score=100.0)
        self.assertEqual(res["quantity"], 0.5)
        self.assertEqual(res["notional_value"], 25.0)

    def test_position_sizer_leverage_cap(self):
        sizer = PositionSizer(base_risk_pct=0.10, max_notional_leverage=1.0)
        res = sizer.calculate_size(account_equity=100.0, entry_price=10.0, atr=0.25, stop_loss_atr_multiplier=2.0, confidence_score=100.0)
        self.assertEqual(res["quantity"], 10.0)
        self.assertEqual(res["notional_value"], 100.0)

    def test_circuit_breaker(self):
        cb = CircuitBreaker(daily_limit=0.05, total_limit=0.15)
        self.assertTrue(cb.check_circuit_breakers(lambda: 98.0))

        with self.assertRaises(Exception):
            cb.check_circuit_breakers(lambda: 84.0)





