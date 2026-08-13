"""Standalone VERIFY C3-1 (v2): Avellaneda-Lee s-score short, 2015-2026 daily.

Method (matches STRATEGY-CANDIDATES.md C3 spec):
- daily log returns of name and SPY, date-aligned
- rolling 60d OLS of name-ret on SPY-ret (window params, predictive residual:
  res_t = r_t - alpha_w - beta_w * r_spy_t)
- s-score = (res - mean60) / std60
- SHORT entry at T+1 open when s >= ENTRY_S and res > 0 (signal at T close)
- exit at close when s <= EXIT_S, or after STOP_DAYS sessions, or SL hit:
  SL distance = 1.5 * window residual std (price units)
- P&L in log-price units -> % per trade
- MIN_HOLD=1 bar avoids same-bar entry/exit.

Also per-name AR(1) half-life on the residual (C3-2 input).
Configs: entry in {1.25 (paper), 1.0, 1.5} x exit 0.75 x stop 10d.
"""
import numpy as np
import pandas as pd
import yfinance as yf

UNIVERSE = ["GME", "AMC", "NVDA", "TSLA", "AAPL", "MSFT", "META", "AMD",
            "NFLX", "SHOP", "ROKU", "SNAP", "PINS", "CRM", "MU", "U", "F",
            "KO", "JNJ", "BA"]
SPY = "SPY"
START, END = "2015-01-01", "2026-08-09"
WINDOW, EXIT_S, SL_MULT, STOP_DAYS, MIN_HOLD = 60, 0.75, 1.5, 10, 1


def load():
    px = yf.download(UNIVERSE + [SPY], start=START, end=END, progress=False,
                     auto_adjust=True)["Close"]
    spy = px[SPY].dropna()
    data = {}
    for t in UNIVERSE:
        s = px[t].dropna()
        if len(s) <= WINDOW + 100:
            continue
        df = pd.DataFrame({"close": s})
        df = df.loc[df.index.intersection(spy.index)]
        df["r"] = np.log(df["close"]).diff()
        df["rm"] = np.log(spy.loc[df.index]).diff()
        data[t] = df
    return data


def residual_series(df):
    r = df["r"].values.astype(float)
    rm = df["rm"].values.astype(float)
    n = len(r)
    res = np.full(n, np.nan)
    for i in range(WINDOW, n):
        x, y = rm[i - WINDOW:i], r[i - WINDOW:i]
        ok = ~(np.isnan(x) | np.isnan(y))
        if ok.sum() < WINDOW // 2:
            continue
        b, a = np.polyfit(x[ok], y[ok], 1)
        res[i] = r[i] - (a + b * rm[i])
    return pd.Series(res, index=df.index)


def simulate(df, res_s, entry_s):
    mu = res_s.rolling(WINDOW, min_periods=WINDOW // 2).mean()
    sd = res_s.rolling(WINDOW, min_periods=WINDOW // 2).std()
    sc = (res_s - mu) / sd
    close = df["close"]
    n = len(df)
    trades = []
    pos = 0
    ei = None
    entry_log = None
    sl_log = None
    for i in range(n):
        s_ok = np.isfinite(sc.iloc[i])
        if pos == 0:
            if s_ok and sc.iloc[i] >= entry_s and np.isfinite(res_s.iloc[i]) and res_s.iloc[i] > 0:
                if i + 1 >= n:
                    continue
                pos = -1
                ei = i
                entry_log = np.log(close.iloc[i + 1])
                rstd = sd.iloc[i]
                sl_log = entry_log - SL_MULT * rstd if np.isfinite(rstd) else None
        else:
            if i - (ei + 1) < MIN_HOLD:
                continue
            bar_log = np.log(close.iloc[i])
            if s_ok and sc.iloc[i] <= EXIT_S:
                trades.append((df.index[i], entry_log - bar_log, i - ei));
                pos = 0
            elif i - ei >= STOP_DAYS + 1:
                trades.append((df.index[i], entry_log - bar_log, i - ei));
                pos = 0
            elif sl_log is not None and bar_log <= sl_log:
                trades.append((df.index[i], entry_log - bar_log, i - ei));
                pos = 0
    return trades


def half_life(res_s):
    av = res_s.dropna()
    if len(av) < 250:
        return np.nan
    rho = np.corrcoef(av.values[:-1], av.values[1:])[0, 1]
    if not np.isfinite(rho) or abs(rho) >= 1:
        return np.nan
    return -np.log(2) / np.log(rho)


def main():
    data = load()
    print(f"universe loaded: {len(data)} names: {list(data.keys())}")
    per_name = {t: half_life(residual_series(df)) for t, df in data.items()}
    flat_all = []
    for entry_s in [1.25, 1.0, 1.5]:
        all_trades = []
        for t, df in data.items():
            res_s = residual_series(df)
            for (d, r, h) in simulate(df, res_s, entry_s):
                all_trades.append((t, d, r, h))
        flat = [(d, r, h) for (_, d, r, h) in all_trades]
        flat_all.append((entry_s, flat))
        print(f"\n=== config entry_s={entry_s} (exit 0.75, stop 10d, SL 1.5x) ===")
        if not flat:
            print("  no trades")
            continue
        print(f"  total trades: {len(flat)}  mean hold: {np.mean([h for (_,_,h) in flat]):.1f} bars")
        for label, y0, y1 in [("2015-2019", 2015, 2019), ("2020-2021", 2020, 2021), ("2022-2026", 2022, 2026)]:
            sub = [r for (d, r, h) in flat if y0 <= d.year <= y1]
            if not sub:
                print(f"  {label}: none")
                continue
            a = np.array(sub)
            tstat = a.mean() / a.std() * np.sqrt(len(a)) if a.std() > 0 else np.nan
            print(f"  {label}: n={len(a):4d}  mean={a.mean()*100:+.2f}%/t  t={tstat:+.2f}  "
                  f"win={100*(a>0).mean():.0f}%  sum={a.sum()*100:+.1f}%")
        g = np.array([r for (_, r, _) in flat])
        for bp in [0, 20, 60, 100]:
            net = g - bp / 10000
            print(f"    round-trip {bp:3d}bp: mean {net.mean()*100:+.2f}%/t  sum {net.sum()*100:+.1f}%")
    hl_vals = [h for h in per_name.values() if np.isfinite(h)]
    if hl_vals:
        print(f"\nOU half-life: median {np.median(hl_vals):.1f}d  mean {np.mean(hl_vals):.1f}d  n={len(hl_vals)}")
    for t, h in per_name.items():
        print(f"  {t:6s} OU hl={h:6.1f}d" if np.isfinite(h) else f"  {t:6s} OU hl= n/a")


if __name__ == "__main__":
    main()