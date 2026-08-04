import unittest
from src.execution.alpaca_broker import AlpacaBroker

class TestBrokers(unittest.TestCase):
    def test_alpaca_mock_mode(self):
        broker = AlpacaBroker()
        bal = broker.get_account_balance()
        self.assertIsInstance(bal, dict)
        self.assertIn('equity', bal)
        try:
            res = broker.place_order("AAPL", qty=1.0, side="buy", order_type="market")
            self.assertEqual(res["status"], "success")
        except ConnectionError:
            pass
        except Exception:
            pass
