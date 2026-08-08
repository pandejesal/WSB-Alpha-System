import math

# ============================================================================
# PHASE 4: LIVE CAPITAL GATE & SAFETY RAILS (REFACTORED FOR QUANT OVERHAUL)
# ============================================================================

LIVE_TRADING_ENABLED = False

# Hard-coded safety rails for the $100 micro-account constraint
ACCOUNT_BASE_CAPITAL = 100.0

# Hard cap of US$ notional risk <= 1% of equity per trade
MAX_RISK_PER_TRADE_PCT = 0.01

MAX_POSITION_SIZE_PCT = 0.25

# Absolute maximum concurrent positions
MAX_CONCURRENT_POSITIONS = 4

# Circuit breakers (Halt trading if drawdown exceeds these thresholds)
DAILY_LOSS_CIRCUIT_BREAKER_PCT = 0.05
WEEKLY_LOSS_CIRCUIT_BREAKER_PCT = 0.10
MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT = 0.15

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
        broker_min_increment: float = 1.0
    ) -> float:
        """
        Calculates the fractional share quantity based on Fractional Kelly,
        hard risk caps, and confidence thresholds.
        """
        # Zero-size trades when confidence is low
        if confidence_score < 0.5:
            return 0.0

        # Calculate base Kelly risk fraction
        target_risk_pct = PositionSizer.calculate_kelly_fraction(win_rate, win_loss_ratio)

        # Adjust risk based on regime volatility (e.g., lower risk in high vol)
        target_risk_pct *= regime_volatility_multiplier

        # Apply HARD constraints
        actual_risk_pct = min(target_risk_pct, MAX_RISK_PER_TRADE_PCT)

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

        # Take the minimum of risk-based qty and equity-based qty
        final_target_qty = min(target_qty_from_risk, max_qty_from_equity)

        # Apply fractional rounding edge cases
        # floor_to_increment(qty, broker_min_increment)
        qty = math.floor(final_target_qty / broker_min_increment) * broker_min_increment

        return max(0.0, qty)
