import unittest
from typing import Any

from src.execution.alpaca_broker import AlpacaBroker
from src.execution.base_broker import BaseBroker
from src.execution.ccxt_broker import CCXTBroker

REQUIRED_CAPABILITY_KEYS = ('supports_market_orders', 'supports_stop_limit', 'supports_paper')


class FakeExchange:
    """Minimal stand-in for a CCXT exchange exposing a `has` capability map."""

    def __init__(self, has: dict[str, bool] | None = None):
        self.has = has or {}


def make_ccxt_broker(has: dict[str, bool] | None = None) -> CCXTBroker:
    """Build a CCXTBroker without credentials by bypassing __init__ (which requires API keys)."""
    broker = object.__new__(CCXTBroker)
    broker.exchange = FakeExchange(has)
    return broker


class SandboxBroker(BaseBroker):
    """In-memory broker used to validate the BaseBroker contract without credentials."""

    def __init__(self, capabilities: dict[str, bool] | None = None):
        self._capabilities = capabilities or {
            'supports_market_orders': True,
            'supports_stop_limit': False,
            'supports_paper': True,
        }

    def get_account_balance(self) -> dict[str, Any]:
        return {'equity': 100000.0, 'cash': 100000.0}

    def place_order(self, symbol: str, qty: float | None, side: str, order_type: str = 'market',
                    stop_loss_price: float | None = None) -> dict[str, Any]:
        if order_type == 'stop_limit' and not self._capabilities['supports_stop_limit']:
            raise NotImplementedError("Broker does not support stop-limit orders.")
        return {"status": "success", "order_id": "sandbox-0001", "status_details": "submitted"}

    def get_positions(self) -> list[dict[str, Any]]:
        return []

    def cancel_order(self, symbol: str) -> bool:
        return True

    def get_capabilities(self) -> dict[str, bool]:
        return dict(self._capabilities)


class TestBrokerCapabilities(unittest.TestCase):
    def test_capability_contract_keys(self):
        ccxt_broker = make_ccxt_broker({'market': True, 'stopLimit': False, 'sandbox': True})
        for broker in (AlpacaBroker(), ccxt_broker, SandboxBroker()):
            caps = broker.get_capabilities()
            self.assertIsInstance(caps, dict)
            for key in REQUIRED_CAPABILITY_KEYS:
                self.assertIn(key, caps, f"{broker.__class__.__name__} missing {key}")
                self.assertIsInstance(caps[key], bool, f"{broker.__class__.__name__}.{key} not bool")

    def test_alpaca_supports_full_capabilities(self):
        caps = AlpacaBroker().get_capabilities()
        self.assertTrue(caps['supports_market_orders'])
        self.assertTrue(caps['supports_stop_limit'])
        self.assertTrue(caps['supports_paper'])

    def test_ccxt_returns_bool_capabilities(self):
        caps = make_ccxt_broker({'market': True, 'stopLimit': False, 'sandbox': True}).get_capabilities()
        self.assertIn('supports_market_orders', caps)
        self.assertIsInstance(caps['supports_market_orders'], bool)
        self.assertTrue(caps['supports_market_orders'])
        self.assertFalse(caps['supports_stop_limit'])

    def test_ccxt_defaults_market_to_true(self):
        caps = make_ccxt_broker().get_capabilities()
        self.assertTrue(caps['supports_market_orders'])
        self.assertFalse(caps['supports_stop_limit'])

    def test_sandbox_blocks_unsupported_order_type(self):
        broker = SandboxBroker()
        caps = broker.get_capabilities()
        if not caps['supports_stop_limit']:
            with self.assertRaises(NotImplementedError):
                broker.place_order("AAPL", qty=1.0, side="buy", order_type="stop_limit")

    def test_capabilities_are_mutable_per_instance(self):
        limited = SandboxBroker(capabilities={
            'supports_market_orders': False,
            'supports_stop_limit': False,
            'supports_paper': True,
        })
        self.assertFalse(limited.get_capabilities()['supports_market_orders'])
        full = SandboxBroker()
        self.assertTrue(full.get_capabilities()['supports_market_orders'])


if __name__ == "__main__":
    unittest.main()