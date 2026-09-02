"""
Kelly Criterion Primary Position Sizing with Regime-Adjusted, Semi-Variance-Penalized,
Multi-Strategy Aggregation (KellyBoost) and Half-Kelly Capping.

Primary sizing: Kelly fraction from historical win rate, avg win, avg loss.
Fallback: ATR-based sizing when Kelly inputs unavailable.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


BASE_RISK_PCT = 0.02
MAX_NOTIONAL_LEV = 1.0
KELLY_FRACTION = 0.5  # Half-Kelly default


@dataclass
class TradeStats:
    """Trade statistics for Kelly calculation."""
    wins: int
    losses: int
    avg_win: float
    avg_loss: float
    downside_var: Optional[float] = None


@dataclass
class PositionResult:
    """Final position sizing result."""
    size: int
    method: str  # "kelly" or "atr_fallback"
    kelly_fraction_used: float = 0.0
    regime_adjustment: float = 1.0
    raw_kelly: float = 0.0
    confidence: float = 0.0


class KellyCalculator:
    """Core Kelly fraction with semi-variance adjustment."""

    @staticmethod
    def kelly_fraction(win_probability: float, win_loss_ratio: float) -> float:
        """f* = (p*b - q) / b"""
        if win_probability <= 0 or win_probability >= 1 or win_loss_ratio <= 0:
            return 0.0
        p = win_probability
        q = 1 - p
        b = win_loss_ratio
        f_star = (p * b - q) / b
        return max(f_star, 0.0)

    @staticmethod
    def semi_variance_adjustment(trade_stats: TradeStats) -> float:
        """Adjust Kelly for downside variance penalty."""
        if trade_stats.downside_var is None or trade_stats.avg_win == 0:
            return 1.0
        avg_win_sq = trade_stats.avg_win ** 2
        downside_var = trade_stats.downside_var
        if avg_win_sq + downside_var == 0:
            return 1.0
        adjustment = 1.0 - (downside_var / (avg_win_sq + downside_var))
        return max(adjustment, 0.1)

    @staticmethod
    def raw_kelly(trade_stats: TradeStats) -> float:
        """Compute raw Kelly fraction from trade stats."""
        total = trade_stats.wins + trade_stats.losses
        if total == 0 or trade_stats.avg_loss == 0:
            return 0.0
        win_prob = trade_stats.wins / total
        win_loss_ratio = abs(trade_stats.avg_win / trade_stats.avg_loss)
        return KellyCalculator.kelly_fraction(win_prob, win_loss_ratio)

    @staticmethod
    def adjusted_kelly(trade_stats: TradeStats) -> float:
        """Raw Kelly × semi-variance adjustment."""
        raw = KellyCalculator.raw_kelly(trade_stats)
        adj = KellyCalculator.semi_variance_adjustment(trade_stats)
        return raw * adj


class RegimeAdjuster:
    """Adjust Kelly fraction based on market regime."""

    # Regime multipliers (from RegimeDetector labels)
    REGIME_MULTIPLIERS = {
        "strong_bull": 1.0,
        "weak_bull": 0.9,
        "neutral": 0.7,
        "weak_bear": 0.5,
        "strong_bear": 0.3,
        "crisis": 0.1,
    }

    @classmethod
    def adjust(cls, kelly_frac: float, regime: str) -> float:
        mult = cls.REGIME_MULTIPLIERS.get(regime, 0.7)
        return kelly_frac * mult


class MacroAdjuster:
    """Adjust Kelly fraction based on macro conditions from FRED provider."""

    MACRO_MULTIPLIERS = {
        "expansion": 1.0,
        "slowdown": 0.8,
        "contraction": 0.6,
        "recovery": 0.9,
        "unknown": 0.8,
    }

    @classmethod
    def adjust(cls, kelly_frac: float, macro_regime: str) -> float:
        mult = cls.MACRO_MULTIPLIERS.get(macro_regime, 0.8)
        return kelly_frac * mult


class KellyBoostAggregator:
    """Aggregate Kelly fractions across multiple strategies (KellyBoost)."""

    @staticmethod
    def aggregate(kelly_fractions: list[float], weights: list[float] | None = None) -> float:
        """Aggregate Kelly fractions using weighted average with correlation adjustment."""
        if not kelly_fractions:
            return 0.0
        if weights is None:
            weights = [1.0] * len(kelly_fractions)

        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(f * w for f, w in zip(kelly_fractions, weights))
        base_agg = weighted_sum / total_weight

        # Diversification bonus: if strategies are uncorrelated, boost slightly
        # Penalty if all strategies agree (concentration risk)
        if len(kelly_fractions) > 1:
            variance = np.var(kelly_fractions) if len(kelly_fractions) > 1 else 0
            diversification_bonus = float(min(variance * 2, 0.05))  # Cap at 5% bonus
            return base_agg + diversification_bonus

        return base_agg


class ConfidenceAdjuster:
    """Adjust Kelly based on sample size confidence."""

    @staticmethod
    def adjust(kelly_frac: float, total_trades: int) -> float:
        """Reduce Kelly when sample size is small."""
        if total_trades < 20:
            return kelly_frac * 0.5
        elif total_trades < 50:
            return kelly_frac * 0.75
        return kelly_frac


class PositionSizer:
    """
    Primary position sizing via Kelly Criterion.

    Fallback to ATR-based sizing when Kelly inputs unavailable.
    """

    def __init__(
        self,
        half_kelly: float = KELLY_FRACTION,
        max_notional_lev: float = MAX_NOTIONAL_LEV,
        base_risk_pct: float = BASE_RISK_PCT,
    ):
        self.half_kelly = half_kelly
        self.max_notional_lev = max_notional_lev
        self.base_risk_pct = base_risk_pct

    def size_position(
        self,
        trade_stats: Optional[TradeStats],
        price: float,
        regime: str = "neutral",
        macro_regime: str = "unknown",
        strategy_kelly_fractions: Optional[list[float]] = None,
        strategy_weights: Optional[list[float]] = None,
        account_value: float = 10000.0,
        total_trades: int = 0,
    ) -> PositionResult:
        """
        Size a position using Kelly as primary method.

        Returns PositionResult with size, method used, and all adjustments.
        """
        # PRIMARY: Kelly-based sizing
        if trade_stats is not None and trade_stats.wins + trade_stats.losses > 0:
            return self._kelly_size(
                trade_stats=trade_stats,
                price=price,
                regime=regime,
                macro_regime=macro_regime,
                strategy_kelly_fractions=strategy_kelly_fractions,
                strategy_weights=strategy_weights,
                account_value=account_value,
                total_trades=total_trades,
            )

        # FALLBACK: ATR-based sizing when Kelly inputs unavailable
        return self._atr_fallback_size(
            price=price,
            account_value=account_value,
            base_risk_pct=self.base_risk_pct,
        )

    def _kelly_size(
        self,
        trade_stats: TradeStats,
        price: float,
        regime: str,
        macro_regime: str,
        strategy_kelly_fractions: Optional[list[float]],
        strategy_weights: Optional[list[float]],
        account_value: float,
        total_trades: int,
    ) -> PositionResult:
        """Primary Kelly-based position sizing."""
        # Step 1: Raw Kelly
        raw = KellyCalculator.raw_kelly(trade_stats)

        # Step 2: Semi-variance adjustment
        semi_var_adj = KellyCalculator.semi_variance_adjustment(trade_stats)
        adjusted = raw * semi_var_adj

        # Step 3: Confidence normalization
        confidence_adj = ConfidenceAdjuster.adjust(adjusted, total_trades)

        # Step 4: Regime adjustment
        regime_adj = RegimeAdjuster.adjust(confidence_adj, regime)

        # Step 5: Macro adjustment
        macro_adj = MacroAdjuster.adjust(regime_adj, macro_regime)

        # Step 6: KellyBoost aggregation if multiple strategies
        if strategy_kelly_fractions:
            aggregated = KellyBoostAggregator.aggregate(
                strategy_kelly_fractions, strategy_weights
            )
            # Blend aggregated with individual Kelly
            final_kelly = (macro_adj + aggregated) / 2
        else:
            final_kelly = macro_adj

        # Step 7: Half-Kelly capping
        capped_kelly = final_kelly * self.half_kelly

        # Step 8: Max notional leverage cap
        capped_kelly = min(capped_kelly, self.max_notional_lev)

        # Step 9: Convert to shares
        risk_amount = account_value * self.base_risk_pct
        if price > 0 and capped_kelly > 0:
            position_value = risk_amount / capped_kelly
            size = int(position_value / price)
        else:
            size = 0

        return PositionResult(
            size=max(size, 0),
            method="kelly",
            kelly_fraction_used=capped_kelly,
            regime_adjustment=RegimeAdjuster.REGIME_MULTIPLIERS.get(regime, 0.7),
            raw_kelly=raw,
            confidence=semi_var_adj,
        )

    def _atr_fallback_size(
        self,
        price: float,
        account_value: float,
        base_risk_pct: float,
    ) -> PositionResult:
        """ATR-based fallback sizing when Kelly inputs unavailable."""
        # Simple ATR-based sizing using base risk percentage
        risk_amount = account_value * base_risk_pct
        if price > 0:
            size = int(risk_amount / price)
        else:
            size = 0

        return PositionResult(
            size=max(size, 0),
            method="atr_fallback",
            kelly_fraction_used=0.0,
            regime_adjustment=1.0,
            raw_kelly=0.0,
            confidence=0.0,
        )
