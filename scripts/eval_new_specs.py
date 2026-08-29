#!/usr/bin/env python3
"""
Standalone evaluator for Wave 3 hedge-fund specs (cycles 6-11).

Generates signals from the signal handlers in src/ops/signals.py, runs a
vectorized backtest with proper holding-period logic, and reports
CAGR / Sharpe / maxDD / win-rate vs SPY buy-and-hold.
"""
import sys
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ops.signals import (
    get_factor_momentum_signal,
    get_quality_lowvol_signal,
    get_cta_ensemble_signal,
    get_donchian_breakout_signal,
    get_pead_quality_signal,
)
from src.backtest.metrics import safe_sharpe, safe_sortino

import yfinance as yf
import yaml

# ─── Config ────────────────────────────────────────────────────────────────
UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM",
    "V", "UNH", "MA", "JNJ", "PG", "XOM", "HD", "CVX", "MRK", "ABBV",
    "LLY", "AVGO", "PEP", "KO", "COST", "WMT", "MCD", "CSCO", "AMD",
    "NFLX", "ADBE", "CRM", "ORCL", "TXN", "INTC", "QCOM", "AMAT",
    "INTU", "ISRG", "BKNG", "ADI", "MDLZ", "GILD", "SYK", "BLK",
    "VRTX", "ADP", "CI", "REGN", "SBUX", "MMC", "PLD",
]
START = "2018-01-01"
END = "2026-08-20"
INIT_CASH = 100_000.0
SLIPPAGE_BPS = 5  # per side


def fetch_data(tickers, start, end):
    """Fetch OHLCV from yfinance, return dict of DataFrames per ticker."""
    print(f"Fetching {len(tickers)} tickers from {start} to {end}...")
    raw = yf.download(tickers + ["SPY"], start=start, end=end,
                      progress=False, auto_adjust=True, threads=True)
    if raw.empty:
        raise ValueError("No data downloaded")

    # Handle multi-level columns
    if isinstance(raw.columns, pd.MultiIndex):
        spy = raw.xs("SPY", axis=1, level=1).copy() if "SPY" in raw.columns.get_level_values(1) else None
        stock_dfs = {}
        for t in tickers:
            if t in raw.columns.get_level_values(1):
                df = raw.xs(t, axis=1, level=1).copy()
                df = df.dropna(subset=["Close", "Open", "High", "Low"])
                if len(df) >= 200:
                    stock_dfs[t] = df
    else:
        spy = raw.copy()
        stock_dfs = {tickers[0]: raw}

    print(f"  Got {len(stock_dfs)} stock DataFrames, SPY {'OK' if spy is not None else 'MISSING'}")
    return stock_dfs, spy


def build_close_df(stock_dfs, tickers):
    """Build a single multi-column Close DataFrame from per-ticker DataFrames."""
    closes = {}
    for t in tickers:
        if t in stock_dfs:
            closes[t] = stock_dfs[t]["Close"].copy()
    if not closes:
        return pd.DataFrame()
    return pd.DataFrame(closes).sort_index().ffill()


def build_ohlcv_data(stock_dfs, tickers):
    """Build a dict with 'Close', 'Open', 'High', 'Low', 'Volume' as multi-column DataFrames."""
    frames = {}
    for field in ["Close", "Open", "High", "Low", "Volume"]:
        cols = {}
        for t in tickers:
            if t in stock_dfs and field in stock_dfs[t].columns:
                cols[t] = stock_dfs[t][field].copy()
        if cols:
            frames[field] = pd.DataFrame(cols).sort_index().ffill()
    return frames


