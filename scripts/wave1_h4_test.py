"""Wave-1 H4 test — Politician-trade replication (Arm P, House-only) +
Cramer follow-vs-fade pair (Arm C1/C2). FROZEN SPEC:
docs/data/wave1_h4_poltrade_cramer_prereg.md incl. Amendment A (A1-A5).

PAPER-ONLY / FAIL-CLOSED. Serial single-file verification only.
Gate machinery IMPORTED VERBATIM from scripts/wave1_h3_test.py (never
re-implemented). Per-arm G4 fold-end lists are the prereg-frozen half-year
dates intersected with each arm's evaluation span (Amendment A5), injected
via the imported module's constants before calling its unchanged functions.

Arms:
  P  House PTR purchases, entry = close of first bar >= filing_date + 45d
  C1 Cramer start_long picks, entry = close of first bar >= air_date + 1 bar
  C2 synthetic inverse-excess of C1: -(r_stock - r_SPY), SIGNAL VALIDATION ONLY

Shared engine per arm: equal-weight slots (equity_prev/10 at entry), max 10
open positions, fixed 90-trading-bar hold, 5bps/side, cash yield 0%, no
re-entry in an open window, overflow events skipped, incomplete final holds
excluded symmetrically (A5). SPY twin leg = identical schedule/slots in SPY.
"""

import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import wave1_h3_test as W1  # noqa: E402  (constants + gate machinery, verbatim)

IS_END = W1.IS_END
OOS_START = W1.OOS_START

OHLCV_DIR = W1.OHLCV_DIR
RAW_DIR = os.path.join(BASE, "data", "h4_raw")
OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave1_h4_results.json")

BENCHMARK = "SPY"
COST = W1.COST
INIT_EQUITY = W1.INIT_EQUITY
HOLD_BARS = 90
MAX_OPEN = 10
PTR_LAG_DAYS = 45
EVAL_WINDOW_END = pd.Timestamp("2026-08-07")
ARM_C_SIGNAL_START = pd.Timestamp("2019-01-02")
ARM_C_SIGNAL_END = pd.Timestamp("2024-12-31")
POWER_MIN_EVENTS = 40
FROZEN_FOLD_ENDS = [pd.Timestamp("2024-06-30"), pd.Timestamp("2024-12-31"),
                    pd.Timestamp("2025-06-30"), pd.Timestamp("2025-12-31"),
                    pd.Timestamp("2026-08-07")]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_panel(tickers, cal):
    frames = {}
    for t in sorted(set(tickers)):
        p = os.path.join(OHLCV_DIR, f"{t}.csv")
        if not os.path.isfile(p):
            raise SystemExit(f"FAIL-CLOSED: missing OHLCV file for {t}")
        df = pd.read_csv(p, parse_dates=["date"])
        if df.empty:
            raise SystemExit(f"FAIL-CLOSED: empty OHLCV file for {t}")
        frames[t] = df.set_index("date")["close"].astype(float).sort_index()
    missing_bars = int((frames[BENCHMARK].index > cal).sum())
    close_ffill = {t: s.reindex(cal).ffill() for t, s in frames.items()}
    return close_ffill


def build_arm_p_events(cal, local_tickers):
    path = os.path.join(RAW_DIR, "house_transactions_raw.csv")
    if not os.path.isfile(path):
        raise SystemExit("FAIL-CLOSED: house_transactions_raw.csv missing (acquire first)")
    df = pd.read_csv(path, dtype=str)
    df = df[(df["tx_type_norm"] == "purchase") & (df["ticker_confident"] == "True")]
    df["filing_dt"] = pd.to_datetime(df["filing_date_iso"], errors="coerce")
    df["trigger"] = df["filing_dt"] + pd.Timedelta(days=PTR_LAG_DAYS)
    df = df.dropna(subset=["trigger"])
    df["ticker"] = df["ticker"].str.upper()
    raw_n = len(df)
    df = df[df["ticker"].isin(local_tickers)]
    n_unmapped = raw_n - len(df)
    df = df.drop_duplicates(subset=["ticker", "tx_date_iso", "filing_date_iso"])
    df = df.sort_values(["trigger", "ticker"])
    dropped_incomplete = 0
    events, seen_open_order = [], set()
    last_i = len(cal) - 1
    for _, r in df.iterrows():
        j = int(cal.searchsorted(r["trigger"], side="left"))
        if j > last_i or j + HOLD_BARS > last_i:
            dropped_incomplete += 1
            continue
        events.append({"ticker": r["ticker"], "entry_i": j,
                       "member": r["member_name"], "filing": r["filing_date_iso"]})
    counts = {"raw_purchase_rows_confident": int(raw_n),
              "unmapped_tickers": int(n_unmapped),
              "deduped_events": int(len(events)),
              "dropped_incomplete_hold": int(dropped_incomplete)}
    return events, counts


