import logging

from src.execution.base_broker import BaseBroker
from src.utils.config import config

logger = logging.getLogger(__name__)

class CCXTBroker(BaseBroker):
    """
    Concrete implementation of BaseBroker using CCXT for Crypto execution.
    """

    def __init__(self, exchange_id: str = "binance"):
        self.logger = logging.getLogger(__name__)
        self.is_paper = not config.trading.live_trading_enabled
        self.exchange_id = exchange_id

        self.api_key = config.api_keys.binance_api_key
        try:
            self.secret_key = config.api_keys.binance_secret_key.get_secret_value()
        except AttributeError:
            self.secret_key = config.api_keys.binance_secret_key

        if not self.api_key or not self.secret_key:
            raise ValueError("CCXTBroker requires valid exchange API credentials (e.g., BINANCE_API_KEY).")

        self.exchange = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            import ccxt
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot' # or 'future'
                }
            })
            if self.is_paper:
                self.exchange.set_sandbox_mode(True)
        except ImportError:
            raise ImportError("ccxt not installed. CCXTBroker requires ccxt to function.")
        except Exception as e:
            self.logger.error(f"Failed to initialize CCXT client: {e}")
            raise

    def get_account_balance(self) -> dict:
        if not self.exchange:
            raise ConnectionError("CCXT exchange not initialized.")

        balance = self.exchange.fetch_balance()
        # For simplicity, assuming USD/USDT is the base currency
        total_equity = balance.get('total', {}).get('USDT', config.trading.initial_capital)
        free_cash = balance.get('free', {}).get('USDT', config.trading.initial_capital)

        return {
            'equity': float(total_equity),
            'cash': float(free_cash)
        }

    def get_positions(self) -> list[dict]:
        if not self.exchange:
            raise ConnectionError("CCXT exchange not initialized.")

        # CCXT positions API depends heavily on the exchange (spot vs futures).
        # For spot, it's just checking balances of non-USDT tokens.
        balance = self.exchange.fetch_balance()
        positions = []
        for asset, data in balance['total'].items():
            if asset != 'USDT' and data > 0:
                positions.append({
                    'symbol': f"{asset}/USDT",
                    'qty': float(data),
                    'market_value': 0.0, # Would require fetching ticker
                    'unrealized_pl': 0.0
                })
        return positions

    def place_order(self, symbol: str, qty: float | None, side: str, order_type: str = 'market', stop_loss_price: float | None = None, reduce_only: bool = False) -> dict:
        if not self.exchange:
            raise ConnectionError("CCXT exchange not initialized.")

        import ccxt
        ccxt_side = side.lower()

        params = {}
        if stop_loss_price is not None:
            params['stopPrice'] = stop_loss_price
        if reduce_only:
            params['reduceOnly'] = True

        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=ccxt_side,
                amount=qty,
                params=params
            )
            return {"status": "success", "order_id": str(order['id']), "status_details": order['status']}
        except (ccxt.InsufficientFunds, ccxt.InvalidOrder, ccxt.NetworkError, ccxt.ExchangeError) as e:
            logger.error(f"CCXT Order Placement failed for {symbol}: {e}")
            return {"status": "failed", "error_message": str(e)}

    def cancel_order(self, symbol: str) -> bool:
        if not self.exchange:
            return True
        try:
            self.exchange.cancel_all_orders(symbol)
            return True
        except Exception:  # noqa: BLE001 - Catching Exception to fail gracefully
            return False

    def get_capabilities(self) -> dict[str, bool]:
        return {
            'supports_market_orders': True,
            'supports_stop_limit': True,
            'supports_paper': self.is_paper,
            'supports_crypto': True,
            'supports_fractional': True
        }
