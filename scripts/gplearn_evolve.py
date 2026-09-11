#!/usr/bin/env python3
"""gplearn evolve -> export -> backtest on local SPY data (paper only).

Usage:
  python scripts/gplearn_evolve.py --symbol SPY --generations 5 --population 100
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.backtest.nexttrade_backtest import load_prices  # noqa: E402
from src.signals.gplearn_factors import EvolveConfig, evolve  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="SPY")
    ap.add_argument("--generations", type=int, default=5)
    ap.add_argument("--population", type=int, default=100)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    prices = load_prices(args.symbol, root=str(ROOT))
    close_col = [c for c in prices.columns if "close" in c][0]
    bars = pd.DataFrame(index=prices.index)
    bars["close"] = prices[close_col].astype(float).values
    for f in ("high", "low"):
        col = [c for c in prices.columns if f in c]
        if col:
            bars[f] = prices[col[0]].astype(float).values
    vol = [c for c in prices.columns if "volume" in c or "vol" in c]
    if vol:
        bars["volume"] = prices[vol[0]].astype(float).values

    cfg = EvolveConfig(population_size=args.population, generations=args.generations,
                       random_state=args.seed)
    out = evolve(bars, cfg)
    close = bars["close"].astype(float)
    spy_ret = float(close.iloc[-1] / close.iloc[0] - 1) * 100
    out.update({"symbol": args.symbol, "spy_buyhold_pct": spy_ret,
                "excess_pct": out["oos_return_pct"] - spy_ret * (out["val_rows"] / len(bars)),
                "status": "paper", "live": False})
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
