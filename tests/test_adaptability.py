import unittest
from src.risk.position_sizer import RegimeDetector

class TestAdaptability(unittest.TestCase):
    def test_regime_detection(self):
        self.assertEqual(RegimeDetector.detect_regime(0.15), "low_volatility")
        self.assertEqual(RegimeDetector.detect_regime(0.35), "normal")
        self.assertEqual(RegimeDetector.detect_regime(0.65), "high_volatility")

    def test_position_sizer_regime_scale(self):
        self.assertEqual(RegimeDetector.get_risk_multiplier("low_volatility"), 1.5)
        self.assertEqual(RegimeDetector.get_risk_multiplier("normal"), 1.0)
        self.assertEqual(RegimeDetector.get_risk_multiplier("high_volatility"), 0.5)

    def test_circuit_breaker_regime_scale(self):
        from src.risk.circuit_breakers import CircuitBreaker
        cb_low = CircuitBreaker(regime="low_volatility")
        self.assertAlmostEqual(cb_low.daily_limit, 0.05 * 1.2)

        cb_high = CircuitBreaker(regime="high_volatility")
        self.assertAlmostEqual(cb_high.daily_limit, 0.05 * 0.6)

if __name__ == '__main__':
    unittest.main()
