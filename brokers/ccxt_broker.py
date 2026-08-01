from typing import Dict, Any, List
from brokers.base_broker import Broker
from configuration.config import config
import ccxt
import logging

class CCXTBroker(Broker):
    """
    Concrete implementation of the Broker abstraction for Crypto via CCXT (e.g. Binance/Bybit).
    """
    def __init__(self, exchange_id: str = 'binance', is_paper: bool = True):
        self.logger = logging.getLogger(__name__)
        self.exchange_id = exchange_id

        # Ensure we ALWAYS enforce paper trading unless explicit global live trading is enabled.
        if config.trading.live_trading_enabled:
            self.logger.critical(f"INITIALIZING LIVE TRADING CLIENT ON CCXT ({exchange_id})! REAL FUNDS AT RISK!")
            self.is_paper = False
        else:
            self.is_paper = True
            self.logger.info(f"Initializing Paper Trading client on CCXT ({exchange_id}). (Live trading is explicitly disabled)")

        api_key = config.api_keys.binance_api_key
        secret_key = config.api_keys.binance_secret_key.get_secret_value()

        if not api_key or not secret_key:
            self.logger.warning(f"CCXT {exchange_id} keys missing. Broker will run in mock mode.")
            self.client = None
        else:
            try:
                exchange_class = getattr(ccxt, exchange_id)
                self.client = exchange_class({
                    'apiKey': api_key,
                    'secret': secret_key,
                    'enableRateLimit': True,
                })
                if self.is_paper:
                    self.client.set_sandbox_mode(True)
                    self.logger.info(f"Initialized Paper Trading client for {exchange_id}.")
            except AttributeError:
                self.logger.error(f"Exchange {exchange_id} not supported by CCXT.")
                self.client = None

    def get_account_balance(self) -> float:
        if not self.client:
            return config.trading.initial_capital

        try:
            balance = self.client.fetch_balance()
            return float(balance.get('USDT', {}).get('total', 0.0))
        except Exception as e:
            self.logger.error(f"Failed to fetch account balance: {e}")
            return 0.0

    def submit_order(self, ticker: str, side: str, quantity: float, order_type: str = 'market', **kwargs) -> Dict[str, Any]:
        if quantity <= 0:
            return {"status": "error", "message": "Quantity must be > 0"}

        if not self.client:
            self.logger.info(f"Mock Crypto Order: {side} {quantity} of {ticker}")
            return {"status": "success", "order_id": "mock_crypto_id", "filled_qty": quantity}

        try:
            self.logger.info(f"Submitting {order_type} {side} order for {quantity} {ticker}...")
            order = self.client.create_order(symbol=ticker, type=order_type, side=side, amount=quantity)
            return {"status": "success", "order_id": str(order.get('id')), "status_details": str(order.get('status'))}

        except Exception as e:
            self.logger.error(f"Crypto Order submission failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_positions(self) -> List[Dict[str, Any]]:
        # CCXT position fetching is exchange specific, often requiring fetch_positions() or reading from balance
        if not self.client:
            return []
        try:
            if self.client.has['fetchPositions']:
                positions = self.client.fetch_positions()
                return [{"ticker": p['symbol'], "quantity": float(p['contracts']), "market_value": float(p['notional'])} for p in positions if p['contracts'] > 0]
            else:
                self.logger.warning("Exchange does not support fetchPositions via CCXT directly.")
                return []
        except Exception as e:
            self.logger.error(f"Failed to fetch crypto positions: {e}")
            return []
