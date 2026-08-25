"""Wave-3 H4 test — Overnight-session capture on the incumbent basket.

FROZEN SPEC: docs/data/wave3_h4_overnight_capture_prereg.md (frozen @ 664ed78).
PAPER-ONLY / FAIL-CLOSED. Serial single-file verification only.

PRE-RUN DISAMBIGUATION (declared before any run, zero results seen): the frozen
spec's parenthetical "(captures Mon/Tue/Wed/Thu overnight legs)" and its
"exec_delay 1 bar" clause conflict. The detailed mechanism sentence governs:
entry executes AT the close of the first trading day of each ISO week (no delay);
exit at the open of the last trading day of the same week. Single-trading-day
weeks are skipped and counted.

Signals byte-identical to incumbent; gates verbatim from scripts/wave1_h3_test.py.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import wave1_h3_test as W1  # noqa: E402

OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave3_h4_results.json")


def month_end_mask(cal):
    periods = pd.Series(cal).dt.to_period("M")
    return (periods != periods.shift(-1)).to_numpy()


def overnight_portfolio(panel, cal, me_mask, spy_mode=False):
    cash = W1.INIT_EQUITY
    prev_eq = W1.INIT_EQUITY
    n = len(cal)
    eq = np.empty(n)
    weeks = pd.Series(cal).dt.isocalendar()
    week_id = (weeks["year"].astype(str) + "-W" + weeks["week"].astype(str)).to_numpy()
    first_of_week = np.zeros(n, dtype=bool)
    last_of_week = np.zeros(n, dtype=bool)
    for i in range(n):
        first_of_week[i] = (i == 0) or week_id[i] != week_id[i - 1]
        last_of_week[i] = (i == n - 1) or week_id[i] != week_id[i + 1]
    open_pos = {}
    pending_exit = False
    weeks_entered = weeks_skipped_single_day = 0
    latest_scores = {}

    def src_px(t, i):
        return panel["SPY_TWIN"].close_ffill.iloc[i] if spy_mode else panel[t]["close_ffill"].iloc[i]

    def src_open(t, i):
        return panel["SPY_TWIN"].open_ffill.iloc[i] if spy_mode else panel[t]["open_ffill"].iloc[i]

    for i in range(n):
        if pending_exit and open_pos:
            realized = 0.0
            ok = True
            for t, rec in open_pos.items():
                px = src_open(t, i)
                if pd.isna(px) or px <= 0:
                    ok = False
                    break
                realized += rec["shares"] * float(px) * (1.0 - W1.COST)
            if ok:
                cash += realized
                open_pos = {}
            pending_exit = False
        if last_of_week[i]:
            pending_exit = bool(open_pos)

        if me_mask[i]:
            scores = {}
            for t, d in panel.items():
                if t == "SPY_TWIN":
                    continue
                m = d["mom"].iloc[i]
                if not pd.isna(m) and d["hist_cnt"][i] >= W1.WARMUP:
                    scores[t] = float(m)
            latest_scores = {t: v for t, v in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:W1.TOP_N]}

        if first_of_week[i] and not last_of_week[i] and latest_scores:
            alloc = prev_eq / W1.TOP_N
            names = {}
            for t in latest_scores:
                px = src_px(t, i)
                if pd.isna(px) or px <= 0:
                    continue
                shares = alloc / (float(px) * (1.0 + W1.COST))
                names[t] = {"shares": shares}
            if len(names) == len(latest_scores):
                cost = sum(r["shares"] * float(src_px(t, i)) for t, r in names.items())
                cash -= cost * (1.0 + W1.COST)
                open_pos = names
                weeks_entered += 1
            else:
                weeks_skipped_single_day += 1
        elif first_of_week[i] and last_of_week[i]:
            weeks_skipped_single_day += 1

        mark = cash
        if open_pos:
            for t, rec in open_pos.items():
                px = src_px(t, i)
                if not pd.isna(px):
                    mark += rec["shares"] * float(px)
        eq[i] = mark
        prev_eq = mark
    stats = {"weeks_entered": weeks_entered,
             "weeks_skipped_single_day_or_gap": weeks_skipped_single_day}
    return pd.Series(eq, index=cal), stats


class TwinPanel:
    pass


def main():
    tickers = W1.load_snapshot_tickers()
    if not tickers:
        raise SystemExit("FAIL-CLOSED: empty universe")
    panel, cal, spy_close, spy_ffill, integrity = W1.load_data(tickers)
    if cal[-1] != W1.G4_FOLD_ENDS[-1]:
        raise SystemExit(f"FAIL-CLOSED: data ends {cal[-1].date()} != frozen endpoint")
    for t in list(panel):
        df = pd.read_csv(os.path.join(W1.OHLCV_DIR, f"{t}.csv"), parse_dates=["date"])
        o = df.set_index("date")["open"].astype(float).sort_index().reindex(cal)
        panel[t]["open_ffill"] = o.ffill()
    tp = TwinPanel()
    tp.close_ffill = spy_ffill
    tp.open_ffill = spy_close.reindex(cal).ffill()
    panel_twin = dict(panel)
    panel_twin["SPY_TWIN"] = tp
    me_mask = month_end_mask(cal)
    start_i, last_i = W1.WARMUP, len(cal) - 1

    strat_eq, st = overnight_portfolio(panel, cal, me_mask, spy_mode=False)
    spy_eq, _ = overnight_portfolio(panel_twin, cal, me_mask, spy_mode=True)

    r_s = strat_eq.pct_change()
    r_b = spy_eq.pct_change()
    ex = (r_s - r_b).dropna()
    is_ex = ex[ex.index <= W1.IS_END]
    oos_ex = ex[ex.index >= W1.OOS_START]

    def pack(eq, r):
        return {"sharpe": W1.sharpe(r), "cagr": W1.cagr(eq), "maxdd": W1.max_dd(eq)}

    arms = {
        "strategy_overnight_incumbent": {
            "is": pack(strat_eq[strat_eq.index <= W1.IS_END], r_s[r_s.index <= W1.IS_END]),
            "oos": pack(strat_eq[strat_eq.index >= W1.OOS_START], r_s[r_s.index >= W1.OOS_START]),
            "engine": st},
        "spy_benchmark": {"is": pack(spy_eq[spy_eq.index <= W1.IS_END], r_b[r_b.index <= W1.IS_END]),
                          "oos": pack(spy_eq[spy_eq.index >= W1.OOS_START], r_b[r_b.index >= W1.OOS_START])},
    }
    charter = bool(arms["strategy_overnight_incumbent"]["oos"]["cagr"] > arms["spy_benchmark"]["oos"]["cagr"]
                   and arms["strategy_overnight_incumbent"]["oos"]["sharpe"] > arms["spy_benchmark"]["oos"]["sharpe"])

    g2 = W1.g2_stationary_bootstrap(is_ex)
    g3 = W1.g3_cpcv(ex)
    g4 = W1.g4_walk_forward(oos_ex)
    g5 = W1.g5_permutation_null(oos_ex, W1.sharpe(oos_ex))
    gates_pass = bool(g2["pass"] and g3["pass"] and g4["pass"] and g5["pass"])

    results = {
        "generated_note": "wave3_h4 test; paper-only; overnight capture on incumbent "
                          "basket; PRE-RUN DISAMBIGUATION declared in module docstring",
        "prereg_frozen_commit": "664ed78",
        "signal_spec": {"name": "overnight_capture",
                        "entry": "close of first trading day of ISO week (at that close)",
                        "exit": "open of last trading day of same ISO week"},
        "arms": arms,
        "charter_bar": {"rule": "OOS net CAGR and Sharpe both > SPY same-engine",
                        "pass": charter},
        "gates": {"G2_is_bootstrap": g2, "G3_cpcv": g3,
                  "G4_walk_forward": g4, "G5_permutation_null": g5},
        "verdict": ("PASS" if (gates_pass and charter) else "FAIL"),
        "gates_all_pass": gates_pass,
    }
    with open(OUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({"verdict": results["verdict"],
                      "g2_p": g2["p_value"], "g3_fail_combos": g3["details"]["combinations_failing"],
                      "g4_pass": g4["pass"], "max_share": g4["details"]["max_fold_share"],
                      "g5_obs": g5["statistic"], "g5_p95": g5["threshold"],
                      "charter": charter, "engine": st}))


if __name__ == "__main__":
    main()
