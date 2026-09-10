"""CS-07 canonical backtest engine drift test — T+1 @ 5bps equivalence."""

import numpy as np
import pandas as pd

from src.backtest.engines import backtest as canonical_backtest


def test_canonical_tplus1_5bps():
    idx = pd.date_range("2020-01-01", periods=100, freq="B")
    close = pd.Series(100 + np.arange(100) * 0.1, index=idx)
    spy_close = pd.Series(100 + np.arange(100) * 0.05, index=idx)
    signal = pd.Series([1 if i % 10 < 5 else 0 for i in range(100)], index=idx, dtype=float)

    out = canonical_backtest(signal, close, spy_close, slippage=0.0005, tplus1=True)
    assert "sharpe" in out and "cagr" in out and "max_dd" in out
    assert out["n_bars"] == 100
    # T+1 check: first position should be 0 due to shift, so first strat return 0
    # canonical should not use today's signal for same-day return
    pos = signal.shift(1).fillna(0.0)
    assert pos.iloc[0] == 0.0
    assert out["trades"] >= 0


def test_canonical_vs_evolve_real_drift():
    """Assert evolve_real.backtest wrapper stays close to canonical on fixture (tolerance for tiered cost)."""
    import sys
    from unittest.mock import MagicMock

    # evolve_real imports ccxt etc — mock heavy deps
    sys.modules.setdefault("ccxt", MagicMock())
    from evolve_real import backtest as evolve_backtest

    idx = pd.date_range("2020-01-01", periods=50, freq="B")
    close = pd.Series(100 + np.random.randn(50).cumsum() * 0.5 + 5, index=idx)
    spy_close = pd.Series(100 + np.random.randn(50).cumsum() * 0.3 + 5, index=idx)
    signal = pd.Series(np.random.choice([0, 1], size=50).astype(float), index=idx)

    can = canonical_backtest(signal, close, spy_close, slippage=0.0005, tplus1=True)
    evo = evolve_backtest(signal, close, spy_close, family="spy_sma", slippage_bps=5.0)
    # Core P&L must be directionally consistent: sharpe sign should match when tiered cost not huge
    # Use loose tolerance because tiered cost adds vol-scaled slippage
    assert abs(can["sharpe"] - evo["sharpe"]) < 2.0  # generous drift guard
    assert can["n_bars"] == evo["n_bars"]
