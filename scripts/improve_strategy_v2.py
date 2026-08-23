"""Strategy improvement v2: honest event-driven portfolio simulation with
train/test split, realistic costs and production-consistent constraints.

Fixes over verify_backtest_local.py:
 - proper compounding + portfolio-level daily returns (no per-trade return summation)
 - adds long-term trend (ticker SMA200) + market regime (SPY SMA200) confluence items
 - max 4 concurrent positions (matches MAX_CONCURRENT_POSITIONS), equal weight,
   no pyramiding, T+1 open fills, ATR slippage (same formula as engine),
   0.04% round-trip commission, optional intraday stop-loss
 - train (2019-2023) / test (2024-2026) split; ranking on TRAIN only, test is judgment
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.disable(logging.CRITICAL)

DATA_DIR = "market_data_2019_2026/ohlcv"
UNIVERSE = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ", "WMT", "MA", "UNH", "XOM", "DIS"]
MAX_POSITIONS = 4
COMMISSION = 0.0004  # 0.04% round trip
SPLIT_DATE = "2024-01-01"


def load_local_data():
    stock_dfs, spy_close = {}, {}
    for ticker in UNIVERSE + ["SPY"]:
        path = os.path.join(DATA_DIR, f"{ticker}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index.name = "Date"
        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"])
        rename_map = {c: c.capitalize() for c in df.columns if c.lower() in ["open", "high", "low", "close", "volume"]}
        df.rename(columns=rename_map, inplace=True)
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if ticker == "SPY":
            spy_close = dict(zip(df["Date"], df["Close"]))
        else:
            stock_dfs[ticker] = df
    return stock_dfs, spy_close


def prepare_frames(stock_dfs, spy_close):
    """Compute indicators + long-term trends. Returns per-ticker dict of numpy arrays."""
    from src.alpha.indicators import compute_indicators

    spy_s = pd.Series(spy_close).sort_index()
    spy_sma200 = spy_s.rolling(200).mean()
    spy_trend = dict(zip(spy_s.index.astype("datetime64[ns]").to_numpy(), (spy_s > spy_sma200).to_numpy()))

    frames = {}
    for ticker, df in stock_dfs.items():
        px = df.set_index("Date")
        if len(px) < 250:
            continue
        ind = compute_indicators(px)
        if ind is None or ind.empty:
            continue
        ind["SMA_200"] = ind["Close"].rolling(200).mean()
        ind = ind.dropna(subset=["SMA_200"])
        if len(ind) < 20:
            continue
        frames[ticker] = ind
    return frames, spy_trend


def gen_signals(frames, spy_trend, rsi_mode, min_conf, direction="both", spy_gate=False):
    """Vectorized confluence signal generation.

    Long score items (each +1):
      1. HA_Close > HA_Open
      2. Close > EMA_20 and MACD_Hist > 0
      3. Close > BB_Lower
      4. RSI band (momentum: 50-70, neutral: 30-70)
      5. Close > SMA_200 (ticker long-term uptrend)
      6. SPY > SPY_SMA_200 (market uptrend)
    Short = mirror. Vol shield: GK_Vol < 1.2. Signal if score >= min_conf.
    spy_gate=True: SPY trend is MANDATORY (no signal when market below 200d MA).
    """
    signals = []  # (ticker, bar_position_of_signal, direction)
    for ticker, ind in frames.items():
        c = ind["Close"].to_numpy()
        ha_c = ind["HA_Close"].to_numpy()
        ha_o = ind["HA_Open"].to_numpy()
        macd = ind["MACD_Hist"].to_numpy()
        bb_low = ind["BB_Lower"].to_numpy()
        bb_high = ind["BB_Upper"].to_numpy()
        ema20 = ind["EMA_20"].to_numpy()
        rsi = ind["RSI_14"].to_numpy()
        gk = ind["GK_Vol"].to_numpy()
        sma200 = ind["SMA_200"].to_numpy()
        dates = ind.index.to_numpy()
        spy_t = np.array([spy_trend.get(d, False) for d in dates])

        ha_long = ha_c > ha_o
        ha_short = ha_c < ha_o
        ema_long = (c > ema20) & (macd > 0)
        ema_short = (c < ema20) & (macd < 0)
        bb_l = c > bb_low
        bb_s = c < bb_high
        if rsi_mode == "momentum":
            rsi_l = (rsi > 50) & (rsi < 70)
            rsi_s = (rsi > 30) & (rsi < 50)
        else:
            rsi_l = (rsi > 30) & (rsi < 70)
            rsi_s = (rsi > 30) & (rsi < 70)
        trend_l = c > sma200
        trend_s = c < sma200
        mkt_l = spy_t
        mkt_s = ~spy_t
        vol_ok = gk < 1.2

        score_l = ha_long.astype(int) + ema_long.astype(int) + bb_l.astype(int) + rsi_l.astype(int) + trend_l.astype(int) + mkt_l.astype(int)
        score_s = ha_short.astype(int) + ema_short.astype(int) + bb_s.astype(int) + rsi_s.astype(int) + trend_s.astype(int) + mkt_s.astype(int)

        long_mask = vol_ok & (score_l >= min_conf)
        short_mask = vol_ok & (score_s >= min_conf)
        if spy_gate:
            long_mask = long_mask & mkt_l
            short_mask = short_mask & mkt_s
        if direction == "long_only":
            short_mask[:] = False
        elif direction == "short_only":
            long_mask[:] = False

        for pos, d in enumerate(dates):
            if long_mask[pos]:
                signals.append((ticker, pos, 1))
            elif short_mask[pos]:
                signals.append((ticker, pos, -1))
    return signals


def run_portfolio_sim(frames, spy_close, signals, holding_days, stop_loss_pct,
                      slippage_mult=1.0, commission=COMMISSION):
    """Event-driven portfolio sim. Returns trades list + daily portfolio returns (aligned to SPY dates).

    Rules (honest):
    - signal at close of bar d -> fill at open of next bar (T+1), decision data from bar d only
    - slippage = clamp(ATR_14*0.05, 0.001*px, 0.025*px) same as engine (x slippage_mult stress)
    - commission 0.04% round trip (overridable for stress)
    - exit at close of bar d+holding_days; intraday stop-loss breach exits at stop price
    - max 4 concurrent positions, equal weight 1/4, no pyramiding
    """
    tdata = {}  # ticker -> dict of arrays
    for ticker, ind in frames.items():
        tdata[ticker] = {
            "dates": ind.index.to_numpy(),
            "open": ind["Open"].to_numpy(),
            "close": ind["Close"].to_numpy(),
            "high": ind["High"].to_numpy(),
            "low": ind["Low"].to_numpy(),
            "atr": ind["ATR_14"].to_numpy(),
        }

    # group signals by their exec date (bar pos+1)
    sig_by_date = {}
    for ticker, pos, d in signals:
        d0 = tdata[ticker]
        if pos + 1 >= len(d0["dates"]):
            continue
        exec_date = d0["dates"][pos + 1]
        sig_by_date.setdefault(exec_date, []).append((ticker, pos, d))

    # global trading calendar = union of all dates
    all_dates = sorted(set().union(*[set(t["dates"]) for t in tdata.values()]))

    pos_list = []  # open positions
    trades = []
    port_rets = []  # (date, portfolio_return)
    cur_iloc = {t: -1 for t in tdata}

    for day in all_dates:
        day64 = np.datetime64(day)
        for t in tdata:
            arr = tdata[t]["dates"]
            idx = int(np.searchsorted(arr, day64))
            if idx < len(arr) and arr[idx] == day64:
                cur_iloc[t] = idx

        day_ret = 0.0

        # 1. update open positions with today's move
        still_open = []
        for p in pos_list:
            t = p["ticker"]
            d = tdata[t]
            i = cur_iloc.get(t, -1)
            if i < 0 or i == p["last_iloc"]:
                # no new bar today: zero contribution, keep basis for next bar
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
            exited = stop_hit or (i - p["entry_iloc"] >= holding_days)
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

        # 2. open new positions whose exec date is today
        today_sigs = sig_by_date.get(day64, [])
        for ticker, pos, d in today_sigs:
            if len(pos_list) >= MAX_POSITIONS:
                break
            if any(p["ticker"] == ticker for p in pos_list):
                continue
            d0 = tdata[ticker]
            i = cur_iloc.get(ticker, -1)
            if i < 0:
                continue
            # exec bar = signal bar + 1; today's bar must be exactly that
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
                "stop_price": stop_price, "last_move": move, "weight": 1.0 / MAX_POSITIONS,
            })
            day_ret += (1.0 / MAX_POSITIONS) * move

        port_rets.append((day, day_ret))

    return trades, port_rets


def portfolio_metrics(port_rets, spy_close):
    """Compound portfolio returns over SPY calendar; benchmark vs SPY same window."""
    if not port_rets:
        return {}
    df = pd.DataFrame(port_rets, columns=["date", "ret"])
    df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    df = df.groupby(df.index).sum()
    eq = (1 + df["ret"]).cumprod()
    total = eq.iloc[-1] - 1
    years = (df.index.max() - df.index.min()).days / 365.25
    ann = (1 + total) ** (1 / years) - 1 if years > 0 else total
    daily = df["ret"]
    sharpe = daily.mean() / (daily.std() + 1e-12) * np.sqrt(252) if daily.std() > 0 else 0.0
    dd = (eq / eq.cummax() - 1).min()

    spy = pd.Series(spy_close).sort_index()
    spy = spy[(spy.index >= df.index.min()) & (spy.index <= df.index.max())]
    spy_total = spy.iloc[-1] / spy.iloc[0] - 1
    spy_ann = (1 + spy_total) ** (1 / years) - 1 if years > 0 else spy_total
    return {
        "total_return": float(total), "annualized_return": float(ann),
        "sharpe": float(sharpe), "max_drawdown": float(dd),
        "years": float(years), "spy_total": float(spy_total), "spy_ann": float(spy_ann),
        "excess_total": float(total - spy_total), "n_days": int(len(df)),
    }


def trade_summary(trades):
    if not trades:
        return {"trades": 0}
    rets = np.array([t["return"] for t in trades])
    excess = np.array([t["excess_return"] for t in trades])
    wins = rets > 0
    return {
        "trades": int(len(rets)),
        "win_rate": float(wins.mean()),
        "mean_return": float(rets.mean()),
        "mean_excess": float(excess.mean()),
        "excess_win_rate": float((excess > 0).mean()),
        "mean_holding": float(np.mean([t["holding_days"] for t in trades])),
        "long_share": float(np.mean([t["direction"] == 1 for t in trades])),
        "top_tickers": dict(pd.Series([t["ticker"] for t in trades]).value_counts().head(3).to_dict()),
    }


def main():
    print("=" * 80)
    print("STRATEGY IMPROVEMENT v2: portfolio sim, train/test split, realistic costs")
    print("=" * 80)
    stock_dfs, spy_close = load_local_data()
    frames, spy_trend = prepare_frames(stock_dfs, spy_close)
    print(f"Frames ready: {len(frames)} tickers (SMA200 filtered)")

    grid = []
    for rsi_mode in ["momentum", "neutral"]:
        for min_conf in [3, 4, 5]:
            for holding in [5, 10, 15, 20]:
                for stop in [0.0, 0.05, 0.08]:
                    for direction in ["long_only", "both"]:
                        for spy_gate in [False] if direction == "both" else [False, True]:
                            grid.append({"rsi_mode": rsi_mode, "min_conf": min_conf,
                                         "holding": holding, "stop": stop, "direction": direction,
                                         "spy_gate": spy_gate})

    results = []
    for g in grid:
        signals = gen_signals(frames, spy_trend, g["rsi_mode"], g["min_conf"], g["direction"], g["spy_gate"])
        if len(signals) < 100:
            continue
        trades, port_rets = run_portfolio_sim(frames, spy_close, signals, g["holding"], g["stop"])

        train_rets = [(d, r) for d, r in port_rets if d < np.datetime64(SPLIT_DATE)]
        test_rets = [(d, r) for d, r in port_rets if d >= np.datetime64(SPLIT_DATE)]
        train_trades = [t for t in trades if t["entry_date"] < SPLIT_DATE]
        test_trades = [t for t in trades if t["entry_date"] >= SPLIT_DATE]

        m_train = portfolio_metrics(train_rets, spy_close)
        m_test = portfolio_metrics(test_rets, spy_close)
        ts_train = trade_summary(train_trades)
        ts_test = trade_summary(test_trades)
        results.append({
            "params": g, "signals": len(signals),
            "train": {**m_train, **ts_train}, "test": {**m_test, **ts_test},
        })
        print(f"rsi={g['rsi_mode'][:3]} conf={g['min_conf']} hold={g['holding']:>2} stop={g['stop']:.2f} dir={g['direction'][:4]:<4} gate={str(g['spy_gate'])[0]} "
              f"| sig={len(signals):>6} | TRAIN ret={m_train.get('total_return', 0)*100:>7.1f}% excess={m_train.get('excess_total', 0)*100:>7.1f}% sh={m_train.get('sharpe', 0):>5.2f} "
              f"| TEST ret={m_test.get('total_return', 0)*100:>7.1f}% excess={m_test.get('excess_total', 0)*100:>7.1f}% sh={m_test.get('sharpe', 0):>5.2f} trades={ts_train.get('trades', 0)}/{ts_test.get('trades', 0)}")

    results.sort(key=lambda r: r["train"].get("excess_total", -1), reverse=True)

    print()
    print("=" * 80)
    print("TOP 10 BY TRAIN EXCESS VS SPY (test = out-of-sample judgment)")
    print("=" * 80)
    for i, r in enumerate(results[:10]):
        tr, te = r["train"], r["test"]
        print(f"#{i+1} rsi={r['params']['rsi_mode'][:3]} conf={r['params']['min_conf']} hold={r['params']['holding']:>2} stop={r['params']['stop']:.2f} dir={r['params']['direction'][:4]:<4} gate={str(r['params']['spy_gate'])[0]} "
              f"| TRAIN ret={tr.get('total_return',0)*100:>7.1f}% excess={tr.get('excess_total',0)*100:>7.1f}% wr={tr.get('win_rate',0)*100:>4.1f}% "
              f"| TEST ret={te.get('total_return',0)*100:>7.1f}% excess={te.get('excess_total',0)*100:>7.1f}% wr={te.get('win_rate',0)*100:>4.1f}% "
              f"| trades={tr.get('trades',0)}/{te.get('trades',0)}")

    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/improve_v2_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved docs/data/improve_v2_results.json")


if __name__ == "__main__":
    main()