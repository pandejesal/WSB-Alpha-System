"""Standalone VERIFY C1 + C2 (daily data 2015-2026, proxy universe).

C1 (OBB-Fade): count episodes of Close >= BB_upper(20,2) & RSI14 >= 70,
episode-length distribution, and gross forward short returns from T+1 open with
TP=entry-day BB_mid / 5d time stop / SL=1.5x ATR14 (Wilder). Also 3/10d raw
forward returns for geometry sanity (C1-1, C1-2).

C2 (WeeklyTopFade): each Friday rank names by trailing 5d (1w) return; short top
4 (quintile of 20); hold 5 or 10 sessions; gross and friction 20/60bp per
round-trip per position (C2-1 one-week vs two-week hold).
"""
import numpy as np
import pandas as pd
import yfinance as yf

UNIVERSE = ["GME", "AMC", "NVDA", "TSLA", "AAPL", "MSFT", "META", "AMD",
            "NFLX", "SHOP", "ROKU", "SNAP", "PINS", "CRM", "MU", "U", "F",
            "KO", "JNJ", "BA"]
SPY = "SPY"
START, END = "2015-01-01", "2026-08-09"


def wilder_atr(h, l, c, n=14):
    tr = np.maximum(h - l, np.maximum((h - c.shift(1)).abs(), (l - c.shift(1)).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def wilder_rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn
    return 100 - 100 / (1 + rs)


def load():
    px = yf.download(UNIVERSE + [SPY], start=START, end=END, progress=False,
                     auto_adjust=True)
    closes = px["Close"]
    data = {}
    for t in UNIVERSE:
        s = closes[t].dropna()
        if len(s) <= 400:
            continue
        o = px["Open"][t].reindex(s.index).astype(float)
        h = px["High"][t].reindex(s.index).astype(float)
        lo = px["Low"][t].reindex(s.index).astype(float)
        df = pd.DataFrame({"close": s.astype(float), "open": o, "high": h, "low": lo})
        data[t] = df.dropna()
    return data


def c1_verify(data):
    results = []
    for t, df in data.items():
        c = df["close"]
        bb_mid = c.rolling(20).mean()
        bb_up = bb_mid + 2 * c.rolling(20).std()
        rsi = wilder_rsi(c, 14)
        atr = wilder_atr(df["high"], df["low"], c, 14)
        sig = (c >= bb_up) & (rsi >= 70)
        # episodes = consecutive signal days
        runs = []
        start = None
        for i in range(len(sig)):
            if sig.iloc[i] and start is None:
                start = i
            elif not sig.iloc[i] and start is not None:
                runs.append((start, i - 1))
                start = None
        if start is not None:
            runs.append((start, len(sig) - 1))
        ep_lens = [j - i + 1 for (i, j) in runs]
        # forward short sim per episode
        fwd = []
        for (i, j) in runs:
            if j + 1 >= len(df):
                continue
            entry_px = df["open"].iloc[j + 1]
            entry = np.log(entry_px)
            tp = bb_mid.iloc[i]
            sl_px = entry_px - 1.5 * atr.iloc[i]
            exit_log = None
            exit_tag = None
            for k in range(j + 2, min(j + 1 + 6, len(df))):
                cl = df["close"].iloc[k]
                if cl <= tp:
                    exit_log = np.log(cl)
                    exit_tag = "TP"
                    break
                if cl <= sl_px:
                    exit_log = np.log(cl)
                    exit_tag = "SL"
                    break
            if exit_log is None:
                kk = min(j + 1 + 5, len(df) - 1)
                exit_log = np.log(df["close"].iloc[kk])
                exit_tag = "TIME"
            fwd.append((df.index[j + 1], entry - exit_log, exit_tag))
        results.append((t, sig.sum(), len(runs), ep_lens, fwd))
    tot_sig = sum(r[1] for r in results)
    tot_ep = sum(r[2] for r in results)
    ep_lens = [l for r in results for l in r[3]]
    fw = [x for r in results for (_, x, _) in r[4]]
    tags = [tag for r in results for (_, _, tag) in r[4]]
    print(f"[C1] signal days={tot_sig}  episodes={tot_ep}  trades={len(fw)}")
    print(f"[C1] episode lengths: mean={np.mean(ep_lens):.2f}d median={np.median(ep_lens):.0f}d "
          f"p90={np.percentile(ep_lens, 90):.0f}d max={max(ep_lens)}d")
    a = np.array(fw)
    tstat = a.mean() / a.std() * np.sqrt(len(a)) if a.std() > 0 else np.nan
    print(f"[C1] gross short mean={a.mean()*100:+.2f}%/t t={tstat:+.2f} win={100*(a>0).mean():.0f}%  "
          f"TP={100*np.mean([t2=='TP' for t2 in tags]):.0f}%  SL={100*np.mean([t2=='SL' for t2 in tags]):.0f}%  "
          f"TIME={100*np.mean([t2=='TIME' for t2 in tags]):.0f}%")
    print(f"[C1] tails p5={np.percentile(a,5)*100:+.2f}% p50={np.median(a)*100:+.2f}% "
          f"p95={np.percentile(a,95)*100:+.2f}%  worst={a.min()*100:+.2f}%")
    for label, y0, y1 in [("2015-2019", 2015, 2019), ("2020-2021", 2020, 2021), ("2022-2026", 2022, 2026)]:
        sub = [x for r in results for (d, x, _) in r[4] if y0 <= d.year <= y1]
        if not sub:
            print(f"[C1][{label}] none")
            continue
        sa = np.array(sub)
        st = sa.mean() / sa.std() * np.sqrt(len(sa)) if sa.std() > 0 else np.nan
        print(f"[C1][{label}] n={len(sa):4d} mean={sa.mean()*100:+.2f}%/t t={st:+.2f} "
              f"win={100*(sa>0).mean():.0f}% sum={sa.sum()*100:+.1f}%")
    for bp in [20, 60]:
        net = a - bp / 10000
        print(f"[C1] round-trip {bp}bp: mean {net.mean()*100:+.2f}%  sum {net.sum()*100:+.1f}%")


def c2_verify(data):
    # weekly (last trading day) cross-sectional reversal: short top quintile
    frames = []
    for t, df in data.items():
        w = df["close"].resample("W-FRI").last().dropna()
        frames.append(pd.DataFrame({"close": w, "ticker": t}))
    panel = pd.concat(frames).sort_index()
    per_week = []
    for d, g in panel.groupby(level=0):
        if len(g) < 10:
            continue
        r5 = g["close"].pct_change(1).groupby(level=0)
        r5 = g.groupby(level=0)["close"].pct_change(1)
        per_week.append((d, g))
    # simpler: build weekly returns per ticker, then cross-section
    wide = panel.pivot(columns="ticker", values="close")
    rw = wide.pct_change(1)  # prior-week return (this week = 1w ago to this week)
    fwd = wide.pct_change(1).shift(-1)  # next-week return (short PnL), one-week hold
    fwd2 = wide.pct_change(2).shift(-2)  # two-week hold
    for hold_lbl, f in [("1w", fwd), ("2w", fwd2)]:
        rets = []
        for i in range(len(rw) - 1):
            row = rw.iloc[i].dropna()
            if len(row) < 10:
                continue
            top5 = row.sort_values().iloc[-5:].index
            nxt = f.iloc[i].reindex(top5)
            nxt = nxt[nxt.notna() & np.isfinite(nxt)]
            if len(nxt) == 0:
                continue
            rets.append(-nxt.mean())  # SHORT PnL = negative of winners' next-week return
        rr = np.array(rets)
        tstat = rr.mean() / rr.std() * np.sqrt(len(rr)) if rr.std() > 0 else np.nan
        print(f"[C2][{hold_lbl}] SHORT weeks={len(rr)}  mean/sh name={rr.mean()*100:+.2f}%  "
              f"t={tstat:+.2f}  win={100*(rr>0).mean():.0f}%")
        for bp in [20, 60]:
            net = rr - bp / 10000
            print(f"[C2][{hold_lbl}] rt {bp}bp: mean {net.mean()*100:+.2f}%  "
                  f"(top-5 of {len(UNIVERSE)} names; per-position cost)")


def main():
    data = load()
    print(f"loaded {len(data)} names: {list(data.keys())}")
    c1_verify(data)
    c2_verify(data)


if __name__ == "__main__":
    main()