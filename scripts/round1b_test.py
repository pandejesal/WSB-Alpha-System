"""Round 1b test: R1-3 GK-vol regime conditioning + R1-4 cross-sectional ranking.

Pre-registered (docs/data/round1_preregistration.md):
- R1-3: per-bar dynamic min_conf by GK regime: GK<1.2 -> conf 5 (base),
  GK in [1.2,1.5) -> conf 6, GK>=1.5 -> no trades. Replaces binary shield.
- R1-4: on each exec day, candidates sorted by 20-day return at signal bar
  (descending); slots filled best-first instead of ticker order.
- Acceptance (same as 1a): A OOS median >= base A OOS median AND B OOS median > 0.
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
GK_MID = 1.2
GK_HIGH = 1.5


def gen_signals_r13(frames, spy_trend, cfg):
    """R1-3: GK regime-conditioned confidence. GK<1.2 -> conf=cfg, 1.2<=GK<1.5 -> conf=6,
    GK>=1.5 -> blocked. Identical score stack otherwise."""
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

        ha_long = ha_c > ha_o
        ema_long = (c > ema20) & (macd > 0)
        bb_l = c > bb_low
        rsi_l = (rsi > 30) & (rsi < 70)
        trend_l = c > sma200
        mkt_l = spy_t

        score = (ha_long.astype(int) + ema_long.astype(int) + bb_l.astype(int)
                 + rsi_l.astype(int) + trend_l.astype(int) + mkt_l.astype(int))

        conf_req = np.where(gk < GK_MID, cfg["min_conf"],
                            np.where(gk < GK_HIGH, 6, np.inf))
        long_mask = (score >= conf_req) & (gk < GK_HIGH)
        if cfg["direction"] == "long_only":
            pass  # already long-only

        for pos, d in enumerate(dates):
            if long_mask[pos]:
                signals.append((ticker, pos, 1))
    return signals


def gen_signals_r14(frames, spy_trend, cfg, rank_lag=20):
    """R1-4: base signal generation, but the returned list is ordered so that on
    each exec date candidates with the highest 20-day return at signal bar come
    first (sim fills slots in list order)."""
    sigs = []
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

        ret20 = np.full(len(c), np.nan)
        ret20[rank_lag:] = c[rank_lag:] / c[:-rank_lag] - 1.0

        ha_long = ha_c > ha_o
        ema_long = (c > ema20) & (macd > 0)
        bb_l = c > bb_low
        rsi_l = (rsi > 30) & (rsi < 70)
        trend_l = c > sma200
        mkt_l = spy_t
        vol_ok = gk < 1.2

        score_l = (ha_long.astype(int) + ema_long.astype(int) + bb_l.astype(int)
                   + rsi_l.astype(int) + trend_l.astype(int) + mkt_l.astype(int))
        long_mask = vol_ok & (score_l >= cfg["min_conf"])
        if cfg["direction"] == "long_only":
            pass

        for pos in range(len(dates)):
            if long_mask[pos]:
                exec_dt = dates[pos + 1] if pos + 1 < len(dates) else None
                sigs.append({"ticker": ticker, "pos": pos, "dir": 1,
                             "exec": exec_dt, "rank": ret20[pos]})

    sigs.sort(key=lambda s: (np.datetime64(s["exec"]) if s["exec"] is not None
                             else np.datetime64("2099-01-01"),
                             -(s["rank"] if s["rank"] == s["rank"] else -np.inf)))
    return [(s["ticker"], s["pos"], s["dir"]) for s in sigs]


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
    return {
        "signals": len(signals), "trades": len(df), "oos_trades": len(oos),
        "median_excess_all": float(df["excess_return"].median()),
        "median_excess_oos": float(oos["excess_return"].median()),
        "mean_excess_oos": float(oos["excess_return"].mean()),
        "oos_win_rate": float((oos["excess_return"] > 0).mean()),
        "per_year": {str(k): float(v) for k, v in pym.items()},
    }


def main():
    results = {"round": "1b", "base_cfg": BASE}

    _frames_a, _spy_trend_a = None, None
    for uni_name, tickers in [("A_megacap", UNIVERSE_A), ("B_laggard", UNIVERSE_B)]:
        stock_dfs, spy_close = load_universe(tickers)
        frames, spy_trend = m.prepare_frames(stock_dfs, spy_close)
        print(f"\n=== Universe {uni_name} ({len(tickers)} tickers) ===")

        base_sigs = m.gen_signals(frames, spy_trend, BASE["rsi_mode"], BASE["min_conf"],
                                  BASE["direction"], BASE["spy_gate"])
        r13_sigs = gen_signals_r13(frames, spy_trend, BASE)
        r14_sigs = gen_signals_r14(frames, spy_trend, BASE)
        r34_sigs = None
        # combined: R1-3 conf conditioning + R1-4 ranking (rank on R1-3 survivors)
        r3_t = {}
        for t, ind in frames.items():
            c = ind["Close"].to_numpy()
            ret20 = np.full(len(c), np.nan)
            ret20[20:] = c[20:] / c[:-20] - 1.0
            r3_t[t] = ret20
        tmp = []
        for (t, pos, d) in r13_sigs:
            rank = r3_t[t][pos]
            exec_dt = frames[t].index.to_numpy()[pos + 1] if pos + 1 < len(frames[t]) else None
            tmp.append({"t": t, "pos": pos, "d": d, "exec": exec_dt, "rank": rank})
        tmp.sort(key=lambda s: (np.datetime64(s["exec"]) if s["exec"] is not None
                                else np.datetime64("2099-01-01"),
                                -(s["rank"] if s["rank"] == s["rank"] else -np.inf)))
        r34_sigs = [(s["t"], s["pos"], s["d"]) for s in tmp]

        for name, sigs in [("base", base_sigs), ("r13_gk_conf", r13_sigs),
                           ("r14_rank", r14_sigs), ("r13_r14", r34_sigs)]:
            r = run(sigs, stock_dfs, spy_close)
            results[f"{uni_name}_{name}"] = r
            print(f"  {name:<12} sig={r['signals']:>5} trades={r['trades']:>5} "
                  f"oos={r['oos_trades']:>4} | med_all={r['median_excess_all']:+.4f} "
                  f"med_oos={r['median_excess_oos']:+.4f} mean_oos={r['mean_excess_oos']:+.4f} "
                  f"wr_oos={r['oos_win_rate']:.1%} | per_year={r['per_year']}")

    base_a = results["A_megacap_base"]["median_excess_oos"]
    verdicts = {}
    for name in ["r13_gk_conf", "r14_rank", "r13_r14"]:
        a_ok = results[f"A_megacap_{name}"]["median_excess_oos"] >= base_a
        b_ok = results[f"B_laggard_{name}"]["median_excess_oos"] > 0
        verdicts[name] = "PASS" if (a_ok and b_ok) else "FAIL"
        print(f"\nR1-{name}: A_oos_med={results[f'A_megacap_{name}']['median_excess_oos']:+.4f} "
              f"(base={base_a:+.4f}, ok={a_ok}) | B_oos_med={results[f'B_laggard_{name}']['median_excess_oos']:+.4f} "
              f"(ok={b_ok}) -> {verdicts[name]}")

    results["verdicts"] = verdicts
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/round1b_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved docs/data/round1b_results.json")


if __name__ == "__main__":
    main()
