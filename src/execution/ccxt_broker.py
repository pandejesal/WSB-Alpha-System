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

        # In a real setup, keys would come from config.
        # Using dummy keys for demonstration as per instructions to mock crypto integration.
        self.api_key = "dummy_api_key"
        self.secret_key = "dummy_secret_key"

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
            self.logger.warning("ccxt not installed. CCXTBroker will run in mock mode.")
        except Exception as e:
            self.logger.error(f"Failed to initialize CCXT client: {e}")

    def get_account_balance(self) -> dict:
        if not self.exchange:
            return {'equity': config.trading.initial_capital, 'cash': config.trading.initial_capital}

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
            return []

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

    def place_order(self, symbol: str, qty: float | None, side: str, order_type: str = 'market', stop_loss_price: float | None = None) -> dict:
        if not self.exchange:
            raise ConnectionError("CCXT exchange not initialized.")

        # Standardize symbol (e.g., BTC/USDT)
        ccxt_side = side.lower()

        params = {}
        if stop_loss_price is not None:
            params['stopPrice'] = stop_loss_price

        order = self.exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=ccxt_side,
            amount=qty,
            params=params
        )
        return {"status": "success", "order_id": str(order['id']), "status_details": order['status']}

    def cancel_order(self, symbol: str) -> bool:
        if not self.exchange:
            return True
        try:
            self.exchange.cancel_all_orders(symbol)
            return True
        except Exception:
            return False
