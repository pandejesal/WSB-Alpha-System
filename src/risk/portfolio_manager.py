
class PortfolioManager:
    def __init__(self, max_strategies: int = 5, max_allocation_per_strategy_pct: float = 0.5):
        self.max_strategies = max_strategies
        self.max_allocation_per_strategy_pct = max_allocation_per_strategy_pct
        self.active_strategies = {}

    def register_strategy(self, strategy_id: str, confidence_score: float) -> bool:
        if len(self.active_strategies) >= self.max_strategies and strategy_id not in self.active_strategies:
            return False

        allocation_pct = min((confidence_score / 100.0) * self.max_allocation_per_strategy_pct, self.max_allocation_per_strategy_pct)
        self.active_strategies[strategy_id] = allocation_pct
        self._rebalance_allocations()
        return True

    def _rebalance_allocations(self):
        if not self.active_strategies:
            return
        total_allocation = sum(self.active_strategies.values())
        if total_allocation > 1.0:
            scale = 1.0 / total_allocation
            for sid in self.active_strategies:
                self.active_strategies[sid] *= scale

    def get_target_allocation(self, strategy_id: str, account_equity: float) -> float:
        return account_equity * self.active_strategies.get(strategy_id, 0.0)
