"""Wave 1 / H2 — FRED-Regime-Conditioned Momentum Top-5 (FROZEN PREREG RUNNER).

PAPER-ONLY. LIVE TRADING DISABLED. FAIL-CLOSED. Zero fitted parameters.

Implements docs/data/wave1_h2_fred_regime_momentum_prereg.md (frozen
2026-08-24) EXACTLY: gates G2-G5 computed mechanically; G1 reported as
artifact check; G6 (DSR ledger) left as an explicit MANUAL STEP for the
operator/auditor -- this script NEVER self-certifies a PASS verdict
(builder seat has no PASS authority under hunt law).

Core rule/costs are BYTE-IDENTICAL to strategies/us_momentum_top5.yaml and
to Wave-1/H1 (scripts/wave1_h1_test.py): monthly last-bar top-5 by 126d
return skipping 21d, equal weight 1/5, warmup 340d, drift_rebal 0.05,
exec_delay 1 bar, 5 bps/side slippage, $0 commission, T+1 cash, min-$1
order. Benchmark: SPY buy-and-hold through IDENTICAL fee accounting.
H2 differs from H1 ONLY in: (1) universe = full snapshot intersect local
OHLCV minus SPY (scripts/ml_sl_exit_test.py load_snapshot_tickers logic);
(2) a binary FRED-regime exposure gate; (3) NO control arm.

EXECUTED BRANCH: B_lag5_trading_days (MANDATORY per prereg section 3
point-in-time guard: MAIN pre-run PIT verification FAILED -- the generator
(src/risk/fred_macro_provider.py lines 161-176) stamps same-day values and
the regime cache has no in-repo reproducible writer, so label availability
as-of each historical close is NOT verifiable). effective_gate(i) = last
regime label with date <= cal[i-5] == "RISK_ON"; missing/no label ->
gate OFF (fail-closed), occurrences counted. Branch A (lag=1) was NEVER run.

Lineage: portfolio machinery, stochastic gates G2/G3/G4/G5, and reporting
helpers are copied VERBATIM from scripts/wave1_h1_test.py (which itself
derives from scripts/ml_sl_exit_test.py). Only the regime-gating layer,
the universe loader, and the removal of the control arm are new. Metric
helpers imported from ml_sl_exit_test when possible with verbatim inline
fallbacks so this file runs standalone offline.

Outputs:
  docs/data/wave1_h2_results.json   (full numbers; deterministic, seeded)
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
SNAP_PATH = os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json")
REGIME_PATH = os.path.join(BASE, "data", "cache",
                           "fred_historical_regimes.json")
PREREG_PATH = os.path.join(BASE, "docs", "data",
                           "wave1_h2_fred_regime_momentum_prereg.md")
OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave1_h2_results.json")

# ---- Frozen spec constants (docs/data/wave1_h2_fred_regime_momentum_prereg.md)
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

# Regime layer (executed branch B; ZERO tuned parameters)
REGIME_LAG_BARS = 5                 # mandatory branch B: 5 TRADING bars
ALLOWED_LABELS = {"RISK_ON", "NEUTRAL", "RISK_OFF", "STAGFLATION"}
RISK_ON_LABEL = "RISK_ON"

# Gates (identical constants to H1)
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


# ---- Universe + regime data ---------------------------------------------------
def load_snapshot_tickers():
    """VERBATIM from scripts/ml_sl_exit_test.py: snapshot map keys intersect
    local OHLCV csv stems, SPY excluded."""
    with open(SNAP_PATH, encoding="utf-8") as f:
        snap = set(json.load(f)["ticker_to_names"].keys())
    local = {f[:-4].upper() for f in os.listdir(OHLCV_DIR) if f.endswith(".csv")}
    return sorted((snap & local) - {"SPY"})


def load_regimes():
    """Load {ISO date: label} FRED historical regime cache. Fail-closed."""
    if not os.path.isfile(REGIME_PATH):
        raise SystemExit(f"FAIL-CLOSED: missing regime cache: {REGIME_PATH}")
    with open(REGIME_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict) or not raw:
        raise SystemExit("FAIL-CLOSED: regime cache empty or malformed")
    by_ts = {}
    for k, v in raw.items():
        ts = pd.Timestamp(k).normalize()
        if v not in ALLOWED_LABELS:
            raise SystemExit(
                f"FAIL-CLOSED: unknown regime label {v!r} at {k}")
        by_ts[ts] = v
    return by_ts


def effective_gate_array(cal, regimes_by_ts):
    """EXECUTED BRANCH B (prereg section 3): effective_gate(i) = (last regime
    label with date <= cal[i-5] == RISK_ON), i.e. the label as-of the date
    5 TRADING BARS before bar i. Exact-date lookup on the daily-keyed regime
    cache; a missing/no label yields gate OFF (fail-closed) and is counted.
    Branch A (lag=1 trading day) was NEVER run (PIT verification failed)."""
    n = len(cal)
    gate = np.zeros(n, dtype=bool)
    missing = np.zeros(n, dtype=np.int64)
    for i in range(n):
        j = i - REGIME_LAG_BARS
        if j < 0:
            missing[i] += 1
            continue
        lab = regimes_by_ts.get(cal[j])
        if lab is None:
            missing[i] += 1
            continue
        gate[i] = (lab == RISK_ON_LABEL)
    return gate, missing


# ---- Data -------------------------------------------------------------------
def load_data(tickers):
    """Load universe + SPY OHLCV closes onto a union calendar. Fail-closed."""
    need = list(tickers) + [BENCHMARK]
    missing = [t for t in need
               if not os.path.isfile(os.path.join(OHLCV_DIR, f"{t}.csv"))]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: missing OHLCV files: {missing}")
    frames, per_file_rows = {}, {}
    for t in need:
        df = pd.read_csv(os.path.join(OHLCV_DIR, f"{t}.csv"),
                         parse_dates=["date"])
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
            "close": close,                    # raw (NaN where absent)
            "close_ffill": close.ffill(),      # marks, as in reference engine
            "mom": close.shift(SKIP) / close.shift(SKIP + LOOKBACK) - 1.0,
            "hist_cnt": close.notna().cumsum().to_numpy(),
        }
    spy_close = frames[BENCHMARK].reindex(cal)
    spy_ffill = spy_close.ffill()
    short_names = sorted(t for t in tickers
                         if str(frames[t].index[-1].date())
                         < str(cal[-1].date()))
    integrity = {
        "universe_size": len(tickers),
        "universe_tickers_sorted": list(tickers),
        "universe_source": ("cache/cycle3_13f_ticker_map.json keys "
                            "INTERSECT market_data_2019_2026/ohlcv/*.csv "
                            "stems MINUS SPY (verbatim "
                            "scripts/ml_sl_exit_test.py "
                            "load_snapshot_tickers logic)"),
        "benchmark": {"ticker": BENCHMARK,
                      "rows": per_file_rows[BENCHMARK],
                      "first": str(frames[BENCHMARK].index[0].date()),
                      "last": str(frames[BENCHMARK].index[-1].date())},
        "calendar": {"n_bars": int(len(cal)),
                     "first": str(cal[0].date()),
                     "last": str(cal[-1].date())},
        "names_ending_before_calendar_end_count": len(short_names),
        "names_ending_before_calendar_end": short_names,
    }
    return panel, cal, spy_close, spy_ffill, integrity


# ---- Engines ----------------------------------------------------------------
def spy_engine(spy_ffill, start_i, end_i):
    """SPY buy-and-hold, identical fee accounting.

    Fee convention (defined HERE; no prior house precedent in the reference
    engine): single entry at the first evaluated close paying COST via reduced
    shares; $0 commission; position held open to the window end (no terminal
    exit cost applied); daily marks at ffilled close. Copied verbatim from
    scripts/wave1_h1_test.py.
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


