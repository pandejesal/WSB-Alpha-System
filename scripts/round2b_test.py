"""Round 2b test (pre-registered docs/data/round2_preregistration.md):
R2-3 volume surge as confidence BOOSTER + R2-4 liquidity floor.

R2-3: conf_req = 5 if Volume > 1.5x rolling 20-bar mean else 6 (same stack).
R2-4: per-bar floor — 20d mean dollar volume >= $20M AND 20d mean close >= $5,
      applied IDENTICALLY to both universes (fixed thresholds, never tuned).
Protocol: A OOS median >= base A AND B OOS median > 0. Kill rules honored.
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
FLOOR_DOLLAR_VOL = 20_000_000.0
FLOOR_PRICE = 5.0


def gen_signals_r23(frames, spy_trend, cfg):
    """R2-3: surge bars trade at conf cfg.min_conf; non-surge bars need conf 6."""
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
        conf_req = np.where(surge, cfg["min_conf"], 6)
        long_mask = vol_ok & (score >= conf_req)
        for pos in range(len(dates)):
            if long_mask[pos]:
                signals.append((ticker, pos, 1))
    return signals


def gen_signals_r24(frames, spy_trend, cfg):
    """R2-4: liquidity floor, per-bar, identical on both universes."""
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

        dolvol = c * vol
        dolvol20 = pd.Series(dolvol).rolling(20, min_periods=20).mean().to_numpy()
        price20 = pd.Series(c).rolling(20, min_periods=20).mean().to_numpy()
        floor_ok = (dolvol20 >= FLOOR_DOLLAR_VOL) & (price20 >= FLOOR_PRICE) \
            & ~np.isnan(dolvol20) & ~np.isnan(price20)

        ha_long = ha_c > ha_o
        ema_long = (c > ema20) & (macd > 0)
        bb_l = c > bb_low
        rsi_l = (rsi > 30) & (rsi < 70)
        trend_l = c > sma200
        mkt_l = spy_t
        vol_ok = gk < 1.2

        score = (ha_long.astype(int) + ema_long.astype(int) + bb_l.astype(int)
                 + rsi_l.astype(int) + trend_l.astype(int) + mkt_l.astype(int))
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
    results = {"round": "2b", "pre_registration": "docs/data/round2_preregistration.md",
               "base_cfg": BASE,
               "surge_mult": SURGE_MULT, "floor_dollar_vol": FLOOR_DOLLAR_VOL,
               "floor_price": FLOOR_PRICE}

    for uni_name, tickers in [("A_megacap", UNIVERSE_A), ("B_laggard", UNIVERSE_B)]:
        stock_dfs, spy_close = load_universe(tickers)
        frames, spy_trend = m.prepare_frames(stock_dfs, spy_close)
        print(f"\n=== Universe {uni_name} ({len(tickers)} tickers) ===")

        base_sigs = m.gen_signals(frames, spy_trend, BASE["rsi_mode"], BASE["min_conf"],
                                  BASE["direction"], BASE["spy_gate"])
        r23_sigs = gen_signals_r23(frames, spy_trend, BASE)
        r24_sigs = gen_signals_r24(frames, spy_trend, BASE)
        # combined: surge booster AND liquidity floor
        tmp = [s for s in r23_sigs if s in r24_sigs]

        for name, sigs in [("base", base_sigs), ("r23_surge_boost", r23_sigs),
                           ("r24_liquidity", r24_sigs), ("r23_r24", tmp)]:
            r = run(sigs, stock_dfs, spy_close)
            results[f"{uni_name}_{name}"] = r
            print(f"  {name:<16} sig={r['signals']:>5} trades={r['trades']:>5} "
                  f"oos={r['oos_trades']:>4} | med_all={r['median_excess_all']:+.4f} "
                  f"med_oos={r['median_excess_oos']:+.4f} mean_oos={r['mean_excess_oos']:+.4f} "
                  f"wr_oos={r['oos_win_rate']:.1%} | tickers={len(r['tickers_used'])} | per_year={r['per_year']}")

    base_a = results["A_megacap_base"]["median_excess_oos"]
    verdicts = {}
    for name in ["r23_surge_boost", "r24_liquidity", "r23_r24"]:
        a_ok = results[f"A_megacap_{name}"]["median_excess_oos"] >= base_a
        b_ok = results[f"B_laggard_{name}"]["median_excess_oos"] > 0
        verdicts[name] = "PASS" if (a_ok and b_ok) else "FAIL"
        print(f"\nR2-{name}: A_oos_med={results[f'A_megacap_{name}']['median_excess_oos']:+.4f} "
              f"(base={base_a:+.4f}, ok={a_ok}) | B_oos_med={results[f'B_laggard_{name}']['median_excess_oos']:+.4f} "
              f"(ok={b_ok}) -> {verdicts[name]}")

    results["verdicts"] = verdicts
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/round2b_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved docs/data/round2b_results.json")


if __name__ == "__main__":
    main()
