"""Round 1a test: R1-1 RSI slope + R1-2 volume surge (pre-registered).

Protocol (docs/data/round1_preregistration.md):
- Base: rsi=neutral conf=5 hold=20 stop=0 long_only gate=F
- Variants: base+rsi_slope, base+volume_surge, base+both
- Run on Universe A (15 mega-caps) and Universe B (10 laggards)
- Acceptance: A OOS median >= base OOS median AND B OOS median excess > 0
- Record PASS/FAIL in docs/data/round1_results.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.improve_strategy_v2 as m

UNIVERSE_A = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ", "WMT", "MA", "UNH", "XOM", "DIS"]
UNIVERSE_B = ["INTC", "PFE", "KO", "BA", "T", "CSCO", "VZ", "MRK", "GE", "IBM"]

BASE = {"rsi_mode": "neutral", "min_conf": 5, "holding": 20, "stop": 0.0,
        "direction": "long_only", "spy_gate": False}
SPLIT = pd.Timestamp("2024-01-01")


def gen_signals_ext(frames, spy_trend, cfg, rsi_slope=False, volume_surge=False, vol_mult=1.5, slope_lag=5):
    """Same as m.gen_signals + optional R1-1 (RSI slope) / R1-2 (volume surge) filters."""
    signals = []
    for ticker, ind in frames.items():
        c = ind["Close"].to_numpy()
        ind["Open"].to_numpy()
        ind["High"].to_numpy()
        ind["Low"].to_numpy()
        ha_c = ind["HA_Close"].to_numpy()
        ha_o = ind["HA_Open"].to_numpy()
        macd = ind["MACD_Hist"].to_numpy()
        bb_low = ind["BB_Lower"].to_numpy()
        bb_high = ind["BB_Upper"].to_numpy()
        ema20 = ind["EMA_20"].to_numpy()
        rsi = ind["RSI_14"].to_numpy()
        gk = ind["GK_Vol"].to_numpy()
        sma200 = ind["SMA_200"].to_numpy()
        vol = ind["Volume"].to_numpy(dtype="float64")
        dates = ind.index.to_numpy()
        spy_t = np.array([spy_trend.get(d, False) for d in dates])

        ha_long = ha_c > ha_o
        ha_short = ha_c < ha_o
        ema_long = (c > ema20) & (macd > 0)
        ema_short = (c < ema20) & (macd < 0)
        bb_l = c > bb_low
        bb_s = c < bb_high
        rsi_l = (rsi > 30) & (rsi < 70)
        rsi_s = (rsi > 30) & (rsi < 70)
        trend_l = c > sma200
        trend_s = c < sma200
        mkt_l = spy_t
        mkt_s = ~spy_t
        vol_ok = gk < 1.2

        if rsi_slope:
            rsi_prev = np.full_like(rsi, np.nan)
            rsi_prev[slope_lag:] = rsi[:-slope_lag]
            slope_ok_l = (rsi > rsi_prev) & ~np.isnan(rsi_prev)
            slope_ok_s = (rsi < rsi_prev) & ~np.isnan(rsi_prev)
        else:
            slope_ok_l = np.ones(len(rsi), dtype=bool)
            slope_ok_s = np.ones(len(rsi), dtype=bool)

        if volume_surge:
            roll = pd.Series(vol).rolling(20, min_periods=20).mean().to_numpy()
            surge = (vol > vol_mult * roll) & (roll > 0) & ~np.isnan(roll)
            surge_l = surge
            surge_s = surge
        else:
            surge_l = np.ones(len(vol), dtype=bool)
            surge_s = np.ones(len(vol), dtype=bool)

        score_l = (ha_long.astype(int) + ema_long.astype(int) + bb_l.astype(int)
                   + rsi_l.astype(int) + trend_l.astype(int) + mkt_l.astype(int))
        score_s = (ha_short.astype(int) + ema_short.astype(int) + bb_s.astype(int)
                   + rsi_s.astype(int) + trend_s.astype(int) + mkt_s.astype(int))

        long_mask = vol_ok & slope_ok_l & surge_l & (score_l >= cfg["min_conf"])
        short_mask = vol_ok & slope_ok_s & surge_s & (score_s >= cfg["min_conf"])
        if cfg["direction"] == "long_only":
            short_mask[:] = False
        elif cfg["direction"] == "short_only":
            long_mask[:] = False

        for pos, d in enumerate(dates):
            if long_mask[pos]:
                signals.append((ticker, pos, 1))
            elif short_mask[pos]:
                signals.append((ticker, pos, -1))
    return signals


def load_universe(tickers):
    orig = m.UNIVERSE
    m.UNIVERSE = tickers
    stock_dfs, spy_close = m.load_local_data()
    m.UNIVERSE = orig
    return stock_dfs, spy_close


def run(cfg, rsi_slope, volume_surge, stock_dfs, spy_close):
    frames, spy_trend = m.prepare_frames(stock_dfs, spy_close)
    signals = gen_signals_ext(frames, spy_trend, cfg, rsi_slope, volume_surge)
    trades, port_rets = m.run_portfolio_sim(frames, spy_close, signals,
                                            cfg["holding"], cfg["stop"])
    df = pd.DataFrame(trades)
    if df.empty:
        return {"signals": 0, "trades": 0}
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    oos = df[df["entry_date"] >= SPLIT]
    pym = oos.groupby(oos["entry_date"].dt.year)["excess_return"].median().to_dict()
    return {
        "signals": len(signals), "trades": len(df), "oos_trades": len(oos),
        "median_excess_all": float(df["excess_return"].median()),
        "median_excess_oos": float(oos["excess_return"].median()),
        "mean_excess_oos": float(oos["excess_return"].mean()),
        "oos_win_rate": float((oos["excess_return"] > 0).mean()),
        "per_year": {str(k): float(v) for k, v in pym.items()},
    }


def main():
    results = {}
    variants = [("base", False, False), ("rsi_slope", True, False),
                ("volume_surge", False, True), ("both", True, True)]

    for uni_name, tickers in [("A_megacap", UNIVERSE_A), ("B_laggard", UNIVERSE_B)]:
        stock_dfs, spy_close = load_universe(tickers)
        print(f"\n=== Universe {uni_name} ({len(tickers)} tickers) ===")
        for name, rsi_slope, volume_surge in variants:
            r = run(BASE, rsi_slope, volume_surge, stock_dfs, spy_close)
            results[f"{uni_name}_{name}"] = r
            print(f"  {name:<14} sig={r['signals']:>5} trades={r['trades']:>5} "
                  f"oos={r['oos_trades']:>4} | med_excess_all={r['median_excess_all']:+.4f} "
                  f"med_oos={r['median_excess_oos']:+.4f} mean_oos={r['mean_excess_oos']:+.4f} "
                  f"wr_oos={r['oos_win_rate']:.1%} | per_year={r['per_year']}")

    base_a = results["A_megacap_base"]["median_excess_oos"]
    verdicts = {}
    for name in ["rsi_slope", "volume_surge", "both"]:
        a_ok = results[f"A_megacap_{name}"]["median_excess_oos"] >= base_a
        b_ok = results[f"B_laggard_{name}"]["median_excess_oos"] > 0
        verdicts[name] = "PASS" if (a_ok and b_ok) else "FAIL"
        print(f"\nR1-{name}: A_oos_med={results[f'A_megacap_{name}']['median_excess_oos']:+.4f} "
              f"(base={base_a:+.4f}, ok={a_ok}) | B_oos_med={results[f'B_laggard_{name}']['median_excess_oos']:+.4f} "
              f"(ok={b_ok}) -> {verdicts[name]}")

    results["verdicts"] = verdicts
    results["base_cfg"] = BASE
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/round1_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved docs/data/round1_results.json")


if __name__ == "__main__":
    main()
