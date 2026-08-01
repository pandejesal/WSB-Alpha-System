import unittest
from src.execution.alpaca_broker import AlpacaBroker
from src.execution.ccxt_broker import CCXTBroker

class TestBrokers(unittest.TestCase):
    def test_alpaca_mock_mode(self):
        broker = AlpacaBroker()
        bal = broker.get_account_balance()
        self.assertGreater(bal, 0)
        res = broker.submit_order("AAPL", "buy", 1.0)
        self.assertEqual(res["status"], "success")

    def test_ccxt_mock_mode(self):
        broker = CCXTBroker(exchange_id="binance")
        bal = broker.get_account_balance()
        self.assertGreater(bal, 0)
        res = broker.submit_order("BTC/USDT", "buy", 0.01)
        self.assertEqual(res["status"], "success")
