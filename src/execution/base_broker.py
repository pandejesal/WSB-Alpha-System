from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseBroker(ABC):
    @abstractmethod
    def get_account_balance(self) -> dict:
        """Returns account balance dict: {'equity': float, 'cash': float}"""
        pass

    @abstractmethod
    def get_open_positions(self) -> List[Dict]:
        """Returns list of open positions"""
        pass

    @abstractmethod
    def place_order(self, symbol: str, qty: Optional[float], side: str, order_type: str, notional: Optional[float] = None) -> dict:
        """
        Place order. If qty is None, notional must be provided.
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancels an order by ID"""
        pass
