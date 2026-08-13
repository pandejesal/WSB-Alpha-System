from unittest.mock import patch
import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.execution.base_broker import BaseBroker
from src.execution.alpaca_broker import AlpacaBroker
from src.execution.ccxt_broker import CCXTBroker


class SandboxBroker(BaseBroker):
    """
    Mock broker for testing the broker capabilities gate without real credentials.
    """
    def __init__(self):
        self._balance = {'equity': 100000.0, 'cash': 100000.0}
        self._positions = []
        self._orders = []

    def get_account_balance(self) -> dict:
        return self._balance

    def get_positions(self) -> list[dict]:
        return self._positions

    def place_order(self, symbol: str, qty: float, side: str, order_type: str = "market", stop_loss_price: float | None = None) -> dict:
        if qty <= 0:
            raise ValueError("Quantity must be positive.")
        if side.lower() not in ('buy', 'sell'):
            raise ValueError("Side must be 'buy' or 'sell'.")

        order = {
            "status": "success",
            "order_id": f"mock_{len(self._orders)}",
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "status_details": "filled"
        }
        self._orders.append(order)

        # Simple mock position logic
        if side.lower() == 'buy':
            self._positions.append({
                'symbol': symbol,
                'qty': qty,
                'market_value': qty * 100,  # mock value
                'unrealized_pl': 0.0
            })

        return order

    def cancel_order(self, symbol: str) -> bool:
        self._orders = [o for o in self._orders if o['symbol'] != symbol]
        return True

    def get_capabilities(self) -> dict[str, bool]:
        return {
            'supports_market_orders': True,
            'supports_stop_limit': False,
            'supports_paper': True,
            'supports_crypto': False,
            'supports_fractional': False
        }


class TestBrokerCapabilityGate(unittest.TestCase):

    def test_sandbox_broker_capabilities(self):
        broker = SandboxBroker()
        caps = broker.get_capabilities()
        self.assertIn('supports_market_orders', caps)
        self.assertIn('supports_stop_limit', caps)
        self.assertIn('supports_paper', caps)
        self.assertTrue(caps['supports_market_orders'])
        self.assertTrue(caps['supports_paper'])
        self.assertFalse(caps['supports_stop_limit'])

    def test_sandbox_broker_conformance(self):
        broker = SandboxBroker()

        # Balance
        bal = broker.get_account_balance()
        self.assertIn('equity', bal)
        self.assertIn('cash', bal)

        # Order placement
        res = broker.place_order("AAPL", 10.0, "buy")
        self.assertEqual(res['status'], "success")

        # Positions
        pos = broker.get_positions()
        self.assertEqual(len(pos), 1)
        self.assertEqual(pos[0]['symbol'], "AAPL")

        # Cancel
        canceled = broker.cancel_order("AAPL")
        self.assertTrue(canceled)

    @patch('src.execution.alpaca_broker.config')
    def test_alpaca_broker_capabilities(self, mock_config):
        mock_config.trading.live_trading_enabled = False
        mock_config.api_keys.alpaca_api_key = "dummy"
        mock_config.api_keys.alpaca_secret_key = "dummy"
        broker = AlpacaBroker()
        caps = broker.get_capabilities()
        self.assertIn('supports_market_orders', caps)
        self.assertTrue(caps['supports_market_orders'])

if __name__ == '__main__':
    unittest.main()
