"""Round 2a test: R2-1 MACD rollover exit + R2-2 pure trend core.

Pre-registered (docs/data/round2_preregistration.md). Same protocol as R1:
A OOS median >= base A AND B OOS median > 0 (co-gate). Kill criteria honored.
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


def prepare_frames_ext(stock_dfs, spy_close):
    """prepare_frames + SMA_50 column (needed by R2-2)."""
    frames, spy_trend = m.prepare_frames(stock_dfs, spy_close)
    for t, ind in frames.items():
        ind["SMA_50"] = ind["Close"].rolling(50).mean()
        ind = ind.dropna(subset=["SMA_50"])
        frames[t] = ind
    return frames, spy_trend


def gen_signals_trend(frames, spy_trend):
    """R2-2 pure trend core: Close>SMA50 & SMA50>SMA200 & SPY>SPY200 (long only)."""
    signals = []
    for ticker, ind in frames.items():
        c = ind["Close"].to_numpy()
        sma50 = ind["SMA_50"].to_numpy()
        sma200 = ind["SMA_200"].to_numpy()
        dates = ind.index.to_numpy()
        spy_t = np.array([spy_trend.get(d, False) for d in dates])
        mask = (c > sma50) & (sma50 > sma200) & spy_t
        for pos in range(len(dates)):
            if mask[pos]:
                signals.append((ticker, pos, 1))
    return signals


def sim_macd_exit(frames, spy_close, signals, holding_days, stop_loss_pct=0.0,
                  min_hold=3, slippage_mult=1.0, commission=m.COMMISSION):
    """run_portfolio_sim copy with R2-1 exit rule:
    exit at first close where MACD_Hist < 0 (i-entry_iloc >= min_hold) else cap."""
    tdata = {}
    for ticker, ind in frames.items():
        tdata[ticker] = {
            "dates": ind.index.to_numpy(),
            "open": ind["Open"].to_numpy(),
            "close": ind["Close"].to_numpy(),
            "high": ind["High"].to_numpy(),
            "low": ind["Low"].to_numpy(),
            "atr": ind["ATR_14"].to_numpy(),
            "macd": ind["MACD_Hist"].to_numpy(),
        }
    sig_by_date = {}
    for ticker, pos, d in signals:
        d0 = tdata[ticker]
        if pos + 1 >= len(d0["dates"]):
            continue
        exec_date = d0["dates"][pos + 1]
        sig_by_date.setdefault(exec_date, []).append((ticker, pos, d))

    all_dates = sorted(set().union(*[set(t["dates"]) for t in tdata.values()]))
    pos_list = []
    trades = []
    port_rets = []
    cur_iloc = {t: -1 for t in tdata}

    for day in all_dates:
        day64 = np.datetime64(day)
        for t in tdata:
            arr = tdata[t]["dates"]
            idx = int(np.searchsorted(arr, day64))
            if idx < len(arr) and arr[idx] == day64:
                cur_iloc[t] = idx

        day_ret = 0.0
        still_open = []
        for p in pos_list:
            t = p["ticker"]
            d = tdata[t]
            i = cur_iloc.get(t, -1)
            if i < 0 or i == p["last_iloc"]:
                still_open.append(p)
                continue
            prev_close = d["close"][i - 1] if i - 1 >= 0 else p["entry_price"]
            move = (d["close"][i] / prev_close - 1.0) * p["direction"]
            stop_hit = False
            if p["stop_price"] is not None:
                if p["direction"] == 1 and d["low"][i] <= p["stop_price"]:
                    stop_hit = True
                elif p["direction"] == -1 and d["high"][i] >= p["stop_price"]:
                    stop_hit = True
            macd_exit = (i - p["entry_iloc"] >= min_hold) and (d["macd"][i] < 0)
            exited = stop_hit or macd_exit or (i - p["entry_iloc"] >= holding_days)
            if exited:
                if stop_hit:
                    full_ret = -stop_loss_pct
                    today_move = (p["stop_price"] / prev_close - 1.0) * p["direction"]
                else:
                    full_ret = (d["close"][i] / p["entry_price"] - 1.0) * p["direction"]
                    today_move = move
                full_ret -= commission
                today_move -= commission
                entry_date = pd.Timestamp(d["dates"][p["entry_iloc"]])
                exit_date = pd.Timestamp(d["dates"][i])
                spy_ret = 0.0
                s0 = spy_close.get(entry_date)
                s1 = spy_close.get(exit_date)
                if s0 is not None and s1 is not None:
                    spy_ret = (s1 / s0 - 1.0) * p["direction"]
                trades.append({
                    "ticker": t, "direction": p["direction"],
                    "entry_date": str(entry_date.date()), "exit_date": str(exit_date.date()),
                    "entry_price": float(p["entry_price"]), "exit_price": float(d["close"][i]),
                    "return": float(full_ret), "spy_return": float(spy_ret),
                    "excess_return": float(full_ret - spy_ret), "holding_days": int(i - p["entry_iloc"]),
                })
                day_ret += p["weight"] * today_move
            else:
                p["last_iloc"] = i
                day_ret += p["weight"] * move
                still_open.append(p)
        pos_list = still_open

        today_sigs = sig_by_date.get(day64, [])
        for ticker, pos, d in today_sigs:
            if len(pos_list) >= m.MAX_POSITIONS:
                break
            if any(p["ticker"] == ticker for p in pos_list):
                continue
            d0 = tdata[ticker]
            i = cur_iloc.get(ticker, -1)
            if i < 0:
                continue
            if i != pos + 1:
                continue
            entry_price = d0["open"][i]
            atr_val = d0["atr"][pos]
            raw_slip = atr_val * 0.05 * slippage_mult
            min_slip = entry_price * 0.001
            max_slip = entry_price * 0.025
            slippage = max(min_slip, min(raw_slip, max_slip))
            actual_entry = entry_price + slippage * d
            stop_price = None
            if stop_loss_pct > 0.0:
                stop_price = actual_entry * (1.0 - stop_loss_pct) if d == 1 else actual_entry * (1.0 + stop_loss_pct)
            move = (d0["close"][i] / actual_entry - 1.0) * d
            pos_list.append({
                "ticker": ticker, "direction": d, "entry_iloc": i,
                "last_iloc": i, "entry_price": actual_entry,
                "stop_price": stop_price, "last_move": move, "weight": 1.0 / m.MAX_POSITIONS,
            })
            day_ret += (1.0 / m.MAX_POSITIONS) * move

        port_rets.append((day, day_ret))

    return trades, port_rets


def load_universe(tickers):
    orig = m.UNIVERSE
    m.UNIVERSE = tickers
    stock_dfs, spy_close = m.load_local_data()
    m.UNIVERSE = orig
    return stock_dfs, spy_close


def summarize(trades, signals):
    if not trades:
        return {"signals": len(signals), "trades": 0}
    df = pd.DataFrame(trades)
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    oos = df[df["entry_date"] >= SPLIT]
    pym = oos.groupby(oos["entry_date"].dt.year)["excess_return"].median().to_dict()
    return {
        "signals": len(signals), "trades": len(df), "oos_trades": len(oos),
        "median_excess_all": float(df["excess_return"].median()),
        "median_excess_oos": float(oos["excess_return"].median()),
        "mean_excess_oos": float(oos["excess_return"].mean()),
        "oos_win_rate": float((oos["excess_return"] > 0).mean()),
        "mean_holding": float(df["holding_days"].mean()),
        "per_year": {str(k): float(v) for k, v in pym.items()},
    }


def main():
    results = {"round": "2a", "base_cfg": BASE}

    for uni_name, tickers in [("A_megacap", UNIVERSE_A), ("B_laggard", UNIVERSE_B)]:
        stock_dfs, spy_close = load_universe(tickers)
        frames, spy_trend = prepare_frames_ext(stock_dfs, spy_close)
        print(f"\n=== Universe {uni_name} ({len(tickers)} tickers) ===")

        base_sigs = m.gen_signals(frames, spy_trend, BASE["rsi_mode"], BASE["min_conf"],
                                  BASE["direction"], BASE["spy_gate"])
        r21_sigs = base_sigs  # R2-1 changes the sim, not the signals
        r22_sigs = gen_signals_trend(frames, spy_trend)

        # base (standard sim)
        trades, _ = m.run_portfolio_sim(frames, spy_close, base_sigs,
                                        BASE["holding"], BASE["stop"])
        r = summarize(trades, base_sigs)
        results[f"{uni_name}_base"] = r
        print(f"  base      sig={r['signals']:>6} trades={r['trades']:>5} oos={r['oos_trades']:>4} "
              f"| med_oos={r['median_excess_oos']:+.4f} mean_oos={r['mean_excess_oos']:+.4f} "
              f"wr={r['oos_win_rate']:.1%} hold={r['mean_holding']:.1f} | {r['per_year']}")

        # R2-1: MACD rollover exit
        trades, _ = sim_macd_exit(frames, spy_close, r21_sigs,
                                  BASE["holding"], BASE["stop"])
        r = summarize(trades, r21_sigs)
        results[f"{uni_name}_r21_macd_exit"] = r
        print(f"  r21_exit  sig={r['signals']:>6} trades={r['trades']:>5} oos={r['oos_trades']:>4} "
              f"| med_oos={r['median_excess_oos']:+.4f} mean_oos={r['mean_excess_oos']:+.4f} "
              f"wr={r['oos_win_rate']:.1%} hold={r['mean_holding']:.1f} | {r['per_year']}")

        # R2-2: pure trend core, standard sim
        trades, _ = m.run_portfolio_sim(frames, spy_close, r22_sigs,
                                        BASE["holding"], BASE["stop"])
        r = summarize(trades, r22_sigs)
        results[f"{uni_name}_r22_trend"] = r
        print(f"  r22_trend sig={r['signals']:>6} trades={r['trades']:>5} oos={r['oos_trades']:>4} "
              f"| med_oos={r['median_excess_oos']:+.4f} mean_oos={r['mean_excess_oos']:+.4f} "
              f"wr={r['oos_win_rate']:.1%} hold={r['mean_holding']:.1f} | {r['per_year']}")

    base_a = results["A_megacap_base"]["median_excess_oos"]
    verdicts = {}
    for name in ["r21_macd_exit", "r22_trend"]:
        a_ok = results[f"A_megacap_{name}"]["median_excess_oos"] >= base_a
        b_ok = results[f"B_laggard_{name}"]["median_excess_oos"] > 0
        verdicts[name] = "PASS" if (a_ok and b_ok) else "FAIL"
        print(f"\nR2-{name}: A_oos_med={results[f'A_megacap_{name}']['median_excess_oos']:+.4f} "
              f"(base={base_a:+.4f}, ok={a_ok}) | B_oos_med={results[f'B_laggard_{name}']['median_excess_oos']:+.4f} "
              f"(ok={b_ok}) -> {verdicts[name]}")

    results["verdicts"] = verdicts
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/round2a_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved docs/data/round2a_results.json")


if __name__ == "__main__":
    main()
