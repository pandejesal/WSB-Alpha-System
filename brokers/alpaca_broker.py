from typing import Dict, Any, List
from brokers.base_broker import Broker
from configuration.config import config

class AlpacaBroker(Broker):
    def __init__(self, is_paper: bool = True):
        self.is_paper = is_paper
        # Initialize Alpaca client here using config.api_keys.alpaca_api_key/secret
        pass

    def get_account_balance(self) -> float:
        return 0.0

    def submit_order(self, ticker: str, side: str, quantity: float, order_type: str = 'market', **kwargs) -> Dict[str, Any]:
        return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        return []
