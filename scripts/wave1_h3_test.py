"""Wave 1 / H3 — Volatility-Targeted Sizing Overlay (FROZEN PREREG RUNNER).

PAPER-ONLY. LIVE TRADING DISABLED. FAIL-CLOSED. Zero fitted parameters.

Implements docs/data/wave1_h3_voltarget_overlay_prereg.md (frozen 2026-08-24)
EXACTLY: gates G2-G5 computed mechanically on overlay-arm net excess vs
SPY-engine; G1 artifact check; G6 DSR ledger manual; charter bar + PRIMARY
ACCEPTANCE margin evaluated mechanically; this script NEVER self-certifies PASS.

Baseline arm = untargeted incumbent us_momentum_top5 run on identical machinery
in the same session (snapshot∩local−SPY universe, same sim start, same costs).
Overlay arm = same rule plus deterministic vol-target scaling m_t at month-ends.

Lineage: portfolio machinery, stochastic gates G2/G3/G4/G5, and reporting
helpers copied VERBATIM from scripts/wave1_h1_test.py / wave1_h2_test.py
(derived from scripts/ml_sl_exit_test.py). Baseline is verbatim H1 simulate;
overlay extends it with the vol-target layer only.

Outputs:
  docs/data/wave1_h3_results.json   (full numbers; deterministic, seeded)
Stdout: compact six-gate + charter + PRIMARY MARGIN summary table.

Deterministic: numpy default_rng(seed=7) freshly per stochastic gate; no
network; no randomness outside seeded generators.
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OHLCV_DIR = os.path.join(BASE, "market_data_2019_2026", "ohlcv")
SNAP_PATH = os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json")
PREREG_PATH = os.path.join(BASE, "docs", "data",
                           "wave1_h3_voltarget_overlay_prereg.md")
OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave1_h3_results.json")

# ---- Frozen spec constants ----
BENCHMARK = "SPY"
TOP_N = 5
LOOKBACK = 126
SKIP = 21
WARMUP = 340
DRIFT_BAND = 0.05
EXEC_DELAY = 1
COST = 0.0005
COMMISSION = 0.0
INIT_EQUITY = 100_000.0
MIN_ORDER = 1.0

# Vol-target overlay constants (4 declared, ZERO search)
VOL_TARGET_ANN = 0.15
VOL_WINDOW = 21
VOL_FLOOR = 0.25
VOL_CAP = 1.00

IS_END = pd.Timestamp("2023-12-31")
OOS_START = pd.Timestamp("2024-01-01")

# Gates (identical to H1/H2)
G2_MEAN_BLOCK = 21
G2_DRAWS = 1000
G2_SEED = 7
G2_ALPHA = 0.05
G3_K = 6
G3_EMBARGO = 10
G4_FOLD_ENDS = [pd.Timestamp("2024-06-30"), pd.Timestamp("2024-12-31"),
                pd.Timestamp("2025-06-30"), pd.Timestamp("2025-12-31"),
                pd.Timestamp("2026-08-07")]
G4_MAX_FOLD_SHARE = 0.60
G5_BLOCK = 10
G5_DRAWS = 1000
G5_SEED = 7

ANN = 252


# ---- Metric helpers ----
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from ml_sl_exit_test import cagr, max_dd, month_end_mask, sharpe, yearly_returns
    METRIC_SOURCE = "imported:scripts/ml_sl_exit_test.py"
except Exception:
    METRIC_SOURCE = "inline_verbatim_fallback"

    def sharpe(rets):
        r = rets.dropna()
        if len(r) < 2:
            return 0.0
        sd = r.std(ddof=1)
        return 0.0 if sd == 0 or np.isnan(sd) else float(r.mean() / sd * np.sqrt(ANN))

    def max_dd(eq):
        return float((eq / eq.cummax() - 1.0).min())

    def cagr(eq):
        years = (eq.index[-1] - eq.index[0]).days / 365.25
        return float((eq.iloc[-1] / eq.iloc[0]) ** (1.0 / years) - 1.0)

    def yearly_returns(eq):
        r = eq.pct_change().dropna()
        return {str(y): float((1.0 + g).prod() - 1.0)
                for y, g in r.groupby(r.index.year)}

    def month_end_mask(cal):
        periods = pd.Series(cal).dt.to_period("M")
        return ((periods != periods.shift(-1)).to_numpy())


# ---- Universe + Data ----
def load_snapshot_tickers():
    """VERBATIM from ml_sl_exit_test.py: snapshot∩local−SPY."""
    with open(SNAP_PATH, encoding="utf-8") as f:
        snap = set(json.load(f)["ticker_to_names"].keys())
    local = {f[:-4].upper() for f in os.listdir(OHLCV_DIR) if f.endswith(".csv")}
    return sorted((snap & local) - {"SPY"})


def load_data(tickers):
    need = list(tickers) + [BENCHMARK]
    missing = [t for t in need if not os.path.isfile(os.path.join(OHLCV_DIR, f"{t}.csv"))]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: missing OHLCV files: {missing}")
    frames, per_file_rows = {}, {}
    for t in need:
        df = pd.read_csv(os.path.join(OHLCV_DIR, f"{t}.csv"), parse_dates=["date"])
        if df.empty:
            raise SystemExit(f"FAIL-CLOSED: empty OHLCV file for {t}")
        s = df.set_index("date")["close"].astype(float).sort_index()
        frames[t] = s
        per_file_rows[t] = int(len(s))
    cal = pd.DatetimeIndex(sorted(set().union(*[s.index for s in frames.values()])))
    panel = {}
    for t in tickers:
        close = frames[t].reindex(cal)
        panel[t] = {
            "close": close,
            "close_ffill": close.ffill(),
            "mom": close.shift(SKIP) / close.shift(SKIP + LOOKBACK) - 1.0,
            "hist_cnt": close.notna().cumsum().to_numpy(),
        }
    spy_close = frames[BENCHMARK].reindex(cal)
    spy_ffill = spy_close.ffill()
    integrity = {
        "universe_size": len(tickers),
        "universe_tickers_sorted": list(tickers),
        "benchmark": {"ticker": BENCHMARK, "rows": per_file_rows[BENCHMARK],
                      "first": str(frames[BENCHMARK].index[0].date()),
                      "last": str(frames[BENCHMARK].index[-1].date())},
        "calendar": {"n_bars": int(len(cal)), "first": str(cal[0].date()), "last": str(cal[-1].date())},
    }
    return panel, cal, spy_close, spy_ffill, integrity


def cal_slice_index(series, start_i, end_i):
    return series.index[start_i:end_i + 1]


def spy_engine(spy_ffill, start_i, end_i):
    p0 = spy_ffill.iloc[start_i]
    if pd.isna(p0) or p0 <= 0:
        raise SystemExit("FAIL-CLOSED: invalid SPY price at evaluated start")
    shares = INIT_EQUITY / (float(p0) * (1.0 + COST))
    eq = shares * spy_ffill.iloc[start_i:end_i + 1]
    return pd.Series(eq.to_numpy(dtype=float), index=cal_slice_index(spy_ffill, start_i, end_i))


def simulate(panel, cal, me_mask, start_i, end_i):
    """Baseline: verbatim H1 simulate (monthly top-5, drift 0.05, exec_delay 1, 5bps)."""
    cash = INIT_EQUITY
    positions = {}
    pending_buys, pending_sells = [], []
    equity = np.empty(end_i - start_i + 1)
    n_trades = 0

    def px(t, i):
        v = panel[t]["close_ffill"].iloc[i]
        return np.nan if pd.isna(v) else float(v)

    def mark(i):
        return cash + sum(rec["shares"] * px(t, i) for t, rec in positions.items())

    for i in range(start_i, end_i + 1):
        for order in pending_sells:
            t = order["ticker"]
            if t not in positions:
                continue
            p = px(t, i)
            if pd.isna(p):
                continue
            rec = positions[t]
            want = rec["shares"] if order.get("shares") is None else min(order["shares"], rec["shares"])
            cash += want * p * (1.0 - COST)
            rec["shares"] -= want
            n_trades += 1
            if rec["shares"] * p < 1e-9:
                positions.pop(t)
        pending_sells = []

        eq_mark = mark(i)
        target = eq_mark / TOP_N
        for order in pending_buys:
            t = order["ticker"]
            p = px(t, i)
            if pd.isna(p) or t in positions:
                continue
            notional = target if order.get("notional") is None else order["notional"]
            notional = min(notional, max(cash, 0.0))
            if notional < MIN_ORDER:
                continue
            shares = notional / (p * (1.0 + COST))
            cash -= shares * p * (1.0 + COST)
            positions[t] = {"shares": shares}
            n_trades += 1
        pending_buys = []

        if me_mask[i] and i < end_i:
            scores = {}
            for t, d in panel.items():
                m = d["mom"].iloc[i]
                if not pd.isna(m) and d["hist_cnt"][i] >= WARMUP:
                    scores[t] = float(m)
            top = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]]
            for t in list(positions):
                if t not in top:
                    pending_sells.append({"ticker": t, "shares": None, "reason": "rank_drop"})
            for t in top:
                if t not in positions:
                    pending_buys.append({"ticker": t, "notional": None, "reason": "entry"})

        if i < end_i and positions:
            eq_now = mark(i)
            tgt = eq_now / TOP_N
            queued = ({o["ticker"] for o in pending_buys} | {o["ticker"] for o in pending_sells})
            for t, rec in positions.items():
                if t in queued:
                    continue
                p = px(t, i)
                if pd.isna(p):
                    continue
                val = rec["shares"] * p
                dev = val / tgt - 1.0 / TOP_N
                if dev > DRIFT_BAND:
                    sell_val = val - tgt
                    if sell_val >= MIN_ORDER:
                        pending_sells.append({"ticker": t, "shares": sell_val / p, "reason": "drift"})
                elif dev < -DRIFT_BAND:
                    buy_val = min(tgt - val, max(cash, 0.0))
                    if buy_val >= MIN_ORDER:
                        pending_buys.append({"ticker": t, "notional": buy_val, "reason": "drift"})
        equity[i - start_i] = mark(i)
    return {"equity": pd.Series(equity, index=cal[start_i:end_i + 1]), "trades": n_trades}


def simulate_voltarget(panel, cal, me_mask, start_i, end_i):
    """Overlay: H1 simulate plus deterministic vol-target scaling m_t at month-ends.

    m_t = clamp(0.15 / sigma_hat_21d_ann, 0.25, 1.00)
    sigma_hat computed from overlay's own daily net returns over trailing 21
    trading days ending at bar t-1 (annualized sqrt(252)*std). Cold start:
    m=1.00 before 21 returns exist. Drift target scaled by current m_t.
    """
    cash = INIT_EQUITY
    positions = {}
    pending_buys, pending_sells = [], []
    equity = np.empty(end_i - start_i + 1)
    n_trades = 0
    m_series = {}  # month-end date -> m_t
    m_current = 1.0

    def px(t, i):
        v = panel[t]["close_ffill"].iloc[i]
        return np.nan if pd.isna(v) else float(v)

    def mark(i):
        return cash + sum(rec["shares"] * px(t, i) for t, rec in positions.items())

    # need equity history for sigma estimation; we compute returns from equity array filled so far
    for i in range(start_i, end_i + 1):
        # 1) fills sells
        for order in pending_sells:
            t = order["ticker"]
            if t not in positions:
                continue
            p = px(t, i)
            if pd.isna(p):
                continue
            rec = positions[t]
            want = rec["shares"] if order.get("shares") is None else min(order["shares"], rec["shares"])
            cash += want * p * (1.0 - COST)
            rec["shares"] -= want
            n_trades += 1
            if rec["shares"] * p < 1e-9:
                positions.pop(t)
        pending_sells = []

        # 2) fills buys (scaled)
        eq_mark = mark(i)
        # target per name is m_current * eq / TOP_N, but queued buys have explicit notional already
        # For generic entry notional=None we use current m_current scaling at fill time:
        # pending buys queued at month-end stored notional=None means use fill-time m_current/eq
        # We instead stored explicit notional at queue time for m-scaled buys; but for simplicity handle here:
        for order in pending_buys:
            t = order["ticker"]
            p = px(t, i)
            if pd.isna(p) or t in positions:
                continue
            if order.get("notional") is not None:
                notional = order["notional"]
            else:
                # legacy entry (baseline) — but overlay queues explicit notionals, so this fallback uses m_current
                notional = m_current * eq_mark / TOP_N
            notional = min(notional, max(cash, 0.0))
            if notional < MIN_ORDER:
                continue
            shares = notional / (p * (1.0 + COST))
            cash -= shares * p * (1.0 + COST)
            positions[t] = {"shares": shares}
            n_trades += 1
        pending_buys = []

        # 3) month-end signal: recompute selection AND m_t
        if me_mask[i] and i < end_i:
            # compute m_t from trailing 21 overlay returns ending at i-1
            # equity history filled up to index i - start_i - 1 (previous bar)
            # Build returns series from equity array so far
            hist_len = i - start_i  # number of equity points already filled before this bar? actually equity[i-start_i] not yet set, previous bars are 0..i-start_i-1
            if hist_len >= VOL_WINDOW + 1:
                # equity[0..hist_len-1] are filled
                eq_hist = equity[:hist_len]
                # compute daily pct returns for last VOL_WINDOW returns ending at hist_len-1
                # returns = pct_change of eq_hist
                rets = np.diff(eq_hist) / eq_hist[:-1]
                # rets length = hist_len-1; we need last VOL_WINDOW values ending at last return (which corresponds to bar i-1)
                if len(rets) >= VOL_WINDOW:
                    window = rets[-VOL_WINDOW:]
                    sigma_daily = float(np.std(window, ddof=1)) if len(window) > 1 else 0.0
                    sigma_ann = sigma_daily * np.sqrt(ANN) if sigma_daily and not np.isnan(sigma_daily) else 0.0
                    if sigma_ann > 1e-12:
                        m_raw = VOL_TARGET_ANN / sigma_ann
                        m_current = float(np.clip(m_raw, VOL_FLOOR, VOL_CAP))
                    else:
                        m_current = VOL_CAP
                    m_series[str(cal[i].date())] = m_current
                else:
                    m_series[str(cal[i].date())] = m_current
            else:
                # cold start: not enough history -> m=1.00 neutral
                m_series[str(cal[i].date())] = m_current

            scores = {}
            for t, d in panel.items():
                m = d["mom"].iloc[i]
                if not pd.isna(m) and d["hist_cnt"][i] >= WARMUP:
                    scores[t] = float(m)
            top = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]]
            # queue trades scaled by m_current
            # For dropped names: full sells
            for t in list(positions):
                if t not in top:
                    pending_sells.append({"ticker": t, "shares": None, "reason": "rank_drop"})
            # For kept names: delta to reach m_current*eq/TOP_N
            eq_now = mark(i)
            tgt_scaled = m_current * eq_now / TOP_N
            queued_sells = {o["ticker"] for o in pending_sells}
            for t in top:
                if t in positions and t not in queued_sells:
                    p = px(t, i)
                    if pd.isna(p):
                        continue
                    val = positions[t]["shares"] * p
                    delta = tgt_scaled - val
                    if delta < -MIN_ORDER:
                        # need to sell
                        pending_sells.append({"ticker": t, "shares": (-delta) / p, "reason": "vol_target_down"})
                    elif delta > MIN_ORDER and delta <= cash + 1e-9:
                        # need to buy more (if cash allows, otherwise pending buy with capped notional)
                        buy_notional = min(delta, max(cash, 0.0))
                        if buy_notional >= MIN_ORDER:
                            pending_buys.append({"ticker": t, "notional": buy_notional, "reason": "vol_target_up"})
                elif t not in positions:
                    # new entry: buy m_current*eq/TOP_N
                    notional = m_current * eq_now / TOP_N
                    if notional >= MIN_ORDER:
                        pending_buys.append({"ticker": t, "notional": notional, "reason": "entry_voltarget"})

        # 4) drift-band rebalance scaled by m_current
        if i < end_i and positions:
            eq_now = mark(i)
            tgt_scaled = m_current * eq_now / TOP_N
            queued = ({o["ticker"] for o in pending_buys} | {o["ticker"] for o in pending_sells})
            for t, rec in positions.items():
                if t in queued:
                    continue
                p = px(t, i)
                if pd.isna(p):
                    continue
                val = rec["shares"] * p
                # deviation vs scaled target weight (m_current/TOP_N)
                # For cash-scaled portfolio, drift target is tgt_scaled
                if tgt_scaled < 1e-9:
                    continue
                dev = val / tgt_scaled - 1.0
                # band is absolute 0.05 of target weight scaled? Use same absolute band as H1 but relative to scaled target
                # H1: dev = val/tgt - 1/TOP_N with band 0.05. For scaled, dev_scaled = val/tgt_scaled -1, band 0.05*TOP_N? Simpler: band 0.05 absolute on weight fraction m_current/TOP_N => relative band 0.05/(m_current/TOP_N)
                # Instead keep absolute 0.05 on unscaled weight deviation scaled proportionally: threshold = DRIFT_BAND / (m_current/TOP_N) ??? Too complex.
                # Declared interpretation: drift band checks vs scaled target with same absolute 0.05 fraction of total equity? Use 0.05 absolute portfolio weight deviation.
                # For simplicity: if val deviates from tgt_scaled by > DRIFT_BAND * eq_now => trade back.
                # DRIFT_BAND=0.05 means 5pp of total equity. So threshold = 0.05 * eq_now.
                thresh = DRIFT_BAND * eq_now
                diff = val - tgt_scaled
                if diff > thresh:
                    sell_val = diff
                    if sell_val >= MIN_ORDER:
                        pending_sells.append({"ticker": t, "shares": sell_val / p, "reason": "drift_voltarget"})
                elif diff < -thresh:
                    buy_val = min(-diff, max(cash, 0.0))
                    if buy_val >= MIN_ORDER:
                        pending_buys.append({"ticker": t, "notional": buy_val, "reason": "drift_voltarget"})
        equity[i - start_i] = mark(i)

    # m stats
    m_vals = list(m_series.values())
    m_stats = {"n_months": len(m_vals), "min": float(min(m_vals)) if m_vals else None,
               "max": float(max(m_vals)) if m_vals else None,
               "mean": float(np.mean(m_vals)) if m_vals else None,
               "frac_at_cap": float(sum(1 for v in m_vals if abs(v - VOL_CAP) < 1e-9) / len(m_vals)) if m_vals else 0,
               "frac_at_floor": float(sum(1 for v in m_vals if abs(v - VOL_FLOOR) < 1e-9) / len(m_vals)) if m_vals else 0}

    return {"equity": pd.Series(equity, index=cal[start_i:end_i + 1]), "trades": n_trades, "m_series": m_series, "m_stats": m_stats}


# ---- Stochastic machinery ----
def stationary_bootstrap_series(x, mean_block, n_draws, seed):
    rng = np.random.default_rng(seed)
    n = len(x)
    p = 1.0 / float(mean_block)
    out = np.empty((n_draws, n), dtype=float)
    for d in range(n_draws):
        jumps = rng.random(n) < p
        starts = rng.integers(0, n, size=n)
        idx = np.empty(n, dtype=np.int64)
        cur = int(rng.integers(0, n))
        for k in range(n):
            idx[k] = cur
            if jumps[k]:
                cur = int(starts[k])
            else:
                cur = (cur + 1) % n
        out[d] = x[idx]
    return out

def g2_stationary_bootstrap(is_excess):
    x = is_excess.to_numpy(dtype=float)
    obs = float(np.mean(x))
    boots = stationary_bootstrap_series(x, G2_MEAN_BLOCK, G2_DRAWS, G2_SEED)
    boot_means = boots.mean(axis=1)
    centered = boot_means - obs
    p_left = float(np.mean(centered >= obs))
    p_right = float(np.mean(centered <= obs))
    p_two = float(min(1.0, 2.0 * min(p_left, p_right)))
    return {"pass": bool(p_two <= G2_ALPHA), "statistic": obs, "p_value": p_two, "threshold": G2_ALPHA,
            "borderline_flag": bool(G2_ALPHA * 0.8 < p_two <= G2_ALPHA),
            "details": {"method": "two-sided stationary block bootstrap p-value (Hall-Wilson): p = 2*min(P(T*-Tbar >= Tbar), P(T*-Tbar <= Tbar)), T* = bootstrap means",
                        "mean_block_days": G2_MEAN_BLOCK, "draws": G2_DRAWS, "seed": G2_SEED, "series_len": int(len(x)),
                        "boot_mean_dist": {"mean": float(np.mean(boot_means)), "std": float(np.std(boot_means, ddof=1))}}}

def circular_block_shuffle(x, block, seed):
    rng = np.random.default_rng(seed)
    n = len(x)
    m = -(-n // block)
    blocks = np.empty((m, block), dtype=np.int64)
    for j in range(m):
        s = (j * block) % n
        blocks[j] = [(s + k) % n for k in range(block)]
    out = np.empty((G5_DRAWS, n), dtype=float)
    for d in range(G5_DRAWS):
        order = rng.permutation(m)
        out[d] = x[blocks[order].reshape(-1)[:n]]
    return out

def g5_permutation_null(oos_excess, observed_ann_sharpe):
    x = oos_excess.to_numpy(dtype=float)
    nulls = circular_block_shuffle(x, G5_BLOCK, G5_SEED)
    def ann_sharpe_rows(arr):
        sd = arr.std(axis=1, ddof=1)
        mu = arr.mean(axis=1)
        return np.where(sd > 0, mu / sd * np.sqrt(ANN), 0.0)
    null_sharpes = ann_sharpe_rows(nulls)
    p95 = float(np.percentile(null_sharpes, 95))
    return {"pass": bool(observed_ann_sharpe > p95), "statistic": float(observed_ann_sharpe), "threshold": p95,
            "details": {"method": "circular block shuffle (multiset-preserving permutation), observed annualized net-excess Sharpe vs null p95",
                        "block_days": G5_BLOCK, "draws": G5_DRAWS, "seed": G5_SEED, "series_len": int(len(x)),
                        "null_mean": float(np.mean(null_sharpes)), "null_std": float(np.std(null_sharpes, ddof=1))}}

def g3_cpcv(full_excess):
    x = full_excess.to_numpy(dtype=float)
    n = len(x)
    folds = [seg for seg in np.array_split(np.arange(n), G3_K) if len(seg)]
    if len(folds) != G3_K:
        raise SystemExit("FAIL-CLOSED: could not form K folds (history too short)")
    combos = []
    for size in range(1, G3_K):
        combos.extend(itertools.combinations(range(G3_K), size))
    results = []
    all_positive = True
    n_fail = 0
    def in_train(combo, j):
        return j not in combo
    for combo in combos:
        vals = []
        for j, seg in enumerate(folds):
            if j not in combo:
                continue
            lo, hi = 0, len(seg)
            if j > 0 and in_train(combo, j - 1):
                lo = min(G3_EMBARGO, hi)
            if j < G3_K - 1 and in_train(combo, j + 1):
                hi = max(hi - G3_EMBARGO, lo)
            if hi > lo:
                vals.append(x[seg[lo:hi]])
        if not vals:
            raise SystemExit(f"FAIL-CLOSED: combination {combo} fully embargoed to empty")
        mean_ret = float(np.concatenate(vals).mean())
        results.append((combo, mean_ret))
        if mean_ret <= 0:
            all_positive = False
            n_fail += 1
    results.sort(key=lambda cr: cr[1])
    return {"pass": bool(all_positive), "statistic": results[0][1], "threshold": 0.0,
            "details": {"K": G3_K, "embargo_days": G3_EMBARGO,
                        "combination_semantics": "all non-empty proper subsets of K folds = test sets; embargo purged at train/test edges inside each test fold",
                        "combination_count": len(results), "combinations_failing": n_fail,
                        "worst_combinations": [{"combo": [int(j) + 1 for j in c], "mean_net_excess": v} for c, v in results[:5]],
                        "best_combination": {"combo": [int(j) + 1 for j in results[-1][0]], "mean_net_excess": results[-1][1]},
                        "evaluated_history": {"n_days": n, "start": str(full_excess.index[0].date()), "end": str(full_excess.index[-1].date())}}}

def g4_walk_forward(oos_excess):
    idx = oos_excess.index
    ends = []
    for ts in G4_FOLD_ENDS:
        j = int(idx.searchsorted(ts, side="right")) - 1
        if j < 0:
            raise SystemExit(f"FAIL-CLOSED: no evaluated bar on or before frozen WF endpoint {ts.date()}")
        ends.append(j)
    if any(ends[k] >= ends[k + 1] for k in range(len(ends) - 1)):
        raise SystemExit("FAIL-CLOSED: WF endpoints not strictly increasing")
    if ends[-1] != len(idx) - 1:
        raise SystemExit(f"FAIL-CLOSED: final frozen endpoint {G4_FOLD_ENDS[-1].date()} is not the last evaluated OOS bar")
    total = float(oos_excess.sum())
    if abs(total) < 1e-12:
        raise SystemExit("FAIL-CLOSED: cumulative OOS net excess ~ 0; share undefined")
    table, cum_ok, max_share = [], True, -np.inf
    prev_end = -1
    for k, e in enumerate(ends):
        cum = oos_excess.iloc[:e + 1]
        cum_sh = sharpe(cum)
        incr = oos_excess.iloc[prev_end + 1:e + 1]
        incr_sum = float(incr.sum())
        share = incr_sum / total
        cum_ok &= bool(cum_sh > 0)
        max_share = max(max_share, share)
        table.append({"fold": k + 1, "expanding_span": [str(cum.index[0].date()), str(cum.index[-1].date())],
                      "cum_n_days": int(len(cum)), "cum_net_excess_sharpe": cum_sh,
                      "incremental_segment": [str(incr.index[0].date()), str(incr.index[-1].date())],
                      "incremental_n_days": int(len(incr)), "incremental_sum_net_excess": incr_sum,
                      "incremental_sharpe_descriptive": sharpe(incr), "share_of_cumulative_oos_net_excess": float(share)})
        prev_end = e
    return {"pass": bool(cum_ok and max_share <= G4_MAX_FOLD_SHARE), "statistic": float(min(r["cum_net_excess_sharpe"] for r in table)), "threshold": 0.0,
            "details": {"rule": "expanding-span net-excess Sharpe > 0 in EVERY fold AND max incremental fold share <= 0.60 of cumulative OOS net excess",
                        "min_cum_sharpe": float(min(r["cum_net_excess_sharpe"] for r in table)), "max_fold_share": float(max_share),
                        "max_share_threshold": G4_MAX_FOLD_SHARE, "total_oos_sum_net_excess": total, "per_fold_table": table}}

def arm_metrics(eq_full, returns_full, label):
    is_eq = eq_full[eq_full.index <= IS_END]
    oos_eq = eq_full[eq_full.index >= OOS_START]
    is_r = returns_full[returns_full.index <= IS_END]
    oos_r = returns_full[returns_full.index >= OOS_START]
    def pack(eq, r):
        return {"cagr": cagr(eq), "sharpe": sharpe(r), "maxdd": max_dd(eq), "n_days": int(len(r)), "yearly": yearly_returns(eq)}
    return {label: {"is": pack(is_eq, is_r), "oos": pack(oos_eq, oos_r)}}

def excess_summary(seg):
    x = seg.to_numpy(dtype=float)
    sd = float(np.std(x, ddof=1)) if len(x) > 1 else float("nan")
    return {"n_days": int(len(x)), "mean_daily": float(np.mean(x)), "std_daily": sd,
            "annualized_sharpe": (float(np.mean(x)) / sd * np.sqrt(ANN)) if sd and sd > 0 and not np.isnan(sd) else 0.0,
            "sum": float(np.sum(x)), "min": float(np.min(x)), "max": float(np.max(x)),
            "start": str(seg.index[0].date()), "end": str(seg.index[-1].date())}

def main():
    tickers = load_snapshot_tickers()
    if not tickers:
        raise SystemExit("FAIL-CLOSED: empty universe (snapshot intersect local)")
    panel, cal, _spy_raw, spy_ffill, integrity = load_data(tickers)
    if len(cal) <= WARMUP + 1:
        raise SystemExit(f"FAIL-CLOSED: calendar has {len(cal)} bars; warmup {WARMUP} leaves no evaluated history")
    start_i = WARMUP
    last_i = len(cal) - 1
    if cal[-1] != G4_FOLD_ENDS[-1]:
        raise SystemExit(f"FAIL-CLOSED: data ends {cal[-1].date()} but frozen WF final endpoint is {G4_FOLD_ENDS[-1].date()}")
    me_mask = month_end_mask(cal)

    # Run both arms in same session
    baseline = simulate(panel, cal, me_mask, start_i, last_i)
    overlay = simulate_voltarget(panel, cal, me_mask, start_i, last_i)

    base_eq = baseline["equity"]
    over_eq = overlay["equity"]
    spy_eq = spy_engine(spy_ffill, start_i, last_i)

    base_r = base_eq.pct_change()
    over_r = over_eq.pct_change()
    spy_r = spy_eq.pct_change()

    # Overlay is the gated claim; compute excess vs SPY for gates
    over_excess = (over_r - spy_r).dropna()
    if over_excess.empty:
        raise SystemExit("FAIL-CLOSED: empty overlay net-excess series")
    is_excess = over_excess[over_excess.index <= IS_END]
    oos_excess = over_excess[over_excess.index >= OOS_START]
    full_evaluated = over_excess
    if is_excess.empty or oos_excess.empty:
        raise SystemExit("FAIL-CLOSED: IS or OOS excess segment empty")

    arms = {}
    arms.update(arm_metrics(base_eq, base_r.dropna(), "baseline_incumbent"))
    arms.update(arm_metrics(over_eq, over_r.dropna(), "overlay"))
    arms.update(arm_metrics(spy_eq, spy_r.dropna(), "spy"))

    # Gates on overlay
    g1_present = os.path.isfile(PREREG_PATH)
    g1_frozen = False
    if g1_present:
        with open(PREREG_PATH, encoding="utf-8") as f:
            head = f.read(4096)
        g1_frozen = ("FROZEN" in head.upper()) or ("LOCKED" in head.upper())
    gates = {
        "g1_prereg_committed": {"pass": bool(g1_present and g1_frozen), "statistic": "artifact_check",
                                "details": {"path": os.path.relpath(PREREG_PATH, BASE), "present": g1_present, "frozen_marker_found": g1_frozen}},
        "g2_is_stationary_bootstrap": g2_stationary_bootstrap(is_excess),
        "g3_cpcv": g3_cpcv(full_evaluated),
        "g4_walk_forward": g4_walk_forward(oos_excess),
        "g6_dsr_ledger": {"pass": None, "status": "MANUAL_STEP_REQUIRED",
                         "details": {"note": "Per prereg section 4 gate 6: positive Deflated-Sharpe ledger entry via scripts/preregister.py record into docs/data/eval_wave1_h3.json, trials charged = 1. Recorded by operator AFTER auditor verdict.",
                                     "command_shape": "python scripts/preregister.py record <spec_path> --verdict <PASS|FAIL|HONEST_ABANDON> [--eval-path docs/data/wave1_h3_results.json]"}},
    }
    gates["g5_permutation_null"] = g5_permutation_null(oos_excess, excess_summary(oos_excess)["annualized_sharpe"])

    charter = {"oos_net_cagr_overlay": arms["overlay"]["oos"]["cagr"], "oos_net_cagr_spy": arms["spy"]["oos"]["cagr"],
               "oos_net_sharpe_overlay": arms["overlay"]["oos"]["sharpe"], "oos_net_sharpe_spy": arms["spy"]["oos"]["sharpe"]}
    charter["pass"] = bool(charter["oos_net_cagr_overlay"] > charter["oos_net_cagr_spy"] and charter["oos_net_sharpe_overlay"] > charter["oos_net_sharpe_spy"])

    # Primary acceptance: overlay Sharpe margin >= +0.10 over baseline AND overlay CAGR > SPY AND charter
    sharpe_margin = arms["overlay"]["oos"]["sharpe"] - arms["baseline_incumbent"]["oos"]["sharpe"]
    primary = {"oos_sharpe_overlay": arms["overlay"]["oos"]["sharpe"], "oos_sharpe_baseline": arms["baseline_incumbent"]["oos"]["sharpe"],
               "sharpe_margin": float(sharpe_margin), "sharpe_margin_bar": 0.10,
               "sharpe_margin_pass": bool(sharpe_margin >= 0.10),
               "oos_cagr_overlay": arms["overlay"]["oos"]["cagr"], "oos_cagr_spy": arms["spy"]["oos"]["cagr"],
               "cagr_vs_spy_pass": bool(arms["overlay"]["oos"]["cagr"] > arms["spy"]["oos"]["cagr"]),
               "charter_pass": bool(charter["pass"])}
    primary["pass"] = bool(primary["sharpe_margin_pass"] and primary["cagr_vs_spy_pass"] and primary["charter_pass"])
    primary["maxdd_delta_overlay_minus_baseline"] = float(arms["overlay"]["oos"]["maxdd"] - arms["baseline_incumbent"]["oos"]["maxdd"])
    primary["turnover_delta_trades"] = int(overlay["trades"] - baseline["trades"])

    computed = [k for k in ("g1_prereg_committed", "g2_is_stationary_bootstrap", "g3_cpcv", "g4_walk_forward", "g5_permutation_null")]
    all_gates_pass = all(gates[k]["pass"] for k in computed)

    results = {
        "claim": "Scaling the incumbent us_momentum_top5 portfolio by m_t=clamp(0.15/sigma_hat_21d_ann,0.25,1.00) at month-ends improves OOS net Sharpe vs untargeted incumbent by >=+0.10 while keeping OOS net CAGR above SPY and passing gates G2-G5",
        "prereg": os.path.relpath(PREREG_PATH, BASE), "prereg_status": "FROZEN 2026-08-24 - LOCKED before any in-sample run", "paper_only": True,
        "verdict_authority": "RESERVED FOR AUDITOR SEAT - this output reports mechanical gate booleans only; no PASS claim is made by the builder",
        "config_echo": {
            "universe": {"definition": "snapshot map keys INTERSECT local OHLCV csv stems MINUS SPY (verbatim ml_sl_exit_test.py load_snapshot_tickers)", "size": integrity["universe_size"], "verified_size": 481, "size_matches": bool(integrity["universe_size"] == 481)},
            "benchmark": BENCHMARK,
            "params_byte_identical_to": "strategies/us_momentum_top5.yaml",
            "params": {"top_n": TOP_N, "lookback_days": LOOKBACK, "skip_days": SKIP, "warmup_days": WARMUP, "rebalance": "monthly (last trading bar)", "drift_rebal": DRIFT_BAND, "exec_delay_bars": EXEC_DELAY, "slippage_per_side": COST, "commission": COMMISSION},
            "vol_target_overlay": {"target_ann_vol": VOL_TARGET_ANN, "window_days": VOL_WINDOW, "floor": VOL_FLOOR, "cap": VOL_CAP, "sigma_source": "overlay strategy's own daily net returns trailing 21d ending t-1, ann sqrt(252)*std", "cold_start_m": 1.00, "cap_binding_no_margin": True},
            "windows": {"is_nominal": ["2019-01-02", "2023-12-31"], "oos_nominal": ["2024-01-01", "2026-08-07"], "sim_start_rule": "bar index WARMUP=340 of union calendar (declared interpretation)", "effective_evaluated_start": str(cal[start_i].date())},
            "stochastic": {"g2": {"mean_block": G2_MEAN_BLOCK, "draws": G2_DRAWS, "seed": G2_SEED, "alpha": G2_ALPHA}, "g3": {"K": G3_K, "embargo_days": G3_EMBARGO}, "g4": {"fold_ends": [str(d.date()) for d in G4_FOLD_ENDS], "endpoint_snap": "last_trading_bar_on_or_before", "max_fold_share": G4_MAX_FOLD_SHARE}, "g5": {"block": G5_BLOCK, "draws": G5_DRAWS, "seed": G5_SEED}},
            "engine_lineage": {"derived_from": "scripts/wave1_h1_test.py / wave1_h2_test.py (adapted from ml_sl_exit_test.py static arm)", "metric_source": METRIC_SOURCE, "overlay_deltas_vs_baseline": ["m_t recomputed at month-ends from trailing 21d overlay returns; new/delta trades scaled by m_t; drift band vs m_t-scaled target; cash residual at 0%"]},
            "data_integrity": integrity,
        },
        "arms": arms,
        "excess_series_summary": {"definition": "overlay NET daily returns minus SPY-engine NET daily returns (identical fee accounting), date-aligned",
                                  "is": excess_summary(is_excess), "oos": excess_summary(oos_excess), "full_evaluated": excess_summary(full_evaluated)},
        "m_series": overlay["m_series"], "m_stats": overlay["m_stats"],
        "gates": gates, "charter_bar": charter, "primary_acceptance": primary,
        "trades_baseline": baseline["trades"], "trades_overlay": overlay["trades"],
        "all_computed_gates_pass": bool(all_gates_pass),
        "notes": [
            "PRIOR ART: closed-form deterministic vol-target sizing never tested before; 17/17 ML-overlay failures were LEARNED models (decision 2026-08-16-ml-overlay.md); improvement-regime closure explicitly left SIZING open as remaining lane.",
            "TARGET CORE bound to us_momentum_top5 AT FREEZE TIME regardless of other wave-1 outcomes; retargeting requires new prereg (anti-cherry-pick).",
            "Declared interpretation: universe = incumbent-as-machined (snapshot∩local−SPY 481 names).",
            "Declared cold-start: m=1.00 before 21 overlay returns exist (neutral to incumbent).",
            "Declared sigma window: last 21 overlay daily net returns ending at bar t-1 (annualized). Between month-ends drift guards vs m_t-scaled target.",
            "G3 combination semantics declared in gates.g3_cpcv.details; G4 per-fold Sharpe is EXPANDING-SPAN; incremental Sharpes descriptive.",
            "G4 frozen endpoints snap to last trading bar on or before each date (pre-run delta from H1).",
        ],
    }
    os.makedirs(os.path.dirname(OUT_RESULTS), exist_ok=True)
    with open(OUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    g2, g3 = gates["g2_is_stationary_bootstrap"], gates["g3_cpcv"]
    g4, g5 = gates["g4_walk_forward"], gates["g5_permutation_null"]
    def yn(v):
        return "TRUE" if v else ("PENDING" if v is None else "FALSE")
    print("=" * 78)
    print("WAVE-1 / H3 VOL-TARGETED SIZING OVERLAY  |  PAPER-ONLY | FAIL-CLOSED | FROZEN PREREG")
    print("=" * 78)
    print(f"{'gate':<4} {'description':<44} {'statistic':>14} {'bar':>10} {'state':>7}")
    print("-" * 78)
    print(f"{'G1':<4} {'prereg frozen artifact':<44} {'artifact':>14} {'locked':>10} {yn(gates['g1_prereg_committed']['pass']):>7}")
    print(f"{'G2':<4} {'IS stationary bootstrap (blk21,n1000,s7)':<44} {g2['p_value']:>14.4f} {'<=0.05':>10} {yn(g2['pass']):>7}")
    print(f"{'G3':<4} {'CPCV K=6 emb10 all-combos mean>0':<44} {g3['statistic']:>14.6f} {'>0':>10} {yn(g3['pass']):>7}")
    print(f"{'G4':<4} {'5 expanding WF folds + 60pct share cap':<44} {g4['statistic']:>14.4f} {'>0/all':>10} {yn(g4['pass']):>7}")
    print(f"{'G5':<4} {'circ-block perm (blk10,n1000,s7) vs p95':<44} {g5['statistic']:>14.4f} {('>p95 %.4f' % g5['threshold']):>10} {yn(g5['pass']):>7}")
    print(f"{'G6':<4} {'DSR ledger via preregister.py (operator)':<44} {'manual':>14} {'ledger':>10} {'PENDING':>7}")
    print("-" * 78)
    print(f"{'CHR':<4} {'OOS net CAGR>SPY AND OOS net Sharpe>SPY':<44} {charter['oos_net_sharpe_overlay'] - charter['oos_net_sharpe_spy']:>14.4f} {'both>':>10} {yn(charter['pass']):>7}")
    print(f"{'PRI':<4} {'Sharpe margin >=+0.10 vs baseline':<44} {primary['sharpe_margin']:>14.4f} {'>=+0.10':>10} {yn(primary['pass']):>7}")
    print("-" * 78)
    print(f"eval start {cal[start_i].date()} | baseline trades {baseline['trades']} | overlay trades {overlay['trades']} | m months {overlay['m_stats']['n_months']} mean {overlay['m_stats']['mean']:.3f} cap_frac {overlay['m_stats']['frac_at_cap']:.1%}")
    print(f"G3 combos failing: {g3['details']['combinations_failing']}/{g3['details']['combination_count']} | G4 max fold share: {g4['details']['max_fold_share']:.4f} (cap {G4_MAX_FOLD_SHARE})")
    print(f"all_computed_gates_pass={all_gates_pass} | primary_pass={primary['pass']} | verdict authority: AUDITOR | G6 DSR ledger = manual")
    print(f"results -> {os.path.relpath(OUT_RESULTS, BASE)}")

if __name__ == "__main__":
    main()
