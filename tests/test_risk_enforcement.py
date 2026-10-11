"""P1.4: risk limits must be enforced by the sizer itself (audit finding F1)."""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk.position_sizing import (
    MAX_CONCURRENT_POSITIONS,
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE_PCT,
    PRM_HARD_STOP_ENABLED,
    PositionSizer,
)


def _size(**overrides):
    kwargs = {
        "account_equity": 1000.0,
        "current_price": 100.0,
        "stop_loss_price": 99.0,  # $1 risk per share
        "win_rate": 0.6,
        "win_loss_ratio": 2.0,
        "confidence_score": 0.8,
    }
    kwargs.update(overrides)
    return PositionSizer.calculate_position_size(**kwargs)


def test_breakers_default_enabled():
    from src.risk import position_sizing as risk_config
    assert risk_config.CIRCUIT_BREAKER_ENABLED is True
    assert risk_config.MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT == 0.15
    assert risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT == 0.05
    assert risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT == 0.10


def test_negative_edge_rejected_not_defaulted():
    """Kelly <= 0 must yield NO trade (the old code fell back to 1% risk)."""
    assert _size(win_rate=0.2, win_loss_ratio=1.0) == 0.0  # kelly = 0.2 - 0.8 < 0
    assert _size(win_loss_ratio=0.5) == 0.0


def test_invalid_inputs_rejected():
    assert _size(account_equity=0.0) == 0.0
    assert _size(account_equity=-5.0) == 0.0
    assert _size(current_price=0.0) == 0.0
    assert _size(win_rate=1.5) == 0.0
    assert _size(win_rate=-0.1) == 0.0
    assert _size(confidence_score=1.5) == 0.0
    assert _size(confidence_score=-0.2) == 0.0
    assert _size(win_loss_ratio=-1.0) == 0.0


def test_low_confidence_rejected():
    assert _size(confidence_score=0.4) == 0.0


def test_per_trade_risk_cap_enforced():
    """With the hard stop on (default), risk is capped at 1% of equity."""
    qty = _size()
    risk_per_share = 1.0
    assert qty * risk_per_share <= 1000.0 * MAX_RISK_PER_TRADE_PCT + 1e-9


def test_position_size_cap_enforced():
    """Qty never exceeds 25% of equity in notional (declared cap, now enforced)."""
    qty = _size(stop_loss_price=99.999)  # tiny risk/share -> huge risk-based qty
    assert qty <= (1000.0 * MAX_POSITION_SIZE_PCT) / 100.0 + 1e-9


def test_equity_umbrella_enforced():
    qty = _size(stop_loss_price=50.0)  # $50 risk/share
    assert qty <= 1000.0 / 100.0  # cannot exceed equity


def test_concurrent_position_limit_enforced():
    assert _size(open_positions=MAX_CONCURRENT_POSITIONS) == 0.0
    assert _size(open_positions=MAX_CONCURRENT_POSITIONS - 1) > 0.0


def test_hard_stop_flag_matches_default():
    """Default posture: hard stop ON (env can still opt out)."""
    assert PRM_HARD_STOP_ENABLED is True
