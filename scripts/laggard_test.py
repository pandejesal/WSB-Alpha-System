"""Laggard falsification test (pre-registered in the grilling design tree).

Criterion (claim dies if it fails): the production-claim config
  rsi_mode=neutral, min_conf=5, holding=20, stop=0, direction=long_only, gate=F
run on the 10 laggard tickers (INTC PFE KO BA T CSCO VZ MRK GE IBM) must show
median trade excess_return > 0 over the 2024-2026 out-of-sample window.

If laggards also beat SPY, the improved-config edge is NOT universe-survivorship
driven; if they fail, the honest claim collapses (edge was just mega-cap luck).
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.improve_strategy_v2 import (
    gen_signals, prepare_frames, run_portfolio_sim,
)

LAGGARDS = ["INTC", "PFE", "KO", "BA", "T", "CSCO", "VZ", "MRK", "GE", "IBM"]

CFG = {"rsi_mode": "neutral", "min_conf": 5, "holding": 20,
       "stop": 0.0, "direction": "long_only", "spy_gate": False}

OOS_START = "2024-01-01"
OOS_END = "2027-01-01"

def load_laggard_data():
    """Load laggard CSVs + SPY benchmark, same loader contract as the harness."""
    import scripts.improve_strategy_v2 as m

    orig_universe = m.UNIVERSE
    m.UNIVERSE = LAGGARDS
    stock_dfs, spy_close = m.load_local_data()
    m.UNIVERSE = orig_universe
    return stock_dfs, spy_close

def per_year_median_excess(trades):
    """Median trade excess_return by entry calendar year."""
    if not trades:
        return {}
    df = pd.DataFrame(trades)
    df["year"] = pd.to_datetime(df["entry_date"]).dt.year
    return df.groupby("year")["excess_return"].median().to_dict()

if __name__ == "__main__":
    stock_dfs, spy_close = load_laggard_data()
    print(f"Laggard frames: {len(stock_dfs)} tickers")
    for t in LAGGARDS:
        if t not in stock_dfs:
            print(f"  MISSING: {t}")

    frames, spy_trend = prepare_frames(stock_dfs, spy_close)
    print(f"Frames ready (SMA200 filtered): {len(frames)}")

    signals = gen_signals(frames, spy_trend, CFG["rsi_mode"], CFG["min_conf"],
                          CFG["direction"], CFG["spy_gate"])
    print(f"Signals generated: {len(signals)}")

    trades, port_rets = run_portfolio_sim(frames, spy_close, signals,
                                          CFG["holding"], CFG["stop"])

    df = pd.DataFrame(trades)
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    oos = df[(df["entry_date"] >= OOS_START) & (df["entry_date"] < OOS_END)]

    print("=" * 70)
    print("LAGGARD FALSIFICATION TEST — config: neutral/conf5/hold20/stop0/long/gate=F")
    print("=" * 70)
    print(f"Total trades: {len(df)} (OOS {OOS_START[:4]}-{OOS_END[:4]}: {len(oos)})")
    print(f"Universe median excess (full): {df['excess_return'].median():+.4f}")
    print(f"OOS median excess (2024-2026): {oos['excess_return'].median():+.4f}  <- CRITERION")
    print(f"OOS mean excess:   {oos['excess_return'].mean():+.4f}")
    print(f"OOS win rate (excess>0): {(oos['excess_return'] > 0).mean():.1%}")
    print()
    print("Per-year median excess (OOS years):")
    pym = per_year_median_excess(oos.to_dict("records"))
    for yr in sorted(pym):
        print(f"  {yr}: {pym[yr]:+.4f}  ({'PASS' if pym[yr] > 0 else 'FAIL'})")
    print()
    print("Trades per laggard (all-time):")
    print(df.groupby("ticker")["return"].agg(["count", "mean"]).round(4).to_string())
    print()
    verdict = "PASS — edge survives on laggards" if oos["excess_return"].median() > 0 else "FAIL — claim dies: edge is survivorship/mega-cap luck"
    print(f"VERDICT: {verdict}")

    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/laggard_test.json", "w") as f:
        json.dump({
            "config": CFG, "universe": LAGGARDS,
            "n_trades": int(len(df)), "n_oos": int(len(oos)),
            "median_excess_full": float(df["excess_return"].median()),
            "median_excess_oos": float(oos["excess_return"].median()),
            "mean_excess_oos": float(oos["excess_return"].mean()),
            "oos_win_rate": float((oos["excess_return"] > 0).mean()),
            "per_year_median": pym,
            "verdict": "PASS" if oos["excess_return"].median() > 0 else "FAIL",
        }, f, indent=2)
    print("\nSaved docs/data/laggard_test.json")
