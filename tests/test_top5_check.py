"""Tests for top5 triple-check: determinism, gates, dedupe, no-lookahead."""
import pandas as pd

from scripts.top5_check import (  # noqa: E402
    GATE,
    build_signal,
    dedupe_top5,
    run_backtest,
    sma_signal,
)


def _spy(n=200):
    import numpy as np
    rng = np.random.RandomState(3)
    idx = pd.date_range("2021-01-01", periods=n, freq="D")
    c = pd.Series(300 + rng.randn(n).cumsum() + 0.1 * np.arange(n), index=idx)
    return c


def test_recompute_deterministic():
    c = _spy()
    a = run_backtest(sma_signal(c, 20), c)
    b = run_backtest(sma_signal(c, 20), c)
    assert a == b


def test_gate_logic():
    assert GATE["sharpe_min"] == 0.8 and GATE["trips_min"] == 10
    good = {"sharpe": 0.9, "max_dd": 0.2, "oos": 0.6, "trips": 12}
    assert (good["sharpe"] >= GATE["sharpe_min"] and good["max_dd"] <= GATE["max_dd"]
            and good["oos"] >= GATE["oos_min"] and good["trips"] >= GATE["trips_min"])
    bad = dict(good, trips=5)
    assert not bad["trips"] >= GATE["trips_min"]


def test_dedupe_unique():
    strats = [
        {"id": "a", "status": "paper", "family": "spy_sma",
         "metrics": {"oos_sharpe": 1.6, "params": {"window": 127}}},
        {"id": "b", "status": "paper", "family": "spy_sma",
         "metrics": {"oos_sharpe": 1.6, "params": {"window": 127}}},
        {"id": "c", "status": "retired", "family": "spy_sma",
         "metrics": {"oos_sharpe": 2.0, "params": {"window": 50}}},
        {"id": "d", "status": "paper", "family": "spy_rsi2",
         "metrics": {"oos_sharpe": 1.0,
                     "params": {"entry": 12, "exit_hi": 76, "max_hold": 7}}},
    ]
    top, dupes = dedupe_top5(strats, top=5)
    assert dupes == 1
    assert [s["id"] for s in top] == ["a", "d"]  # retired excluded, best first


def test_no_lookahead_spot():
    c = _spy()
    s1 = sma_signal(c, 20)
    c2 = c.copy()
    c2.iloc[-1] *= 1.5  # shock the last bar
    s2 = sma_signal(c2, 20)
    # signals strictly before the last bar must not change (T+1 uses shifted)
    assert (s1.iloc[:-1] == s2.iloc[:-1]).all()


def test_build_signal_unknown_family():
    import pytest
    with pytest.raises(ValueError):
        build_signal("nope", {}, {"SPY": _spy()})
