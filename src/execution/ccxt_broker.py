import ccxt
import logging
from typing import Dict, List, Optional
from src.execution.base_broker import BaseBroker

logger = logging.getLogger(__name__)

class CCXTBroker(BaseBroker):
    def __init__(self, exchange_id: str, api_key: str = None, secret: str = None, enable_rate_limit: bool = True):
        self.logger = logging.getLogger(__name__)
        exchange_class = getattr(ccxt, exchange_id)

        config = {
            'enableRateLimit': enable_rate_limit,
            'options': {
                'defaultType': 'swap' # Support perpetual futures
            }
        }

        if api_key and secret:
            config['apiKey'] = api_key
            config['secret'] = secret

        self.exchange = exchange_class(config)

    def get_account_balance(self) -> dict:
        try:
            balance = self.exchange.fetch_balance()
            # Simplification: returning total USDT balance
            total = balance.get('USDT', {}).get('total', 0.0)
            free = balance.get('USDT', {}).get('free', 0.0)
            return {'equity': total, 'cash': free}
        except Exception as e:
            self.logger.error(f"CCXT fetch_balance failed: {e}")
            raise

    def get_positions(self) -> List[Dict]:
        try:
            positions = self.exchange.fetch_positions()
            return [
                {
                    'symbol': p['symbol'],
                    'qty': p['contracts'],
                    'market_value': p['notional'],
                    'unrealized_pl': p['unrealizedPnl']
                } for p in positions if float(p.get('contracts', 0)) > 0
            ]
        except Exception as e:
            self.logger.error(f"CCXT fetch_positions failed: {e}")
            raise

    def place_order(self, symbol: str, qty: Optional[float], side: str, order_type: str = 'market', notional: Optional[float] = None) -> dict:
        try:
            if qty is None and notional is not None:
                # CCXT usually requires base currency quantity. We must convert.
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                qty = notional / current_price

            if qty is None or qty <= 0:
                raise ValueError("Invalid quantity")

            order = self.exchange.create_order(symbol, type=order_type.lower(), side=side.lower(), amount=qty)
            return {"status": "success", "order_id": order['id'], "filled_qty": order.get('filled', 0)}

        except Exception as e:
            self.logger.error(f"CCXT create_order failed: {e}")
            raise

    def cancel_order(self, order_id: str, symbol: str = None) -> bool:
        try:
            self.exchange.cancel_order(order_id, symbol)
            return True
        except Exception:
            return False

    def sync_orders(self, open_order_ids: List[str], symbol: str = None) -> List[Dict]:
        """Implement order synchronization to detect partial fills, cancellations."""
        updates = []
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            active_ids = [o['id'] for o in orders]

            for oid in open_order_ids:
                if oid not in active_ids:
                    # Order is either filled, partially filled and canceled, or fully canceled
                    # Need to fetch the specific order to check status
                    try:
                        order = self.exchange.fetch_order(oid, symbol)
                        updates.append(order)
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch order {oid} during sync: {e}")
        except Exception as e:
            self.logger.error(f"CCXT sync_orders failed: {e}")
            raise
        return updates