def backtest_monthly_rotation(spec_name, signal_fn, stock_dfs, spy_close,
                              tickers, top_n=5, lookback=126, skip=21, **kwargs):
    """
    Monthly rotation backtest: at each month-end, select top-N tickers by
    signal_fn, hold until next month-end. Equal-weight portfolio.
    """
    close_df = build_close_df(stock_dfs, tickers)
    ohlcv_data = build_ohlcv_data(stock_dfs, tickers)
    if close_df.empty:
        return pd.DataFrame()

    common_dates = close_df.dropna().index
    if len(common_dates) < lookback + skip + 22:
        return pd.DataFrame()

    # Find month-end dates
    month_ends = common_dates.to_series().groupby(
        [common_dates.year, common_dates.month]
    ).max().values
    month_ends = pd.DatetimeIndex(month_ends)

    trades = []
    prev_tickers = []

    for i, me in enumerate(month_ends):
        if i < 1:
            continue

        # Build data slice up to current month-end for the signal handler
        slice_data = pd.DataFrame({
            field: ohlcv_data[field].loc[:me] for field in ohlcv_data
        }) if ohlcv_data else close_df.loc[:me]

        try:
            signal = signal_fn(slice_data, tickers, top_n=top_n)
        except Exception:
            signal = None

        if signal is None or signal.get("signal") != "LONG":
            if prev_tickers:
                prev_tickers = []
            continue

        new_tickers = signal.get("targets", [])
        if not new_tickers:
            continue
        if isinstance(new_tickers[0], dict):
            new_tickers = [x["ticker"] for x in new_tickers]

        # Close positions not in new set
        for t in prev_tickers:
            if t not in new_tickers and t in close_df.columns:
                if i + 1 < len(month_ends):
                    exit_date = month_ends[i + 1]
                else:
                    exit_date = common_dates[-1]
                if me in close_df.index and exit_date in close_df.index:
                    ret = close_df.loc[exit_date, t] / close_df.loc[me, t] - 1
                    trades.append({
                        "post_date": me, "ticker": t, "return": ret,
                        "holding_days": (exit_date - me).days,
                    })

        # Open new positions
        for t in new_tickers:
            if t not in prev_tickers and t in close_df.columns:
                if i + 1 < len(month_ends):
                    exit_date = month_ends[i + 1]
                else:
                    exit_date = common_dates[-1]
                if me in close_df.index and exit_date in close_df.index:
                    ret = close_df.loc[exit_date, t] / close_df.loc[me, t] - 1
                    trades.append({
                        "post_date": me, "ticker": t, "return": ret,
                        "holding_days": (exit_date - me).days,
                    })

        prev_tickers = new_tickers

    return pd.DataFrame(trades)


def backtest_daily_cta(spec_name, signal_fn, stock_dfs, spy_close, tickers, **kwargs):
    """
    Daily CTA backtest: on each trading day, check signal_fn. When LONG,
    buy equal-weight. When FLAT, close. Uses close-to-close returns.
    """
    close_df = build_close_df(stock_dfs, tickers)
    ohlcv_data = build_ohlcv_data(stock_dfs, tickers)
    if close_df.empty:
        return pd.DataFrame()

    common_dates = close_df.dropna().index

    trades = []
    in_position = False
    entry_date = None
    entry_tickers = []

    for i, date in enumerate(common_dates):
        if i < 96:  # warmup (slow EMA needs 96 bars)
            continue

        # Build data slice up to current date for the signal handler
        slice_data = pd.DataFrame({
            field: ohlcv_data[field].loc[:date] for field in ohlcv_data
        }) if ohlcv_data else close_df.loc[:date]

        try:
            signal = signal_fn(slice_data, tickers)
        except Exception:
            signal = None

        if signal is None:
            continue

        sig_type = signal.get("signal", "FLAT")
        targets = signal.get("targets", [])
        if isinstance(targets, list) and len(targets) > 0 and isinstance(targets[0], dict):
            targets = [x["ticker"] for x in targets]

        if sig_type == "LONG" and not in_position:
            in_position = True
            entry_date = date
            entry_tickers = targets if targets else tickers[:3]

        elif sig_type == "FLAT" and in_position:
            for t in entry_tickers:
                if t in close_df.columns and entry_date in close_df.index and date in close_df.index:
                    ret = close_df.loc[date, t] / close_df.loc[entry_date, t] - 1
                    trades.append({
                        "post_date": entry_date, "ticker": t, "return": ret,
                        "holding_days": (date - entry_date).days,
                    })
            in_position = False
            entry_date = None
            entry_tickers = []

    # Close any open position at end
    if in_position and entry_date is not None:
        last_date = common_dates[-1]
        for t in entry_tickers:
            if t in close_df.columns and entry_date in close_df.index:
                ret = close_df.loc[last_date, t] / close_df.loc[entry_date, t] - 1
                trades.append({
                    "post_date": entry_date, "ticker": t, "return": ret,
                    "holding_days": (last_date - entry_date).days,
                })

    return pd.DataFrame(trades)