def simulate_gated(panel, cal, me_mask, gate_arr, start_i, end_i):
    """Monthly top-5 momentum sim with the FRED-regime exposure gate.

    Engine core copied VERBATIM from scripts/wave1_h1_test.simulate (itself
    adapted from scripts/ml_sl_exit_test.py): signals at month-end close,
    fills NEXT bar (exec_delay 1), 5 bps/side, $0 commission, same-bar cash
    crediting, ffilled marks, min-$1 order guard, unfilled orders dropped
    after their single next-bar attempt.

    Declared gating mechanics (recorded in results notes):
      * Selection state updates monthly EXACTLY like the ungated engine --
        top-5 recomputed EVERY month-end REGARDLESS of gate (silently while
        OFF: the selection variable updates but NO orders are queued).
      * When the gate turns OFF (detected at the TOP of bar i, BEFORE that
        bar's fills): discard any still-unfilled pending BUY orders queued
        under the ON regime (zero cost -- never filled), and queue FULL
        liquidation (shares=None) of every open position; fills land NEXT
        bar through the normal queue (exec_delay 1; sells pay 5bps).
        While OFF: hold cash (0% interest), no drift rebalance, selection
        keeps updating silently.
      * When the gate turns ON at bar i: queue entry buys (notional=None =>
        fills at 1/5 of marked equity at the fill bar) restoring equal-weight
        in the CURRENT (most recent monthly) selection members through the
        engine's pending queues; min-$1 guard applies; entries pay 5bps.
      * Drift-band rebalance active ONLY while the gate is ON.
    """
    cash = INIT_EQUITY
    positions = {}                      # t -> {"shares": float}
    pending_buys, pending_sells = [], []  # dicts: {"ticker","notional"|"shares","reason"}
    sel = []                            # current monthly selection (updates silently)
    equity = np.empty(end_i - start_i + 1)
    n_trades = 0
    stats = {"transitions": 0,
             "cancelled_pending_buy_orders": 0,
             "regime_entry_orders_queued": 0,
             "regime_exit_orders_queued": 0,
             "off_bars_with_open_positions": 0}
    prev_on = None                      # cold start: no transition on first bar

    def px(t, i):
        v = panel[t]["close_ffill"].iloc[i]
        return np.nan if pd.isna(v) else float(v)

    def mark(i):
        return cash + sum(rec["shares"] * px(t, i) for t, rec in positions.items())

    for i in range(start_i, end_i + 1):
        cur_on = bool(gate_arr[i])

        # 0) regime-gate transition handling -- detected at the TOP of bar i
        #    BEFORE that bar's fills so in-flight orders queued under the
        #    prior regime can still be acted on (orders queued HERE fill
        #    NEXT bar; exec_delay 1; costs arise only from actual fills on
        #    switched notional).
        if prev_on is not None and cur_on != prev_on:
            stats["transitions"] += 1
            if prev_on and not cur_on:
                # ON -> OFF: cancel unfilled intended buys (never filled,
                # zero cost) and queue FULL liquidation of all positions.
                stats["cancelled_pending_buy_orders"] += len(pending_buys)
                pending_buys = []
                for t in list(positions):
                    pending_sells.append({"ticker": t, "shares": None,
                                          "reason": "regime_exit"})
                    stats["regime_exit_orders_queued"] += 1
            else:
                # OFF -> ON: restore equal-weight 1/5-of-current-equity in
                # the CURRENT selection members (entries pay 5bps at fill).
                queued_t = {o["ticker"] for o in pending_buys}
                for t in sel:
                    if t not in positions and t not in queued_t:
                        pending_buys.append({"ticker": t, "notional": None,
                                             "reason": "regime_entry"})
                        stats["regime_entry_orders_queued"] += 1
        prev_on = cur_on

        # 1) fills for sells queued on the previous bar (VERBATIM H1)
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

        # 2) fills for buys queued on the previous bar (VERBATIM H1)
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

        # 3) month-end selection signal (byte-identical rule). Selection is
        #    recomputed EVERY month-end REGARDLESS of gate; order queuing
        #    happens ONLY while the gate is ON ("selection keeps updating
        #    silently" while OFF).
        if me_mask[i] and i < end_i:
            scores = {}
            for t, d in panel.items():
                m = d["mom"].iloc[i]
                if not pd.isna(m) and d["hist_cnt"][i] >= WARMUP:
                    scores[t] = float(m)
            top = [t for t, _ in sorted(scores.items(),
                                        key=lambda kv: kv[1],
                                        reverse=True)[:TOP_N]]
            sel = top
            if cur_on:
                # dedup vs regime_entry orders queued earlier THIS bar
                # (OFF->ON transition coinciding with a month-end): H2-only
                # guard, no-op in ungated flow.
                queued_t = {o["ticker"] for o in pending_buys}
                for t in list(positions):
                    if t not in top:
                        pending_sells.append({"ticker": t, "shares": None,
                                              "reason": "rank_drop"})
                for t in top:
                    if t not in positions and t not in queued_t:
                        pending_buys.append({"ticker": t, "notional": None,
                                             "reason": "entry"})

        # 4) drift-band rebalance (VERBATIM H1 extension; ACTIVE ONLY while
        #    gate ON). Checked daily after marking; deviations beyond
        #    +/-0.05 of the 1/TOP_N target weight are traded back to target
        #    on the NEXT bar through the same pending queues; min-$1 guard.
        if cur_on and i < end_i and positions:
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
        if not cur_on and positions:
            stats["off_bars_with_open_positions"] += 1

    return {"equity": pd.Series(equity, index=cal[start_i:end_i + 1]),
            "trades": n_trades,
            "stats": stats}


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
    scripts/ml_sl_exit_test.py -- the H2 prereg specifies CIRCULAR (identical
    to H1 machinery).
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
    # period ENDS, not session requirements. (Identical to H1 machinery.)
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
    tickers = load_snapshot_tickers()
    if not tickers:
        raise SystemExit("FAIL-CLOSED: empty universe (snapshot intersect local)")
    panel, cal, _spy_raw, spy_ffill, integrity = load_data(tickers)
    regimes_by_ts = load_regimes()
    gate_arr, missing_arr = effective_gate_array(cal, regimes_by_ts)

    # SIM START (DECLARED INTERPRETATION, recorded in notes): bar index
    # WARMUP=340 of the union calendar. The YAML warmup_days=340 skips the
    # first 340 bars; per-name hist_cnt>=340 governs SELECTABILITY exactly as
    # in wave1_h1_test.py. SPY baseline starts at the SAME bar.
    if len(cal) <= WARMUP + 1:
        raise SystemExit(
            f"FAIL-CLOSED: calendar has {len(cal)} bars; warmup {WARMUP} "
            "leaves no evaluated history")
    start_i = WARMUP
    last_i = len(cal) - 1
    if cal[-1] != G4_FOLD_ENDS[-1]:
        raise SystemExit(
            f"FAIL-CLOSED: data ends {cal[-1].date()} but frozen WF final endpoint "
            f"is {G4_FOLD_ENDS[-1].date()}")

    me_mask = month_end_mask(cal)

    strat = simulate_gated(panel, cal, me_mask, gate_arr, start_i, last_i)
    strat_eq = strat["equity"]
    spy_eq = spy_engine(spy_ffill, start_i, last_i)

    strat_r = strat_eq.pct_change()
    spy_r = spy_eq.pct_change()
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

    # Gate-state statistics over the evaluated span
    g_span = gate_arr[start_i:last_i + 1]
    m_span = missing_arr[start_i:last_i + 1]
    gate_state = {
        "evaluated_bars": int(g_span.size),
        "bars_gate_on": int(g_span.sum()),
        "bars_gate_off": int((~g_span).sum()),
        "fraction_on": float(g_span.mean()),
        "transitions_total": int(np.count_nonzero(g_span[1:] != g_span[:-1])),
        "on_to_off_transitions":
            int(np.count_nonzero(g_span[1:] & ~g_span[:-1])),
        "off_to_on_transitions":
            int(np.count_nonzero(~g_span[1:] & g_span[:-1])),
        "missing_label_bars": int(m_span.sum()),
        "missing_label_dates_example": [str(cal[start_i + k].date())
                                        for k in np.flatnonzero(m_span)[:5]],
        "sim_off_bars_with_open_positions":
            strat["stats"]["off_bars_with_open_positions"],
        "regime_entry_orders_queued":
            strat["stats"]["regime_entry_orders_queued"],
        "regime_exit_orders_queued":
            strat["stats"]["regime_exit_orders_queued"],
        "pending_buy_orders_cancelled_at_gate_off":
            strat["stats"]["cancelled_pending_buy_orders"],
    }
    if gate_state["missing_label_bars"] > 0:
        print(f"WARNING: {gate_state['missing_label_bars']} evaluated bars had "
              f"no regime label -> gate forced OFF (fail-closed)")

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
                         "docs/data/eval_wave1_h2.json, trials charged = 1 "
                         "(the single executed point-in-time branch). Recorded "
                         "by the operator AFTER auditor verdict; this "
                         "builder-run never self-certifies."),
                "command_shape": ("python scripts/preregister.py record "
                                  "<spec_path> --verdict <PASS|FAIL|"
                                  "HONEST_ABANDON> [--eval-path "
                                  "docs/data/wave1_h2_results.json]"),
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

    results = {
        "claim": ("Gating the EXACT incumbent us_momentum_top5 rule (full "
                  "snapshot universe) to be invested ONLY when the FRED macro "
                  "regime label is RISK_ON improves OOS net performance to beat "
                  "SPY buy-and-hold on BOTH CAGR and Sharpe while passing gates "
                  "G2-G5"),
        "prereg": os.path.relpath(PREREG_PATH, BASE),
        "prereg_status": "FROZEN 2026-08-24 - LOCKED before any in-sample run",
        "paper_only": True,
        "verdict_authority": ("RESERVED FOR AUDITOR SEAT - this output reports "
                              "mechanical gate booleans only; no PASS claim is "
                              "made by the builder"),
        "executed_branch": "B_lag5_trading_days",
        "branch_decision": {
            "executed": "B_lag5_trading_days",
            "prereg_basis": "section 3 point-in-time guard (both branches "
                            "pre-declared before any in-sample run)",
            "verification_outcome": (
                "MAIN pre-run PIT verification of the generating pipeline "
                "FAILED: src/risk/fred_macro_provider.py lines 161-176 stamp "
                "each date's regime from SAME-DAY spread/inflation values with "
                "no publication-lag handling, and the regime cache "
                "(data/cache/fred_historical_regimes.json) has no in-repo "
                "reproducible writer, so label availability as-of each "
                "historical close is NOT verifiable"),
            "consequence": ("branch B (mandatory 5-trading-bar application lag) "
                            "is PRIMARY per prereg; branch A (lag=1) was NEVER "
                            "run; no other variant may be run"),
            "trials_charged": 1,
        },
        "config_echo": {
            "universe": {
                "definition": "snapshot map keys INTERSECT local OHLCV csv "
                              "stems MINUS SPY (verbatim "
                              "scripts/ml_sl_exit_test.py "
                              "load_snapshot_tickers logic)",
                "size": integrity["universe_size"],
                "verified_size_from_prereg_verification": 481,
                "size_matches_verified": bool(integrity["universe_size"] == 481),
                "tickers_sorted": integrity["universe_tickers_sorted"],
            },
            "benchmark": BENCHMARK,
            "params_byte_identical_to": ("strategies/us_momentum_top5.yaml and "
                                         "scripts/wave1_h1_test.py"),
            "params": {"top_n": TOP_N, "lookback_days": LOOKBACK,
                       "skip_days": SKIP, "warmup_days": WARMUP,
                       "rebalance": "monthly (last trading bar)",
                       "drift_rebal": DRIFT_BAND, "exec_delay_bars": EXEC_DELAY,
                       "slippage_per_side": COST, "commission": COMMISSION,
                       "settlement": "T+1 declared; engine credits cash same-bar "
                                     "(identical to reference engine)"},
            "regime_layer": {
                "source_path": os.path.relpath(REGIME_PATH, BASE),
                "labels_allowed": sorted(ALLOWED_LABELS),
                "invested_label": RISK_ON_LABEL,
                "rule": "ONE binary rule; full weight iff effective gate ON, "
                        "else 100% cash at 0% interest; no scaling grid, no "
                        "per-label treatment (ZERO tuned parameters)",
                "effective_gate": ("label looked up as-of the date "
                                   "REGIME_LAG_BARS trading bars before bar i"),
                "regime_lag_bars": REGIME_LAG_BARS,
                "fail_closed_missing": True,
            },
            "windows": {"is_nominal": ["2019-01-02", "2023-12-31"],
                        "oos_nominal": ["2024-01-01", "2026-08-07"],
                        "sim_start_rule": "bar index WARMUP=340 of the union "
                                          "calendar (declared interpretation)",
                        "effective_evaluated_start":
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
                "derived_from": ("scripts/wave1_h1_test.py (Wave-1/H1 runner; "
                                 "itself adapted from "
                                 "scripts/ml_sl_exit_test.py static arm)"),
                "metric_source": METRIC_SOURCE,
                "copied_verbatim": ["simulate core (fills/scoring/drift)",
                                    "spy_engine + fee convention",
                                    "stationary bootstrap G2",
                                    "circular block shuffle G5",
                                    "CPCV G3",
                                    "walk-forward G4",
                                    "metric + reporting helpers"],
                "h2_deltas_vs_h1": [
                    "universe = full snapshot minus SPY instead of fixed "
                    "Universe A",
                    "binary FRED-regime exposure gate (branch B, lag=5 "
                    "trading bars) with fail-closed missing labels",
                    "NO control arm (descriptive control removed)",
                    "sim start = bar index WARMUP=340 of the union calendar "
                    "(H1 used first bar where EVERY member warmed)",
                ],
                "spying_fee_convention": (
                    "copied verbatim from H1: SPY pays entry slippage 5bps "
                    "via reduced shares at the first evaluated close; held "
                    "open; no terminal exit cost; $0 commission"),
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
        "gate_state": gate_state,
        "gates": gates,
        "charter_bar": charter,
        "control_arm": None,
        "trades_total": strat["trades"],
        "all_computed_gates_pass": bool(all_gates_pass),
        "notes": [
            "PRIOR ART CITATION (standing rule): cycle5_c6_evaluation.json -- "
            "the FRED RISK_ON gate FAILED its bar (bar_pass false, null_pass "
            "false) on an SMA200 multi-asset core. H2 changed conditions = "
            "different core family (momentum top-5 equities) + six-gate "
            "machinery.",
            "PIT VERIFICATION OUTCOME (branch decision): the regime generator "
            "uses same-day values (src/risk/fred_macro_provider.py lines "
            "161-176) and the cache has no in-repo writer => NOT verifiable => "
            "branch B (5-trading-day application lag) is primary per prereg "
            "section 3; branch A never run.",
            "SIM-START INTERPRETATION (declared): simulation begins at bar "
            "index WARMUP=340 of the union calendar; YAML warmup_days=340 "
            "skips the first 340 bars; per-name hist_cnt>=340 governs "
            "selectability exactly as in wave1_h1_test.py. SPY baseline "
            "starts at the same bar.",
            "GATING MECHANICS (declared): selection state updates monthly "
            "EXACTLY like the ungated engine (top-5 recomputed every "
            "month-end regardless of gate, silently while OFF). Realized "
            "exposure follows the gate: ON->OFF discards still-unfilled "
            "pending buys (never filled, zero cost) and queues FULL "
            "liquidation of all positions next bar (sells pay 5bps); while "
            "OFF hold cash at 0% interest; OFF->ON queues entry buys next "
            "bar restoring equal-weight 1/5-of-current-equity in the CURRENT "
            "selection members through the engine's pending-order queues "
            "(min-$1 guard; entries pay 5bps). Drift-band rebalance active "
            "only while ON. Costs arise only from actual fills = switched "
            "notional only.",
            "Cold start: if the gate is ON at the first evaluated bar, "
            "initial deployment waits for the FIRST month-end signal (or an "
            "OFF->ON transition), identical to the incumbent engine's "
            "cold-start behavior; no artificial immediate deployment.",
            "Unfilled pending orders are dropped after their single next-bar "
            "attempt (reference-engine behavior). Post-warmup this is "
            "expected to be a no-op for HELD names: close_ffill only holds "
            "NaN before a name's first observation, and a position cannot "
            "exist in a name with no observations up to that bar.",
            "Regime lookups use exact calendar-date keys against a "
            "daily-keyed cache covering 2003-01-02..2026-08-14, so lag-5 "
            "lookups inside 2019..2026-08-07 are safe; any missing label "
            "forces the gate OFF and is counted in "
            "gate_state.missing_label_bars.",
            "G3 combination semantics declared in gates.g3_cpcv.details; G4 "
            "per-fold Sharpe is EXPANDING-SPAN by reading of 'expanding OOS "
            "folds'; incremental-segment Sharpes reported descriptively.",
            "G4 frozen calendar endpoints snap to the last trading bar on or "
            "before each date (inherited pre-run delta from H1, recorded "
            "before any in-sample run; e.g. Sun 2024-06-30 -> Fri 2024-06-28).",
            "Survivorship/universe lookahead inherited from the frozen "
            "2026-era snapshot definition; accepted by the prereg as "
            "claim-scoping (same posture as H1).",
            "Warmup 340 trading bars consumes the leading portion of nominal "
            "IS; evaluation begins at cal[340].",
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
    print("WAVE-1 / H2 FRED-REGIME-GATED MOMENTUM TOP-5  |  PAPER-ONLY | "
          "FAIL-CLOSED | FROZEN PREREG | BRANCH B_lag5_trading_days")
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
    print(f"universe={len(tickers)} | eval start {cal[start_i].date()} | "
          f"IS excess n={len(is_excess)} | OOS excess n={len(oos_excess)} | "
          f"trades={strat['trades']}")
    print(f"gate: ON {gate_state['bars_gate_on']}/{gate_state['evaluated_bars']} "
          f"({gate_state['fraction_on']:.1%}) | transitions "
          f"{gate_state['transitions_total']} "
          f"(off->{gate_state['on_to_off_transitions']}, "
          f"on->{gate_state['off_to_on_transitions']}) | missing-label bars "
          f"{gate_state['missing_label_bars']} | off-bars-with-positions "
          f"{gate_state['sim_off_bars_with_open_positions']}")
    print(f"G3 combos failing: {g3['details']['combinations_failing']}/"
          f"{g3['details']['combination_count']} | G4 max fold share: "
          f"{g4['details']['max_fold_share']:.4f} (cap {G4_MAX_FOLD_SHARE})")
    print(f"all_computed_gates_pass={all_gates_pass} | verdict authority: AUDITOR "
          "| G6 DSR ledger = manual operator step")
    print(f"results -> {os.path.relpath(OUT_RESULTS, BASE)}")


if __name__ == "__main__":
    main()
