from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Broker(ABC):
    @abstractmethod
    def get_account_balance(self) -> float:
        """Get the current account balance."""
        pass

    @abstractmethod
    def submit_order(self, ticker: str, side: str, quantity: float, order_type: str = 'market', **kwargs) -> Dict[str, Any]:
        """Submit a new order."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get currently open positions."""
        pass
