"""PositionSizer macro-regime tests against the current Kelly contract.

Contract migration note (2026-09-11): ``src.risk.position_sizer.PositionSizer``
is Kelly-primary (``size_position`` -> ``PositionResult``); there is no
``FredMacroProvider`` attribute, no ``macro_provider`` member and no
``calculate_size`` method on this class. Macro state enters as a
``macro_regime`` label (see ``MacroAdjuster`` and
``src.risk.fred_macro_provider.FredMacroProvider``). These tests cover the same
intent as the pre-Kelly suite (macro scales sizing; unknown is mild; missing
Kelly inputs fall back) through the current API.
"""

import pytest

from src.risk.position_sizer import MacroAdjuster, PositionSizer, TradeStats


def _stats() -> TradeStats:
    return TradeStats(wins=60, losses=40, avg_win=100.0, avg_loss=50.0)


def test_position_sizer_with_macro_regime():
    # Contraction multiplier is 0.6 (MacroAdjuster).
    assert MacroAdjuster.adjust(1.0, "contraction") == pytest.approx(0.6)
    sizer = PositionSizer(base_risk_pct=0.02)
    res = sizer.size_position(
        _stats(), price=100.0, macro_regime="contraction",
        total_trades=100, account_value=10000.0,
    )
    assert res.method == "kelly"
    assert res.kelly_fraction_used == pytest.approx(0.084)
    assert res.size == 23


def test_position_sizer_neutral_macro_regime_noop():
    # Unknown/neutral macro is the mild 0.8 multiplier, not a full derisk.
    assert MacroAdjuster.adjust(1.0, "unknown") == pytest.approx(0.8)
    sizer = PositionSizer(base_risk_pct=0.02)
    res = sizer.size_position(
        _stats(), price=100.0, macro_regime="unknown",
        total_trades=100, account_value=10000.0,
    )
    assert res.method == "kelly"
    assert res.kelly_fraction_used == pytest.approx(0.112)
    assert res.size == 17


def test_position_sizer_macro_provider_failure():
    # No Kelly inputs (e.g. macro/stats feed unavailable) -> ATR fallback.
    sizer = PositionSizer(base_risk_pct=0.02)
    res = sizer.size_position(None, price=100.0, account_value=10000.0)
    assert res.method == "atr_fallback"
    assert res.size == 2


def test_position_sizer_macro_provider_method_failure():
    # Degenerate stats (zero trades) cannot produce Kelly -> graceful fallback.
    sizer = PositionSizer(base_risk_pct=0.02)
    res = sizer.size_position(
        TradeStats(wins=0, losses=0, avg_win=0.0, avg_loss=0.0),
        price=100.0, account_value=10000.0,
    )
    assert res.method == "atr_fallback"
    assert res.size == 2
