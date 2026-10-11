from abc import ABC, abstractmethod
from typing import Any


class BaseBroker(ABC):
    """
    Abstract interface for execution brokers.
    All implementations must return standard generic Dict/List structures.
    """

    @abstractmethod
    def get_account_balance(self) -> dict[str, Any]:
        """
        Returns account balance metrics.
        Must return a dict containing at minimum: 'equity', 'cash'.
        """

    @abstractmethod
    def place_order(self, symbol: str, qty: float, side: str, order_type: str = "market", stop_loss_price: float | None = None, client_order_id: str | None = None) -> dict[str, Any]:
        """
        Places an order.

        client_order_id (audit finding F4): a caller-generated, stable,
        deterministic idempotency key. Implementations MUST forward it to the
        venue where supported so a retry after an ambiguous outcome (timeout,
        crash between submission and durable record) cannot create a duplicate
        order. A local-only duplicate check is not sufficient.
        """

    def get_order(self, client_order_id: str) -> dict[str, Any] | None:
        """
        Look up an order by client_order_id. Optional capability: the default
        returns None (unknown), which callers must treat as "cannot answer" —
        never as permission to resubmit.
        """
        return None

    @abstractmethod
    def get_positions(self) -> list[dict[str, Any]]:
        """
        Returns a list of current active positions.
        """

    @abstractmethod
    def cancel_order(self, symbol: str) -> bool:
        """
        Cancels any open/working orders for a symbol.
        Used primarily during fails-closed events.
        """

    @abstractmethod
    def get_capabilities(self) -> dict[str, bool]:
        """
        Returns broker capability flags, mirroring freqtrade's exchange_has/_ft_has.
        Must return a dict containing at minimum:
        'supports_market_orders', 'supports_stop_limit', 'supports_paper'.
        Capabilities are checked before every order type (LIVE_DESIGN section 2).
        """
