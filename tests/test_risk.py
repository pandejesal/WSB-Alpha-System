import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import risk_config

class TestRiskConfig(unittest.TestCase):
    def test_risk_values(self):
        # Validate that these strictly adhere to constraints
        self.assertFalse(risk_config.LIVE_TRADING_ENABLED)
        self.assertEqual(risk_config.RISK_PER_TRADE_PCT, 0.03)
        self.assertEqual(risk_config.MAX_POSITION_SIZE_PCT, 0.25)
        self.assertEqual(risk_config.MAX_CONCURRENT_POSITIONS, 4)
        self.assertEqual(risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT, 0.08)
        self.assertEqual(risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT, 0.15)

if __name__ == '__main__':
    unittest.main()
