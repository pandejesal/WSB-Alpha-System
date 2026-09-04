"""NextTrade backtester port (Python / pandas, Alpaca-only, paper-only).

Source: NextTrade app/src/models/backtester/index.ts +
  portfolio/* + statistics/index.ts + brokerage/BacktestBrokerage.ts

Ported semantics:
  - Baseline asset SPY buy-and-hold (NextTrade hardcodes `new Stock("SPY")`).
  - Statistics: percentChange / totalChange / averageChange / sharpe /
    sortino / maxDrawdown. Sharpe/Sortino computed with WSB safe helpers
    (src.backtest.metrics) — NextTrade's raw formula divides by sd of
    levels which explodes; safe version guards near-zero std.
  - BacktestBrokerage cache idea: caller passes one prices frame; no network.

Safety deltas (WSB mandate, user: Alpaca only, beat SPY, paper only):
  - T+1 execution (signal.shift(1)) + slippage_bps deduction per trade-day.
  - Long/flat single-symbol composable strategies only. No short, no
    options/debit-spreads, no leverage, no live orders.
  - Buying-power guard: target notional capped at min(allocation, buying
    power); insufficient funds => stay flat (fail-closed).
  - SPY baseline over the SAME window is always reported; verdict needs
    excess return AND gate metrics, never raw return alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from src.backtest.metrics import safe_sharpe, safe_sortino
from src.signals.nexttrade_conditions import (
    AbstractCondition,
    ConditionContext,
    _ohlc_col,
    create,
)


@dataclass
class BacktestConfig:
    symbol: str = "SPY"
    initial_value: float = 100000.0
    allocation: float = 3000.0  # dollars per entry (NextTrade README: $3000 SPY)
    slippage_bps: float = 5.0
    t_plus_1: bool = True


def _normalize_spy_csv(path: str) -> pd.DataFrame:
    """Load data/spy_ohlcv_2019_2026.csv (yfinance MultiIndex-flattened)."""
    df = pd.read_csv(path)
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    # columns like "('Close', 'SPY')" -> SPY_close
    rename = {}
    for c in df.columns:
        s = str(c).replace("(", "").replace(")", "").replace("'", "").replace('"', "")
        parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
        if len(parts) >= 2:
            rename[c] = f"{parts[1]}_{parts[0]}".lower()  # spy_close
        else:
            rename[c] = s.lower()
    df = df.rename(columns=rename)
    return df


def load_prices(symbol: str, root: str = ".") -> pd.DataFrame:
    """Load OHLC frame for symbol: ohlcv/<SYM>.csv preferred, SPY csv fallback."""
    import os

    for cand in (f"{root}/market_data_2019_2026/ohlcv/{symbol}.csv",
                 f"{root}/market_data_2019_2026/ohlcv/{symbol.upper()}.csv"):
        if os.path.exists(cand):
            df = pd.read_csv(cand, parse_dates=["date"])
            df = df.set_index("date").sort_index()
            df.columns = [c.lower() for c in df.columns]
            # normalize to <sym>_<field>
            out = pd.DataFrame(index=df.index)
            for col in ("open", "high", "low", "close", "volume"):
                if col in df.columns:
                    out[f"{symbol.lower()}_{col}"] = df[col].astype(float)
            if f"{symbol.lower()}_close" in out.columns:
                return out
    if symbol.upper() == "SPY":
        return _normalize_spy_csv(f"{root}/data/spy_ohlcv_2019_2026.csv")
    raise FileNotFoundError(f"no price data for {symbol}")


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, np.nan)
    return float(-dd.min()) if len(dd) else 0.0


def run_composable_backtest(
    entry: AbstractCondition,
    prices: pd.DataFrame,
    cfg: BacktestConfig,
    exit_cond: Optional[AbstractCondition] = None,
) -> Dict[str, Any]:
    """Vectorized long/flat backtest of a condition tree.

    Position mirrors the entry signal each bar (NextTrade re-evaluates the
    condition tree every step). Execution T+1 via shift. Costs:
    slippage_bps on traded fraction. Allocation scales exposure to
    min(allocation, initial)/initial — fail-closed, never levered.
    """
    close = _ohlc_col(prices, cfg.symbol, "close")
    ctx = ConditionContext(symbol=cfg.symbol, price=float(close.iloc[-1]),
                           buying_power=cfg.initial_value,
                           portfolio_value=cfg.initial_value,
                           initial_value=cfg.initial_value)
    entry_sig = entry.evaluate(prices, ctx).fillna(False).astype(bool)
    if exit_cond is not None:
        exit_sig = exit_cond.evaluate(prices, ctx).fillna(False).astype(bool)
    else:
        exit_sig = pd.Series(False, index=prices.index)

    # Position mirrors the entry signal each bar (NextTrade re-evaluates the
    # condition tree every step; when false with no exit rule the system is
    # flat). An explicit exit_cond forces flat while true.
    pos = (entry_sig & ~exit_sig).astype(float)
    if cfg.t_plus_1:
        pos = pos.shift(1).fillna(0.0)

    frac = min(cfg.allocation, cfg.initial_value) / cfg.initial_value
    strat_ret = close.pct_change().fillna(0.0) * pos * frac
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * (cfg.slippage_bps / 10000.0) * frac
    net_ret = strat_ret - cost
    equity = cfg.initial_value * (1 + net_ret).cumprod()

    buy_hold = cfg.initial_value * (close / close.iloc[0])
    n_trades = int((turnover > 0).sum())

    stats = {
        "symbol": cfg.symbol,
        "bars": len(prices),
        "trades": n_trades,
        "final_value": float(equity.iloc[-1]),
        "total_change": float(equity.iloc[-1] - cfg.initial_value),
        "percent_change": float((equity.iloc[-1] / cfg.initial_value - 1) * 100),
        "average_change": float((equity.iloc[-1] - cfg.initial_value) / max(len(prices), 1)),
        "sharpe": float(safe_sharpe(net_ret)),
        "sortino": float(safe_sortino(net_ret)),
        "max_drawdown": float(max_drawdown(equity)),
        "spy_final": float(buy_hold.iloc[-1]),
        "spy_percent": float((buy_hold.iloc[-1] / cfg.initial_value - 1) * 100),
        "excess_percent": float((equity.iloc[-1] - buy_hold.iloc[-1]) / cfg.initial_value * 100),
    }
    detail = pd.DataFrame({"close": close, "position": pos,
                           "equity": equity, "buy_hold": buy_hold})
    return {"stats": stats, "detail": detail}


def spec_backtest(spec: Dict[str, Any], prices: pd.DataFrame,
                  cfg: BacktestConfig) -> Dict[str, Any]:
    entry = create(spec["entry"])
    exit_c = create(spec["exit"]) if spec.get("exit") else None
    return run_composable_backtest(entry, prices, cfg, exit_c)
