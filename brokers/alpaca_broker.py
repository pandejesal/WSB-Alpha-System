from typing import Dict, Any, List
from brokers.base_broker import Broker
from configuration.config import config
import logging

class AlpacaBroker(Broker):
    def __init__(self, is_paper: bool = True):
        self.logger = logging.getLogger(__name__)
        if config.trading.live_trading_enabled:
            self.logger.critical("INITIALIZING LIVE TRADING CLIENT ON ALPACA! REAL FUNDS AT RISK!")
            self.is_paper = False
        else:
            self.is_paper = True
            self.logger.info("Initializing Paper Trading client on Alpaca. (Live trading is explicitly disabled)")

        self.client = None

    def get_account_balance(self) -> float:
        return config.trading.initial_capital

    def submit_order(self, ticker: str, side: str, quantity: float, order_type: str = 'market', **kwargs) -> Dict[str, Any]:
        if quantity <= 0:
            return {"status": "error", "message": "Quantity must be > 0"}
        return {"status": "success", "order_id": "mock_id", "filled_qty": quantity}

    def get_positions(self) -> List[Dict[str, Any]]:
        return []
