from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseBroker(ABC):
    @abstractmethod
    def get_account_balance(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def place_order(self, symbol: str, qty: float, side: str, order_type: str = "market") -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        pass