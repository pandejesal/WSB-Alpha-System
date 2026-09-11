import unittest

from src.risk.circuit_breakers import CircuitBreaker
from src.risk.position_sizer import PositionSizer, TradeStats


class TestRiskEngine(unittest.TestCase):
    def test_position_sizer(self):
        # Contract migration note (2026-09-11): Kelly-primary PositionSizer
        # uses size_position() -> PositionResult and max_notional_lev (not
        # calculate_size()/max_notional_leverage). ATR fallback sizes from
        # account_value * base_risk_pct / price as integer shares.
        sizer = PositionSizer(base_risk_pct=0.02, max_notional_lev=1.0)
        res = sizer.size_position(None, price=50.0, account_value=100.0)
        self.assertEqual(res.method, "atr_fallback")
        self.assertEqual(res.size, 0)

    def test_position_sizer_leverage_cap(self):
        # Half-Kelly output is capped at max_notional_lev: raw Kelly 0.89
        # would give 0.445 after half-Kelly, capped here to 0.01.
        sizer = PositionSizer(base_risk_pct=0.10, max_notional_lev=0.01)
        stats = TradeStats(wins=90, losses=10, avg_win=100.0, avg_loss=10.0)
        res = sizer.size_position(
            stats, price=10.0, regime="strong_bull",
            macro_regime="expansion", total_trades=100, account_value=100.0,
        )
        self.assertEqual(res.method, "kelly")
        self.assertEqual(res.kelly_fraction_used, 0.01)
        self.assertEqual(res.size, 100)

    def test_circuit_breaker(self):
        cb = CircuitBreaker(daily_limit=0.05, total_limit=0.15)
        self.assertTrue(cb.check_circuit_breakers(lambda: 98.0))

        with self.assertRaises(Exception):
            cb.check_circuit_breakers(lambda: 84.0)
