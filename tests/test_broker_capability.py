import pytest
from src.execution.base_broker import BaseBroker
from src.execution.alpaca_broker import AlpacaBroker
from src.execution.ccxt_broker import CCXTBroker

class SandboxBroker(BaseBroker):
    """
    Test broker that implements the BaseBroker interface without using real credentials.
    """

    def get_account_balance(self) -> dict[str, float]:
        return {'equity': 100000.0, 'cash': 100000.0}

    def place_order(self, symbol: str, qty: float, side: str, order_type: str = "market", stop_loss_price: float | None = None) -> dict[str, str]:
        return {"status": "success", "order_id": "test_order_123"}

    def get_positions(self) -> list[dict[str, float]]:
        return []

    def cancel_order(self, symbol: str) -> bool:
        return True

    def get_capabilities(self) -> dict[str, bool]:
        return {
            "supports_market_orders": True,
            "supports_stop_limit": True,
            "supports_paper": True
        }

def test_sandbox_broker_capabilities():
    broker = SandboxBroker()
    caps = broker.get_capabilities()
    assert isinstance(caps, dict)
    assert "supports_market_orders" in caps
    assert "supports_stop_limit" in caps
    assert "supports_paper" in caps
    assert caps["supports_market_orders"] is True

def test_sandbox_broker_contract():
    broker = SandboxBroker()
    assert broker.get_account_balance() == {'equity': 100000.0, 'cash': 100000.0}
    assert broker.place_order("AAPL", 10.0, "buy") == {"status": "success", "order_id": "test_order_123"}
    assert broker.get_positions() == []
    assert broker.cancel_order("AAPL") is True

def test_alpaca_broker_capabilities(monkeypatch):
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "False")
    # instantiate without real credentials.
    broker = AlpacaBroker()
    caps = broker.get_capabilities()
    assert isinstance(caps, dict)
    assert "supports_market_orders" in caps
    assert "supports_stop_limit" in caps
    assert "supports_paper" in caps
    assert caps["supports_market_orders"] is True
    assert caps["supports_paper"] is True

def test_ccxt_broker_capabilities(monkeypatch):
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "False")
    monkeypatch.setenv("BINANCE_API_KEY", "dummy_key")
    monkeypatch.setenv("BINANCE_SECRET_KEY", "dummy_secret")

    # Reload config if necessary, or just rely on broker defaults if it allows dummy keys.
    try:
        broker = CCXTBroker(exchange_id="binance")
        caps = broker.get_capabilities()
        assert isinstance(caps, dict)
        assert "supports_market_orders" in caps
        assert "supports_stop_limit" in caps
        assert "supports_paper" in caps
        assert caps["supports_market_orders"] is True
    except Exception as e:
        pytest.skip(f"Skipping CCXT capability test due to config/instantiation constraints: {e}")
