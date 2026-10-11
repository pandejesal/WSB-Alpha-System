import math
import os

# Risk safety rails — DEFAULT ON (audit remediation 2026-10-11, phase 1).
# Env override: PRM_HARD_STOP_ENABLED=0 or CIRCUIT_BREAKER_ENABLED=0 to disable.
# Rationale (audit finding F1): the previous defaults (off, with loss limits
# widened to 100%) meant a configuration could look risk-managed while the
# active execution path enforced nothing. Safety limits must be enforced by
# the implementation, not opt-in via environment.
PRM_HARD_STOP_ENABLED = os.getenv("PRM_HARD_STOP_ENABLED", "1").lower() not in ("0", "false", "off", "")
CIRCUIT_BREAKER_ENABLED = os.getenv("CIRCUIT_BREAKER_ENABLED", "1").lower() not in ("0", "false", "off", "")

# ============================================================================
# PHASE 4: LIVE CAPITAL GATE & SAFETY RAILS (REFACTORED FOR QUANT OVERHAUL)
# ============================================================================

# Live trading gate — FAIL-CLOSED: absent/blank/garbage env => False (paper).
# Strict token match (no stripping/casing tricks): only 1/true/yes enables.
# Flipped to true ONLY via the live_gate_flip.yml manual dispatch after CI passes.
LIVE_TRADING_ENABLED = os.getenv("LIVE_TRADING_ENABLED", "0") in ("1", "true", "yes", "True", "Yes", "TRUE", "YES")

# Hard-coded safety rails for the $100 micro-account constraint
ACCOUNT_BASE_CAPITAL = 100.0

# Hard cap of US$ notional risk <= 1% of equity per trade
MAX_RISK_PER_TRADE_PCT = 0.01

MAX_POSITION_SIZE_PCT = 0.25

# Absolute maximum concurrent positions
MAX_CONCURRENT_POSITIONS = 4

# Circuit breakers (Halt trading if drawdown exceeds these thresholds).
# Defaults are the real limits when CIRCUIT_BREAKER_ENABLED (the default);
# they widen to 1.0 (100% loss allowed) ONLY on an explicit env opt-out.
DAILY_LOSS_CIRCUIT_BREAKER_PCT = 0.05 if CIRCUIT_BREAKER_ENABLED else 1.0
WEEKLY_LOSS_CIRCUIT_BREAKER_PCT = 0.10 if CIRCUIT_BREAKER_ENABLED else 1.0
MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT = 0.15 if CIRCUIT_BREAKER_ENABLED else 1.0

class PositionSizer:
    """
    Implements Regime-adjusted Fractional Kelly Criterion for position sizing,
    with hard constraints for micro-accounts.
    """

    @staticmethod
    def calculate_kelly_fraction(win_rate: float, win_loss_ratio: float, kelly_fraction: float = 0.15) -> float:
        """
        Calculates the fractional Kelly criterion.
        kelly = W - ((1 - W) / R)
        where W is win rate, R is win/loss ratio.
        """
        if win_loss_ratio <= 0:
            return 0.0

        kelly = win_rate - ((1.0 - win_rate) / win_loss_ratio)

        if kelly <= 0:
            return 0.0

        # Apply fractional multiplier (typically 0.1 to 0.25)
        return kelly * kelly_fraction

    @staticmethod
    def calculate_position_size(
        account_equity: float,
        current_price: float,
        stop_loss_price: float,
        win_rate: float,
        win_loss_ratio: float,
        confidence_score: float,
        regime_volatility_multiplier: float = 1.0,
        broker_min_increment: float = 1.0,
        open_positions: int = 0
    ) -> float:
        """
        Calculates the fractional share quantity based on Fractional Kelly,
        hard risk caps, and confidence thresholds.

        Audit finding F1: the hard cap now applies by default, negative-edge /
        invalid inputs are rejected (no fallback to a default risk), and the
        declared position-size and concurrent-position limits are enforced here
        rather than merely declared.
        """
        # Invalid or non-positive inputs -> no trade (never fall back to a
        # default risk allocation).
        if not all(isinstance(v, (int, float)) for v in (account_equity, current_price, stop_loss_price)):
            return 0.0
        if account_equity <= 0 or current_price <= 0:
            return 0.0
        if not 0.0 <= win_rate <= 1.0 or win_loss_ratio <= 0 or confidence_score < 0 or confidence_score > 1:
            return 0.0
        # Concurrent-position limit is a portfolio-level rail enforced at sizing.
        if open_positions >= MAX_CONCURRENT_POSITIONS:
            return 0.0

        # Zero-size trades when confidence is low
        if confidence_score < 0.5:
            return 0.0

        # Calculate base Kelly risk fraction
        target_risk_pct = PositionSizer.calculate_kelly_fraction(win_rate, win_loss_ratio)

        # A non-positive estimated edge is a no-trade, not a default allocation.
        if target_risk_pct <= 0:
            return 0.0

        # Adjust risk based on regime volatility (e.g., lower risk in high vol)
        target_risk_pct *= regime_volatility_multiplier
        if target_risk_pct <= 0:
            return 0.0

        # Apply HARD constraints — enforced by default; env opt-out narrows
        # only the 1% per-trade risk cap (PRM_HARD_STOP_ENABLED=0).
        if PRM_HARD_STOP_ENABLED:
            actual_risk_pct = min(target_risk_pct, MAX_RISK_PER_TRADE_PCT)
        else:
            actual_risk_pct = target_risk_pct if target_risk_pct > 0 else MAX_RISK_PER_TRADE_PCT

        # Calculate absolute US$ risk amount
        risk_amount_usd = account_equity * actual_risk_pct

        # Calculate risk per share based on stop loss
        risk_per_share = abs(current_price - stop_loss_price)

        if risk_per_share <= 0:
            return 0.0

        # Calculate target quantity based on risk
        target_qty_from_risk = risk_amount_usd / risk_per_share

        # Hard max notional umbrella to ensure we don't exceed available equity (no margin)
        max_notional_allowed = account_equity
        max_qty_from_equity = max_notional_allowed / current_price

        # Declared max position size (25% of equity) — enforced, not decorative.
        max_qty_from_position_cap = (account_equity * MAX_POSITION_SIZE_PCT) / current_price

        # Take the minimum of risk-based qty, equity-based qty and position cap
        final_target_qty = min(target_qty_from_risk, max_qty_from_equity, max_qty_from_position_cap)

        # Apply fractional rounding edge cases
        # floor_to_increment(qty, broker_min_increment)
        qty = math.floor(final_target_qty / broker_min_increment) * broker_min_increment

        return max(0.0, qty)
