"""Phase 3 (Cycle 2): weekly cross-sectional factor portfolio engine.

Pre-registered (docs/data/factor_claim_preregistration.md):
- Factors: MOM12-1 (cumulative return months M-12..M-2), REV1 (month M-1),
  computed from month-end closes STRICTLY BEFORE the signal bar.
- Composite = pct_rank(MOM) + (1 - pct_rank(REV1))  (reversal shorted).
- Rebalance: weekly, last trading bar of the ISO week (signal date D).
- Fills: T+1 — executed at next trading bar E's OPEN (no lookahead).
- Long = top-decile names, short = bottom-decile names, equal weight/leg.
- Weekly factor return = mean(long open-to-open returns) - mean(short ...).
- No stop, no vol shield, no leakage: all factor inputs < D, all fills > D.
"""
import json
import os

import numpy as np
import pandas as pd

DATA_DIR = "market_data_2019_2026/ohlcv"
SNAPSHOT_JSON = "docs/data/snapshot_SP500.json"


def load_frames(tickers=None):
    if tickers is None:
        with open(SNAPSHOT_JSON) as f:
            tickers = json.load(f)["included"]
    frames = {}
    for t in tickers:
        p = os.path.join(DATA_DIR, f"{t}.csv")
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        frames[t] = df
    return frames


def monthly_last_close(frames):
    """Per ticker: last close of each calendar month (index = Period 'M')."""
    out = {}
    for t, df in frames.items():
        out[t] = df["close"].groupby(df.index.to_period("M")).last()
    return out


def factor_panel(monthly):
    """Per ticker DataFrame (index Period 'M') with mom12_1 and rev1.

    mom12_1[M] = close(M-2)/close(M-12) - 1;  rev1[M] = close(M-1)/close(M-2) - 1.
    Row M is knowable at the end of month M-1 -> usable for any signal bar in M.
    """
    panels = {}
    for t, s in monthly.items():
        s = s.astype(float)
        mom = s.shift(2) / s.shift(12) - 1.0
        rev = s.shift(1) / s.shift(2) - 1.0
        panels[t] = pd.DataFrame({"mom12_1": mom, "rev1": rev})
    return panels


def union_calendar(frames):
    dates = set()
    for df in frames.values():
        dates.update(df.index)
    return pd.DatetimeIndex(sorted(dates))


def weekly_signal_dates(calendar):
    """DataFrame(week=ISO week, signal_date D, exec_date E). E = next bar after D."""
    cal = pd.Series(calendar, index=calendar)
    groups = cal.groupby(cal.index.to_period("W"))
    rows = []
    for wk, grp in groups:
        d = grp.index.max()
        idx = cal.index.get_loc(d)
        if idx + 1 < len(cal):
            e = cal.index[idx + 1]
            rows.append((wk, d, e))
    return pd.DataFrame(rows, columns=["week", "signal_date", "exec_date"])


def _pct_rank(s):
    n = s.notna().sum()
    if n == 0:
        return pd.Series(np.nan, index=s.index)
    r = s.rank(method="average")
    return (r - 1.0) / max(n - 1, 1)


def rank_week(panel_row, tickers):
    """Composite ranks for one month row -> DataFrame(ticker, mom, rev, comp, pct)."""
    mom = panel_row["mom12_1"].reindex(tickers)
    rev = panel_row["rev1"].reindex(tickers)
    valid = mom.notna() & rev.notna()
    out = pd.DataFrame({"mom12_1": mom[valid], "rev1": rev[valid]})
    if out.empty:
        return out
    out["pct_mom"] = _pct_rank(out["mom12_1"])
    out["pct_rev"] = _pct_rank(out["rev1"])
    out["composite"] = out["pct_mom"] + (1.0 - out["pct_rev"])
    out["pct_comp"] = _pct_rank(out["composite"])
    return out


