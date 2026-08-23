"""Cycle 4 — Claim 5/1: "Mega" Composite Meta-Model engine.

Implements docs/data/cycle4_prereg_mega.md EXACTLY as pre-registered
(frozen 2026-08-16). No tuning. Two legs, ONE frozen model spec:

  L1: 481-name weekly cross-section, 26 features (12 C4 price features +
      11 TA from compute_indicators + 13F carry-forward + MOM12-1 + REV1),
      all rank-normalized per rebalance date; decile L/S; 10 bps/side.
  L2: 12-instrument multi-asset (ETFs + crypto), 23 features (price+TA
      only), rank-normalized per rebalance date; top/bottom quartile L/S
      (top 3 long / bottom 3 short, equal weight); C2 tiered costs
      (5 bps equity / 10 bps crypto).

Model: GradientBoostingRegressor with the frozen C4 hyperparameters, refit
annually (every 52 rebalance dates) on the EXPANDING train window, last
anchor <= 2023-12-31; OOS predicted with the final train-fitted model only.

Gates (per leg, same as C1-C4): train consistency, OOS median 3-of-4
years > 0, Sharpe >= 1.0, maxDD >= -25%, CAGR >= 15% net, OOS mean > p95 of
1000x block-shuffle null (RNG seed 7). C5 bar_pass = L1 bar AND L2 bar.

Outputs:
  docs/data/cycle4_mega_evaluation.json  (per-leg gate verdicts + C5 verdict)
  docs/data/cycle4_mega_results.json     (full numbers per leg)
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import GradientBoostingRegressor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
sys.path.insert(0, os.path.join(BASE, "src"))
RNG = np.random.default_rng(7)

from cycle3_13f_engine import parse_xmls, build_ticker_resolver, LAG_DAYS  # noqa: E402
from alpha.indicators import compute_indicators  # noqa: E402

COST_BPS = 10  # L1 per side
EQUITY_COST_BPS = 0.0005  # L2 equity/index
CRYPTO_COST_BPS = 0.0010  # L2 crypto
CRYPTO = {"BTC-USD", "ETH-USD"}
TRAIN_END = pd.Timestamp("2023-12-31")
YEARS = ["2024", "2025", "2026", "2027"]
N_NULL = 1000
MIN_N_L1 = 20
MIN_N_L2 = 12  # ALL 12 instruments required (pre-reg A.4)
REBALANCE_PERIOD = 52  # annual refit on the expanding window

L2_INSTRUMENTS = [
    "SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "SLV", "HYG", "UUP",
    "BTC-USD", "ETH-USD",
]

MODEL_PARAMS = dict(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=3,
    min_samples_leaf=20,
    subsample=0.8,
    random_state=7,
    loss="squared_error",
)

XCOLS = ["r1w", "r2w", "r4w", "r12w", "r26w", "r52w",
         "vol20", "vol60", "rsi14", "d_sma20", "d_sma50", "d_sma200"]
TA_COLS = ["ema20_dist", "atr14_rel", "rsi14_daily", "macd_rel", "macd_sig_rel",
           "macd_hist_rel", "ha_close_dist", "bb_pos", "gk_vol", "var95", "cvar95"]
FUND_COLS = ["f13f_acc", "mom12_1", "rev1"]
L1_FEATS = XCOLS + TA_COLS + FUND_COLS  # 26
L2_FEATS = XCOLS + TA_COLS              # 23


def load_snapshot():
    with open(os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json"), encoding="utf-8") as f:
        return set(json.load(f)["ticker_to_names"].keys())


def load_ohlcv():
    out = {}
    for f in os.listdir(os.path.join(BASE, "market_data_2019_2026", "ohlcv")):
        if not f.endswith(".csv"):
            continue
        t = f[:-4].upper()
        if t in {"INSTRUMENTS", "MISSING"}:
            continue
        df = pd.read_csv(os.path.join(BASE, "market_data_2019_2026", "ohlcv", f),
                         parse_dates=["date"]).set_index("date").sort_index()
        out[t] = df
    return out


def rebalance_dates_union(closes, tickers):
    all_dates = pd.DatetimeIndex(sorted(set().union(*[closes[t].index for t in tickers])))
    s = pd.Series(all_dates, index=all_dates)
    return s.groupby(s.index.to_period("W")).max()


def rebalance_dates_spy(closes):
    eq = closes["SPY"].index
    s = pd.Series(eq, index=eq)
    return s.groupby(s.index.to_period("W")).max()


def rsi_wilder(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    return out.fillna(50.0)


def ta_features(ohlcv_df, rebal):
    """11 TA features from compute_indicators (daily OHLCV), at rebalance dates."""
    ind = ohlcv_df.rename(columns={"open": "Open", "high": "High",
                                   "low": "Low", "close": "Close"})
    if len(ind) < 20:
        return pd.DataFrame(index=rebal)
    ind = compute_indicators(ind)
    c = ind["Close"]
    ta = pd.DataFrame({
        "ema20_dist": c / ind["EMA_20"] - 1.0,
        "atr14_rel": ind["ATR_14"] / c,
        "rsi14_daily": ind["RSI_14"],
        "macd_rel": ind["MACD"] / c,
        "macd_sig_rel": ind["MACD_Signal"] / c,
        "macd_hist_rel": ind["MACD_Hist"] / c,
        "ha_close_dist": ind["HA_Close"] / c - 1.0,
        "bb_pos": (c - ind["BB_Lower"]) / (ind["BB_Upper"] - ind["BB_Lower"]),
        "gk_vol": ind["GK_Vol"],
        "var95": ind["VaR_95"],
        "cvar95": ind["CVaR_95"],
    }, index=ind.index)
    return ta.reindex(rebal)


def mom_rev(close_series, rebal):
    """MOM12-1 and REV1 from month-end closes; row M knowable at end of month
    M-1 -> used for any signal bar in month M (exact C2 factor_engine.py
    definition, no lookahead)."""
    monthly = close_series.groupby(close_series.index.to_period("M")).last()
    mom = monthly.shift(2) / monthly.shift(12) - 1.0
    rev = monthly.shift(1) / monthly.shift(2) - 1.0
    periods = pd.PeriodIndex(rebal, freq="M")
    return mom.reindex(periods).to_numpy(), rev.reindex(periods).to_numpy()


def build_13f_carry(closes, snapshot, rebal, ticker_to_names, fund_list):
    """acc per quarter (exact Claim 1 pipeline) -> carry-forward series at
    rebalance dates (pre-reg A.3 item 24: latest q with entry <= d)."""
    rows, _ = parse_xmls(set(fund_list))
    resolve = build_ticker_resolver(ticker_to_names)
    h = []
    for r in rows:
        if r["discretion"] != "SOLE":
            continue
        t, _ = resolve(r["name"], r["cls"])
        if t:
            r["ticker"] = t
            h.append(r)
    df13 = pd.DataFrame(h)
    shares = (df13.groupby(["fund", "quarter", "ticker"])["shares"]
              .sum().unstack("fund").fillna(0.0))
    quarters = sorted(df13["quarter"].unique())
    filing_funds = df13.groupby("quarter")["fund"].apply(set).to_dict()
    acc = {}
    for i, q in enumerate(quarters):
        cur = shares.loc[q]
        if i == 0:
            acc[q] = pd.Series(0.0, index=cur.index)
            continue
        prev = shares.loc[quarters[i - 1]]
        d = cur.sub(prev, fill_value=0.0)
        mask = pd.Series(cur.columns.isin(filing_funds.get(quarters[i - 1], set())),
                         index=cur.columns)
        acc[q] = d.mul(mask, axis=1).sum(axis=1)

    qend_map = {"1": "3-31", "2": "6-30", "3": "9-30", "4": "12-31"}
    qends = {q: pd.Timestamp(f"{q[:4]}-{qend_map[q[5:]]}")
             for q in quarters}
    entries = {q: qends[q] + pd.Timedelta(days=LAG_DAYS + 1) for q in quarters}
    qlist = sorted(quarters, key=lambda q: entries[q])
    earr = np.array([entries[q].value for q in qlist])
    acc_df = pd.DataFrame(acc).T  # quarters x tickers

    carry = pd.DataFrame(np.nan, index=rebal, columns=sorted(snapshot))
    for d in rebal:
        idx = int(np.searchsorted(earr, d.value, side="right")) - 1
        if idx >= 0:
            carry.loc[d] = acc_df.loc[qlist[idx]].reindex(snapshot)
    return carry


def build_panel(closes, ohlcv, rebal, tickers, feats, carry=None, months=None):
    """Long panel indexed by (date, ticker): features + fwd target.
    Rows with ANY NaN feature or target are dropped (no imputation, pre-reg A.3)."""
    frames = []
    for t in tickers:
        if t not in closes:
            continue
        c = closes[t]
        c_week = c.reindex(rebal)
        daily_ret = c.pct_change()
        vol20 = (daily_ret.rolling(20).std() * np.sqrt(252)).reindex(rebal)
        vol60 = (daily_ret.rolling(60).std() * np.sqrt(252)).reindex(rebal)
        sma20 = (c / c.rolling(20).mean() - 1.0).reindex(rebal)
        sma50 = (c / c.rolling(50).mean() - 1.0).reindex(rebal)
        sma200 = (c / c.rolling(200).mean() - 1.0).reindex(rebal)
        rsi14 = rsi_wilder(c_week)
        fwd = c_week.pct_change().shift(-1)
        f = pd.DataFrame({
            "r1w": c_week.pct_change(1),
            "r2w": c_week.pct_change(2),
            "r4w": c_week.pct_change(4),
            "r12w": c_week.pct_change(12),
            "r26w": c_week.pct_change(26),
            "r52w": c_week.pct_change(52),
            "vol20": vol20,
            "vol60": vol60,
            "rsi14": rsi14,
            "d_sma20": sma20,
            "d_sma50": sma50,
            "d_sma200": sma200,
            "fwd": fwd,
        }, index=rebal)
        ta = ta_features(ohlcv[t], rebal)
        f = f.join(ta)
        if carry is not None:
            f["f13f_acc"] = carry[t].reindex(rebal)
        if months is not None:
            mom, rev = months[t]
            f["mom12_1"] = mom
            f["rev1"] = rev
        f["ticker"] = t
        frames.append(f)
    df = pd.concat(frames)
    df = df.dropna(subset=feats + ["fwd"])
    return df


def rank_normalize(df, cols):
    """Cross-sectional rank -> uniform -> inverse normal CDF, per rebalance
    date (pre-reg A.2/B.2, no lookahead: per-date transform only)."""
    out = df.copy()
    for col in cols:
        out[col] = df.groupby(level=0)[col].transform(
            lambda s: norm.ppf(s.rank(method="average") / (len(s) + 1.0))
        )
    return out


def walk_forward(df, feats):
    """Expanding-window annual refits on train dates only; returns
    (train_pred_df, oos_pred_df, final_model, train_mask)."""
    dates = df.index.get_level_values(0)
    X = df[feats].astype(float)
    y = df["y"]
    train_mask = dates < TRAIN_END
    train_dates = sorted(df.index[train_mask].unique())
    anchors = train_dates[::REBALANCE_PERIOD]

    model = None
    for d in train_dates:
        if anchors and d >= anchors[0]:
            m = df.index.get_level_values(0) <= d
            model = GradientBoostingRegressor(**MODEL_PARAMS).fit(X[m].to_numpy(), y[m].to_numpy())
            anchors.pop(0)
    final_model = model

    anchors_all = train_dates[::REBALANCE_PERIOD]
    model = None
    train_pred = {}
    for d in train_dates:
        if anchors_all and d >= anchors_all[0]:
            m = df.index.get_level_values(0) <= d
            model = GradientBoostingRegressor(**MODEL_PARAMS).fit(X[m].to_numpy(), y[m].to_numpy())
            anchors_all.pop(0)
        sel = df.index.get_level_values(0) == d
        train_pred[d] = pd.Series(model.predict(X[sel].to_numpy()),
                                  index=df.loc[sel, "ticker"].to_numpy())
    train_pred_df = pd.DataFrame(train_pred).T

    oos_dates = sorted(df.index[~train_mask].unique())
    oos_pred = {}
    for d in oos_dates:
        sel = df.index.get_level_values(0) == d
        oos_pred[d] = pd.Series(final_model.predict(X[sel].to_numpy()),
                                index=df.loc[sel, "ticker"].to_numpy())
    oos_pred_df = pd.DataFrame(oos_pred).T
    return train_pred_df, oos_pred_df, final_model, train_mask


def factor_series(pred_df, ret_pivot, dates, min_n, cost_mode):
    """Portfolio from predictions. cost_mode: "decile10" (L1) or
    "quartile_tiered" (L2)."""
    factors = {}
    weights_prev = None
    for d in dates:
        p = pred_df.loc[d]
        r = ret_pivot.loc[d]
        both = p.index.intersection(r.index)
        if len(both) < min_n:
            weights_prev = None
            continue
        p = p[both]
        r = r[both]
        ranks = p.rank(method="average")
        n = len(both)
        if cost_mode == "decile10":
            hi = ranks > n - np.floor(n / 10)
            lo = ranks <= np.ceil(n / 10)
            if hi.sum() == 0 or lo.sum() == 0:
                weights_prev = None
                continue
            w = pd.Series(0.0, index=both)
            w[hi] = 1.0 / hi.sum()
            w[lo] = -1.0 / lo.sum()
            if weights_prev is None:
                turn = w.abs().sum()
            else:
                w2 = w.reindex(weights_prev.index).fillna(0.0)
                turn = (w - w2).abs().sum() + w2[w2.index.difference(w.index)].abs().sum()
            cost = COST_BPS / 1e4 * turn
        else:  # quartile_tiered (L2): top 3 long / bottom 3 short, equal weight
            nq = 3
            hi = ranks > n - nq
            lo = ranks <= nq
            if hi.sum() == 0 or lo.sum() == 0:
                weights_prev = None
                continue
            w = pd.Series(0.0, index=both)
            w[hi] = 1.0 / hi.sum()
            w[lo] = -1.0 / lo.sum()
            uniq = w.index.union(weights_prev.index) if weights_prev is not None else w.index
            wu = w.reindex(uniq).fillna(0.0)
            w2u = weights_prev.reindex(uniq).fillna(0.0) if weights_prev is not None else pd.Series(0.0, index=uniq)
            rates = pd.Series([CRYPTO_COST_BPS if s in CRYPTO else EQUITY_COST_BPS
                               for s in uniq], index=uniq)
            turn = (wu - w2u).abs()
            cost = float(turn.dot(rates))
        factors[d] = float((w * r).sum() - cost)
        weights_prev = w
    return pd.Series(factors).sort_index()


def evaluate(fser, label):
    train = fser[fser.index < TRAIN_END]
    oos = fser[fser.index >= TRAIN_END]
    train_consistency = bool(train.mean() > 0)
    oos_median = float(oos.median()) if len(oos) else float("nan")
    oos_mean = float(oos.mean()) if len(oos) else float("nan")
    oos_sharpe = float(oos.mean() / oos.std() * np.sqrt(52)) if len(oos) > 1 and oos.std() > 0 else float("nan")
    eq = (1 + oos).cumprod()
    oos_maxdd = float((eq / eq.cummax() - 1).min()) if len(eq) else float("nan")
    n_years = len(oos) / 52.0
    oos_cagr = float(eq.iloc[-1] ** (1 / n_years) - 1) if len(eq) and n_years > 0 and eq.iloc[-1] > 0 else float("nan")

    fkeys = list(fser.index)
    fvals = np.array(list(fser.values))
    oos_mask_arr = np.array([k >= TRAIN_END for k in fkeys])
    null_oos = []
    for _ in range(N_NULL):
        perm = RNG.permutation(len(fkeys))
        null_oos.append(float(fvals[perm][oos_mask_arr].mean()))
    null_oos = np.array(null_oos)
    p95 = float(np.percentile(null_oos, 95))
    null_pass = bool(oos_mean > p95)

    oos_years_pos = {y: bool(oos[oos.index.year == int(y)].median() > 0) for y in YEARS}
    n_years_pos = sum(1 for y in YEARS if oos_years_pos.get(y, False))
    bar_pass = (
        n_years_pos >= 3
        and oos_sharpe >= 1.0
        and oos_maxdd >= -0.25
        and oos_cagr >= 0.15
        and null_pass
        and train_consistency
    )
    gates = {
        "train_consistency": {"pass": train_consistency, "value": float(train.mean())},
        "oos_median_3of4_years": {"pass": n_years_pos >= 3, "value": oos_years_pos,
                                  "note": "2026 partial, 2027 not computable; earliest possible pass end-2027 (pre-registered)"},
        "oos_sharpe_ge_1": {"pass": bool(oos_sharpe >= 1.0), "value": oos_sharpe},
        "oos_maxdd_le_25": {"pass": bool(oos_maxdd >= -0.25), "value": oos_maxdd},
        "oos_cagr_ge_15_net": {"pass": bool(oos_cagr >= 0.15), "value": oos_cagr},
        "null_p95": {"pass": null_pass, "value": p95},
    }
    stats = {
        f"{label}_train_mean": float(train.mean()),
        f"{label}_oos_median": oos_median,
        f"{label}_oos_mean": oos_mean,
        f"{label}_oos_sharpe_annualized": oos_sharpe,
        f"{label}_oos_maxdd": oos_maxdd,
        f"{label}_oos_cagr_net": oos_cagr,
        f"{label}_oos_years_positive_median": oos_years_pos,
        f"{label}_null_p95_oos_mean": p95,
    }
    return gates, stats, bar_pass


def main():
    import time as _t
    def stage(msg):
        print(f"[{_t.strftime('%H:%M:%S')}] {msg}", flush=True)
    t0 = _t.time()
    snapshot = load_snapshot()
    ohlcv = load_ohlcv()
    closes = {t: df["close"] for t, df in ohlcv.items()}
    stage(f"loaded {len(ohlcv)} price files + snapshot {len(snapshot)}")

    # ---------------- LEG 1: 481-name weekly cross-section ----------------
    rebal1 = rebalance_dates_union(closes, snapshot)
    stage(f"rebal1 dates: {len(rebal1)}")
    with open(os.path.join(BASE, "market_data_2019_2026", "institutions", "13f_funds.csv"),
              encoding="utf-8") as f:
        import csv
        fund_list = [r["fund_slug"] for r in csv.DictReader(f)]
    with open(os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json"), encoding="utf-8") as f:
        ticker_to_names = json.load(f)["ticker_to_names"]
    stage("building 13F carry-forward...")
    carry = build_13f_carry(closes, snapshot, rebal1, ticker_to_names, fund_list)
    stage(f"carry done ({_t.time()-t0:.0f}s)")
    months = {t: mom_rev(closes[t], rebal1) for t in snapshot if t in closes}
    stage(f"mom/rev done ({_t.time()-t0:.0f}s)")
    panel1 = build_panel(closes, ohlcv, rebal1, snapshot, L1_FEATS, carry=carry, months=months)
    stage(f"L1 panel built: {len(panel1)} rows ({_t.time()-t0:.0f}s)")
    panel1["y"] = panel1.groupby(level=0)["fwd"].transform(
        lambda s: norm.ppf(s.rank(method="average") / (len(s) + 1.0)))
    panel1 = rank_normalize(panel1, L1_FEATS)
    stage(f"L1 panel normalized ({_t.time()-t0:.0f}s)")

    train_pred1, oos_pred1, model1, train_mask1 = walk_forward(panel1, L1_FEATS)
    stage(f"L1 walk-forward done ({_t.time()-t0:.0f}s)")
    ret_df1 = panel1[["fwd", "ticker"]].copy()
    ret_pivot1 = ret_df1.pivot(columns="ticker", values="fwd")
    train_dates1 = sorted(panel1.index[train_mask1].unique())
    oos_dates1 = sorted(panel1.index[~train_mask1].unique())
    train_f1 = factor_series(train_pred1, ret_pivot1, train_dates1, MIN_N_L1, "decile10")
    oos_f1 = factor_series(oos_pred1, ret_pivot1, oos_dates1, MIN_N_L1, "decile10")
    fser1 = pd.concat([train_f1, oos_f1]).sort_index()
    stage(f"L1 factor series done: train {len(train_f1)} / OOS {len(oos_f1)} ({_t.time()-t0:.0f}s)")

    # ---------------- LEG 2: 12-instrument multi-asset ----------------
    rebal2 = rebalance_dates_spy(closes)
    panel2 = build_panel(closes, ohlcv, rebal2, L2_INSTRUMENTS, L2_FEATS)
    stage(f"L2 panel built: {len(panel2)} rows ({_t.time()-t0:.0f}s)")
    panel2["y"] = panel2.groupby(level=0)["fwd"].transform(
        lambda s: norm.ppf(s.rank(method="average") / (len(s) + 1.0)))
    panel2 = rank_normalize(panel2, L2_FEATS)
    stage(f"L2 panel normalized ({_t.time()-t0:.0f}s)")

    train_pred2, oos_pred2, model2, train_mask2 = walk_forward(panel2, L2_FEATS)
    stage(f"L2 walk-forward done ({_t.time()-t0:.0f}s)")
    ret_df2 = panel2[["fwd", "ticker"]].copy()
    ret_pivot2 = ret_df2.pivot(columns="ticker", values="fwd")
    train_dates2 = sorted(panel2.index[train_mask2].unique())
    oos_dates2 = sorted(panel2.index[~train_mask2].unique())
    train_f2 = factor_series(train_pred2, ret_pivot2, train_dates2, MIN_N_L2, "quartile_tiered")
    oos_f2 = factor_series(oos_pred2, ret_pivot2, oos_dates2, MIN_N_L2, "quartile_tiered")
    fser2 = pd.concat([train_f2, oos_f2]).sort_index()
    stage(f"L2 factor series done: train {len(train_f2)} / OOS {len(oos_f2)} ({_t.time()-t0:.0f}s)")

    # ---------------- gates ----------------
    stage("evaluating gates + null...")
    gates1, stats1, bar1 = evaluate(fser1, "l1")
    gates2, stats2, bar2 = evaluate(fser2, "l2")
    bar_pass = bool(bar1 and bar2)  # Q17: BOTH legs required
    stage(f"gates done ({_t.time()-t0:.0f}s); bar1={bar1} bar2={bar2} C5={bar_pass}")

    log = [
        "Pre-reg: docs/data/cycle4_prereg_mega.md frozen 2026-08-16 BEFORE any backtest. No tuning.",
        "Installed-version delta (Appendix B.1): sklearn 1.6.1 / numpy 2.4.6 / pandas 3.0.5 used (frozen versions 1.9.0/2.2.0/2.2.3 not installed); declared BEFORE any run.",
        "L1 features (26, all rank-normalized per rebalance date): 12 C4 price features; 11 TA from compute_indicators (EMA20 dist, ATR14 rel, RSI14 daily, MACD/MACD_Signal/MACD_Hist rel, HA_Close dist, BB position, GK_Vol, VaR95, CVaR95); 13F accumulation carry-forward (latest quarter with entry date = q_end+45d+1d <= rebalance date, Claim 1 pipeline); MOM12-1/REV1 monthly (row M usable for signal bars in month M, C2 factor_engine.py).",
        "L2 features (23): price+TA only (13F/MOM12-1/REV1 excluded — not defined for ETFs/crypto, pre-reg A.4/Q15).",
        "Target (both legs): forward 1-week Friday-to-Friday return, rank-normalized within each rebalance date (norm.ppf(rank/(n+1))).",
        "Model (both legs, one frozen spec, SEPARATE fitted models): GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20, subsample=0.8, random_state=7); refit annually (every 52 rebalance dates) on the EXPANDING train window; last anchor <= 2023-12-31; OOS predicted with final train-fitted model only.",
        "L1 portfolio: decile L/S (top decile long, bottom decile short), equal weight, MIN_N=20; costs 10 bps/side turnover-based both legs (C4 convention).",
        "L2 portfolio: top/bottom QUARTILE L/S (top 3 long / bottom 3 short, equal weight), ALL 12 instruments required (MIN_N=12); costs C2 tiered: 5 bps/side equity/index, 10 bps/side crypto, turnover-based vs prior weights.",
        "L1 rebalance: last trading bar of each ISO week on the union of snapshot calendars. L2 rebalance: last trading bar of each ISO week on the SPY calendar; crypto reindexed to the same Fridays.",
        "Rows with ANY NaN feature or forward return dropped (no imputation, no feature selection — pre-reg A.3).",
        "First full-feature L1 row ~2020-01 (52w lag + 200d SMA + 12-month MOM12-1 warm-up; 13F first entry ~2019-05-16) — declared availability fact.",
        "OOS window 2024-01-01..2026-08-07: 2024, 2025 complete; 2026 partial; 2027 empty -> 3-of-4-complete-year rule cannot pass before end-2027 (pre-registered structural constraint).",
        "Null (per leg): 1000x permutation of the leg's weekly factor return series (block-shuffle on weekly rebalance dates), OOS-mean statistic, RNG seed 7.",
        "C5 verdict rule (Q17): BOTH legs must pass the full bar.",
    ]

    results = {
        "claim": "C5 Mega composite meta-model (two legs, one frozen spec)",
        "model_params": MODEL_PARAMS,
        "l1": {
            "n_train_rows": int(panel1.index[train_mask1].shape[0]),
            "n_oos_rows": int(panel1.index[~train_mask1].shape[0]),
            "train_dates": [str(d.date()) for d in train_f1.index],
            "oos_dates": [str(d.date()) for d in oos_f1.index],
            "weekly_factor_returns_net": {str(k.date()): float(v) for k, v in fser1.items()},
            "features": L1_FEATS,
        },
        "l2": {
            "n_train_rows": int(panel2.index[train_mask2].shape[0]),
            "n_oos_rows": int(panel2.index[~train_mask2].shape[0]),
            "train_dates": [str(d.date()) for d in train_f2.index],
            "oos_dates": [str(d.date()) for d in oos_f2.index],
            "weekly_factor_returns_net": {str(k.date()): float(v) for k, v in fser2.items()},
            "features": L2_FEATS,
        },
        **stats1, **stats2,
    }
    evaluation = {
        "claim": "C5 Mega composite meta-model",
        "legs": {
            "l1_481": {"gates": gates1, "bar_pass": bar1},
            "l2_multiasset": {"gates": gates2, "bar_pass": bar2},
        },
        "bar_pass": bar_pass,
        "note": "Q17: BOTH legs must pass the full bar.",
        "pending": {"note": "2026 weeks after 2026-08-07 and 2027 not yet computable"},
        "data_handling_log": log,
    }
    with open(os.path.join(BASE, "docs", "data", "cycle4_mega_evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=2)
    with open(os.path.join(BASE, "docs", "data", "cycle4_mega_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("== LEG 1 (481 names) ==")
    print(f"rows train: {len(train_f1)} | rows OOS: {len(oos_f1)}")
    print(f"train mean: {train_f1.mean():+.5f} | OOS median: {oos_f1.median():+.5f} | OOS mean: {oos_f1.mean():+.5f}")
    print(f"OOS Sharpe: {stats1['l1_oos_sharpe_annualized']:.2f} | maxDD: {stats1['l1_oos_maxdd']:.1%} | CAGR: {stats1['l1_oos_cagr_net']:.1%}")
    print(f"years positive: {stats1['l1_oos_years_positive_median']} | null p95: {stats1['l1_null_p95_oos_mean']:+.5f} | null pass: {gates1['null_p95']['pass']}")
    print(f"BAR PASS L1: {bar1}")
    print("== LEG 2 (multi-asset) ==")
    print(f"rows train: {len(train_f2)} | rows OOS: {len(oos_f2)}")
    print(f"train mean: {train_f2.mean():+.5f} | OOS median: {oos_f2.median():+.5f} | OOS mean: {oos_f2.mean():+.5f}")
    print(f"OOS Sharpe: {stats2['l2_oos_sharpe_annualized']:.2f} | maxDD: {stats2['l2_oos_maxdd']:.1%} | CAGR: {stats2['l2_oos_cagr_net']:.1%}")
    print(f"years positive: {stats2['l2_oos_years_positive_median']} | null p95: {stats2['l2_null_p95_oos_mean']:+.5f} | null pass: {gates2['null_p95']['pass']}")
    print(f"BAR PASS L2: {bar2}")
    print(f"== C5 BAR PASS (both legs): {bar_pass} ==")


if __name__ == "__main__":
    main()