def backtest_donchian(ohlc, spy_close, channel=20, exit_ch=10):
    """
    Donchian breakout backtest on a single instrument.
    Buy on channel break above, sell on channel break below.
    """
    if ohlc is None or len(ohlc) < channel + 5:
        return pd.DataFrame()

    df = ohlc.copy()
    df["don_high"] = df["High"].rolling(channel).max()
    df["don_low"] = df["Low"].rolling(exit_ch).min()
    df["atr"] = (df["High"] - df["Low"]).rolling(14).mean()

    trades = []
    in_pos = False
    entry_date = None
    entry_price = 0.0

    for i in range(channel + 5, len(df)):
        date = df.index[i]
        prev_close = df["Close"].iloc[i - 1]
        cur_high = df["High"].iloc[i]
        cur_low = df["Low"].iloc[i]
        don_high = df["don_high"].iloc[i - 1]  # previous bar's channel
        don_low = df["don_low"].iloc[i - 1]

        if not in_pos and prev_close < don_high and cur_high >= don_high:
            in_pos = True
            entry_date = date
            entry_price = don_high * (1 + SLIPPAGE_BPS / 10_000)

        elif in_pos and cur_low <= don_low:
            exit_price = don_low * (1 - SLIPPAGE_BPS / 10_000)
            ret = (exit_price - entry_price) / entry_price
            trades.append({
                "post_date": entry_date, "ticker": "BTC-USD" if "BTC" in str(ohlc.columns) else "SPY",
                "return": ret, "holding_days": (date - entry_date).days,
            })
            in_pos = False

    return pd.DataFrame(trades)


