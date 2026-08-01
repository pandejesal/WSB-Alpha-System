from typing import Dict, Any, List
from src.execution.base_broker import Broker
from src.utils.config import config
import logging

class AlpacaBroker(Broker):
    def __init__(self, is_paper: bool = True):
        self.logger = logging.getLogger(__name__)
        self.is_paper = not config.trading.live_trading_enabled

    def get_account_balance(self) -> float:
        return config.trading.initial_capital

    def submit_order(self, ticker: str, side: str, quantity: float, order_type: str = 'market', **kwargs) -> Dict[str, Any]:
        if quantity <= 0: return {"status": "error"}
        return {"status": "success"}

    def get_positions(self) -> List[Dict[str, Any]]:
        return []
