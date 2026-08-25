"""Wave-3 H3 test — Turn-of-Month concentration on the incumbent core.

FROZEN SPEC: docs/data/wave3_h3_tom_timing_prereg.md (frozen @ 664ed78).
PAPER-ONLY / FAIL-CLOSED. Serial single-file verification only.

Signals/universe byte-identical to incumbent (panel['mom'] from
scripts/wave1_h1_test.py load_data via scripts/wave1_h3_test.py). Invested ONLY
in frozen windows: order at last-TD close of month M-1 fills next-bar close;
exit at close of the 4th trading day of month M. No drift/rebalance inside a
window. Gates verbatim from scripts/wave1_h3_test.py.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import wave1_h3_test as W1  # noqa: E402

OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave3_h3_results.json")
WINDOW_HOLD_BARS = 4  # entry bar + 3 more closes = 4th TD close


def month_end_mask(cal):
    periods = pd.Series(cal).dt.to_period("M")
    return (periods != periods.shift(-1)).to_numpy()


def tom_portfolio(panel, cal, me_mask, spy_mode=False):
    cash = W1.INIT_EQUITY
    prev_eq = W1.INIT_EQUITY
    n = len(cal)
    eq = np.empty(n)
    open_pos = {}
    pending = None
    n_windows = skipped_windows = 0
    for i in range(n):
        if open_pos:
            if i - open_pos["entry_i"] >= WINDOW_HOLD_BARS:
                realized = 0.0
                ok = True
                for t, rec in open_pos["names"].items():
                    px = panel[t]["close_ffill"].iloc[i] if not spy_mode \
                        else panel["SPY_TWIN"].close_ffill.iloc[i]
                    if pd.isna(px) or px <= 0:
                        ok = False
                        break
                    realized += rec["shares"] * float(px) * (1.0 - W1.COST)
                if ok:
                    cash += realized
                    n_windows += 1
                    open_pos = {}
            elif i == n - 1:
                open_pos = {}  # force-flat at end (counted)
        if pending is not None:
            tickers, alloc = pending
            names = {}
            for t in tickers:
                src = panel["SPY_TWIN"].close_ffill if spy_mode else panel[t]["close_ffill"]
                px = src.iloc[i]
                if pd.isna(px) or px <= 0:
                    continue
                shares = alloc / (float(px) * (1.0 + W1.COST))
                names[t] = {"shares": shares}
            if len(names) == len(tickers) and names:
                cost = sum(r["shares"] * float((panel["SPY_TWIN"].close_ffill if spy_mode else panel[t]["close_ffill"]).iloc[i])
                           for t, r in names.items())
                cash -= cost * (1.0 + W1.COST)
                open_pos = {"names": names, "entry_i": i, "cost_basis": cost}
            else:
                skipped_windows += 1
            pending = None
        if me_mask[i] and i < n - 1:
            scores = {}
            for t, d in panel.items():
                if t == "SPY_TWIN":
                    continue
                m = d["mom"].iloc[i]
                if not pd.isna(m) and d["hist_cnt"][i] >= W1.WARMUP:
                    scores[t] = float(m)
            top = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:W1.TOP_N]]
            if top:
                alloc = prev_eq / W1.TOP_N
                pending = (top, alloc)
        mark = cash
        if open_pos:
            for t, rec in open_pos["names"].items():
                px = panel["SPY_TWIN"].close_ffill.iloc[i] if spy_mode else panel[t]["close_ffill"].iloc[i]
                if not pd.isna(px):
                    mark += rec["shares"] * float(px)
        eq[i] = mark
        prev_eq = mark
    return pd.Series(eq, index=cal), {"windows_completed": n_windows,
                                      "windows_skipped_price_gap": skipped_windows}


class TwinPanel:
    pass


def main():
    tickers = W1.load_snapshot_tickers()
    if not tickers:
        raise SystemExit("FAIL-CLOSED: empty universe")
    panel, cal, spy_close, spy_ffill, integrity = W1.load_data(tickers)
    if cal[-1] != W1.G4_FOLD_ENDS[-1]:
        raise SystemExit(f"FAIL-CLOSED: data ends {cal[-1].date()} != frozen endpoint")
    tp = TwinPanel()
    tp.close_ffill = spy_ffill
    panel_twin = dict(panel)
    panel_twin["SPY_TWIN"] = tp
    me_mask = month_end_mask(cal)
    start_i, last_i = W1.WARMUP, len(cal) - 1

    strat_eq, st = tom_portfolio(panel, cal, me_mask, spy_mode=False)
    spy_eq, _ = tom_portfolio(panel_twin, cal, me_mask, spy_mode=True)

    r_s = strat_eq.pct_change()
    r_b = spy_eq.pct_change()
    ex = (r_s - r_b).dropna()
    is_ex = ex[ex.index <= W1.IS_END]
    oos_ex = ex[ex.index >= W1.OOS_START]

    def pack(eq, r):
        return {"sharpe": W1.sharpe(r), "cagr": W1.cagr(eq), "maxdd": W1.max_dd(eq)}

    arms = {
        "strategy_tom_incumbent": {
            "is": pack(strat_eq[strat_eq.index <= W1.IS_END], r_s[r_s.index <= W1.IS_END]),
            "oos": pack(strat_eq[strat_eq.index >= W1.OOS_START], r_s[r_s.index >= W1.OOS_START]),
            "engine": st},
        "spy_benchmark": {"is": pack(spy_eq[spy_eq.index <= W1.IS_END], r_b[r_b.index <= W1.IS_END]),
                          "oos": pack(spy_eq[spy_eq.index >= W1.OOS_START], r_b[r_b.index >= W1.OOS_START])},
    }
    charter = bool(arms["strategy_tom_incumbent"]["oos"]["cagr"] > arms["spy_benchmark"]["oos"]["cagr"]
                   and arms["strategy_tom_incumbent"]["oos"]["sharpe"] > arms["spy_benchmark"]["oos"]["sharpe"])

    g2 = W1.g2_stationary_bootstrap(is_ex)
    g3 = W1.g3_cpcv(ex)
    g4 = W1.g4_walk_forward(oos_ex)
    g5 = W1.g5_permutation_null(oos_ex, W1.sharpe(oos_ex))
    gates_pass = bool(g2["pass"] and g3["pass"] and g4["pass"] and g5["pass"])

    results = {
        "generated_note": "wave3_h3 test; paper-only; TOM window timing on unchanged "
                          "incumbent signals; gates imported verbatim",
        "prereg_frozen_commit": "664ed78",
        "signal_spec": {"name": "tom_concentration", "hold_bars": WINDOW_HOLD_BARS,
                        "entry": "order last-TD close M-1, fill next-bar close",
                        "exit": "close of 4th TD of month M"},
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
                      "charter": charter, "windows": st}))


if __name__ == "__main__":
    main()
