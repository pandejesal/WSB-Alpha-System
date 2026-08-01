import unittest
from risk.position_sizer import PositionSizer
from risk.circuit_breakers import CircuitBreaker

class TestRiskEngine(unittest.TestCase):
    def test_position_sizer(self):
        sizer = PositionSizer(base_risk_pct=0.02, max_notional_leverage=1.0)

        # Scenario: $100 account, $50 asset, 2 ATR, 100 confidence (1.0x multiplier).
        # Risk amount = $2. Stop loss dist = 2 * 2 = $4. Qty = 2 / 4 = 0.5 shares. Notional = $25.
        res = sizer.calculate_size(account_equity=100.0, entry_price=50.0, atr=2.0, stop_loss_atr_multiplier=2.0, confidence_score=100.0)

        self.assertEqual(res["quantity"], 0.5)
        self.assertEqual(res["notional_value"], 25.0)

    def test_position_sizer_leverage_cap(self):
        sizer = PositionSizer(base_risk_pct=0.10, max_notional_leverage=1.0)
        # Risk = $10. Stop dist = $0.5. Qty = 20 shares. Notional = 20 * $10 = $200.
        # Guardrail should cap notional at $100 (1x leverage), so qty = 10.
        res = sizer.calculate_size(account_equity=100.0, entry_price=10.0, atr=0.25, stop_loss_atr_multiplier=2.0, confidence_score=100.0)

        self.assertEqual(res["quantity"], 10.0)
        self.assertEqual(res["notional_value"], 100.0)

    def test_circuit_breaker(self):
        cb = CircuitBreaker(max_drawdown_pct=0.15, max_daily_loss_pct=0.05)

        # Safe
        res = cb.check_safety(peak_equity=100.0, current_equity=98.0, daily_starting_equity=100.0)
        self.assertTrue(res["safe"])

        # Max Drawdown breach
        res = cb.check_safety(peak_equity=100.0, current_equity=84.0, daily_starting_equity=100.0)
        self.assertFalse(res["safe"])
        self.assertEqual(res["action"], "HALT_ALL_TRADING")

        # Daily loss breach
        res = cb.check_safety(peak_equity=150.0, current_equity=140.0, daily_starting_equity=150.0)
        self.assertFalse(res["safe"])
        self.assertEqual(res["action"], "HALT_DAILY_TRADING")

if __name__ == '__main__':
    unittest.main()