def run_engine(frames, monthly=None, panel=None, schedule=None):
    """Full weekly factor backtest. Returns dict with returns/deciles/positions."""
    if monthly is None:
        monthly = monthly_last_close(frames)
    if panel is None:
        panel = factor_panel(monthly)
    if schedule is None:
        schedule = weekly_signal_dates(union_calendar(frames))
    tickers = sorted(frames.keys())

    panel_df = {t: panel[t] for t in tickers}
    opens = {t: frames[t]["open"] for t in tickers}
    month_last_date = {
        t: df.index.to_series().groupby(df.index.to_period("M")).max()
        for t, df in frames.items()
    }

    week_rows, decile_rows, pos_rows = [], [], []
    for i, row in schedule.iterrows():
        wk, d, e = row["week"], row["signal_date"], row["exec_date"]
        month = d.to_period("M")
        sub = {t: panel_df[t] for t in tickers}
        pr = pd.DataFrame({t: sub[t].loc[month] if month in sub[t].index else
                           pd.Series([np.nan, np.nan],
                                     index=["mom12_1", "rev1"])
                           for t in tickers}).T
        pr.columns = ["mom12_1", "rev1"]
        ranked = rank_week(pr, tickers)
        if ranked.empty:
            week_rows.append({"week": wk, "signal_date": d, "exec_date": e,
                              "n_ranked": 0, "n_long": 0, "n_short": 0,
                              "mean_long": np.nan, "mean_short": np.nan,
                              "factor_return": np.nan, "mom_ls": np.nan,
                              "rev_ls": np.nan})
            continue
        # Leak guard: every month-end close used by ranked tickers must be < D.
        for t in ranked.index:
            mld = month_last_date[t]
            for m in range(1, 13):
                me = mld.get(month - m)
                if me is not None and me >= d:
                    raise AssertionError(
                        f"LEAK at {d.date()} {t}: month-end {me.date()} not < D")
        ranked = ranked.sort_values("pct_comp", ascending=False)
        n = len(ranked)
        long_set = ranked[ranked["pct_comp"] >= 0.90]
        short_set = ranked[ranked["pct_comp"] <= 0.10]

        # next exec bar for the return window
        if i + 1 < len(schedule):
            e_next = schedule.iloc[i + 1]["exec_date"]
        else:
            e_next = None

        def leg_ret(tlist):
            rs = []
            for t in tlist:
                try:
                    p0 = opens[t].loc[e]
                    p1 = opens[t].loc[e_next]
                    rs.append(p1 / p0 - 1.0)
                except KeyError:
                    continue
            return rs

        ml = leg_ret(long_set.index.tolist())
        ms = leg_ret(short_set.index.tolist())
        mean_long = float(np.mean(ml)) if ml else np.nan
        mean_short = float(np.mean(ms)) if ms else np.nan
        fac = (mean_long - mean_short) if (ml and ms) else np.nan

        # sign-gate components: MOM-only and REV-only long-short (deciles)
        mom_long = ranked[ranked["pct_mom"] >= 0.90].index.tolist()
        mom_short = ranked[ranked["pct_mom"] <= 0.10].index.tolist()
        rev_long = ranked[ranked["pct_rev"] >= 0.90].index.tolist()
        rev_short = ranked[ranked["pct_rev"] <= 0.10].index.tolist()
        rl, rs = leg_ret(mom_long), leg_ret(mom_short)
        mom_ls = (float(np.mean(rl)) - float(np.mean(rs))) if (rl and rs) else np.nan
        rl, rs = leg_ret(rev_long), leg_ret(rev_short)
        rev_ls = (float(np.mean(rl)) - float(np.mean(rs))) if (rl and rs) else np.nan

        week_rows.append({"week": wk, "signal_date": d, "exec_date": e,
                          "n_ranked": n, "n_long": len(long_set),
                          "n_short": len(short_set),
                          "mean_long": mean_long, "mean_short": mean_short,
                          "factor_return": fac, "mom_ls": mom_ls, "rev_ls": rev_ls})

        # decile rows (bucket 0..9 by composite percentile)
        buckets = ranked["pct_comp"].mul(10).clip(0, 9).astype(int)
        for b in range(10):
            members = ranked[buckets == b].index.tolist()
            r = leg_ret(members)
            decile_rows.append({"week": wk, "signal_date": d, "decile": b,
                                "n": len(members),
                                "mean_return": (float(np.mean(r)) if r else np.nan)})

        # positions log
        for t in long_set.index.tolist():
            pos_rows.append({"week": wk, "signal_date": d, "exec_date": e,
                             "ticker": t, "side": "L", "weight": 1.0 / len(long_set)})
        for t in short_set.index.tolist():
            pos_rows.append({"week": wk, "signal_date": d, "exec_date": e,
                             "ticker": t, "side": "S", "weight": 1.0 / len(short_set)})

    returns = pd.DataFrame(week_rows)
    deciles = pd.DataFrame(decile_rows)
    positions = pd.DataFrame(pos_rows)
    return {"returns": returns, "deciles": deciles, "positions": positions}


