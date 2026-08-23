"""H-SLX-1 — SL-adjusted-label GBDT exit overlay on us_momentum_top5.

Implements docs/data/ml_sl_exit_prereg.md EXACTLY as pre-registered (frozen
2026-08-24, commit 5e25748). No tuning; post-hoc changes prohibited.

Pipeline:
  1. Panel: frozen snapshot ∩ local OHLCV CSVs, SPY excluded from selection.
  2. Static-path simulation (monthly top-5, rank-drop exits) -> holding spells.
  3. SL-adjusted labels on static-path holding bars (K=10, delta=0.20, Low-based).
  4. Final model: HistGradientBoostingClassifier, monotonic_cst on pos_ret only,
     trained on ALL rows <= 2023-12-31; OOS predicted by this model ONLY.
  5. Arms: static vs ML-exit @ theta in {0.30, 0.40}; gates evaluated on the
     WORSE theta. Costs 5 bps/side, exec_delay 1, no drift rebalance (both arms).
  6. Gate 3: annual expanding refits <=Y-1 predict year Y over 2021-2023.
  7. Gate 4: 1000x circular block shuffle (block=10) of observed p_good, seed 7.

Outputs:
  docs/data/ml_sl_exit_results.json   (full numbers)
  docs/data/eval_ml_sl_exit.json      (gate verdicts ledger)
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OHLCV_DIR = os.path.join(BASE, "market_data_2019_2026", "ohlcv")
SNAP_PATH = os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json")
OUT_RESULTS = os.path.join(BASE, "docs", "data", "ml_sl_exit_results.json")
OUT_EVAL = os.path.join(BASE, "docs", "data", "eval_ml_sl_exit.json")

K = 10
DELTA = 0.20
THETAS = (0.30, 0.40)
TRAIN_END = pd.Timestamp("2023-12-31")
COST = 0.0005
TOP_N = 5
SKIP = 21
LB = 126
MIN_HIST = 260
START_POS = 260
N_NULL = 1000
BLOCK = 10
SEED = 7
INIT_EQUITY = 100_000.0
MIN_ORDER = 1.0
MARKET_FEATS = ["r1", "r2", "r5", "r21", "r63", "r252",
                "vol20", "vol60", "rsi14", "d_sma20", "d_sma50", "d_sma200"]
MONO_CST = [0] * 12 + [1]


def make_model():
    return HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20,
        l2_regularization=0.0, random_state=7, monotonic_cst=MONO_CST)


def load_snapshot_tickers():
    with open(SNAP_PATH, encoding="utf-8") as f:
        snap = set(json.load(f)["ticker_to_names"].keys())
    local = {f[:-4].upper() for f in os.listdir(OHLCV_DIR) if f.endswith(".csv")}
    return sorted((snap & local) - {"SPY"})


def rsi_wilder(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    ag = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = ag / al.replace(0.0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)


def build_panel():
    tickers = load_snapshot_tickers()
    frames = {}
    for t in tickers:
        df = pd.read_csv(os.path.join(OHLCV_DIR, f"{t}.csv"), parse_dates=["date"])
        frames[t] = df.set_index("date")[["low", "close"]].astype(float).sort_index()
    cal = pd.DatetimeIndex(sorted(set().union(*[f.index for f in frames.values()])))
    panel = {}
    for t, df in frames.items():
        close = df["close"].reindex(cal)
        low = df["low"].reindex(cal)
        ret = close.pct_change()
        feats = pd.DataFrame({
            "r1": close.pct_change(1), "r2": close.pct_change(2),
            "r5": close.pct_change(5), "r21": close.pct_change(21),
            "r63": close.pct_change(63), "r252": close.pct_change(252),
            "vol20": ret.rolling(20).std() * np.sqrt(252),
            "vol60": ret.rolling(60).std() * np.sqrt(252),
            "rsi14": rsi_wilder(close),
            "d_sma20": close / close.rolling(20).mean() - 1.0,
            "d_sma50": close / close.rolling(50).mean() - 1.0,
            "d_sma200": close / close.rolling(200).mean() - 1.0,
        }, index=cal)[MARKET_FEATS]
        panel[t] = {
            "close": close, "close_ffill": close.ffill(), "low": low,
            "mom": close.shift(SKIP) / close.shift(SKIP + LB) - 1.0,
            "hist_cnt": close.notna().cumsum().to_numpy(),
            "feats": feats,
        }
    return tickers, cal, panel


def month_end_mask(cal):
    periods = pd.Series(cal).dt.to_period("M")
    return ((periods != periods.shift(-1)).to_numpy())


def simulate(panel, cal, me_mask, start_i, end_i, predict_fn=None, theta=None,
             record_timeline=False):
    cash = INIT_EQUITY
    positions = {}
    pending_buys, pending_sells = [], []
    equity = np.empty(end_i - start_i + 1)
    n_trades = 0
    n_ml_exits = 0
    timeline = [] if record_timeline else None

    def px(t, i):
        v = panel[t]["close_ffill"].iloc[i]
        return np.nan if pd.isna(v) else float(v)

    for i in range(start_i, end_i + 1):
        for t in pending_sells:
            if t in positions:
                p = px(t, i)
                if p is not np.nan and not pd.isna(p):
                    rec = positions.pop(t)
                    cash += rec["shares"] * p * (1.0 - COST)
                    n_trades += 1
                    if record_timeline:
                        for sp in timeline:
                            if sp["ticker"] == t and sp["exit_i"] is None:
                                sp["exit_i"] = i
                                sp["exit_px"] = p
                                sp["reason"] = rec.get("pending_reason", sp["reason"])
                                break
        pending_sells = []

        eq_mark = cash + sum(rec["shares"] * px(t, i) for t, rec in positions.items())
        target = eq_mark / TOP_N
        for t in pending_buys:
            p = px(t, i)
            if pd.isna(p) or t in positions:
                continue
            notional = min(target, max(cash, 0.0))
            if notional < MIN_ORDER:
                continue
            shares = notional / (p * (1.0 + COST))
            cash -= shares * p * (1.0 + COST)
            positions[t] = {"shares": shares, "entry_px": p}
            n_trades += 1
            if record_timeline:
                timeline.append({"ticker": t, "entry_i": i, "entry_px": p,
                                 "exit_i": None, "exit_px": None, "reason": None})
        pending_buys = []

        if me_mask[i] and i < end_i:
            scores = {}
            for t, d in panel.items():
                m = d["mom"].iloc[i]
                if not pd.isna(m) and d["hist_cnt"][i] >= MIN_HIST:
                    scores[t] = float(m)
            top = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]]
            for t in list(positions):
                if t not in top:
                    pending_sells.append(t)
                    positions[t]["pending_reason"] = "rank_drop"
            for t in top:
                if t not in positions:
                    pending_buys.append(t)

        if predict_fn is not None:
            for t, rec in list(positions.items()):
                p_now = px(t, i)
                pos_ret = np.nan if pd.isna(p_now) else p_now / rec["entry_px"] - 1.0
                pv = predict_fn(t, i, pos_ret)
                if pv is not None and pv < theta and t not in pending_sells:
                    pending_sells.append(t)
                    rec["pending_reason"] = "ml_exit"
                    n_ml_exits += 1

        equity[i - start_i] = cash + sum(r["shares"] * px(t, i) for t, r in positions.items())

    out = {"equity": pd.Series(equity, index=cal[start_i:end_i + 1]),
           "trades": n_trades, "ml_exits": n_ml_exits}
    if record_timeline:
        out["timeline"] = timeline
    return out


def build_train_rows(panel, cal, timeline, last_i):
    rows_X, rows_y, rows_dates = [], [], []
    for sp in timeline:
        t = sp["ticker"]
        d = panel[t]
        for i in range(sp["entry_i"], sp["exit_i"] if sp["exit_i"] is not None else last_i + 1):
            dt = cal[i]
            if dt > TRAIN_END or i + K > last_i:
                continue
            c0 = d["close"].iloc[i]
            if pd.isna(c0):
                continue
            lows = d["low"].iloc[i + 1:i + K + 1].to_numpy(dtype=float)
            fwd = d["close"].iloc[i + K]
            if np.isnan(lows).all() or pd.isna(fwd):
                continue
            min_low = np.nanmin(lows) / c0 - 1.0
            label = 1 if (min_low >= -DELTA and fwd / c0 - 1.0 > 0) else 0
            xr = d["feats"].iloc[i].to_numpy(dtype=float).tolist()
            xr.append(c0 / sp["entry_px"] - 1.0)
            rows_X.append(xr)
            rows_y.append(label)
            rows_dates.append(dt)
    return (np.array(rows_X, dtype=float), np.array(rows_y, dtype=int),
            pd.DatetimeIndex(rows_dates))


def sharpe(rets):
    r = rets.dropna()
    if len(r) < 2:
        return 0.0
    sd = r.std(ddof=1)
    return 0.0 if sd == 0 or np.isnan(sd) else float(r.mean() / sd * np.sqrt(252))


def max_dd(eq):
    return float((eq / eq.cummax() - 1.0).min())


def cagr(eq):
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    return float((eq.iloc[-1] / eq.iloc[0]) ** (1.0 / years) - 1.0)


def yearly_returns(eq):
    r = eq.pct_change().dropna()
    return {str(y): float((1.0 + g).prod() - 1.0) for y, g in r.groupby(r.index.year)}


def block_shuffle(arr, rng):
    n_blocks = len(arr) // BLOCK
    out = arr.copy()
    if n_blocks > 1:
        blocks = arr[:n_blocks * BLOCK].reshape(n_blocks, BLOCK)
        out[:n_blocks * BLOCK] = blocks[rng.permutation(n_blocks)].reshape(-1)
    return out


def main():
    tickers, cal, panel = build_panel()
    me_mask = month_end_mask(cal)
    last_i = len(cal) - 1
    train_end_i = int(np.searchsorted(cal, TRAIN_END, side="right")) - 1
    oos_start_i = train_end_i + 1

    static_full = simulate(panel, cal, me_mask, START_POS, last_i, record_timeline=True)

    X, y, row_dates = build_train_rows(panel, cal, static_full["timeline"], last_i)
    base_rate = float(y.mean())

    model = make_model()
    model.fit(X, y)

    feat_store = {t: panel[t]["feats"] for t in tickers}

    class Pred:
        def __init__(self, mdl, store):
            self.mdl, self.store, self.cache, self.record = mdl, store, {}, None

        def __call__(self, t, i, pos_ret):
            key = (t, i, pos_ret)
            if key in self.cache:
                return self.cache[key]
            mf = self.store[t].iloc[i].to_numpy(dtype=float)
            xr = np.append(mf, pos_ret).reshape(1, -1)
            p = float(self.mdl.predict_proba(np.nan_to_num(xr, nan=-999.0))[:, 1][0])
            self.cache[key] = p
            if self.record is not None:
                self.record.setdefault(t, {})[i] = p
            return p

    pred_final = Pred(model, feat_store)
    pred_final.record = {}

    static_eq = static_full["equity"]
    stat_oos = static_eq.iloc[oos_start_i - START_POS:]
    stat_r = {"sharpe": sharpe(stat_oos.pct_change()), "cagr": cagr(stat_oos),
              "maxdd": max_dd(stat_oos), "trades": static_full["trades"],
              "yearly": yearly_returns(stat_oos)}

    ml_runs = {}
    for th in THETAS:
        run = simulate(panel, cal, me_mask, oos_start_i, last_i,
                       predict_fn=pred_final, theta=th)
        eq = run["equity"]
        ml_runs[th] = {"sharpe": sharpe(eq.pct_change()), "cagr": cagr(eq),
                       "maxdd": max_dd(eq), "trades": run["trades"],
                       "ml_exits": run["ml_exits"], "yearly": yearly_returns(eq)}

    deltas = {th: ml_runs[th]["sharpe"] - stat_r["sharpe"] for th in THETAS}
    worse_th = min(deltas, key=deltas.get)
    total_ml_exits = sum(ml_runs[th]["ml_exits"] for th in THETAS)

    gates = {}
    auto_fail = total_ml_exits < 20
    gates["auto_fail_insufficient_intervention"] = {
        "value": total_ml_exits, "bar": 20, "pass": not auto_fail}

    g1 = deltas[worse_th] >= 0.10
    g2 = abs(ml_runs[worse_th]["maxdd"]) <= abs(stat_r["maxdd"]) + 0.005
    gates["gate1_oos_sharpe_delta_ge_p10"] = {
        "value": deltas[worse_th], "bar": 0.10, "theta": worse_th, "pass": bool(g1)}
    gates["gate2_maxdd_not_worse"] = {
        "value": ml_runs[worse_th]["maxdd"], "baseline": stat_r["maxdd"],
        "tolerance": 0.005, "theta": worse_th, "pass": bool(g2)}

    fold_models = {}
    for year in (2021, 2022, 2023):
        cut = pd.Timestamp(year - 1, 12, 31)
        keep = row_dates <= cut
        Xf, yf = X[keep], y[keep]
        if len(Xf) > 50 and 0 < yf.sum() < len(yf):
            m = make_model()
            m.fit(Xf, yf)
            fold_models[year] = m

    def fold_predict(t, i, pos_ret):
        m = fold_models.get(cal[i].year)
        if m is None:
            return None
        mf = feat_store[t].iloc[i].to_numpy(dtype=float)
        xr = np.append(mf, pos_ret).reshape(1, -1)
        return float(m.predict_proba(np.nan_to_num(xr, nan=-999.0))[:, 1][0])

    is_static = simulate(panel, cal, me_mask, START_POS, train_end_i)
    is_ml = simulate(panel, cal, me_mask, START_POS, train_end_i,
                     predict_fn=fold_predict, theta=worse_th)
    ys, ym = yearly_returns(is_static["equity"]), yearly_returns(is_ml["equity"])
    fold_years = [yv for yv in (2021, 2022, 2023) if yv in ys and yv in ym]
    excesses = [ym[yv] - ys[yv] for yv in fold_years]
    mean_is_excess = float(np.mean(excesses)) if excesses else 0.0
    g3 = mean_is_excess > 0
    gates["gate3_train_consistency_sign"] = {
        "value": mean_is_excess, "fold_years": fold_years,
        "fold_excesses": dict(zip(map(str, fold_years), excesses)), "pass": bool(g3)}

    observed_D = deltas[worse_th]
    observed_pg = {}
    for t, v in pred_final.record.items():
        pairs = sorted(v.items())
        observed_pg[t] = np.array([p for _, p in pairs], dtype=float)

    null_D = []
    rng = np.random.default_rng(SEED)
    if not auto_fail:
        class ShufflePred:
            def __init__(self, mapping):
                self.mapping = mapping

            def __call__(self, t, i, pos_ret):
                arr = self.mapping.get(t)
                if arr is None:
                    return None
                off = i - oos_start_i
                if 0 <= off < len(arr):
                    return float(arr[off])
                return None

        for _ in range(N_NULL):
            shuf = {t: block_shuffle(a, rng) for t, a in observed_pg.items()}
            run = simulate(panel, cal, me_mask, oos_start_i, last_i,
                           predict_fn=ShufflePred(shuf), theta=worse_th)
            d_run = sharpe(run["equity"].pct_change()) - stat_r["sharpe"]
            null_D.append(d_run)
        p95 = float(np.percentile(null_D, 95))
        g4 = observed_D > p95
    else:
        p95, g4 = None, False
    gates["gate4_null_survival"] = {
        "value": observed_D, "null_p95": p95, "n_null": N_NULL,
        "block": BLOCK, "seed": SEED, "skipped_auto_fail": auto_fail, "pass": bool(g4)}

    bar_pass = (not auto_fail) and g1 and g2 and g3 and g4
    verdict = "FAIL_AUTO_INSUFFICIENT_INTERVENTION" if auto_fail else (
        "PASS" if bar_pass else "FAIL")

    results = {
        "claim": "H-SLX-1: SL-adjusted-label GBDT exit overlay beats static rank-drop exit "
                 "(OOS Sharpe +0.10, maxDD not worse, train-consistency sign, null survival)",
        "prereg": "docs/data/ml_sl_exit_prereg.md",
        "prereg_commit": "5e25748",
        "date": "2026-08-24",
        "universe": {"snapshot_local_intersection": len(tickers)},
        "train": {"rows": int(len(X)), "base_rate_label1": base_rate},
        "static_arm": stat_r,
        "ml_arms": {f"theta_{th}": v for th, v in ml_runs.items()},
        "worse_theta_selected": worse_th,
        "sharpe_deltas_by_theta": {str(th): deltas[th] for th in THETAS},
        "is_walk_forward": {"years": fold_years, "excesses": dict(zip(map(str, fold_years), excesses)),
                            "mean_is_excess": mean_is_excess},
        "null_test": {"n": N_NULL, "block": BLOCK, "seed": SEED,
                      "observed_D": observed_D, "p95": p95,
                      "null_mean": float(np.mean(null_D)) if null_D else None},
        "gates": gates,
        "verdict": verdict,
        "notes": ["Survivorship bias inherited from frozen today-membership snapshot; "
                  "identical across arms.",
                  "No interim drift rebalancing; same-day settlement; halted-name valuation "
                  "at last known close (both arms).",
                  "sklearn HGB substitutes unavailable xgboost; monotonic_cst native.",
                  "Null shuffles the observed-run p_good series (timing info beyond frequency)."],
    }
    with open(OUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    eval_ledger = {
        "claim": results["claim"],
        "family": "ml_exit_overlay",
        "candidate_id": "ml_sl_exit_v1",
        "date": "2026-08-24",
        "preregistration": "docs/data/ml_sl_exit_prereg.md",
        "bar_pass": bool(bar_pass),
        "checks": gates,
        "headline": {
            "static_oos_sharpe": stat_r["sharpe"],
            "static_oos_maxdd": stat_r["maxdd"],
            "worse_theta": worse_th,
            "worse_theta_oos_sharpe": ml_runs[worse_th]["sharpe"],
            "worse_theta_oos_maxdd": ml_runs[worse_th]["maxdd"],
            "total_oos_ml_exits": total_ml_exits,
            "train_base_rate": base_rate,
        },
        "verdict": verdict,
    }
    with open(OUT_EVAL, "w", encoding="utf-8") as f:
        json.dump(eval_ledger, f, indent=2)

    print(json.dumps({"verdict": verdict, "base_rate": base_rate,
                      "static_sharpe": stat_r["sharpe"], "static_dd": stat_r["maxdd"],
                      "ml": {str(th): {"sharpe": ml_runs[th]["sharpe"],
                                       "dd": ml_runs[th]["maxdd"],
                                       "ml_exits": ml_runs[th]["ml_exits"]}
                             for th in THETAS},
                      "gates": {k: v["pass"] for k, v in gates.items()}}, indent=2))


if __name__ == "__main__":
    main()
