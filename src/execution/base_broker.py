from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseBroker(ABC):
    """
    Abstract interface for execution brokers.
    All implementations must return standard generic Dict/List structures.
    """

    @abstractmethod
    def get_account_balance(self) -> Dict[str, Any]:
        """
        Returns account balance metrics.
        Must return a dict containing at minimum: 'equity', 'cash'.
        """
        pass

    @abstractmethod
    def place_order(self, symbol: str, qty: float, side: str, order_type: str = "market", stop_loss_price: float = None) -> Dict[str, Any]:
        """
        Places an order.
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Returns a list of current active positions.
        """
        pass

    @abstractmethod
    def cancel_order(self, symbol: str) -> bool:
        """
        Cancels any open/working orders for a symbol.
        Used primarily during fails-closed events.
        """
        pass
