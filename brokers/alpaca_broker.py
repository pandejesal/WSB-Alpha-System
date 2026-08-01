from typing import Dict, Any, List
from brokers.base_broker import Broker
from configuration.config import config
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import logging

class AlpacaBroker(Broker):
    """
    Concrete implementation of the Broker abstraction for Alpaca.
    Defaults to paper trading as enforced by the global configuration.
    """
    def __init__(self, is_paper: bool = True):
        self.logger = logging.getLogger(__name__)
        # Ensure we ALWAYS enforce paper trading unless explicit global live trading is enabled.
        if config.trading.live_trading_enabled:
            self.logger.critical("INITIALIZING LIVE TRADING CLIENT ON ALPACA! REAL FUNDS AT RISK!")
            self.is_paper = False
        else:
            self.is_paper = True
            self.logger.info("Initializing Paper Trading client on Alpaca. (Live trading is explicitly disabled)")

        api_key = config.api_keys.alpaca_api_key
        secret_key = config.api_keys.alpaca_secret_key.get_secret_value()

        if not api_key or not secret_key:
            self.logger.warning("Alpaca keys missing. Trading client will run in mock mode.")
            self.client = None
        else:
            self.client = TradingClient(api_key, secret_key, paper=self.is_paper)

    def get_account_balance(self) -> float:
        if not self.client:
            self.logger.warning("Mock mode: returning default balance $100.")
            return config.trading.initial_capital

        try:
            account = self.client.get_account()
            return float(account.equity)
        except Exception as e:
            self.logger.error(f"Failed to fetch account balance: {e}")
            return 0.0

    def submit_order(self, ticker: str, side: str, quantity: float, order_type: str = 'market', **kwargs) -> Dict[str, Any]:
        """Submit a fractional market order to Alpaca."""
        if quantity <= 0:
            return {"status": "error", "message": "Quantity must be > 0"}

        if not self.client:
            self.logger.info(f"Mock Order: {side} {quantity} of {ticker}")
            return {"status": "success", "order_id": "mock_id", "filled_qty": quantity}

        try:
            alpaca_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            market_order_data = MarketOrderRequest(
                symbol=ticker,
                qty=quantity,
                side=alpaca_side,
                time_in_force=TimeInForce.DAY
            )

            self.logger.info(f"Submitting {side} order for {quantity} {ticker}...")
            order = self.client.submit_order(order_data=market_order_data)
            return {"status": "success", "order_id": str(order.id), "status_details": str(order.status)}

        except Exception as e:
            self.logger.error(f"Order submission failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            positions = self.client.get_all_positions()
            return [{"ticker": p.symbol, "quantity": float(p.qty), "market_value": float(p.market_value)} for p in positions]
        except Exception as e:
            self.logger.error(f"Failed to fetch positions: {e}")
            return []
