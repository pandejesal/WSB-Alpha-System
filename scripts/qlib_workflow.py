#!/usr/bin/env python3
"""qlib_workflow.py — CLI end-to-end: features -> scores -> rotation -> metrics.

Usage:
    python scripts/qlib_workflow.py [--tickers AAPL,MSFT,GOOGL] [--top-k 5] [--rebalance 5]

Paper only. Local CSVs only. No network calls.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.signals.qlib_alpha158 import compute_alpha158, get_feature_names
from src.backtest.qlib_topk import (
    compute_metrics,
    load_universe,
    spy_buyhold,
    topk_rotation,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="qlib workflow: Alpha158 features -> TopkDropout rotation -> metrics"
    )
    parser.add_argument(
        "--data-dir",
        default="market_data_2019_2026/ohlcv",
        help="Directory with OHLCV CSV files",
    )
    parser.add_argument(
        "--spy",
        default="data/spy_ohlcv_2019_2026.csv",
        help="Path to SPY buy-hold baseline CSV",
    )
    parser.add_argument(
        "--tickers",
        default=None,
        help="Comma-separated tickers to use (default: all in data dir)",
    )
    parser.add_argument(
        "--top-k", type=int, default=5,
        help="Number of stocks to hold (default: 5)",
    )
    parser.add_argument(
        "--rebalance", type=int, default=5,
        help="Rebalance frequency in days (default: 5)",
    )
    parser.add_argument(
        "--min-hold", type=int, default=5,
        help="Minimum hold days before dropout (default: 5)",
    )
    parser.add_argument(
        "--score-window", type=int, default=20,
        help="Lookback window for scoring (default: 20)",
    )
    parser.add_argument(
        "--dropout-threshold", type=float, default=-1.0,
        help="Z-score threshold for forced dropout (default: -1.0)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Step 1: Load universe
    tickers = args.tickers.split(",") if args.tickers else None
    print(f"[qlib_workflow] Loading universe from {args.data_dir} ...")
    universe = load_universe(args.data_dir, tickers)
    if not universe:
        print("ERROR: No tickers loaded. Check data dir.", file=sys.stderr)
        sys.exit(1)
    print(f"[qlib_workflow] Loaded {len(universe)} tickers")

    # Step 2: Compute Alpha158 features (demonstrated on SPY)
    print("[qlib_workflow] Computing Alpha158 features on SPY ...")
    spy_path = args.spy
    spy_df = pd.read_csv(spy_path)
    spy_df["date"] = pd.to_datetime(spy_df.iloc[:, 0])
    if "close" not in spy_df.columns:
        close_col = [c for c in spy_df.columns if "Close" in str(c)]
        if close_col:
            spy_df["close"] = spy_df[close_col[0]]
        spy_df["high"] = spy_df.get("high", spy_df.get("High", pd.Series()))
        spy_df["low"] = spy_df.get("low", spy_df.get("Low", pd.Series()))
        spy_df["open"] = spy_df.get("open", spy_df.get("Open", pd.Series()))
        spy_df["volume"] = spy_df.get("volume", spy_df.get("Volume", pd.Series()))

    compute_alpha158(spy_df)
    feature_names = get_feature_names()
    print(f"[qlib_workflow] Computed {len(feature_names)} Alpha158 features")

    # Step 3: Run TopkDropout rotation
    print(f"[qlib_workflow] Running TopkDropout (k={args.top_k}, rebal={args.rebalance}d) ...")
    result = topk_rotation(
        universe,
        top_k=args.top_k,
        rebalance_freq=args.rebalance,
        min_hold_days=args.min_hold,
        dropout_threshold=args.dropout_threshold,
        score_window=args.score_window,
        lookback=60,
    )
    strat_metrics = compute_metrics(result)

    # Step 4: SPY buy-hold baseline
    print("[qlib_workflow] Computing SPY buy-hold baseline ...")
    spy_bh = spy_buyhold(spy_path)
    spy_rets = spy_bh["spy_return"]
    spy_eq = spy_bh["spy_equity"]

    spy_std = spy_rets.std()
    spy_sharpe = (spy_rets.mean() / spy_std * np.sqrt(252)) if spy_std > 1e-12 else 0.0
    spy_running_max = spy_eq.cummax()
    spy_dd = (spy_eq - spy_running_max) / spy_running_max
    spy_max_dd = float(spy_dd.min())
    spy_total = float(spy_eq.iloc[-1] / spy_eq.iloc[0] - 1)
    n_years = len(spy_rets) / 252
    spy_cagr = ((1 + spy_total) ** (1 / n_years) - 1) if n_years > 0 else 0.0
    spy_metrics = {
        "sharpe": float(spy_sharpe),
        "max_drawdown": spy_max_dd,
        "total_return": spy_total,
        "cagr": spy_cagr,
    }

    # Step 5: Print results
    print("\n" + "=" * 60)
    print("  qlib Alpha158 + TopkDropout — RESULTS")
    print("=" * 60)
    print(f"\n{'Metric':<25} {'Strategy':>12} {'SPY B&H':>12} {'Excess':>12}")
    print("-" * 61)
    for m in ["sharpe", "max_drawdown", "total_return", "cagr"]:
        sv = strat_metrics[m]
        bv = spy_metrics[m]
        excess = sv - bv if m != "max_drawdown" else sv - bv
        print(f"{m:<25} {sv:>12.4f} {bv:>12.4f} {excess:>+12.4f}")
    print(f"{'turnover':<25} {strat_metrics['turnover']:>12.4f}")
    print(f"\nFeatures used: {len(feature_names)}")
    print(f"Universe size: {len(universe)} tickers")
    print(f"Top-k held: {args.top_k}")
    print(f"Rebalance freq: {args.rebalance} days")
    print("=" * 60)

    if strat_metrics["sharpe"] < spy_metrics["sharpe"]:
        print("\nNOTE: Strategy trails SPY buy-hold on Sharpe. "
              "This is a paper-only port for research purposes.")
    else:
        print("\nNOTE: Strategy outperforms SPY buy-hold on Sharpe.")


if __name__ == "__main__":
    main()
