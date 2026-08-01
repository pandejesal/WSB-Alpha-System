from typing import Dict, Any, List
import logging
import pandas as pd

class PortfolioManager:
    """
    Manages capital allocation across multiple strategies.
    Ensures that the sum of all strategy allocations does not exceed total account equity.
    """
    def __init__(self, max_strategies: int = 5, max_allocation_per_strategy_pct: float = 0.5):
        self.logger = logging.getLogger(__name__)
        self.max_strategies = max_strategies
        self.max_allocation_per_strategy_pct = max_allocation_per_strategy_pct
        self.active_strategies = {}  # dict of strategy_id -> target_allocation_pct

    def register_strategy(self, strategy_id: str, confidence_score: float) -> bool:
        if len(self.active_strategies) >= self.max_strategies and strategy_id not in self.active_strategies:
            self.logger.warning(f"Cannot register {strategy_id}. Max strategies reached.")
            return False

        # Basic confidence-based allocation.
        # e.g., mapping confidence 0-100 to an allocation percentage, capped by max_allocation
        allocation_pct = min((confidence_score / 100.0) * self.max_allocation_per_strategy_pct, self.max_allocation_per_strategy_pct)

        self.active_strategies[strategy_id] = allocation_pct
        self.logger.info(f"Registered strategy {strategy_id} with target allocation {allocation_pct:.2%}")
        self._rebalance_allocations()
        return True

    def deregister_strategy(self, strategy_id: str):
        if strategy_id in self.active_strategies:
            del self.active_strategies[strategy_id]
            self.logger.info(f"Deregistered strategy {strategy_id}")
            self._rebalance_allocations()

    def _rebalance_allocations(self):
        """
        Ensures total target allocations do not exceed 100% of the portfolio.
        If they do, scales them down proportionally.
        """
        if not self.active_strategies:
            return

        total_allocation = sum(self.active_strategies.values())
        if total_allocation > 1.0:
            scale_factor = 1.0 / total_allocation
            for sid in self.active_strategies:
                self.active_strategies[sid] *= scale_factor
            self.logger.info(f"Total allocation exceeded 100%. Scaled down by {scale_factor:.2f}")

    def get_target_allocation(self, strategy_id: str, account_equity: float) -> float:
        """
        Returns the dollar amount allocated to a specific strategy.
        """
        allocation_pct = self.active_strategies.get(strategy_id, 0.0)
        return account_equity * allocation_pct
