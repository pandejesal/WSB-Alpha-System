"""Wave-3 H2 test — residual (market-model) momentum cross-sectional core.

FROZEN SPEC: docs/data/wave3_h2_residual_momentum_prereg.md (frozen @ 664ed78).
PAPER-ONLY / FAIL-CLOSED. Serial single-file verification only.

Signal swap ONLY: per-name OLS of daily returns on SPY daily returns over the
12-1 window [t-252, t-21]; signal = sum of residuals (= resid cum return).
Injected into the incumbent engine's selection slot; simulate() byte-identical
from scripts/wave1_h1_test.py; gates verbatim from scripts/wave1_h3_test.py.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

import wave1_h3_test as W1  # noqa: E402

OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave3_h2_results.json")
EST_WINDOW = 252
SKIP_BARS = 21
MIN_OBS = 180


def load_panel_with_residual(tickers):
    need = list(tickers) + [W1.BENCHMARK]
    missing = [t for t in need if not os.path.isfile(os.path.join(W1.OHLCV_DIR, f"{t}.csv"))]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: missing OHLCV files: {missing[:5]}...")
    frames = {}
    for t in need:
        df = pd.read_csv(os.path.join(W1.OHLCV_DIR, f"{t}.csv"), parse_dates=["date"])
        s = df.set_index("date")["close"].astype(float).sort_index()
        frames[t] = s
    cal = pd.DatetimeIndex(sorted(set().union(*[s.index for s in frames.values()])))
    spy_close = frames[W1.BENCHMARK].reindex(cal)
    spy_ffill = spy_close.ffill()
    r_m = spy_ffill.pct_change()
    panel, excl_counts = {}, {}
    win = EST_WINDOW - SKIP_BARS + 1  # inclusive bars t-252..t-21 -> shift handles skip
    for t in tickers:
        close = frames[t].reindex(cal)
        cff = close.ffill()
        r_i = cff.pct_change()
        # window ending at t-SKIP: use shifted series so no info after t-SKIP
        r_i_l = r_i.shift(SKIP_BARS)
        r_m_l = r_m.shift(SKIP_BARS)
        mean_i = r_i_l.rolling(win, min_periods=MIN_OBS).mean()
        mean_m = r_m_l.rolling(win, min_periods=MIN_OBS).mean()
        cov = (r_i_l * r_m_l).rolling(win, min_periods=MIN_OBS).mean() - mean_i * mean_m
        var = (r_m_l * r_m_l).rolling(win, min_periods=MIN_OBS).mean() - mean_m * mean_m
        beta = cov / var.where(var > 0)
        # residual sum over window: sum(r_i - beta*r_m) with beta time-varying is
        # ill-defined; frozen spec uses SINGLE beta estimated on the same window:
        resid_sum = (mean_i - beta * mean_m) * win
        hist_cnt = close.notna().cumsum().to_numpy()
        panel[t] = {"close": close, "close_ffill": cff, "mom": resid_sum,
                    "hist_cnt": hist_cnt}
        excl_counts[t] = int((resid_sum.isna() & cff.notna()).sum())
    return panel, cal, spy_ffill, excl_counts


def month_end_mask(cal):
    periods = pd.Series(cal).dt.to_period("M")
    return (periods != periods.shift(-1)).to_numpy()


def main():
    tickers = W1.load_snapshot_tickers()
    if not tickers:
        raise SystemExit("FAIL-CLOSED: empty universe")
    panel, cal, spy_ffill, excl = load_panel_with_residual(tickers)
    if cal[-1] != W1.G4_FOLD_ENDS[-1]:
        raise SystemExit(f"FAIL-CLOSED: data ends {cal[-1].date()} != frozen endpoint")
    me_mask = month_end_mask(cal)
    start_i, last_i = W1.WARMUP, len(cal) - 1

    strat = W1.simulate(panel, cal, me_mask, start_i, last_i)
    spy_eq = W1.spy_engine(spy_ffill, start_i, last_i)

    r_s = strat["equity"].pct_change()
    r_b = spy_eq.pct_change()
    ex = (r_s - r_b).dropna()
    is_ex = ex[ex.index <= W1.IS_END]
    oos_ex = ex[ex.index >= W1.OOS_START]

    def pack(eq, r):
        return {"sharpe": W1.sharpe(r), "cagr": W1.cagr(eq), "maxdd": W1.max_dd(eq)}

    arms = {
        "strategy_residual_top5": {
            "is": pack(strat["equity"][strat["equity"].index <= W1.IS_END],
                       r_s[r_s.index <= W1.IS_END]),
            "oos": pack(strat["equity"][strat["equity"].index >= W1.OOS_START],
                        r_s[r_s.index >= W1.OOS_START]),
            "trades": strat["trades"]},
        "spy_benchmark": {"is": pack(spy_eq[spy_eq.index <= W1.IS_END], r_b[r_b.index <= W1.IS_END]),
                          "oos": pack(spy_eq[spy_eq.index >= W1.OOS_START], r_b[r_b.index >= W1.OOS_START])},
    }
    charter = bool(arms["strategy_residual_top5"]["oos"]["cagr"] > arms["spy_benchmark"]["oos"]["cagr"]
                   and arms["strategy_residual_top5"]["oos"]["sharpe"] > arms["spy_benchmark"]["oos"]["sharpe"])

    g2 = W1.g2_stationary_bootstrap(is_ex)
    g3 = W1.g3_cpcv(ex)
    g4 = W1.g4_walk_forward(oos_ex)
    g5 = W1.g5_permutation_null(oos_ex, W1.sharpe(oos_ex))
    gates_pass = bool(g2["pass"] and g3["pass"] and g4["pass"] and g5["pass"])

    results = {
        "generated_note": "wave3_h2 test; paper-only; residual-momentum signal injected "
                          "into incumbent selection slot; gates imported verbatim",
        "prereg_frozen_commit": "664ed78",
        "signal_spec": {"name": "residual_market_model_momentum",
                        "est_window_bars": EST_WINDOW, "skip_bars": SKIP_BARS,
                        "min_obs": MIN_OBS,
                        "formula": "(mean(r_i)-beta*mean(r_m))*window; single beta per window, both means lagged by skip"},
        "arms": arms,
        "charter_bar": {"rule": "OOS net CAGR and Sharpe both > SPY same-engine",
                        "pass": charter},
        "gates": {"G2_is_bootstrap": g2, "G3_cpcv": g3,
                  "G4_walk_forward": g4, "G5_permutation_null": g5},
        "warmup_excluded_bar_counts_total": int(sum(excl.values())),
        "verdict": ("PASS" if (gates_pass and charter) else "FAIL"),
        "gates_all_pass": gates_pass,
    }
    with open(OUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({"verdict": results["verdict"],
                      "g2_p": g2["p_value"], "g3_fail_combos": g3["details"]["combinations_failing"],
                      "g4_pass": g4["pass"], "max_share": g4["details"]["max_fold_share"],
                      "g5_obs": g5["statistic"], "g5_p95": g5["threshold"],
                      "charter": charter}))


if __name__ == "__main__":
    main()
