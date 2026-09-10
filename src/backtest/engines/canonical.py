"""Canonical backtest engine — single source (CS-07).

Extracted from evolve_real.py:386 (T+1 @ 5bps canonical).
All scripts must import this; drift test asserts equivalence.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_sharpe(returns: pd.Series) -> float:
    try:
        m = float(returns.mean())
        s = float(returns.std())
        if s == 0 or np.isnan(s):
            return 0.0
        return m / s * np.sqrt(252)
    except Exception:
        return 0.0


def _cagr(eq: pd.Series) -> float:
    try:
        if len(eq) < 2:
            return 0.0
        return float((eq.iloc[-1] / eq.iloc[0]) ** (252 / len(eq)) - 1)
    except Exception:
        return 0.0


def _max_dd(eq: pd.Series) -> float:
    try:
        roll_max = eq.cummax()
        dd = (roll_max - eq) / roll_max
        return float(dd.max())
    except Exception:
        return 0.0


def backtest(
    signal: pd.Series,
    close: pd.Series,
    spy_close: pd.Series,
    slippage: float = 0.0005,
    tplus1: bool = True,
) -> dict:
    """
    Canonical engine: T+1 @ 5bps (slippage=0.0005).

    Mirrors evolve_real.backtest core mechanics: T+1 position, turnover cost,
    equity curve, Sharpe/CAGR/DD, excess vs SPY. Simplified — DSR/perm screens
    are in evolve_real.stat_screens (evolve-specific); this engine provides
    pure P&L correctness for gate vs paper parity.
    """
    try:
        pos = signal.shift(1).fillna(0.0) if tplus1 else signal.fillna(0.0)
        strat = close.pct_change().fillna(0.0) * pos
        turnover = pos.diff().abs().fillna(pos.abs())
        net = strat - turnover * slippage
        eq = (1 + net).cumprod()
        n = len(net)
        spy = spy_close.pct_change().fillna(0.0).reindex(net.index).fillna(0.0)
        excess = float((1 + net).prod() - (1 + spy).prod()) * 100 if n else 0.0
        out = {
            "sharpe": float(_safe_sharpe(net)),
            "cagr": _cagr(eq),
            "max_dd": _max_dd(eq),
            "trades": int((turnover > 0).sum()),
            "excess": round(excess, 2),
            "n_bars": n,
        }
        return out
    except Exception:
        return {"sharpe": 0.0, "cagr": 0.0, "max_dd": 0.0, "trades": 0, "excess": 0.0, "n_bars": 0}
