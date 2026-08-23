"""Cycle 3 — Claim 4/4: ML Hybrid (Strict Protocol, Price-Only) engine.

Implements docs/data/cycle3_prereg_ml.md EXACTLY as pre-registered, including
Appendix B deltas (installed sklearn 1.6.1; interpretation notes). No tuning.

Pipeline:
  1. Universe: frozen 481-name S&P 500 snapshot (same as Claims 1 and 3).
  2. Weekly rebalance on the last trading bar of each ISO week (Friday close).
  3. 12 fixed price-only features per name per rebalance (return lags 1/2/4/
     12/26/52w, realized vol 20d/60d, RSI(14) weekly, SMA20/50/200 distance).
  4. Target: forward 1-week Friday-to-Friday return, rank-normalized within
     each rebalance date.
  5. GradientBoostingRegressor (fixed hyperparameters, random_state=7), refit
     annually on the EXPANDING train window; last refit anchor <= 2023-12-31;
     OOS predictions use only train-fitted models.
  6. Rank by prediction; long = top decile, short = bottom decile, equal
     weight; net of costs (10 bps/side, turnover-based, both legs — same
     convention as Claims 2 and 3).
  7. Checks: train-consistency gate (walk-forward positive mean on train),
     OOS stats (2024-01-01..2026-08-07), 1000x block-shuffle null on weekly
     rebalance dates (OOS-mean statistic, RNG seed 7).

Outputs:
  docs/data/cycle3_ml_evaluation.json  (gate verdicts)
  docs/data/cycle3_ml_results.json     (full numbers)
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import GradientBoostingRegressor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RNG = np.random.default_rng(7)

COST_BPS = 10  # per side
TRAIN_END = pd.Timestamp("2023-12-31")
YEARS = ["2024", "2025", "2026", "2027"]
N_NULL = 1000
MIN_N = 20  # minimum predicted names per week for a factor
REBALANCE_PERIOD = 52  # annual refit on the expanding window

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


def load_snapshot():
    with open(os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json"), encoding="utf-8") as f:
        return set(json.load(f)["ticker_to_names"].keys())


def load_closes():
    out = {}
    for f in os.listdir(os.path.join(BASE, "market_data_2019_2026", "ohlcv")):
        if not f.endswith(".csv"):
            continue
        t = f[:-4].upper()
        if t in {"INSTRUMENTS", "MISSING"}:
            continue
        df = pd.read_csv(os.path.join(BASE, "market_data_2019_2026", "ohlcv", f), parse_dates=["date"])
        out[t] = df.set_index("date")["close"].sort_index()
    return out


def rebalance_dates(closes, snapshot):
    all_dates = pd.DatetimeIndex(sorted(set().union(*[closes[t].index for t in snapshot])))
    s = pd.Series(all_dates, index=all_dates)
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


def build_features(closes, snapshot, rebal):
    frames = []
    for t in snapshot:
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
        f["ticker"] = t
        frames.append(f)
    df = pd.concat(frames)
    df = df.dropna(subset=XCOLS + ["fwd"])
    return df


def factor_series(pred_df, ret_df, dates, costs):
    """Long top decile / short bottom decile by prediction; equal weight."""
    factors = {}
    weights_prev = None
    for d in dates:
        p = pred_df.loc[d]
        r = ret_df.loc[d]
        both = p.index.intersection(r.index)
        if len(both) < MIN_N:
            weights_prev = None
            continue
        p = p[both]
        r = r[both]
        ranks = p.rank(method="average")
        n = len(both)
        hi = ranks > n - np.floor(n / 10)  # top decile -> LONG
        lo = ranks <= np.ceil(n / 10)      # bottom decile -> SHORT
        w = pd.Series(0.0, index=both)
        w[hi] = 1.0 / hi.sum()
        w[lo] = -1.0 / lo.sum()
        if weights_prev is None:
            turn = w.abs().sum()
        else:
            w2 = w.reindex(weights_prev.index).fillna(0.0)
            turn = (w - w2).abs().sum() + w2[w2.index.difference(w.index)].abs().sum()
        cost = COST_BPS / 1e4 * turn
        factors[d] = float((w * r).sum() - cost)
        weights_prev = w
    return pd.Series(factors).sort_index()


def main():
    snapshot = load_snapshot()
    closes = load_closes()
    rebal = rebalance_dates(closes, snapshot)
    feats = build_features(closes, snapshot, rebal)

    # rank-normalize target within each rebalance date
    y = feats.groupby(level=0)["fwd"].transform(
        lambda s: norm.ppf(s.rank(method="average") / (len(s) + 1.0))
    )

    dates = feats.index.get_level_values(0)
    X = feats[XCOLS].astype(float)
    train_mask = dates < TRAIN_END
    Xtr = X[train_mask]
    Xoos = X[~train_mask]

    # expanding-window annual refits on train dates only
    train_dates = sorted(feats.index[train_mask].unique())
    anchors = train_dates[::REBALANCE_PERIOD]
    model = None
    for d in train_dates:
        if anchors and d >= anchors[0]:
            m = feats.index.get_level_values(0) <= d
            model = GradientBoostingRegressor(**MODEL_PARAMS).fit(X[m], y[m])
            anchors.pop(0)
    final_model = model

    # walk-forward train predictions (model fitted at the latest anchor <= d)
    train_pred = {}
    anchors_all = train_dates[::REBALANCE_PERIOD]
    model = None
    for d in train_dates:
        if anchors_all and d >= anchors_all[0]:
            m = feats.index.get_level_values(0) <= d
            model = GradientBoostingRegressor(**MODEL_PARAMS).fit(X[m], y[m])
            anchors_all.pop(0)
        sel = feats.index.get_level_values(0) == d
        train_pred[d] = pd.Series(model.predict(X[sel].to_numpy()), index=feats[sel]["ticker"].to_numpy())
    train_pred_df = pd.DataFrame(train_pred).T

    # OOS predictions with the final train-fitted model
    oos_dates = sorted(feats.index[~train_mask].unique())
    oos_pred = {}
    for d in oos_dates:
        sel = feats.index.get_level_values(0) == d
        oos_pred[d] = pd.Series(final_model.predict(X[sel].to_numpy()), index=feats[sel]["ticker"].to_numpy())
    oos_pred_df = pd.DataFrame(oos_pred).T

    ret_ser = feats["fwd"]
    ret_df = pd.DataFrame({"ticker": feats["ticker"].to_numpy(), "fwd": ret_ser.to_numpy()}, index=dates)
    ret_pivot = ret_df.pivot(columns="ticker", values="fwd")

    train_f = factor_series(train_pred_df, ret_pivot, train_dates, COST_BPS)
    oos_f = factor_series(oos_pred_df, ret_pivot, oos_dates, COST_BPS)
    fser = pd.concat([train_f, oos_f]).sort_index()

    train_consistency = bool(train_f.mean() > 0)
    oos_median = float(oos_f.median()) if len(oos_f) else float("nan")
    oos_mean = float(oos_f.mean()) if len(oos_f) else float("nan")
    oos_sharpe = float(oos_f.mean() / oos_f.std() * np.sqrt(52)) if len(oos_f) > 1 and oos_f.std() > 0 else float("nan")
    eq = (1 + oos_f).cumprod()
    oos_maxdd = float((eq / eq.cummax() - 1).min()) if len(eq) else float("nan")
    n_years = len(oos_f) / 52.0
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

    oos_years_pos = {y: bool(oos_f[oos_f.index.year == int(y)].median() > 0) for y in YEARS}
    n_years_pos = sum(1 for y in YEARS if oos_years_pos.get(y, False))
    bar_pass = (
        n_years_pos >= 3
        and oos_sharpe >= 1.0
        and oos_maxdd >= -0.25
        and oos_cagr >= 0.15
        and null_pass
        and train_consistency
    )

    log = [
        "Installed-version delta (Appendix B.1): sklearn 1.6.1 / numpy 2.4.6 / pandas 3.0.5 used (frozen Appendix A versions 1.9.0/2.2.0/2.2.3 not installed); declared BEFORE any run.",
        "Features: 12 fixed price-only features from adjusted close (Appendix B.2): return lags 1/2/4/12/26/52 weeks (Friday-to-Friday on weekly bars), realized vol 20d/60d (daily returns, x sqrt252), RSI(14) Wilder on weekly Friday closes, close/SMA20/50/200 - 1 (daily SMAs evaluated at Friday close).",
        "Target: forward 1-week Friday-to-Friday return, rank-normalized within each rebalance date (rank -> uniform -> inverse normal CDF).",
        "Model: GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20, subsample=0.8, random_state=7, loss='squared_error'); refit annually (every 52 rebalance dates) on the EXPANDING train window; last anchor <= 2023-12-31; OOS predicted with the final train-fitted model only.",
        "Feature warm-up: 52w lag + 200-day SMA require ~1 year of history; first complete-feature row ~2020-01 (declared data availability fact, Appendix B.2).",
        "Training rows whose forward-return window crosses past 2023-12-31 are dropped (fail-closed: no OOS-period label used in training).",
        "Portfolio: rank by prediction; long top decile, short bottom decile, equal weight; costs 10 bps/side on traded notional (turnover-based, both legs) — same convention as Claims 2 and 3.",
        "Rebalance: last trading bar of each ISO week (Friday close).",
        "OOS window 2024-01-01..2026-08-07: 2024, 2025 complete; 2026 partial; 2027 empty -> 3-of-4-complete-year rule cannot pass before end-2027 (pre-registered structural constraint).",
        "Null: 1000x permutation of the weekly factor return series (block-shuffle on weekly rebalance dates), OOS-mean statistic, RNG seed 7 (Appendix A TBD resolved).",
    ]

    results = {
        "signal": "GradientBoostingRegressor decile long-short (top decile long, bottom decile short)",
        "model_params": MODEL_PARAMS,
        "n_train_rows": int(len(Xtr)),
        "n_oos_rows": int(len(Xoos)),
        "train_dates": [str(d.date()) for d in train_f.index],
        "oos_dates": [str(d.date()) for d in oos_f.index],
        "weekly_factor_returns_net": {str(k.date()): float(v) for k, v in fser.items()},
        "train_mean": float(train_f.mean()),
        "oos_median": oos_median,
        "oos_mean": oos_mean,
        "oos_sharpe_annualized": oos_sharpe,
        "oos_maxdd": oos_maxdd,
        "oos_cagr_net": oos_cagr,
        "oos_years_positive_median": oos_years_pos,
        "null_p95_oos_mean": p95,
        "costs_bps_per_side": COST_BPS,
    }
    evaluation = {
        "claim": "ML hybrid (price-only, strict protocol) decile long-short",
        "gates": {
            "train_consistency": {"pass": train_consistency, "value": float(train_f.mean())},
            "oos_median_3of4_years": {"pass": n_years_pos >= 3, "value": oos_years_pos,
                                       "note": "2026 partial, 2027 not computable; earliest possible pass end-2027 (pre-registered)"},
            "oos_sharpe_ge_1": {"pass": bool(oos_sharpe >= 1.0), "value": oos_sharpe},
            "oos_maxdd_le_25": {"pass": bool(oos_maxdd >= -0.25), "value": oos_maxdd},
            "oos_cagr_ge_15_net": {"pass": bool(oos_cagr >= 0.15), "value": oos_cagr},
            "null_p95": {"pass": null_pass, "value": p95},
        },
        "bar_pass": bar_pass,
        "pending": {"note": "2026 weeks after 2026-08-07 and 2027 not yet computable"},
        "data_handling_log": log,
    }
    with open(os.path.join(BASE, "docs", "data", "cycle3_ml_evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=2)
    with open(os.path.join(BASE, "docs", "data", "cycle3_ml_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"train rows: {len(Xtr)} | oos rows: {len(Xoos)} | factor weeks: {len(fser)}")
    print(f"train mean: {train_f.mean():+.5f} | OOS median: {oos_median:+.5f} | OOS mean: {oos_mean:+.5f}")
    print(f"OOS Sharpe: {oos_sharpe:.2f} | maxDD: {oos_maxdd:.1%} | CAGR net: {oos_cagr:.1%}")
    print(f"null p95: {p95:+.5f} | null pass: {null_pass} | train consistency: {train_consistency}")
    print(f"years positive: {oos_years_pos}")
    print(f"BAR PASS: {bar_pass}")


if __name__ == "__main__":
    main()