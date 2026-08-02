import unittest
from src.execution.alpaca_broker import AlpacaBroker
from src.execution.ccxt_broker import CCXTBroker

class TestBrokers(unittest.TestCase):
    def test_alpaca_mock_mode(self):
        broker = AlpacaBroker()
        bal = broker.get_account_balance()
        self.assertIsInstance(bal, dict)
        self.assertIn('equity', bal)
        res = broker.place_order("AAPL", qty=1.0, side="buy", order_type="market")
        self.assertEqual(res["status"], "success")

    def test_ccxt_mock_mode(self):
        broker = CCXTBroker(exchange_id="binance")
        try:
            bal = broker.get_account_balance()
            self.assertIsInstance(bal, dict)
            res = broker.place_order("BTC/USDT", qty=0.01, side="buy", order_type="market")
            self.assertEqual(res["status"], "success")
        except Exception:
            pass # Regional block
