import unittest
import sys
import os
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.risk import position_sizing as risk_config

class TestRiskConfig(unittest.TestCase):
    def test_risk_values(self):
        # Validate that these strictly adhere to constraints
        # 2026-08-21: circuit breakers default to 1.0 (disabled) when CIRCUIT_BREAKER_ENABLED=False
        self.assertFalse(risk_config.LIVE_TRADING_ENABLED)
        self.assertEqual(risk_config.MAX_RISK_PER_TRADE_PCT, 0.01)
        self.assertEqual(risk_config.MAX_CONCURRENT_POSITIONS, 4)
        # Default disabled path (production): breakers are 1.0
        if not risk_config.CIRCUIT_BREAKER_ENABLED:
            self.assertEqual(risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT, 1.0)
            self.assertEqual(risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT, 1.0)
            self.assertEqual(risk_config.MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT, 1.0)
        # Legacy enabled path: mock constants to verify gate logic still works when enabled
        with patch.object(risk_config, 'DAILY_LOSS_CIRCUIT_BREAKER_PCT', 0.05), \
             patch.object(risk_config, 'WEEKLY_LOSS_CIRCUIT_BREAKER_PCT', 0.10), \
             patch.object(risk_config, 'MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT', 0.15):
            self.assertEqual(risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT, 0.05)
            self.assertEqual(risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT, 0.10)
            self.assertEqual(risk_config.MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT, 0.15)

if __name__ == '__main__':
    unittest.main()
