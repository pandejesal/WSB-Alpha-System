"""Round 3 test (pre-registered docs/data/round3_preregistration.md):
R3-1 persistence-adaptive core router + R3-2 persistence floor.

persistence_60 = fraction of trailing 60 bars (bar-59..bar, pre-entry) where
Close > SMA_200. Fixed thresholds: P_ROUTE=0.8, P_FLOOR=0.6. persistence_60
undefined (first 59 bars) -> fail-closed: no signal (both themes, both
universes, deterministic). No per-name logic anywhere.

R3-1: persistence_60 >= 0.8 -> exact base confluence core (conf 5);
      persistence_60 <  0.8 -> exact R2-3 surge booster (conf 5 on surge
      bars, conf 6 otherwise; surge = Volume > 1.5x rolling-20 mean).
R3-2: exact base confluence core (conf 5) + persistence_60 >= 0.6.

Acceptance: A OOS median >= base A (+0.07%) AND B OOS median > 0.
Tie-break (pre-specified): simpler rule (R3-2) wins unless R3-1 min(A,B)
median exceeds R3-2's by >= 0.10pp.
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
SURGE_MULT = 1.5
P_ROUTE = 0.8
P_FLOOR = 0.6


def persistence_60(ind):
    c = ind["Close"].to_numpy()
    sma200 = ind["SMA_200"].to_numpy()
    above = c > sma200
    frac = pd.Series(above).rolling(60, min_periods=60).mean().to_numpy()
    return frac


def gen_signals_r31(frames, spy_trend, cfg):
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
        ind["BB_Upper"].to_numpy()
        ema20 = ind["EMA_20"].to_numpy()
        rsi = ind["RSI_14"].to_numpy()
        gk = ind["GK_Vol"].to_numpy()
        sma200 = ind["SMA_200"].to_numpy()
        vol = ind["Volume"].to_numpy(dtype="float64")
        dates = ind.index.to_numpy()
        spy_t = np.array([spy_trend.get(d, False) for d in dates])
        persist = persistence_60(ind)

        roll = pd.Series(vol).rolling(20, min_periods=20).mean().to_numpy()
        surge = (vol > SURGE_MULT * roll) & (roll > 0) & ~np.isnan(roll)

        ha_long = ha_c > ha_o
        ema_long = (c > ema20) & (macd > 0)
        bb_l = c > bb_low
        rsi_l = (rsi > 30) & (rsi < 70)
        trend_l = c > sma200
        mkt_l = spy_t
        vol_ok = gk < 1.2

        score = (ha_long.astype(int) + ema_long.astype(int) + bb_l.astype(int)
                 + rsi_l.astype(int) + trend_l.astype(int) + mkt_l.astype(int))
        routed = np.full(len(dates), -1)
        routed[persist >= P_ROUTE] = 0    # confluence branch
        routed[persist < P_ROUTE] = 1     # surge-booster branch
        undefined = np.isnan(persist)
        conf_req = np.where(routed == 1, np.where(surge, cfg["min_conf"], 6),
                            cfg["min_conf"])
        long_mask = vol_ok & ~undefined & (score >= conf_req)
        for pos in range(len(dates)):
            if long_mask[pos]:
                signals.append((ticker, pos, 1))
    return signals


def gen_signals_r32(frames, spy_trend, cfg):
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
        ind["BB_Upper"].to_numpy()
        ema20 = ind["EMA_20"].to_numpy()
        rsi = ind["RSI_14"].to_numpy()
        gk = ind["GK_Vol"].to_numpy()
        sma200 = ind["SMA_200"].to_numpy()
        dates = ind.index.to_numpy()
        spy_t = np.array([spy_trend.get(d, False) for d in dates])
        persist = persistence_60(ind)

        ha_long = ha_c > ha_o
        ema_long = (c > ema20) & (macd > 0)
        bb_l = c > bb_low
        rsi_l = (rsi > 30) & (rsi < 70)
        trend_l = c > sma200
        mkt_l = spy_t
        vol_ok = gk < 1.2

        score = (ha_long.astype(int) + ema_long.astype(int) + bb_l.astype(int)
                 + rsi_l.astype(int) + trend_l.astype(int) + mkt_l.astype(int))
        floor_ok = (persist >= P_FLOOR) & ~np.isnan(persist)
        long_mask = vol_ok & floor_ok & (score >= cfg["min_conf"])
        for pos in range(len(dates)):
            if long_mask[pos]:
                signals.append((ticker, pos, 1))
    return signals


def load_universe(tickers):
    orig = m.UNIVERSE
    m.UNIVERSE = tickers
    stock_dfs, spy_close = m.load_local_data()
    m.UNIVERSE = orig
    return stock_dfs, spy_close


def run(signals, stock_dfs, spy_close):
    frames, spy_trend = m.prepare_frames(stock_dfs, spy_close)
    trades, port_rets = m.run_portfolio_sim(frames, spy_close, signals,
                                            BASE["holding"], BASE["stop"])
    df = pd.DataFrame(trades)
    if df.empty:
        return {"signals": len(signals), "trades": 0}
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    oos = df[df["entry_date"] >= SPLIT]
    pym = oos.groupby(oos["entry_date"].dt.year)["excess_return"].median().to_dict()
    tickers_used = sorted(df["ticker"].unique())
    return {
        "signals": len(signals), "trades": len(df), "oos_trades": len(oos),
        "median_excess_all": float(df["excess_return"].median()),
        "median_excess_oos": float(oos["excess_return"].median()),
        "mean_excess_oos": float(oos["excess_return"].mean()),
        "oos_win_rate": float((oos["excess_return"] > 0).mean()),
        "tickers_used": tickers_used,
        "per_year": {str(k): float(v) for k, v in pym.items()},
    }


def main():
    results = {"round": "3", "pre_registration": "docs/data/round3_preregistration.md",
               "base_cfg": BASE, "p_route": P_ROUTE, "p_floor": P_FLOOR,
               "surge_mult": SURGE_MULT, "persistence_undefined": "fail-closed no signal"}

    for uni_name, tickers in [("A_megacap", UNIVERSE_A), ("B_laggard", UNIVERSE_B)]:
        stock_dfs, spy_close = load_universe(tickers)
        frames, spy_trend = m.prepare_frames(stock_dfs, spy_close)
        print(f"\n=== Universe {uni_name} ({len(tickers)} tickers) ===")

        base_sigs = m.gen_signals(frames, spy_trend, BASE["rsi_mode"], BASE["min_conf"],
                                  BASE["direction"], BASE["spy_gate"])
        r31_sigs = gen_signals_r31(frames, spy_trend, BASE)
        r32_sigs = gen_signals_r32(frames, spy_trend, BASE)

        for name, sigs in [("base", base_sigs), ("r31_router", r31_sigs),
                           ("r32_floor", r32_sigs)]:
            r = run(sigs, stock_dfs, spy_close)
            results[f"{uni_name}_{name}"] = r
            print(f"  {name:<12} sig={r['signals']:>5} trades={r['trades']:>5} "
                  f"oos={r['oos_trades']:>4} | med_all={r['median_excess_all']:+.4f} "
                  f"med_oos={r['median_excess_oos']:+.4f} mean_oos={r['mean_excess_oos']:+.4f} "
                  f"wr_oos={r['oos_win_rate']:.1%} | tickers={len(r['tickers_used'])} | per_year={r['per_year']}")

    base_a = results["A_megacap_base"]["median_excess_oos"]
    verdicts = {}
    for name in ["r31_router", "r32_floor"]:
        a_med = results[f"A_megacap_{name}"]["median_excess_oos"]
        b_med = results[f"B_laggard_{name}"]["median_excess_oos"]
        a_ok = a_med >= base_a
        b_ok = b_med > 0
        verdicts[name] = "PASS" if (a_ok and b_ok) else "FAIL"
        print(f"\nR3-{name}: A_oos_med={a_med:+.4f} (base={base_a:+.4f}, ok={a_ok}) | "
              f"B_oos_med={b_med:+.4f} (ok={b_ok}) -> {verdicts[name]}")

    results["verdicts"] = verdicts
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/round3_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved docs/data/round3_results.json")


if __name__ == "__main__":
    main()
