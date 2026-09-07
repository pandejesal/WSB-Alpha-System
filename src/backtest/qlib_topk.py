"""qlib TopkDropout long-only rotation backtester.

Ported from microsoft/qlib TopkDropout strategy. This is a long-only
rotation strategy: at each rebalance, rank stocks by a composite score
(z-momentum + vol filter), hold top-k, drop names that fall below a
dropout threshold. No shorts, no leverage, no crypto, no options.

Paper only - no live order placement.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd


def load_ohlcv(path: str) -> pd.DataFrame:
    """Load a single OHLCV CSV."""
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


def load_universe(data_dir: str, tickers: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Load all OHLCV CSVs from a directory into {ticker: DataFrame}."""
    import glob as _glob

    files = _glob.glob(os.path.join(data_dir, "*.csv"))
    universe: dict[str, pd.DataFrame] = {}
    for f in files:
        base = os.path.splitext(os.path.basename(f))[0]
        if base.startswith("^") or base == "missing":
            continue
        if tickers and base not in tickers:
            continue
        try:
            universe[base] = load_ohlcv(f)
        except Exception:
            continue
    return universe


def composite_score(mom: pd.Series, vol: pd.Series,
                    mom_weight: float = 1.0,
                    vol_penalty: float = 0.5) -> pd.Series:
    """Score = mom_weight * z(mom) - vol_penalty * z(vol)."""
    def _z(s: pd.Series) -> pd.Series:
        mu = s.mean()
        sigma = s.std()
        if sigma < 1e-12:
            return s * 0.0
        return (s - mu) / sigma
    return mom_weight * _z(mom) - vol_penalty * _z(vol)


def topk_rotation(
    universe: dict[str, pd.DataFrame],
    top_k: int = 5,
    rebalance_freq: int = 5,
    min_hold_days: int = 5,
    dropout_threshold: float = -1.0,
    score_window: int = 20,
    lookback: int = 60,
    initial_capital: float = 100_000.0,
    slippage_bps: float = 5.0,
) -> pd.DataFrame:
    """Run TopkDropout long-only rotation."""
    if not universe:
        raise ValueError("Universe is empty")

    tickers = sorted(universe.keys())

    def _ensure_dt_index(df: pd.DataFrame) -> pd.DataFrame:
        if "date" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
        return df

    norm_universe = {t: _ensure_dt_index(df) for t, df in universe.items()}

    all_dates = sorted(set().union(*[set(df.index) for df in norm_universe.values()]))
    all_dates = [d for d in all_dates if isinstance(d, pd.Timestamp)]

    if len(all_dates) < lookback:
        raise ValueError(f"Not enough dates ({len(all_dates)}) for lookback ({lookback})")

    returns = pd.DataFrame(index=all_dates, columns=tickers, dtype=float)
    closes = pd.DataFrame(index=all_dates, columns=tickers, dtype=float)
    for t in tickers:
        s = norm_universe[t]["close"].reindex(all_dates).ffill()
        closes[t] = s
        returns[t] = s.pct_change()

    holdings: dict[str, int] = {}
    portfolio_ret = []
    turnover_log = []
    positions_log = []
    rebalance_dates = set(all_dates[lookback::rebalance_freq])
    prev_positions: list[str] = []  # T+1: today's return comes from yesterday's holdings

    for i, date in enumerate(all_dates):
        daily_positions = list(holdings.keys())

        if date in rebalance_dates:
            valid_tickers = [t for t in tickers if t in closes.columns and
                            closes.loc[:date, t].dropna().shape[0] >= score_window]
            if valid_tickers:
                mom = {}
                vol = {}
                for t in valid_tickers:
                    ts = returns.loc[:date, t].dropna()
                    if len(ts) >= score_window:
                        mom[t] = ts.iloc[-score_window:].sum()
                        vol[t] = ts.iloc[-score_window:].std()
                    else:
                        mom[t] = 0.0
                        vol[t] = 1.0

                mom_s = pd.Series(mom)
                vol_s = pd.Series(vol)
                scores = composite_score(mom_s, vol_s)
                ranked = scores.sort_values(ascending=False)

                to_drop = []
                for t in list(holdings):
                    if t in ranked.index and ranked[t] < dropout_threshold:
                        if holdings[t] >= min_hold_days:
                            to_drop.append(t)

                for t in to_drop:
                    del holdings[t]

                candidates = [t for t in ranked.index if t not in holdings]
                for t in candidates:
                    if len(holdings) >= top_k:
                        break
                    holdings[t] = 0

                daily_positions = list(holdings.keys())

        for t in list(holdings):
            holdings[t] += 1

        # T+1 execution: earn today's return on yesterday's holdings, minus
        # 5bps per changed name (round-trip: sell + buy) as a fraction of
        # an equal-weighted book.
        if prev_positions:
            day_ret = returns.loc[date, prev_positions].mean()
            if pd.isna(day_ret):
                day_ret = 0.0
        else:
            day_ret = 0.0
        n_changed = len(set(daily_positions) ^ set(prev_positions))
        book = max(len(prev_positions), top_k, 1)
        day_ret -= n_changed * 2 * (slippage_bps / 10000.0) / book
        prev_positions = daily_positions

        portfolio_ret.append(day_ret)
        positions_log.append(daily_positions[:])
        turnover_log.append(len(set(daily_positions) - set(positions_log[-2])) if len(positions_log) > 1 else 0)

    result = pd.DataFrame({
        "portfolio_return": portfolio_ret,
        "num_positions": [len(p) for p in positions_log],
        "turnover": turnover_log,
    }, index=all_dates)
    result["equity"] = (1 + result["portfolio_return"]).cumprod() * initial_capital
    return result


def compute_metrics(result: pd.DataFrame, periods_per_year: int = 252) -> dict:
    """Compute standard portfolio metrics."""
    rets = result["portfolio_return"].dropna()
    if len(rets) < 2:
        return {"sharpe": 0.0, "max_drawdown": 0.0, "turnover": 0.0,
                "total_return": 0.0, "cagr": 0.0}

    std = rets.std()
    sharpe = (rets.mean() / std * np.sqrt(periods_per_year)) if std > 1e-12 else 0.0

    eq = (1 + rets).cumprod()
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max
    max_dd = float(drawdown.min())

    total_ret = float(eq.iloc[-1] / eq.iloc[0] - 1)
    n_years = len(rets) / periods_per_year
    cagr = ((1 + total_ret) ** (1 / n_years) - 1) if n_years > 0 else 0.0

    avg_turnover = float(result["turnover"].mean())

    return {
        "sharpe": float(sharpe),
        "max_drawdown": max_dd,
        "turnover": avg_turnover,
        "total_return": total_ret,
        "cagr": cagr,
    }


def spy_buyhold(spy_path: str, start: str | None = None,
                end: str | None = None) -> pd.DataFrame:
    """Compute SPY buy-and-hold returns as baseline."""
    df = pd.read_csv(spy_path)
    df["date"] = pd.to_datetime(df.iloc[:, 0])
    df = df.set_index("date").sort_index()
    if "close" not in df.columns:
        close_col = [c for c in df.columns if "Close" in str(c)]
        if close_col:
            df["close"] = df[close_col[0]]
        else:
            df["close"] = df.iloc[:, 0]

    if start:
        df = df[df.index >= start]
    if end:
        df = df[df.index <= end]

    df["spy_return"] = df["close"].pct_change()
    df["spy_equity"] = (1 + df["spy_return"].fillna(0)).cumprod() * 100_000
    return df[["spy_return", "spy_equity"]].dropna()