def build_arm_c_events(cal, local_tickers):
    path = os.path.join(RAW_DIR, "cramer_snapshot_full.csv")
    if not os.path.isfile(path):
        raise SystemExit("FAIL-CLOSED: cramer_snapshot_full.csv missing (acquire first)")
    usecols = ["signal_id", "signal_date", "ticker_symbol", "signal_type"]
    df = pd.read_csv(path, usecols=usecols)
    sig = df.drop_duplicates("signal_id")
    sig["signal_date"] = pd.to_datetime(sig["signal_date"], errors="coerce")
    sig = sig[sig["signal_type"] == "start_long"]
    sig = sig[(sig["signal_date"] >= ARM_C_SIGNAL_START)
              & (sig["signal_date"] <= ARM_C_SIGNAL_END)]
    sig["ticker"] = sig["ticker_symbol"].astype(str).str.upper()
    raw_n = len(sig)
    sig = sig[sig["ticker"].isin(local_tickers)]
    n_unmapped = raw_n - len(sig)
    sig = sig.sort_values(["signal_date", "ticker"])
    dropped_incomplete = 0
    events = []
    last_i = len(cal) - 1
    for _, r in sig.iterrows():
        j = int(cal.searchsorted(r["signal_date"], side="right"))
        if j > last_i or j + HOLD_BARS > last_i:
            dropped_incomplete += 1
            continue
        events.append({"ticker": r["ticker"], "entry_i": j})
    counts = {"raw_start_long_signals_in_window": int(raw_n),
              "unmapped_tickers": int(n_unmapped),
              "deduped_events": int(len(events)),
              "dropped_incomplete_hold": int(dropped_incomplete)}
    return events, counts


def run_portfolio(events, cal, close_ffill, instrument_of):
    """Equal-weight slot portfolio; returns (equity Series, stats dict)."""
    by_day = {}
    for ev in events:
        by_day.setdefault(ev["entry_i"], []).append(ev)
    cash = INIT_EQUITY
    positions = {}
    skipped_overflow = skipped_reentry = extended_exits = 0
    eq_vals = np.full(len(cal), np.nan)
    prev_eq = INIT_EQUITY
    n_bars = len(cal)
    last_exit_i = -1
    for i in range(n_bars):
        due = [t for t, rec in positions.items() if i - rec["entry_i"] >= HOLD_BARS]
        for t in sorted(due):
            px = close_ffill[t].iloc[i]
            if pd.isna(px) or px <= 0:
                if i == n_bars - 1:
                    raise SystemExit(f"FAIL-CLOSED: no exit price for {t} by last bar")
                continue
            rec = positions.pop(t)
            if i - rec["entry_i"] > HOLD_BARS:
                extended_exits += 1
            cash += rec["shares"] * float(px) * (1.0 - COST)
            last_exit_i = max(last_exit_i, i)
        if i in by_day:
            for ev in by_day[i]:
                t = instrument_of(ev)
                if len(positions) >= MAX_OPEN:
                    skipped_overflow += 1
                    continue
                if t in positions:
                    skipped_reentry += 1
                    continue
                px = close_ffill[t].iloc[i]
                if pd.isna(px) or px <= 0:
                    continue
                notional = min(prev_eq / MAX_OPEN, max(cash, 0.0))
                if notional < 1.0:
                    continue
                shares = notional / (float(px) * (1.0 + COST))
                cash -= shares * float(px) * (1.0 + COST)
                positions[t] = {"shares": shares, "entry_i": i}
        mark = cash + sum(rec["shares"] * float(close_ffill[t].iloc[i])
                          for t, rec in positions.items()
                          if not pd.isna(close_ffill[t].iloc[i]))
        eq_vals[i] = mark
        prev_eq = mark
    eq = pd.Series(eq_vals, index=cal)
    stats = {"skipped_overflow": skipped_overflow,
             "skipped_reentry": skipped_reentry,
             "extended_exits": extended_exits,
             "last_exit_i": int(last_exit_i)}
    return eq, stats


def fold_ends_for_span(span):
    ends = [ts for ts in FROZEN_FOLD_ENDS if ts <= span[-1]]
    if not ends or ends[-1] != span[-1]:
        ends = [ts for ts in ends if ts < span[-1]]
        ends.append(span[-1])
    return ends


