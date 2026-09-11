"""
Portfolio risk manager with Kelly-based position sizing (Task 6.2).

Replaces static confidence-only allocation with edge-adjusted Kelly sizing
per the KellyBoost design (research-deliverables/kelly_sizer_pseudocode.md):

  - ``KellySizer``: fractional Kelly criterion (default quarter-Kelly),
    hard position cap, minimum-edge filter, and a retraining signal.
  - ``PortfolioManager``: confidence-based allocation with an optional
    Kelly override. When ``trade_features`` are supplied, the target
    allocation is the MINIMUM of the confidence-based and Kelly-based
    amounts — dual constraint, never over-size relative to either method.
  - Per-trade risk budget (default 2% of account equity) with explicit
    ``compute_trade_risk`` / ``check_risk_budget`` helpers.

Fail-closed: degenerate inputs (zero/negative variance, edge below
threshold, no trade history) return 0.0 — never an oversized position.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np


class KellySizer:
    """
    Dynamic position sizing via the Kelly criterion.

    Replaces static risk-per-trade with edge-adjusted sizing. The GBDT
    prediction model is a placeholder: until enough trade history exists
    (``lookback_window`` samples), ``predict_edge_and_variance`` falls back
    to historical averages, and with no history at all returns a
    conservative (0.0 edge, 1.0 variance) pair.
    """

    def __init__(
        self,
        kelly_fraction: float = 0.25,   # quarter-Kelly default for safety
        max_position_pct: float = 0.20,  # hard cap: never risk >20% on one trade
        min_edge: float = 0.01,          # ignore trades with edge < 1%
        lookback_window: int = 1000,     # minimum samples for GBDT training
        retrain_interval: int = 500,     # retrain every 500 trades
    ):
        self.kelly_fraction = kelly_fraction
        self.max_position_pct = max_position_pct
        self.min_edge = min_edge
        self.lookback_window = lookback_window
        self.retrain_interval = retrain_interval
        self.trade_history: list[dict[str, Any]] = []
        self.model: Any = None  # GBDT model placeholder
        self._retrain_count = 0

    def kelly_size(
        self,
        edge_estimate: float,
        variance: float,
        kelly_fraction: float | None = None,
    ) -> float:
        """
        Compute optimal position size using the Kelly criterion.

        Args:
            edge_estimate: Expected return (win_rate * avg_win - loss_rate * avg_loss)
            variance: Variance of returns (std_dev^2)
            kelly_fraction: Override default fraction (0.25 = quarter-Kelly)

        Returns:
            Position size as fraction of account equity (0.0 to max_position_pct)
        """
        if kelly_fraction is None:
            kelly_fraction = self.kelly_fraction

        # Guard: skip if edge too small (fail-closed)
        if abs(edge_estimate) < self.min_edge:
            return 0.0

        # Guard: skip if variance is zero or negative (degenerate)
        if variance <= 0:
            return 0.0

        # Kelly formula (continuous): f* = mu / sigma^2
        kelly_raw = edge_estimate / variance

        # Apply fractional Kelly (safety scaling)
        kelly_adjusted = kelly_raw * kelly_fraction

        # Clamp to [0, max_position_pct]
        return max(0.0, min(kelly_adjusted, self.max_position_pct))

    def record_trade(self, trade_result: dict[str, Any]) -> None:
        """Record trade outcome for model retraining."""
        self.trade_history.append(trade_result)

        # Trigger retrain if enough new samples
        if len(self.trade_history) % self.retrain_interval == 0:
            self._retrain_model()

    def _retrain_model(self) -> None:
        """Retrain GBDT model on recent trade history (placeholder)."""
        if len(self.trade_history) < self.lookback_window:
            return  # not enough data yet
        # Placeholder: feature engineering + GBDT training (sklearn/xgboost/lightgbm)
        # would happen here. The retraining signal is surfaced for observability.
        self._retrain_count += 1

    def predict_edge_and_variance(self, features: dict[str, Any]) -> tuple[float, float]:
        """
        Predict edge and variance for a new trade.

        Returns:
            (edge_estimate, variance)
        """
        if self.model is None:
            # Fallback: use historical averages
            return self._historical_fallback()
        # Model inference placeholder
        return self._historical_fallback()

    def _historical_fallback(self) -> tuple[float, float]:
        """Fallback when no model is trained yet."""
        if not self.trade_history:
            return (0.0, 1.0)  # conservative: zero edge, unit variance

        returns = [t.get("return", 0.0) for t in self.trade_history[-self.lookback_window:]]
        edge = float(np.mean(returns))
        variance = float(np.var(returns)) if len(returns) > 1 else 1.0
        return (edge, variance)


class PortfolioManager:
    def __init__(
        self,
        max_strategies: int = 5,
        max_allocation_per_strategy_pct: float = 0.5,
        kelly_fraction: float = 0.25,          # quarter-Kelly default
        max_per_trade_risk_pct: float = 0.02,  # 2% max risk per trade
    ):
        self.max_strategies = max_strategies
        self.max_allocation_per_strategy_pct = max_allocation_per_strategy_pct
        self.max_per_trade_risk_pct = max_per_trade_risk_pct
        self.kelly_sizer = KellySizer(kelly_fraction=kelly_fraction)
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

    def get_target_allocation(
        self,
        strategy_id: str,
        account_equity: float,
        trade_features: dict[str, Any] | None = None,
    ) -> float:
        """
        Compute target allocation using Kelly sizing when available.

        Falls back to confidence-based sizing if no trade features provided.
        When Kelly sizing is active, returns the MINIMUM of the
        confidence-based and Kelly-based amounts (dual constraint).
        """
        base_alloc = self.active_strategies.get(strategy_id, 0.0)
        base_amount = account_equity * base_alloc

        if trade_features is not None:
            # Use Kelly sizing
            edge, variance = self.kelly_sizer.predict_edge_and_variance(trade_features)
            kelly_pct = self.kelly_sizer.kelly_size(edge, variance)

            # Kelly result is % of equity — convert to dollar amount
            kelly_amount = account_equity * kelly_pct

            # Take the MINIMUM of confidence-based and Kelly-based
            # This ensures we never over-size relative to either method
            return min(base_amount, kelly_amount)

        return base_amount

    def compute_trade_risk(self, entry_price: float, stop_loss: float, position_size: float) -> float:
        """Compute dollar risk for a single trade."""
        risk_per_share = abs(entry_price - stop_loss)
        dollar_risk = risk_per_share * position_size
        return dollar_risk

    def check_risk_budget(self, account_equity: float, proposed_risk: float) -> bool:
        """Verify proposed risk is within per-trade budget."""
        max_risk = account_equity * self.max_per_trade_risk_pct
        return proposed_risk <= max_risk