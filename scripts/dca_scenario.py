"""DCA scenario (grilling Q5/Q12/Q19/Q29): $100 initial + $50 every 3 months,
full withdrawal at data end (2026-08-07), matched SPY DCA benchmark.

Configs (always labeled):
  A: improved honest claim  = neutral conf5 hold20 stop0 long gate=F (train-selected)
  B: production default     = neutral conf3 hold10 stop0 long gate=F (production params)
  C: SPY DCA benchmark      = same contribution schedule into SPY
  D: A + friction           = 2x slippage + 0.08% round-trip commission stress

Criterion from grilling: compare A vs C on final withdrawal value and CAGR;
bar (median>0 3-of-4 years) is NOT tested here — this answers the money question.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.improve_strategy_v2 import (
    gen_signals, load_local_data, prepare_frames, run_portfolio_sim,
)

UNIVERSE = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ", "WMT", "MA", "UNH", "XOM", "DIS"]

INITIAL = 100.0
DCA_AMOUNT = 50.0
DCA_MONTHS = 3
START_DATE = "2019-01-02"
END_DATE = "2026-08-07"

CONFIGS = {
    "A_improved_gateF": {"rsi_mode": "neutral", "min_conf": 5, "holding": 20, "stop": 0.0, "direction": "long_only", "spy_gate": False, "slippage_mult": 1.0, "commission": 0.0004},
    "B_production":     {"rsi_mode": "neutral", "min_conf": 3, "holding": 10, "stop": 0.0, "direction": "long_only", "spy_gate": False, "slippage_mult": 1.0, "commission": 0.0004},
    "D_A_stressed":     {"rsi_mode": "neutral", "min_conf": 5, "holding": 20, "stop": 0.0, "direction": "long_only", "spy_gate": False, "slippage_mult": 2.0, "commission": 0.0008},
}

def contribution_dates():
    """Jan 2019 + every 3 months -> Jul 2026 (~31 contributions)."""
    dates = [pd.Timestamp(START_DATE)]
    d = pd.Timestamp("2019-04-01")
    end = pd.Timestamp("2026-08-01")
    while d <= end:
        dates.append(d)
        d += pd.DateOffset(months=DCA_MONTHS)
    return dates

def dca_equity_curve(trades, port_rets, spy_close, contributions):
    """Runs portfolio daily returns with cash injection on contribution dates.
    Portfolio return series has weights on invested capital; a DCA investor
    adds cash at contribution dates, so invested capital grows over time.

    Approximation (honest, stated): we track an invested-capital curve and add
    contribution cash at each date; daily PnL = invested_ret * prior capital.
    """
    df = pd.DataFrame(port_rets, columns=["date", "ret"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df.groupby(df.index).sum()

    contrib = pd.DataFrame({"date": contributions})
    contrib["date"] = pd.to_datetime(contrib["date"])
    contrib = contrib.set_index("date")

    # Snap each contribution to the next available trading day (same rule as
    # the SPY DCA benchmark); otherwise holiday/weekend contributions are lost.
    trading_days = df.index
    snapped = []
    for cdt in contrib.index:
        pos = trading_days.searchsorted(cdt)
        if pos < len(trading_days):
            snapped.append(trading_days[pos])
        else:
            snapped.append(trading_days[-1])
    snapped = pd.DatetimeIndex(sorted(set(snapped)))
    contrib_snap = pd.DataFrame({"date": snapped}).set_index("date")

    capital = 0.0
    curve = []
    for dt, row in df.iterrows():
        if dt in contrib_snap.index:
            capital += INITIAL if dt == pd.Timestamp(START_DATE) else DCA_AMOUNT
        capital *= (1.0 + row["ret"])
        curve.append((dt, capital))
    eq = pd.DataFrame(curve, columns=["date", "equity"]).set_index("date")

    total_contrib = sum(INITIAL if pd.Timestamp(d) == pd.Timestamp(START_DATE) else DCA_AMOUNT for d in snapped)
    final = float(eq["equity"].iloc[-1])
    years = (eq.index.max() - eq.index.min()).days / 365.25
    cagr = (final / total_contrib) ** (1 / years) - 1 if final > 0 else -1
    dd = (eq["equity"] / eq["equity"].cummax() - 1).min()
    return {
        "final_value": final, "total_contrib": total_contrib,
        "net_pnl": final - total_contrib, "net_pnl_pct": final / total_contrib - 1,
        "cagr": cagr, "max_drawdown": float(dd),
        "years": float(years), "n_contributions": len(snapped),
    }

def spy_dca(spy_close, contributions):
    """SPY DCA benchmark: same schedule, buys SPY at close on contribution dates."""
    s = pd.Series(spy_close).sort_index()
    capital = 0.0
    units = 0.0
    last_px = None
    snapped = []
    for dt in contributions:
        ts = pd.Timestamp(dt)
        px_series = s[s.index <= ts]
        if px_series.empty:
            continue
        px = float(px_series.iloc[-1])
        snapped.append(pd.Timestamp(px_series.index[-1]))
        add = INITIAL if ts == pd.Timestamp(START_DATE) else DCA_AMOUNT
        capital += add
        units += add / px
        last_px = px
    final = units * last_px
    years = (pd.Timestamp(END_DATE) - pd.Timestamp(START_DATE)).days / 365.25
    cagr = (final / capital) ** (1 / years) - 1 if final > 0 else -1
    return {
        "final_value": final, "total_contrib": capital,
        "net_pnl": final - capital, "net_pnl_pct": final / capital - 1,
        "cagr": cagr, "max_drawdown": float("nan"), "years": float(years),
        "n_contributions": len(snapped),
    }

def main():
    print("=" * 78)
    print("DCA SCENARIO: $100 + $50/quarter (2019-01 -> 2026-08), matched SPY DCA")
    print("=" * 78)
    stock_dfs, spy_close = load_local_data()
    frames, spy_trend = prepare_frames(stock_dfs, spy_close)
    contributions = contribution_dates()
    print(f"Contributions: {len(contributions)} (${INITIAL:.0f} + {len(contributions)-1}x ${DCA_AMOUNT:.0f} = ${INITIAL + (len(contributions)-1)*DCA_AMOUNT:,.0f})")

    results = {}
    for name, cfg in CONFIGS.items():
        signals = gen_signals(frames, spy_trend, cfg["rsi_mode"], cfg["min_conf"],
                              cfg["direction"], cfg["spy_gate"])
        trades, port_rets = run_portfolio_sim(
            frames, spy_close, signals, cfg["holding"], cfg["stop"],
            slippage_mult=cfg["slippage_mult"], commission=cfg["commission"])
        m = dca_equity_curve(trades, port_rets, spy_close, contributions)
        results[name] = {"config": cfg, "n_trades": len(trades), **m}
        print(f"\n[{name}] trades={len(trades)} | final=${m['final_value']:,.2f} "
              f"(+{m['net_pnl_pct']*100:.1f}%) | CAGR={m['cagr']*100:.1f}% | maxDD={m['max_drawdown']*100:.1f}%")

    spy_m = spy_dca(spy_close, contributions)
    results["C_SPY_DCA"] = {"config": {"note": "SPY buy&hold DCA same schedule"}, **spy_m}
    print(f"\n[C_SPY_DCA] final=${spy_m['final_value']:,.2f} (+{spy_m['net_pnl_pct']*100:.1f}%) | CAGR={spy_m['cagr']*100:.1f}%")

    print("\n" + "=" * 78)
    print("VS SPY DCA BENCHMARK")
    print("=" * 78)
    for name in ["A_improved_gateF", "B_production", "D_A_stressed"]:
        diff = results[name]["final_value"] - spy_m["final_value"]
        pct = results[name]["net_pnl_pct"] - spy_m["net_pnl_pct"]
        winner = "BEATS SPY" if diff > 0 else "LOSES to SPY"
        print(f"{name}: ${diff:+,.2f} vs SPY ({(pct*100):+.1f}pp) -> {winner}")

    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/dca_scenario.json", "w") as f:
        json.dump({"contributions": [str(d) for d in contributions],
                   "initial": INITIAL, "dca_amount": DCA_AMOUNT,
                   "results": results}, f, indent=2)
    print("\nSaved docs/data/dca_scenario.json")

if __name__ == "__main__":
    main()
