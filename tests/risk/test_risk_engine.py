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
        cb = CircuitBreaker(max_drawdown_pct=0.15, max_daily_loss_pct=0.05)
        res = cb.check_safety(peak_equity=100.0, current_equity=98.0, daily_starting_equity=100.0)
        self.assertTrue(res["safe"])

        res = cb.check_safety(peak_equity=100.0, current_equity=84.0, daily_starting_equity=100.0)
        self.assertFalse(res["safe"])
        self.assertEqual(res["action"], "HALT_ALL_TRADING")

        res = cb.check_safety(peak_equity=150.0, current_equity=140.0, daily_starting_equity=150.0)
        self.assertFalse(res["safe"])
        self.assertEqual(res["action"], "HALT_DAILY_TRADING")
