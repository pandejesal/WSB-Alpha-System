import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class ExecutionWrapper:
    """
    Hardened orchestration wrapper for broker execution.
    Implements exponential backoff and Fails-Closed logic.
    """

    def __init__(self, broker: Any, max_retries: int = 3, base_timeout: float = 2.0):
        self.broker = broker
        self.max_retries = max_retries
        self.base_timeout = base_timeout
        self.halted_symbols = set()

    def _execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        import random
        retries = 0
        while retries <= self.max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Execution failed after {self.max_retries} retries: {str(e)}")
                    raise e

                # Exponential backoff with jitter
                sleep_time = (self.base_timeout * (2 ** (retries - 1))) + random.uniform(0, 1)
                logger.warning(f"Execution error ({str(e)}). Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)

    def get_account_balance(self) -> dict:
        return self._execute_with_retry(self.broker.get_account_balance)

    def get_positions(self) -> list:
        return self._execute_with_retry(self.broker.get_positions)

    def cancel_order(self, symbol: str) -> bool:
        return self._execute_with_retry(self.broker.cancel_order, symbol)

    def place_order(self, symbol: str, qty: float, side: str, order_type: str = "market", stop_loss_price: float = None) -> dict:
        if symbol in self.halted_symbols:
            logger.error(f"Fails-Closed constraint: Cannot place order for halted symbol {symbol}.")
            return {}

        try:
            return self._execute_with_retry(self.broker.place_order, symbol, qty, side, order_type, stop_loss_price)
        except Exception:
            # FAILS CLOSED PROTOCOL
            logger.error(f"Fails-Closed triggered for {symbol}. Canceling open orders and blocking symbol.")
            try:
                self.broker.cancel_order(symbol)
            except Exception:
                pass
            self.halted_symbols.add(symbol)
            return {}