def null_distribution(frames, n=1000, seed=0, oos_start=pd.Timestamp("2024-01-01")):
    """Permutation null: per week, factor ranks are randomly permuted across
    names (cross-sectional 'no-information' null) and the long-short return is
    recomputed. Returns DataFrame(median, sharpe_ann) over the OOS window."""
    monthly = monthly_last_close(frames)
    panel = factor_panel(monthly)
    schedule = weekly_signal_dates(union_calendar(frames))
    tickers = sorted(frames.keys())
    opens = {t: frames[t]["open"] for t in tickers}

    weeks = []  # dicts: pct (np array), oret (np array), in_oos (bool)
    for i, row in schedule.iterrows():
        d, e = row["signal_date"], row["exec_date"]
        month = d.to_period("M")
        sub = {t: panel[t] for t in tickers}
        pr = pd.DataFrame({t: sub[t].loc[month] if month in sub[t].index else
                           pd.Series([np.nan, np.nan],
                                     index=["mom12_1", "rev1"])
                           for t in tickers}).T
        pr.columns = ["mom12_1", "rev1"]
        ranked = rank_week(pr, tickers)
        if ranked.empty:
            continue
        e_next = schedule.iloc[i + 1]["exec_date"] if i + 1 < len(schedule) else None
        oret = np.full(len(ranked), np.nan)
        for j, t in enumerate(ranked.index):
            try:
                oret[j] = opens[t].loc[e_next] / opens[t].loc[e] - 1.0
            except KeyError:
                pass
        weeks.append({"pct": ranked["pct_comp"].to_numpy(),
                      "oret": oret, "in_oos": e >= oos_start})

    rng = np.random.RandomState(seed)
    medians, sharpes = np.empty(n), np.empty(n)
    ann = np.sqrt(52.0)
    for r in range(n):
        wrets = []
        for w in weeks:
            if not w["in_oos"]:
                continue
            perm = rng.permutation(w["pct"])
            ls = perm >= 0.90
            ss = perm <= 0.10
            ml = w["oret"][ls]
            ms = w["oret"][ss]
            ml, ms = ml[~np.isnan(ml)], ms[~np.isnan(ms)]
            if len(ml) and len(ms):
                wrets.append(ml.mean() - ms.mean())
        wrets = np.asarray(wrets)
        medians[r] = np.median(wrets)
        sharpes[r] = wrets.mean() / wrets.std() * ann if wrets.std() > 0 else 0.0
    return pd.DataFrame({"median": medians, "sharpe_ann": sharpes})


def time_shuffle_null(series, n=1000, seed=0):
    """Literal time-shuffle null on a weekly return series. NOTE: the median
    is invariant under permutation, so only order-dependent statistics
    (sharpe, maxDD) can differ from the observed series."""
    s = pd.Series(series, dtype=float).dropna().to_numpy()
    rng = np.random.RandomState(seed)
    medians, sharpes = np.empty(n), np.empty(n)
    ann = np.sqrt(52.0)
    for r in range(n):
        p = rng.permutation(s)
        medians[r] = np.median(p)
        sharpes[r] = p.mean() / p.std() * ann if p.std() > 0 else 0.0
    return pd.DataFrame({"median": medians, "sharpe_ann": sharpes})


def summary_stats(series):
    s = pd.Series(series, dtype=float).dropna()
    if len(s) < 2:
        return {"n": int(len(s)), "mean": float("nan"), "median": float("nan"),
                "sharpe_ann": float("nan"), "pf": float("nan"),
                "maxdd": float("nan")}
    ann = np.sqrt(52.0)
    sharpe = s.mean() / s.std() * ann if s.std() > 0 else 0.0
    gains = s[s > 0].sum()
    losses = -s[s < 0].sum()
    pf = gains / losses if losses > 0 else float("inf")
    eq = (1 + s).cumprod()
    dd = eq / eq.cummax() - 1.0
    return {"n": int(len(s)), "mean": float(s.mean()), "median": float(s.median()),
            "sharpe_ann": float(sharpe), "pf": float(pf), "maxdd": float(dd.min())}


def main():
    frames = load_frames()
    print(f"Loaded {len(frames)} tickers from snapshot")
    res = run_engine(frames)
    os.makedirs("docs/data", exist_ok=True)
    res["returns"].to_csv("docs/data/factor_returns.csv", index=False)
    res["deciles"].to_csv("docs/data/factor_deciles.csv", index=False)
    res["positions"].to_csv("docs/data/factor_positions.csv", index=False)

    r = res["returns"]
    print(f"Weekly rebalances: {len(r)} | ranked avg: {r['n_ranked'].mean():.0f}")
    print(f"Long/short avg per week: {r['n_long'].mean():.0f} / {r['n_short'].mean():.0f}")
    valid = r.dropna(subset=["factor_return"]).copy()
    valid["year"] = pd.to_datetime(valid["exec_date"]).dt.year
    print(f"Valid weeks: {len(valid)} | first {valid['exec_date'].iloc[0].date()} -> "
          f"last {valid['exec_date'].iloc[-1].date()}")
    stats = summary_stats(valid["factor_return"])
    print("All-window stats:", {k: (round(v, 4) if isinstance(v, float) else v)
                                for k, v in stats.items()})
    pym = valid.groupby("year")["factor_return"].median()
    print("Per-year median factor return:\n", pym.round(4))
    print("\nSaved docs/data/factor_returns.csv, factor_deciles.csv, factor_positions.csv")


if __name__ == "__main__":
    main()