def evaluate_arm(name, strat_eq, spy_eq, active_end_i, extra=None):
    a5_truncated = int(active_end_i) < len(strat_eq) - 1
    if a5_truncated:
        strat_eq = strat_eq.iloc[:int(active_end_i) + 1]
        spy_eq = spy_eq.iloc[:int(active_end_i) + 1]
    r_s = strat_eq.pct_change()
    r_b = spy_eq.pct_change()
    ex = (r_s - r_b).dropna()
    if ex.empty:
        raise SystemExit(f"FAIL-CLOSED: empty excess series for arm {name}")
    span = ex.index
    is_ex = ex[ex.index <= IS_END]
    oos_ex = ex[ex.index >= OOS_START]
    is_r_s = r_s[r_s.index <= IS_END]
    oos_r_s = r_s[r_s.index >= OOS_START]
    is_r_b = r_b[r_b.index <= IS_END]
    oos_r_b = r_b[r_b.index >= OOS_START]
    out = {
        "arm": name,
        "span": [str(span[0].date()), str(span[-1].date())],
        "a5_span_truncated": bool(a5_truncated),
        "n_eval_days": int(len(ex)),
        "n_is_days": int(len(is_ex)), "n_oos_days": int(len(oos_ex)),
        "observed": {
            "is_mean_daily_net_excess": float(is_ex.mean()) if len(is_ex) else None,
            "oos_ann_sharpe_net_excess": W1.sharpe(oos_ex) if len(oos_ex) else None,
            "full_ann_sharpe_net_excess": W1.sharpe(ex),
            "oos_sum_net_excess": float(oos_ex.sum()) if len(oos_ex) else None,
        },
        "strategy_metrics": {
            "is": {"sharpe": W1.sharpe(is_r_s),
                   "cagr": W1.cagr(strat_eq[strat_eq.index <= IS_END]),
                   "maxdd": W1.max_dd(strat_eq[strat_eq.index <= IS_END])},
            "oos": {"sharpe": W1.sharpe(oos_r_s),
                    "cagr": W1.cagr(strat_eq[strat_eq.index >= OOS_START]),
                    "maxdd": W1.max_dd(strat_eq[strat_eq.index >= OOS_START])},
        },
        "benchmark_twin_metrics": {
            "is": {"sharpe": W1.sharpe(is_r_b),
                   "cagr": W1.cagr(spy_eq[spy_eq.index <= IS_END])},
            "oos": {"sharpe": W1.sharpe(oos_r_b),
                    "cagr": W1.cagr(spy_eq[spy_eq.index >= OOS_START])},
        },
    }
    sm, bm = out["strategy_metrics"]["oos"], out["benchmark_twin_metrics"]["oos"]
    out["charter_bar"] = {
        "rule": "OOS net CAGR > SPY twin AND OOS net Sharpe > SPY twin (same engine/window/fees)",
        "cagr_pass": bool(sm["cagr"] > bm["cagr"]),
        "sharpe_pass": bool(sm["sharpe"] > bm["sharpe"]),
        "pass": bool(sm["cagr"] > bm["cagr"] and sm["sharpe"] > bm["sharpe"]),
        "oos_strategy_cagr": sm["cagr"], "oos_spYwin_cagr": bm["cagr"],
        "oos_strategy_sharpe": sm["sharpe"], "oos_spywin_sharpe": bm["sharpe"],
    }
    if extra:
        out["engine_stats"] = extra
    gates = {}

    def run_gates():
        if len(is_ex) < 100:
            gates["G2_insufficient_is_history"] = True
            return False
        fold_ends = fold_ends_for_span(span)
        W1.G4_FOLD_ENDS = fold_ends
        g2 = W1.g2_stationary_bootstrap(is_ex)
        g3 = W1.g3_cpcv(ex)
        g4 = W1.g4_walk_forward(oos_ex)
        g5 = W1.g5_permutation_null(
            oos_ex, out["observed"]["oos_ann_sharpe_net_excess"])
        gates["fold_ends_used"] = [str(ts.date()) for ts in fold_ends]
        for gid, res in (("G2_is_bootstrap", g2), ("G3_cpcv", g3),
                         ("G4_walk_forward", g4), ("G5_permutation_null", g5)):
            gates[gid] = res
        return bool(g2["pass"] and g3["pass"] and g4["pass"] and g5["pass"])

    out["statistical_gates_pass"] = run_gates()
    out["gates"] = gates
    return out


