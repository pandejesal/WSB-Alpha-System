import unittest
import os
import json
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.execution.alpaca_broker import AlpacaBroker
from src.risk.circuit_breakers import CircuitBreaker, TradingHaltedException
from src.monitoring.telegram_bot import TelegramBot

class TestPhase5(unittest.TestCase):

    def test_alpaca_short_sell_integer_qty(self):
        broker = AlpacaBroker()

        # Test short sell logic handles notional strictly via current price
        # The place_order uses self._get_latest_price(symbol), which returns dummy 100.0 if not fully authed
        # A notional of 250 with price 100 should yield int(250/100) = 2 shares

        res = broker.place_order(symbol="AAPL", qty=None, side="sell", notional=250.0)
        self.assertEqual(res["status"], "success")
        # filled_qty in our mock returns the calculated qty for tests when client is None
        self.assertEqual(res["filled_qty"], 2)

    def test_circuit_breaker_fails_closed(self):
        cb = CircuitBreaker(daily_limit=0.05, weekly_limit=0.10, total_limit=0.15)

        # Mock network error get_equity func
        def failing_equity_fetch():
            raise ConnectionError("Network unreachable")

        with self.assertRaises(TradingHaltedException):
            cb.check_circuit_breakers(failing_equity_fetch)

        # Mock invalid data fail closed
        def invalid_equity_fetch():
            return -50.0

        with self.assertRaises(TradingHaltedException):
            cb.check_circuit_breakers(invalid_equity_fetch)

        # Mock standard trip
        cb.initialize_state(1000.0)
        def dropping_equity():
            return 900.0 # 10% drop, trips daily (which is 5%)

        with self.assertRaises(TradingHaltedException) as context:
            cb.check_circuit_breakers(dropping_equity)
        self.assertIn("Daily Loss Limit", str(context.exception))

    def test_telegram_approval_workflow(self):
        bot = TelegramBot()
        test_file = "strategies/test_approved.json"
        bot.approved_file = test_file

        # Ensure clean state
        if os.path.exists(test_file):
            os.remove(test_file)

        self.assertFalse(bot.is_approved("STRAT_123"))

        bot.handle_command("/approve STRAT_123")
        self.assertTrue(bot.is_approved("STRAT_123"))

        bot.handle_command("/reject STRAT_123")
        self.assertFalse(bot.is_approved("STRAT_123"))

        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