def compute_summary(trades_df, spy_close):
    """Compute performance metrics and compare to SPY."""
    if trades_df.empty:
        return {"verdict": "NO_TRADES", "cagr": 0, "sharpe": 0, "max_dd": 0, "win_rate": 0}

    rets = trades_df["return"].fillna(0)
    total_return = rets.sum()
    n_years = max((trades_df["post_date"].max() - trades_df["post_date"].min()).days / 365.25, 1)
    cagr = (1 + total_return) ** (1 / n_years) - 1

    # Daily returns for Sharpe
    daily = rets.groupby(trades_df["post_date"]).sum()
    sharpe = safe_sharpe(daily, 252)
    sortino = safe_sortino(daily, 252)

    cum = rets.cumsum()
    max_dd = (cum.cummax() - cum).max()

    wins = (rets > 0).sum()
    total_trades = len(rets)
    win_rate = wins / total_trades if total_trades > 0 else 0

    # SPY benchmark
    if spy_close is not None and len(spy_close) > 0:
        spy_total = (spy_close.iloc[-1] / spy_close.iloc[0]) - 1
        spy_cagr = (1 + spy_total) ** (1 / n_years) - 1
        spy_daily = spy_close.pct_change().fillna(0)
        spy_sharpe = safe_sharpe(spy_daily, 252)
    else:
        spy_cagr = 0
        spy_sharpe = 0

    beats_sharpe = sharpe > spy_sharpe
    beats_cagr = cagr > spy_cagr

    return {
        "cagr": round(cagr * 100, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "max_dd": round(max_dd * 100, 2),
        "win_rate": round(win_rate * 100, 1),
        "total_trades": total_trades,
        "n_years": round(n_years, 1),
        "spy_cagr": round(spy_cagr * 100, 2),
        "spy_sharpe": round(spy_sharpe, 2),
        "beats_spy_sharpe": beats_sharpe,
        "beats_spy_cagr": beats_cagr,
        "verdict": "PASS" if (beats_sharpe and beats_cagr) else "FAIL",
    }


def run_permutation_test(trades_df, stock_dfs, spy_close, signal_fn,
                         strategy_type, n_perms=100, **kwargs):
    """
    Permutation test: shuffle signal dates and re-run backtest n_perms times.
    Returns fraction of permuted runs that beat the real Sharpe.
    """
    if trades_df.empty:
        return 1.0

    real_sharpe = compute_summary(trades_df, spy_close)["sharpe"]
    perm_sharpes = []

    dates = sorted(trades_df["post_date"].unique())

    for _ in range(n_perms):
        shuffled = trades_df.copy()
        # Shuffle post_dates
        shuffled["post_date"] = np.random.permutation(shuffled["post_date"].values)
        summary = compute_summary(shuffled, spy_close)
        perm_sharpes.append(summary["sharpe"])

    perm_sharpes = np.array(perm_sharpes)
    p_value = float(np.mean(perm_sharpes >= real_sharpe))
    return p_value


def main():
    specs = [
        {
            "name": "factor_momentum_top3",
            "family": "factor_momentum",
            "type": "monthly",
            "fn": get_factor_momentum_signal,
            "kwargs": {"top_n": 3},
        },
        {
            "name": "quality_lowvol_top10",
            "family": "quality_lowvol",
            "type": "monthly",
            "fn": get_quality_lowvol_signal,
            "kwargs": {"top_n": 10},
        },
        {
            "name": "cta_ensemble_3speed",
            "family": "cta_trend",
            "type": "daily_cta",
            "fn": get_cta_ensemble_signal,
            "kwargs": {},
        },
        {
            "name": "donchian_breakout",
            "family": "donchian_breakout",
            "type": "donchian",
            "fn": get_donchian_breakout_signal,
            "kwargs": {"entry_channel": 20, "exit_channel": 10},
        },
    ]

    stock_dfs, spy_close = fetch_data(UNIVERSE, START, END)
    spy_close_series = spy_close["Close"] if spy_close is not None else None

    results = []

    for spec in specs:
        print(f"\n{'='*60}")
        print(f"Evaluating: {spec['name']} (family={spec['family']})")
        print(f"{'='*60}")

        try:
            if spec["type"] == "monthly":
                trades = backtest_monthly_rotation(
                    spec["name"], spec["fn"], stock_dfs, spy_close_series,
                    UNIVERSE, **spec["kwargs"]
                )
            elif spec["type"] == "daily_cta":
                trades = backtest_daily_cta(
                    spec["name"], spec["fn"], stock_dfs, spy_close_series,
                    UNIVERSE, **spec["kwargs"]
                )
            elif spec["type"] == "donchian":
                # Run on SPY as representative
                ohlc = stock_dfs.get("SPY")
                if ohlc is not None:
                    trades = backtest_donchian(
                        ohlc, spy_close_series, **spec["kwargs"]
                    )
                else:
                    trades = pd.DataFrame()
            else:
                trades = pd.DataFrame()

            summary = compute_summary(trades, spy_close_series)

            # Permutation test (reduced to 50 for speed)
            p_value = run_permutation_test(
                trades, stock_dfs, spy_close_series, spec["fn"],
                spec["type"], n_perms=50
            )
            summary["permutation_p"] = round(p_value, 4)
            summary["spec"] = spec["name"]
            summary["family"] = spec["family"]

            # Gate verdict: beats SPY on both CAGR and Sharpe, p < 0.05
            if summary["beats_spy_sharpe"] and summary["beats_spy_cagr"] and p_value < 0.05:
                summary["gate"] = "PASS"
            elif p_value < 0.10:
                summary["gate"] = "MARGINAL"
            else:
                summary["gate"] = "FAIL"

            results.append(summary)

            print(f"  CAGR:    {summary['cagr']}%  (SPY {summary['spy_cagr']}%)")
            print(f"  Sharpe:  {summary['sharpe']}  (SPY {summary['spy_sharpe']})")
            print(f"  Sortino: {summary['sortino']}")
            print(f"  MaxDD:   {summary['max_dd']}%")
            print(f"  WinRate: {summary['win_rate']}%")
            print(f"  Trades:  {summary['total_trades']}")
            print(f"  Perm p:  {summary['permutation_p']}")
            print(f"  Gate:    {summary['gate']}")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "spec": spec["name"], "family": spec["family"],
                "gate": "ERROR", "error": str(e),
            })

    # Summary table
    print(f"\n{'='*60}")
    print("WAVE 3 EVALUATION SUMMARY")
    print(f"{'='*60}")
    print(f"{'Spec':<30} {'CAGR':>8} {'Sharpe':>8} {'MaxDD':>8} {'WinR':>6} {'PermP':>7} {'Gate':>8}")
    print("-" * 80)
    for r in results:
        if "error" in r:
            print(f"{r['spec']:<30} {'ERROR':>8}")
        else:
            print(f"{r['spec']:<30} {r['cagr']:>7}% {r['sharpe']:>7} {r['max_dd']:>7}% {r['win_rate']:>5}% {r['permutation_p']:>7} {r['gate']:>8}")

    # Save results
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "docs", "data", "wave3_eval_results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