def main():
    local = {f[:-4].upper() for f in os.listdir(OHLCV_DIR) if f.endswith(".csv")}
    local.discard(BENCHMARK)

    spy_df = pd.read_csv(os.path.join(OHLCV_DIR, f"{BENCHMARK}.csv"),
                         parse_dates=["date"])
    cal = pd.DatetimeIndex(sorted(spy_df["date"].unique()))
    cal = cal[cal <= EVAL_WINDOW_END]

    p_events, p_counts = build_arm_p_events(cal, local)
    c_events, c_counts = build_arm_c_events(cal, local)

    results = {"generated_note": "wave1_h4 test run; paper-only; gates imported "
                                 "verbatim from scripts/wave1_h3_test.py",
               "provenance": {}, "arms": {}}

    for f in ("house_transactions_raw.csv", "house_ptr_filings.csv",
              "house_parse_report.json", "cramer_snapshot_full.csv"):
        p = os.path.join(RAW_DIR, f)
        if os.path.isfile(p):
            results["provenance"][f] = {"sha256": sha256_file(p)}
    rep = os.path.join(RAW_DIR, "house_parse_report.json")
    if os.path.isfile(rep):
        with open(rep, encoding="utf-8") as fh:
            results["provenance"]["house_parse_report"] = json.load(fh)

    needed = {BENCHMARK} | {e["ticker"] for e in p_events} | {e["ticker"] for e in c_events}
    close_ffill = load_panel(needed, cal)
    integrity = {"canonical_calendar": "SPY trading days <= 2026-08-07",
                 "n_bars": int(len(cal)),
                 "first": str(cal[0].date()), "last": str(cal[-1].date())}
    results["integrity"] = integrity

    def spy_of(ev):
        return BENCHMARK

    arms_meta = [("P_house_ptr_follow", p_events, p_counts),
                 ("C_cramer_pair", c_events, c_counts)]
    for name, events, counts in arms_meta:
        arm = {"power_gate": {"threshold_min_events": POWER_MIN_EVENTS,
                              "independent_events_admitted": len(events),
                              **counts}}
        if len(events) < POWER_MIN_EVENTS:
            arm["verdict"] = "INSUFFICIENT_POWER"
            arm["note"] = ("honest no-op per prereg §4 power gate; no p-values "
                           "reported as encouragement")
            results["arms"][name] = arm
            continue
        sched = sorted(events, key=lambda e: (e["entry_i"], e["ticker"]))
        strat_eq, st = run_portfolio(sched, cal, close_ffill, lambda e: e["ticker"])
        spy_eq, _ = run_portfolio(sched, cal, close_ffill, spy_of)
        active_end_i = st["last_exit_i"]
        arm.update(evaluate_arm(name, strat_eq, spy_eq, active_end_i, extra=st))
        if name.startswith("P"):
            arm["verdict"] = ("PASS" if (arm["statistical_gates_pass"]
                                         and arm["charter_bar"]["pass"]) else "FAIL")
        else:
            follow_pass = bool(arm["statistical_gates_pass"]
                               and arm["charter_bar"]["pass"])
            a5i = int(active_end_i)
            r_s = strat_eq.iloc[:a5i + 1].pct_change()
            r_b = spy_eq.iloc[:a5i + 1].pct_change()
            fade_ex = ((r_s - r_b) * -1.0).dropna()
            span = fade_ex.index
            is_f = fade_ex[fade_ex.index <= IS_END]
            oos_f = fade_ex[fade_ex.index >= OOS_START]
            fold_ends = fold_ends_for_span(span)
            W1.G4_FOLD_ENDS = fold_ends
            fg2 = W1.g2_stationary_bootstrap(is_f)
            fg3 = W1.g3_cpcv(fade_ex)
            fg4 = W1.g4_walk_forward(oos_f)
            fg5 = W1.g5_permutation_null(oos_f, W1.sharpe(oos_f))
            fade_pass = bool(fg2["pass"] and fg3["pass"] and fg4["pass"] and fg5["pass"])
            arm["fade_arm_C2"] = {
                "note": "synthetic inverse-excess; NON-DEPLOYABLE as cash account "
                        "(declared prereg §3); signal validation only",
                "span": [str(span[0].date()), str(span[-1].date())],
                "fold_ends_used": [str(ts.date()) for ts in fold_ends],
                "gates": {"G2_is_bootstrap": fg2, "G3_cpcv": fg3,
                          "G4_walk_forward": fg4, "G5_permutation_null": fg5},
                "pass": fade_pass,
            }
            if follow_pass and fade_pass:
                arm["verdict"] = "MUTUAL_EXCLUSIVE_VIOLATION"
            elif follow_pass:
                arm["verdict"] = "PASS_C1_FOLLOW"
            elif fade_pass:
                arm["verdict"] = "PASS_C2_FADE_NONDEPLOYABLE"
            else:
                arm["verdict"] = "FAIL"
        results["arms"][name] = arm

    with open(OUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({k: v.get("verdict", v.get("power_gate", {}).get(
        "independent_events_admitted")) for k, v in results["arms"].items()}))


if __name__ == "__main__":
    main()
