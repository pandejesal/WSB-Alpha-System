import time
from functools import wraps

def retry(max_retries=3, backoff=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise e
                    time.sleep(backoff * (2 ** (retries - 1)))
            return func(*args, **kwargs)
        return wrapper
    return decorator

import logging
from typing import Dict, Any, List, Optional
from src.execution.base_broker import BaseBroker
from src.utils.config import config

logger = logging.getLogger(__name__)

class AlpacaBroker(BaseBroker):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_paper = not config.trading.live_trading_enabled

        # Load keys
        self.api_key = config.api_keys.alpaca_api_key
        # config.api_keys is our wrapper Stub
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
        except Exception as e:
            self.logger.error(f"Failed to initialize Alpaca TradingClient: {e}")

    @retry(max_retries=3, backoff=1)
    def get_account_balance(self) -> dict:
        if not self.client:
            return {'equity': config.trading.initial_capital, 'cash': config.trading.initial_capital}

        try:
            acct = self.client.get_account()
            return {
                'equity': float(acct.equity),
                'cash': float(acct.cash)
            }
        except Exception as e:
            self.logger.error(f"Alpaca get_account failed: {e}")
            raise

    @retry(max_retries=3, backoff=1)
    def get_positions(self) -> List[Dict]:
        if not self.client:
            return []

        try:
            positions = self.client.get_all_positions()
            return [
                {
                    'symbol': p.symbol,
                    'qty': float(p.qty),
                    'market_value': float(p.market_value),
                    'unrealized_pl': float(p.unrealized_pl)
                } for p in positions
            ]
        except Exception as e:
            self.logger.error(f"Alpaca get_positions failed: {e}")
            raise

    @retry(max_retries=3, backoff=1)
    def place_order(self, symbol: str, qty: Optional[float], side: str, order_type: str = 'market', notional: Optional[float] = None) -> dict:


        try:
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            alpaca_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL

            # CRITICAL BUG FIX: Alpaca does NOT support notional short-selling
            # We must convert to integer shares if side is 'sell' and notional is provided
            if side.lower() == 'sell' and notional is not None and qty is None:
                # Need current price to calculate shares
                # A robust way is to fetch latest quote. We'll use a mocked latest price or fetch via Alpaca data client.
                # For simplicity here, if notional is used for shorting, we estimate using account api or fail.
                # Assuming we have access to current price or we require qty for sells.
                # Actually, the instructions: "calculate whole-share integer quantities (qty = int(notional / current_price))"
                # Since we don't have current_price directly passed in the interface, let's fetch it.
                current_price = self._get_latest_price(symbol)
                qty = int(notional / current_price) if current_price > 0 else 0
                notional = None # Clear notional since we converted to qty

                if qty == 0:
                    raise ValueError(f"Calculated integer qty is 0 for short-sell of {symbol} with notional {notional}")


            if not self.client:
                raise ConnectionError("Alpaca TradingClient not initialized. Check API keys.")

            if notional is not None:
                req = MarketOrderRequest(
                    symbol=symbol,
                    notional=notional,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY
                )
            elif qty is not None:
                req = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=alpaca_side,
                    time_in_force=TimeInForce.DAY
                )
            else:
                raise ValueError("Must provide either qty or notional")

            order = self.client.submit_order(req)
            return {"status": "success", "order_id": str(order.id), "status_details": order.status}

        except Exception as e:
            self.logger.error(f"Alpaca place_order failed: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        if not self.client: return True
        try:
            self.client.cancel_order_by_id(order_id)
            return True
        except Exception:
            return False

    @retry(max_retries=3, backoff=1)
    def _get_latest_price(self, symbol: str) -> float:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestTradeRequest
        try:
            client = StockHistoricalDataClient(self.api_key, self.secret_key)
            req = StockLatestTradeRequest(symbol_or_symbols=symbol)
            res = client.get_stock_latest_trade(req)
            return float(res[symbol].price)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch latest price for {symbol}: {e}")
