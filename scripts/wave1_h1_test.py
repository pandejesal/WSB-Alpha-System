"""Wave 1 / H1 — Mega-Cap-Only Momentum Top-5 (FROZEN PREREGISTRATION RUNNER).

PAPER-ONLY. LIVE TRADING DISABLED. FAIL-CLOSED. Zero fitted parameters.

Implements docs/data/wave1_h1_megacap_momentum_prereg.md (frozen 2026-08-24)
EXACTLY: gates G2-G5 computed mechanically; G1 reported as artifact check;
G6 (DSR ledger) left as an explicit MANUAL STEP for the operator/auditor --
this script NEVER self-certifies a PASS verdict (builder seat has no PASS
authority under hunt law).

Rule (byte-identical to strategies/us_momentum_top5.yaml): monthly last-bar
top-5 by 126d return skipping 21d, equal weight 1/5, warmup 340d,
drift_rebal 0.05, exec_delay 1 bar, 5 bps/side slippage, $0 commission,
T+1 cash, min-$1 order. Benchmark: SPY buy-and-hold through IDENTICAL fee
accounting. Descriptive control (NOT gated, 0 trials): equal-weight passive
buy-and-hold of Universe A, same window/costs.

Lineage: portfolio machinery derived from scripts/ml_sl_exit_test.py (the
H-SLX-1 static arm). Two documented extensions were REQUIRED because the
frozen H1 spec is byte-identical to the YAML while the H-SLX-1 engine omitted
them: (1) daily drift-band rebalance toward the 1/TOP_N target weight;
(2) pending-order entries became dicts so drift trades can be PARTIAL
(rank-drop exits remain full-position sells). Everything else is copied
verbatim. Metric helpers are imported from ml_sl_exit_test when possible with
verbatim inline fallbacks so this file runs standalone offline.

Outputs:
  docs/data/wave1_h1_results.json   (full numbers; deterministic, seeded)
Stdout: compact six-gate + charter-bar summary table.

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
PREREG_PATH = os.path.join(BASE, "docs", "data",
                           "wave1_h1_megacap_momentum_prereg.md")
OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave1_h1_results.json")

# ---- Frozen spec constants (docs/data/wave1_h1_megacap_momentum_prereg.md) --
UNIVERSE_A = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM",
              "V", "JNJ", "WMT", "MA", "UNH", "XOM", "DIS"]  # fixed order
BENCHMARK = "SPY"
TOP_N = 5
LOOKBACK = 126
SKIP = 21
WARMUP = 340
DRIFT_BAND = 0.05
EXEC_DELAY = 1                      # bars (engine queues orders -> next bar)
COST = 0.0005                       # 5 bps per side
COMMISSION = 0.0                    # $0 (Alpaca)
INIT_EQUITY = 100_000.0
MIN_ORDER = 1.0

IS_END = pd.Timestamp("2023-12-31")
OOS_START = pd.Timestamp("2024-01-01")
DATA_START_EXPECTED = pd.Timestamp("2019-01-02")

# Gates
G2_MEAN_BLOCK = 21                  # trading days, stationary bootstrap
G2_DRAWS = 1000
G2_SEED = 7
G2_ALPHA = 0.05                     # PASS iff p <= alpha (borderline = fail downstream)
G3_K = 6                            # contiguous folds over evaluated excess history
G3_EMBARGO = 10                     # trading days purged at train/test boundaries
G4_FOLD_ENDS = [pd.Timestamp("2024-06-30"), pd.Timestamp("2024-12-31"),
                pd.Timestamp("2025-06-30"), pd.Timestamp("2025-12-31"),
                pd.Timestamp("2026-08-07")]
G4_MAX_FOLD_SHARE = 0.60            # no incremental fold > 60% of cumulative OOS net excess
G5_BLOCK = 10                       # trading days, circular block shuffle
G5_DRAWS = 1000
G5_SEED = 7

ANN = 252


# ---- Metric helpers: import from reference engine, verbatim fallback -------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:  # pragma: no cover - exercised only when sibling module imports cleanly
    from ml_sl_exit_test import cagr, max_dd, month_end_mask, sharpe, yearly_returns
    METRIC_SOURCE = "imported:scripts/ml_sl_exit_test.py"
except Exception:  # standalone offline fallback (bodies copied VERBATIM below)
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


# ---- Data -------------------------------------------------------------------
def load_data():
    """Load Universe A + SPY OHLCV closes onto a union calendar. Fail-closed."""
    need = UNIVERSE_A + [BENCHMARK]
    missing = [t for t in need
               if not os.path.isfile(os.path.join(OHLCV_DIR, f"{t}.csv"))]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: missing OHLCV files: {missing}")
    frames, integrity = {}, {}
    for t in need:
        df = pd.read_csv(os.path.join(OHLCV_DIR, f"{t}.csv"),
                         parse_dates=["date"])
        if df.empty:
            raise SystemExit(f"FAIL-CLOSED: empty OHLCV file for {t}")
        s = df.set_index("date")["close"].astype(float).sort_index()
        frames[t] = s
        integrity[t] = {"rows": int(len(s)),
                        "first": str(s.index[0].date()),
                        "last": str(s.index[-1].date())}
    cal = pd.DatetimeIndex(sorted(set().union(*[s.index for s in frames.values()])))
    panel = {}
    for t in UNIVERSE_A:
        close = frames[t].reindex(cal)
        panel[t] = {
            "close": close,                    # raw (NaN where absent)
            "close_ffill": close.ffill(),      # marks, as in reference engine
            "mom": close.shift(SKIP) / close.shift(SKIP + LOOKBACK) - 1.0,
            "hist_cnt": close.notna().cumsum().to_numpy(),
        }
    spy_close = frames[BENCHMARK].reindex(cal)
    spy_ffill = spy_close.ffill()
    return panel, cal, spy_close, spy_ffill, integrity


# ---- Engines ----------------------------------------------------------------
def spy_engine(spy_ffill, start_i, end_i):
    """SPY buy-and-hold, identical fee accounting.

    Fee convention (defined HERE; no prior house precedent in the reference
    engine): single entry at the first evaluated close paying COST via reduced
    shares; $0 commission; position held open to the window end (no terminal
    exit cost applied); daily marks at ffilled close. The descriptive control
    arm uses the SAME convention.
    """
    p0 = spy_ffill.iloc[start_i]
    if pd.isna(p0) or p0 <= 0:
        raise SystemExit("FAIL-CLOSED: invalid SPY price at evaluated start")
    shares = INIT_EQUITY / (float(p0) * (1.0 + COST))
    eq = shares * spy_ffill.iloc[start_i:end_i + 1]
    return pd.Series(eq.to_numpy(dtype=float),
                     index=cal_slice_index(spy_ffill, start_i, end_i))


def cal_slice_index(series, start_i, end_i):
    return series.index[start_i:end_i + 1]


def control_engine(panel, cal, start_i, end_i):
    """Descriptive control: equal-weight passive buy-and-hold of Universe A.

    NOT gated, zero trials. Same fee convention as spy_engine: one entry per
    name at the evaluated-start close paying COST, $0 commission, hold to end,
    ffilled marks. Never rebalanced (passive).
    """
    n = len(UNIVERSE_A)
    leg_notional = INIT_EQUITY / n
    shares = {}
    for t in UNIVERSE_A:
        p0 = panel[t]["close_ffill"].iloc[start_i]
        if pd.isna(p0) or p0 <= 0:
            raise SystemExit(f"FAIL-CLOSED: invalid {t} price at evaluated start")
        shares[t] = leg_notional / (float(p0) * (1.0 + COST))
    eq = np.empty(end_i - start_i + 1)
    for k, i in enumerate(range(start_i, end_i + 1)):
        eq[k] = sum(shares[t] * float(panel[t]["close_ffill"].iloc[i])
                    for t in UNIVERSE_A)
    return pd.Series(eq, index=cal[start_i:end_i + 1])


def simulate(panel, cal, me_mask, start_i, end_i):
    """Monthly top-5 momentum sim, ADAPTED from scripts/ml_sl_exit_test.py.

    Copied verbatim except the two extensions documented in the module
    docstring (drift-band rebalance; dict pending orders enabling partial
    sells / explicit buy notionals). Semantics kept: signals at month-end
    close, fills NEXT bar (exec_delay 1), 5 bps/side, $0 commission, same-bar
    cash crediting (T+1 degenerates to same-bar accounting exactly as in the
    reference engine), ffilled marks, min-$1 order guard, unfilled orders
    dropped after their single next-bar attempt (reference behavior).
    """
    cash = INIT_EQUITY
    positions = {}                      # t -> {"shares": float}
    pending_buys, pending_sells = [], []  # dicts: {"ticker","notional"|"shares","reason"}
    equity = np.empty(end_i - start_i + 1)
    n_trades = 0

    def px(t, i):
        v = panel[t]["close_ffill"].iloc[i]
        return np.nan if pd.isna(v) else float(v)

    def mark(i):
        return cash + sum(rec["shares"] * px(t, i) for t, rec in positions.items())

    for i in range(start_i, end_i + 1):
        # 1) fills for sells queued on the previous bar
        for order in pending_sells:
            t = order["ticker"]
            if t not in positions:
                continue
            p = px(t, i)
            if pd.isna(p):
                continue
            rec = positions[t]
            want = rec["shares"] if order.get("shares") is None \
                else min(order["shares"], rec["shares"])
            cash += want * p * (1.0 - COST)
            rec["shares"] -= want
            n_trades += 1
            if rec["shares"] * p < 1e-9:
                positions.pop(t)
        pending_sells = []

        # 2) fills for buys queued on the previous bar
        eq_mark = mark(i)
        target = eq_mark / TOP_N
        for order in pending_buys:
            t = order["ticker"]
            p = px(t, i)
            if pd.isna(p) or t in positions:
                continue
            notional = target if order.get("notional") is None \
                else order["notional"]
            notional = min(notional, max(cash, 0.0))
            if notional < MIN_ORDER:
                continue
            shares = notional / (p * (1.0 + COST))
            cash -= shares * p * (1.0 + COST)
            positions[t] = {"shares": shares}
            n_trades += 1
        pending_buys = []

        # 3) month-end selection signal (byte-identical rule)
        if me_mask[i] and i < end_i:
            scores = {}
            for t, d in panel.items():
                m = d["mom"].iloc[i]
                if not pd.isna(m) and d["hist_cnt"][i] >= WARMUP:
                    scores[t] = float(m)
            top = [t for t, _ in sorted(scores.items(),
                                        key=lambda kv: kv[1],
                                        reverse=True)[:TOP_N]]
            for t in list(positions):
                if t not in top:
                    pending_sells.append({"ticker": t, "shares": None,
                                          "reason": "rank_drop"})
            for t in top:
                if t not in positions:
                    pending_buys.append({"ticker": t, "notional": None,
                                         "reason": "entry"})

        # 4) drift-band rebalance (H1 extension: us_momentum_top5.yaml
        #    drift_rebal 0.05). Checked daily after marking; deviations beyond
        #    +/-0.05 of the 1/TOP_N target weight are traded back to target on
        #    the NEXT bar through the same pending queues; min-$1 guard.
        if i < end_i and positions:
            eq_now = mark(i)
            tgt = eq_now / TOP_N
            queued = ({o["ticker"] for o in pending_buys}
                      | {o["ticker"] for o in pending_sells})
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
                        pending_sells.append({"ticker": t,
                                              "shares": sell_val / p,
                                              "reason": "drift"})
                elif dev < -DRIFT_BAND:
                    buy_val = min(tgt - val, max(cash, 0.0))
                    if buy_val >= MIN_ORDER:
                        pending_buys.append({"ticker": t, "notional": buy_val,
                                             "reason": "drift"})

        equity[i - start_i] = mark(i)

    return {"equity": pd.Series(equity, index=cal[start_i:end_i + 1]),
            "trades": n_trades}


# ---- Stochastic machinery -----------------------------------------------------
def stationary_bootstrap_series(x, mean_block, n_draws, seed):
    """Politis-Romano stationary bootstrap indices; geometric blocks,
    mean length = mean_block. Fresh default_rng per gate => order-independent."""
    rng = np.random.default_rng(seed)
    n = len(x)
    p = 1.0 / float(mean_block)
    out = np.empty((n_draws, n), dtype=float)
    for d in range(n_draws):
        jumps = rng.random(n) < p          # new block starts
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
    centered = boot_means - obs           # Hall & Wilson two-sided p-value
    p_left = float(np.mean(centered >= obs))
    p_right = float(np.mean(centered <= obs))
    p_two = float(min(1.0, 2.0 * min(p_left, p_right)))
    return {
        "pass": bool(p_two <= G2_ALPHA),
        "statistic": obs,
        "p_value": p_two,
        "threshold": G2_ALPHA,
        "borderline_flag": bool(G2_ALPHA * 0.8 < p_two <= G2_ALPHA),
        "details": {
            "method": ("two-sided stationary block bootstrap p-value "
                       "(Hall-Wilson): p = 2*min(P(T*-Tbar >= Tbar), "
                       "P(T*-Tbar <= Tbar)), T* = bootstrap means"),
            "mean_block_days": G2_MEAN_BLOCK, "draws": G2_DRAWS, "seed": G2_SEED,
            "series_len": int(len(x)),
            "boot_mean_dist": {"mean": float(np.mean(boot_means)),
                               "std": float(np.std(boot_means, ddof=1))},
        },
    }


def circular_block_shuffle(x, block, seed):
    """Multiset-preserving circular block PERMUTATION (prereg: 'shuffle').

    The n observations are cut into m = ceil(n/block) contiguous blocks, the
    last block wrapping circularly into the head so every block has exactly
    `block` elements; blocks are then permuted and the concatenation
    truncated to n. Every observation appears exactly once (true permutation
    null). NOTE: deliberately NOT the truncated non-circular block_shuffle in
    scripts/ml_sl_exit_test.py -- the H1 prereg specifies CIRCULAR.
    """
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
    return {
        "pass": bool(observed_ann_sharpe > p95),
        "statistic": float(observed_ann_sharpe),
        "threshold": p95,
        "details": {
            "method": "circular block shuffle (multiset-preserving permutation), "
                      "observed annualized net-excess Sharpe vs null p95",
            "block_days": G5_BLOCK, "draws": G5_DRAWS, "seed": G5_SEED,
            "series_len": int(len(x)),
            "null_mean": float(np.mean(null_sharpes)),
            "null_std": float(np.std(null_sharpes, ddof=1)),
        },
    }


# ---- G3: combinatorially purged CV -------------------------------------------
def g3_cpcv(full_excess):
    """K=6 contiguous folds over the evaluated net-excess history.

    Combination semantics (declared interpretation of prereg 'EVERY
    training-combination-held-out evaluation'): all NON-EMPTY PROPER SUBSETS
    of the K folds serve as test sets (62 combinations); remaining folds are
    'train'. Nothing is fitted -- evaluation only. Embargo: within each test
    fold, drop G3_EMBARGO trading days at every edge adjacent to a TRAIN fold
    (test-test internal boundaries are not train/test edges and are kept).
    PASS iff mean net excess return > 0 in every combination.
    """
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
            raise SystemExit(
                f"FAIL-CLOSED: combination {combo} fully embargoed to empty")
        mean_ret = float(np.concatenate(vals).mean())
        results.append((combo, mean_ret))
        if mean_ret <= 0:
            all_positive = False
            n_fail += 1
    results.sort(key=lambda cr: cr[1])
    return {
        "pass": bool(all_positive),
        "statistic": results[0][1],   # worst combination mean
        "threshold": 0.0,
        "details": {
            "K": G3_K, "embargo_days": G3_EMBARGO,
            "combination_semantics": ("all non-empty proper subsets of K folds "
                                      "= test sets; embargo purged at train/test "
                                      "edges inside each test fold"),
            "combination_count": len(results),
            "combinations_failing": n_fail,
            "worst_combinations": [
                {"combo": [int(j) + 1 for j in c], "mean_net_excess": v}
                for c, v in results[:5]],
            "best_combination": {"combo": [int(j) + 1 for j in results[-1][0]],
                                 "mean_net_excess": results[-1][1]},
            "evaluated_history": {"n_days": n,
                                  "start": str(full_excess.index[0].date()),
                                  "end": str(full_excess.index[-1].date())},
        },
    }


# ---- G4: expanding walk-forward ------------------------------------------------
def g4_walk_forward(oos_excess):
    """5 EXPANDING OOS folds; per-fold net-excess Sharpe over the expanding
    span [2024-01-01 .. end_k] must be > 0; no single INCREMENTAL fold
    segment contributes > 60% of cumulative OOS net excess (sum of daily
    excess returns). Incremental-segment Sharpes reported descriptively."""
    idx = oos_excess.index
    # Frozen calendar-date endpoints snap to the LAST TRADING BAR on or before
    # each date (e.g. 2024-06-30 is a Sunday -> snaps to Fri 2024-06-28).
    # Pre-run delta (MAIN, before any in-sample run): strict-equality snapping
    # would fail-closed on weekend/holiday endpoints; the frozen dates denote
    # period ENDS, not session requirements.
    ends = []
    for ts in G4_FOLD_ENDS:
        j = int(idx.searchsorted(ts, side="right")) - 1
        if j < 0:
            raise SystemExit(
                f"FAIL-CLOSED: no evaluated bar on or before frozen WF endpoint "
                f"{ts.date()}")
        ends.append(j)
    if any(ends[k] >= ends[k + 1] for k in range(len(ends) - 1)):
        raise SystemExit("FAIL-CLOSED: WF endpoints not strictly increasing")
    if ends[-1] != len(idx) - 1:
        raise SystemExit(
            f"FAIL-CLOSED: final frozen endpoint {G4_FOLD_ENDS[-1].date()} is not "
            "the last evaluated OOS bar")
    total = float(oos_excess.sum())
    if abs(total) < 1e-12:
        raise SystemExit("FAIL-CLOSED: cumulative OOS net excess ~ 0; share undefined")
    table, cum_ok, max_share = [], True, -np.inf
    prev_end = -1  # exclusive; incremental starts at 0 (2024-01-01)
    for k, e in enumerate(ends):
        cum = oos_excess.iloc[:e + 1]
        cum_sh = sharpe(cum)
        incr = oos_excess.iloc[prev_end + 1:e + 1]
        incr_sum = float(incr.sum())
        share = incr_sum / total
        cum_ok &= bool(cum_sh > 0)
        max_share = max(max_share, share)
        table.append({
            "fold": k + 1,
            "expanding_span": [str(cum.index[0].date()), str(cum.index[-1].date())],
            "cum_n_days": int(len(cum)),
            "cum_net_excess_sharpe": cum_sh,
            "incremental_segment": [str(incr.index[0].date()),
                                    str(incr.index[-1].date())],
            "incremental_n_days": int(len(incr)),
            "incremental_sum_net_excess": incr_sum,
            "incremental_sharpe_descriptive": sharpe(incr),
            "share_of_cumulative_oos_net_excess": float(share),
        })
        prev_end = e
    return {
        "pass": bool(cum_ok and max_share <= G4_MAX_FOLD_SHARE),
        "statistic": float(min(r["cum_net_excess_sharpe"] for r in table)),
        "threshold": 0.0,
        "details": {
            "rule": "expanding-span net-excess Sharpe > 0 in EVERY fold AND "
                    "max incremental fold share <= 0.60 of cumulative OOS net excess",
            "min_cum_sharpe": float(min(r["cum_net_excess_sharpe"] for r in table)),
            "max_fold_share": float(max_share),
            "max_share_threshold": G4_MAX_FOLD_SHARE,
            "total_oos_sum_net_excess": total,
            "per_fold_table": table,
        },
    }


# ---- Reporting helpers ----------------------------------------------------------
def arm_metrics(eq_full, returns_full, label):
    """IS/OOS CAGR/Sharpe/maxDD for one arm. Return-series slices filter by
    RETURN-END date (returns ending in the segment); CAGR/maxDD slices anchor
    at segment boundary timestamps. Identical convention for every arm."""
    is_eq = eq_full[eq_full.index <= IS_END]
    oos_eq = eq_full[eq_full.index >= OOS_START]
    is_r = returns_full[returns_full.index <= IS_END]
    oos_r = returns_full[returns_full.index >= OOS_START]

    def pack(eq, r):
        return {"cagr": cagr(eq), "sharpe": sharpe(r), "maxdd": max_dd(eq),
                "n_days": int(len(r)), "yearly": yearly_returns(eq)}
    return {label: {"is": pack(is_eq, is_r), "oos": pack(oos_eq, oos_r)}}


def excess_summary(seg):
    x = seg.to_numpy(dtype=float)
    sd = float(np.std(x, ddof=1)) if len(x) > 1 else float("nan")
    return {"n_days": int(len(x)), "mean_daily": float(np.mean(x)),
            "std_daily": sd,
            "annualized_sharpe": (float(np.mean(x)) / sd * np.sqrt(ANN))
                                 if sd and sd > 0 and not np.isnan(sd) else 0.0,
            "sum": float(np.sum(x)), "min": float(np.min(x)),
            "max": float(np.max(x)),
            "start": str(seg.index[0].date()), "end": str(seg.index[-1].date())}


def main():
    panel, cal, _spy_raw, spy_ffill, integrity = load_data()

    # Warmup start: first bar where EVERY Universe A member has >= WARMUP obs.
    warm_ok = np.all(np.vstack([panel[t]["hist_cnt"] >= WARMUP
                                for t in UNIVERSE_A]), axis=0)
    warm_idx = np.flatnonzero(warm_ok)
    if len(warm_idx) == 0:
        raise SystemExit("FAIL-CLOSED: warmup 340d never satisfied on this panel")
    start_i = int(warm_idx[0])
    last_i = len(cal) - 1
    if cal[-1] != G4_FOLD_ENDS[-1]:
        raise SystemExit(
            f"FAIL-CLOSED: data ends {cal[-1].date()} but frozen WF final endpoint "
            f"is {G4_FOLD_ENDS[-1].date()}")

    me_mask = month_end_mask(cal)

    strat = simulate(panel, cal, me_mask, start_i, last_i)
    strat_eq = strat["equity"]
    spy_eq = spy_engine(spy_ffill, start_i, last_i)
    ctrl_eq = control_engine(panel, cal, start_i, last_i)

    strat_r = strat_eq.pct_change()
    spy_r = spy_eq.pct_change()
    ctrl_r = ctrl_eq.pct_change()
    excess = (strat_r - spy_r).dropna()          # date-aligned net excess
    if excess.empty:
        raise SystemExit("FAIL-CLOSED: empty net-excess series")

    is_excess = excess[excess.index <= IS_END]
    oos_excess = excess[excess.index >= OOS_START]
    full_evaluated = excess                       # IS + OOS post-warmup history
    if is_excess.empty or oos_excess.empty:
        raise SystemExit("FAIL-CLOSED: IS or OOS excess segment empty")

    arms = {}
    arms.update(arm_metrics(strat_eq, strat_r.dropna(), "strategy"))
    arms.update(arm_metrics(spy_eq, spy_r.dropna(), "spy"))
    arms.update(arm_metrics(ctrl_eq, ctrl_r.dropna(), "control"))

    # Gates
    g1_present = os.path.isfile(PREREG_PATH)
    g1_frozen = False
    if g1_present:
        with open(PREREG_PATH, encoding="utf-8") as f:
            head = f.read(4096)
        g1_frozen = ("FROZEN" in head.upper()) or ("LOCKED" in head.upper())
    gates = {
        "g1_prereg_committed": {
            "pass": bool(g1_present and g1_frozen),
            "statistic": "artifact_check",
            "details": {"path": os.path.relpath(PREREG_PATH, BASE),
                        "present": g1_present, "frozen_marker_found": g1_frozen},
        },
        "g2_is_stationary_bootstrap": g2_stationary_bootstrap(is_excess),
        "g3_cpcv": g3_cpcv(full_evaluated),
        "g4_walk_forward": g4_walk_forward(oos_excess),
        "g6_dsr_ledger": {
            "pass": None,
            "status": "MANUAL_STEP_REQUIRED",
            "details": {
                "note": ("Per prereg section 4 gate 6: positive Deflated-Sharpe "
                         "ledger entry via scripts/preregister.py record into "
                         "docs/data/eval_wave1_h1.json, trials charged = 1 "
                         "(control arm excluded, descriptive only). Recorded by "
                         "the operator AFTER auditor verdict; this builder-run "
                         "never self-certifies."),
                "command_shape": ("python scripts/preregister.py record "
                                  "<spec_path> --verdict <PASS|FAIL|"
                                  "HONEST_ABANDON> [--eval-path "
                                  "docs/data/wave1_h1_results.json]"),
            },
        },
    }
    gates["g5_permutation_null"] = g5_permutation_null(
        oos_excess, excess_summary(oos_excess)["annualized_sharpe"])

    charter = {
        "oos_net_cagr_strategy": arms["strategy"]["oos"]["cagr"],
        "oos_net_cagr_spy": arms["spy"]["oos"]["cagr"],
        "oos_net_sharpe_strategy": arms["strategy"]["oos"]["sharpe"],
        "oos_net_sharpe_spy": arms["spy"]["oos"]["sharpe"],
    }
    charter["pass"] = bool(charter["oos_net_cagr_strategy"] > charter["oos_net_cagr_spy"]
                           and charter["oos_net_sharpe_strategy"]
                           > charter["oos_net_sharpe_spy"])

    computed = [k for k in ("g1_prereg_committed", "g2_is_stationary_bootstrap",
                            "g3_cpcv", "g4_walk_forward", "g5_permutation_null")]
    all_gates_pass = all(gates[k]["pass"] for k in computed)

    control_block = {
        "role": "DESCRIPTIVE CONTROL ONLY - NOT GATED, ZERO TRIALS CHARGED",
        "purpose": ("separate 'momentum adds edge inside mega-caps' from "
                    "'mega-caps beat SPY'"),
        "vs_spy_oos": {"cagr_delta": arms["control"]["oos"]["cagr"]
                       - arms["spy"]["oos"]["cagr"],
                       "sharpe_delta": arms["control"]["oos"]["sharpe"]
                       - arms["spy"]["oos"]["sharpe"]},
        "vs_strategy_oos": {"cagr_delta": arms["control"]["oos"]["cagr"]
                            - arms["strategy"]["oos"]["cagr"],
                            "sharpe_delta": arms["control"]["oos"]["sharpe"]
                            - arms["strategy"]["oos"]["sharpe"]},
    }

    results = {
        "claim": ("Restricting the EXACT incumbent us_momentum_top5 rule to frozen "
                  "mega-cap Universe A produces OOS net performance beating SPY "
                  "on BOTH CAGR and Sharpe while passing gates G2-G5"),
        "prereg": os.path.relpath(PREREG_PATH, BASE),
        "prereg_status": "FROZEN 2026-08-24 - LOCKED before any in-sample run",
        "paper_only": True,
        "verdict_authority": ("RESERVED FOR AUDITOR SEAT - this output reports "
                              "mechanical gate booleans only; no PASS claim is "
                              "made by the builder"),
        "config_echo": {
            "universe_a_fixed_order": UNIVERSE_A,
            "benchmark": BENCHMARK,
            "params_byte_identical_to": "strategies/us_momentum_top5.yaml",
            "params": {"top_n": TOP_N, "lookback_days": LOOKBACK,
                       "skip_days": SKIP, "warmup_days": WARMUP,
                       "rebalance": "monthly (last trading bar)",
                       "drift_rebal": DRIFT_BAND, "exec_delay_bars": EXEC_DELAY,
                       "slippage_per_side": COST, "commission": COMMISSION,
                       "settlement": "T+1 declared; engine credits cash same-bar "
                                     "(identical to reference engine; uniform "
                                     "across all arms)"},
            "windows": {"is_nominal": ["2019-01-02", "2023-12-31"],
                        "oos_nominal": ["2024-01-01", "2026-08-07"],
                        "effective_evaluated_start_after_warmup":
                            str(cal[start_i].date()),
                        "warmup_consumes_leading_IS": True},
            "stochastic": {"g2": {"mean_block": G2_MEAN_BLOCK, "draws": G2_DRAWS,
                                  "seed": G2_SEED, "alpha": G2_ALPHA},
                           "g3": {"K": G3_K, "embargo_days": G3_EMBARGO},
                           "g4": {"fold_ends": [str(d.date())
                                                 for d in G4_FOLD_ENDS],
                                  "endpoint_snap": "last_trading_bar_on_or_before",
                                  "max_fold_share": G4_MAX_FOLD_SHARE},
                           "g5": {"block": G5_BLOCK, "draws": G5_DRAWS,
                                  "seed": G5_SEED}},
            "engine_lineage": {
                "derived_from": "scripts/ml_sl_exit_test.py (H-SLX-1 static arm)",
                "metric_source": METRIC_SOURCE,
                "extensions_vs_reference": [
                    "daily drift-band rebalance 0.05 (required by byte-identical "
                    "YAML; omitted by H-SLX-1 engine)",
                    "dict pending orders enabling partial drift sells / explicit "
                    "buy notionals (rank-drop exits unchanged: full sells)",
                    "G5 shuffle is CIRCULAR (prereg wording); reference "
                    "block_shuffle truncated non-circularly",
                ],
                "spying_fee_convention": (
                    "defined here (no precedent in reference engine): SPY and "
                    "control pay entry slippage 5bps via reduced shares at the "
                    "first evaluated close; held open; no terminal exit cost; "
                    "$0 commission"),
            },
            "data_integrity": integrity,
        },
        "arms": arms,
        "excess_series_summary": {
            "definition": "strategy NET daily returns minus SPY-engine NET daily "
                          "returns (identical fee accounting), date-aligned",
            "is": excess_summary(is_excess),
            "oos": excess_summary(oos_excess),
            "full_evaluated": excess_summary(full_evaluated),
        },
        "gates": gates,
        "charter_bar": charter,
        "control_arm": control_block,
        "trades_total": strat["trades"],
        "all_computed_gates_pass": bool(all_gates_pass),
        "notes": [
            "Survivorship/universe lookahead inherited from the frozen 2026-era "
            "Universe A definition; accepted by the prereg as claim-scoping.",
            "Warmup 340 trading days consumes the leading portion of nominal IS; "
            "evaluation begins at the first fully warmed bar.",
            "Unfilled pending orders are dropped after one next-bar attempt "
            "(reference-engine behavior); Universe A panel is complete so this "
            "is expected to be a no-op.",
            "G3 combination semantics declared in gates.g3_cpcv.details; G4 "
            "per-fold Sharpe is EXPANDING-SPAN by reading of 'expanding OOS "
            "folds'; incremental-segment Sharpes reported descriptively.",
            "G4 frozen calendar endpoints snap to the last trading bar on or "
            "before each date (pre-run delta, recorded before any in-sample "
            "run; e.g. Sun 2024-06-30 -> Fri 2024-06-28).",
        ],
    }
    os.makedirs(os.path.dirname(OUT_RESULTS), exist_ok=True)
    with open(OUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Compact stdout summary: six gate rows + charter bar.
    g2, g3 = gates["g2_is_stationary_bootstrap"], gates["g3_cpcv"]
    g4, g5 = gates["g4_walk_forward"], gates["g5_permutation_null"]

    def yn(v):
        return "TRUE" if v else ("PENDING" if v is None else "FALSE")
    print("=" * 78)
    print("WAVE-1 / H1 MEGA-CAP MOMENTUM TOP-5  |  PAPER-ONLY | FAIL-CLOSED | "
          "FROZEN PREREG")
    print("=" * 78)
    print(f"{'gate':<4} {'description':<44} {'statistic':>14} {'bar':>10} {'state':>7}")
    print("-" * 78)
    print(f"{'G1':<4} {'prereg frozen artifact':<44} {'artifact':>14} "
          f"{'locked':>10} {yn(gates['g1_prereg_committed']['pass']):>7}")
    print(f"{'G2':<4} {'IS stationary bootstrap (blk21,n1000,s7)':<44} "
          f"{g2['p_value']:>14.4f} {'<=0.05':>10} {yn(g2['pass']):>7}")
    print(f"{'G3':<4} {'CPCV K=6 emb10 all-combos mean>0':<44} "
          f"{g3['statistic']:>14.6f} {'>0':>10} {yn(g3['pass']):>7}")
    print(f"{'G4':<4} {'5 expanding WF folds + 60pct share cap':<44} "
          f"{g4['statistic']:>14.4f} {'>0/all':>10} {yn(g4['pass']):>7}")
    print(f"{'G5':<4} {'circ-block perm (blk10,n1000,s7) vs p95':<44} "
          f"{g5['statistic']:>14.4f} {('>p95 %.4f' % g5['threshold']):>10} "
          f"{yn(g5['pass']):>7}")
    print(f"{'G6':<4} {'DSR ledger via preregister.py (operator)':<44} "
          f"{'manual':>14} {'ledger':>10} {'PENDING':>7}")
    print("-" * 78)
    print(f"{'CHR':<4} {'OOS net CAGR>SPY AND OOS net Sharpe>SPY':<44} "
          f"{charter['oos_net_sharpe_strategy'] - charter['oos_net_sharpe_spy']:>14.4f} "
          f"{'both>':>10} {yn(charter['pass']):>7}")
    print("-" * 78)
    print(f"effective eval start (post-warmup): {cal[start_i].date()} | "
          f"IS excess n={len(is_excess)} | OOS excess n={len(oos_excess)} | "
          f"trades={strat['trades']}")
    print(f"G3 combos failing: {g3['details']['combinations_failing']}/"
          f"{g3['details']['combination_count']} | G4 max fold share: "
          f"{g4['details']['max_fold_share']:.4f} (cap {G4_MAX_FOLD_SHARE})")
    print(f"all_computed_gates_pass={all_gates_pass} | verdict authority: AUDITOR "
          "| G6 DSR ledger = manual operator step")
    print(f"results -> {os.path.relpath(OUT_RESULTS, BASE)}")


if __name__ == "__main__":
    main()
