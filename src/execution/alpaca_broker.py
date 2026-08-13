import logging

from src.execution.base_broker import BaseBroker
from src.utils.config import config

logger = logging.getLogger(__name__)

class AlpacaBroker(BaseBroker):
    """
    Concrete implementation of BaseBroker using Alpaca API.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_paper = not config.trading.live_trading_enabled
        self.api_key = config.api_keys.alpaca_api_key
        try:
            self.secret_key = config.api_keys.alpaca_secret_key.get_secret_value()
        except AttributeError:
            self.secret_key = config.api_keys.alpaca_secret_key
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            from alpaca.trading.client import TradingClient
            if self.api_key and self.secret_key:
                self.client = TradingClient(self.api_key, self.secret_key, paper=self.is_paper)
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            self.logger.error(f"Failed to initialize Alpaca TradingClient: {e}")

    def get_account_balance(self) -> dict:
        if not self.client:
            return {'equity': config.trading.initial_capital, 'cash': config.trading.initial_capital}

        acct = self.client.get_account()
        return {
            'equity': float(acct.equity),
            'cash': float(acct.cash)
        }

    def get_positions(self) -> list[dict]:
        if not self.client:
            return []

        positions = self.client.get_all_positions()
        return [
            {
                'symbol': p.symbol,
                'qty': float(p.qty),
                'market_value': float(p.market_value),
                'unrealized_pl': float(p.unrealized_pl)
            } for p in positions
        ]

    def place_order(self, symbol: str, qty: float | None, side: str, order_type: str = 'market', stop_loss_price: float | None = None) -> dict:
        if not self.client:
            raise ConnectionError("Alpaca TradingClient not initialized. Check API keys.")

        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest, StopLossRequest

        alpaca_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL

        # Fractional short selling is disallowed, force integer conversion
        if side.lower() == 'sell' and qty is not None:
            qty = int(qty)
            if qty == 0:
                raise ValueError("Quantity truncated to 0 during short-sell integer casting.")

        req_kwargs = {
            "symbol": symbol,
            "qty": qty,
            "side": alpaca_side,
            "time_in_force": TimeInForce.DAY
        }

        if stop_loss_price is not None:
            req_kwargs["stop_loss"] = StopLossRequest(stop_price=stop_loss_price)

        req = MarketOrderRequest(**req_kwargs)
        order = self.client.submit_order(req)
        return {"status": "success", "order_id": str(order.id), "status_details": order.status}

    def cancel_order(self, symbol: str) -> bool:
        """Cancels all open orders for a specific symbol."""
        if not self.client:
            return True
        try:
            self.client.cancel_orders(symbol_or_symbols=symbol)
            return True
        except Exception:  # noqa: BLE001 - Catching Exception to fail gracefully
            return False

    def get_capabilities(self) -> dict[str, bool]:
        return {
            'supports_market_orders': True,
            'supports_stop_limit': True,
            'supports_paper': True,
            'supports_crypto': True,
            'supports_fractional': True
        }
