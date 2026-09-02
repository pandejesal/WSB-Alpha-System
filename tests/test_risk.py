import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.risk import position_sizing as risk_config

class TestRiskConfig(unittest.TestCase):
    def test_risk_values(self):
        # Validate that these strictly adhere to constraints
        self.assertFalse(risk_config.LIVE_TRADING_ENABLED)
        self.assertEqual(risk_config.MAX_RISK_PER_TRADE_PCT, 0.01)
        self.assertEqual(risk_config.MAX_CONCURRENT_POSITIONS, 4)
        self.assertIn(risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT, [0.05, 1.0])
        self.assertIn(risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT, [0.10, 1.0])
        self.assertIn(risk_config.MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT, [0.15, 1.0])

if __name__ == '__main__':
    unittest.main()
