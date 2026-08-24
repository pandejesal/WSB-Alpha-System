"""Wave 2 / W2-H1 — Vol-Target Sizing DELTA Test (FROZEN PREREG RUNNER).

PAPER-ONLY. LIVE TRADING DISABLED. FAIL-CLOSED. Zero fitted parameters.

Implements docs/data/wave2_h1_voltarget_delta_prereg.md (frozen 2026-08-25)
EXACTLY. ALL engine and gate machinery is imported VERBATIM from
scripts/wave1_h3_test.py, so both arms are byte-identical reproductions of the
wave-1 H3 engines: baseline = untargeted us_momentum_top5 simulate();
overlay = simulate_voltarget() with the m_t = clamp(0.15/sigma21d, 0.25, 1.00)
formula BYTE-IDENTICAL to H3 (zero parameter changes, anti-p-hacking). Arms
run in the SAME script invocation (paired by construction - identical
calendar, costs, fills).

The ONLY change versus wave-1 H3: all five statistical gates G2-G5 are
computed on the PAIRED daily overlay-minus-incumbent DELTA series
d_t = r_overlay,t - r_baseline,t (prereg section 4), directly addressing the
wave-1 diagnosis that absolute-excess gates cannot separate overlay value
from 2024-26 beta drift.

Charter bar (overlay beats SPY buy-and-hold on BOTH OOS net CAGR and Sharpe)
and primary acceptance (Sharpe margin >= +0.10 vs incumbent) are unchanged.
This script NEVER self-certifies PASS; verdict authority = AUDITOR seat.

Outputs:
  docs/data/wave2_h1_results.json   (full numbers; deterministic, seeded)
Stdout: compact six-gate + charter + PRIMARY MARGIN summary table.

Deterministic: stochastic generators live inside imported gate functions with
frozen seeds; no network; no randomness outside them.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

try:
    from wave1_h3_test import (
        ANN,
        IS_END,
        OOS_START,
        WARMUP,
        arm_metrics,
        excess_summary,
        g2_stationary_bootstrap,
        g3_cpcv,
        g4_walk_forward,
        g5_permutation_null,
        load_data,
        load_snapshot_tickers,
        simulate,
        simulate_voltarget,
        spy_engine,
    )
    ENGINE_SOURCE = "imported_verbatim:scripts/wave1_h3_test.py"
except Exception as exc:  # pragma: no cover - fail-closed
    raise SystemExit(
        f"FAIL-CLOSED: cannot import byte-identical engine from "
        f"scripts/wave1_h3_test.py ({exc}); refusing to re-implement"
    )

PREREG_PATH = os.path.join(BASE, "docs", "data",
                           "wave2_h1_voltarget_delta_prereg.md")
OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave2_h1_results.json")

# Frozen provenance constants (echo-only; never tuned)
FROZEN_FINAL_BAR = pd.Timestamp("2026-08-07")   # G4_FOLD_ENDS[-1] inside engine module
VERIFIED_UNIVERSE_SIZE = 481                     # snapshot-intersect-local minus SPY

try:
    from ml_sl_exit_test import month_end_mask
    MONTH_END_SOURCE = "imported:scripts/ml_sl_exit_test.py"
except Exception:
    MONTH_END_SOURCE = "inline_verbatim_fallback"

    def month_end_mask(cal):
        periods = pd.Series(cal).dt.to_period("M")
        return ((periods != periods.shift(-1)).to_numpy())


def main():
    tickers = load_snapshot_tickers()
    if not tickers:
        raise SystemExit("FAIL-CLOSED: empty universe (snapshot intersect local)")
    if len(tickers) != VERIFIED_UNIVERSE_SIZE:
        raise SystemExit(
            f"FAIL-CLOSED: universe size {len(tickers)} != frozen verified size "
            f"{VERIFIED_UNIVERSE_SIZE} (universe drift since freeze)"
        )
    panel, cal, _spy_raw, spy_ffill, integrity = load_data(tickers)
    if len(cal) <= WARMUP + 1:
        raise SystemExit(f"FAIL-CLOSED: calendar has {len(cal)} bars; warmup {WARMUP} leaves no evaluated history")
    if cal[-1] != FROZEN_FINAL_BAR:
        raise SystemExit(
            f"FAIL-CLOSED: data ends {cal[-1].date()} but frozen WF final endpoint is {FROZEN_FINAL_BAR.date()}"
        )
    start_i = WARMUP
    last_i = len(cal) - 1
    me_mask = month_end_mask(cal)

    # Both arms in the SAME script run (paired by construction)
    baseline = simulate(panel, cal, me_mask, start_i, last_i)
    overlay = simulate_voltarget(panel, cal, me_mask, start_i, last_i)

    base_eq = baseline["equity"]
    over_eq = overlay["equity"]
    spy_eq = spy_engine(spy_ffill, start_i, last_i)

    base_r = base_eq.pct_change()
    over_r = over_eq.pct_change()
    spy_r = spy_eq.pct_change()

    # THE GATED CLAIM SERIES: paired overlay-minus-incumbent daily NET returns
    delta = (over_r - base_r).dropna()
    if delta.empty:
        raise SystemExit("FAIL-CLOSED: empty paired delta series")
    is_delta = delta[delta.index <= IS_END]
    oos_delta = delta[delta.index >= OOS_START]
    full_delta = delta
    if is_delta.empty or oos_delta.empty:
        raise SystemExit("FAIL-CLOSED: IS or OOS delta segment empty")

    arms = {}
    arms.update(arm_metrics(base_eq, base_r.dropna(), "baseline_incumbent"))
    arms.update(arm_metrics(over_eq, over_r.dropna(), "overlay"))
    arms.update(arm_metrics(spy_eq, spy_r.dropna(), "spy"))

    # Gate 1 artifact check (identical pattern to H3)
    g1_present = os.path.isfile(PREREG_PATH)
    g1_frozen = False
    if g1_present:
        with open(PREREG_PATH, encoding="utf-8") as f:
            head = f.read(4096)
        g1_frozen = ("FROZEN" in head.upper()) or ("LOCKED" in head.upper())

    oos_delta_sharpe = excess_summary(oos_delta)["annualized_sharpe"]
    gates = {
        "g1_prereg_committed": {"pass": bool(g1_present and g1_frozen), "statistic": "artifact_check",
                                "details": {"path": os.path.relpath(PREREG_PATH, BASE), "present": g1_present,
                                            "frozen_marker_found": g1_frozen}},
        "g2_is_stationary_bootstrap": g2_stationary_bootstrap(is_delta),
        "g3_cpcv": g3_cpcv(full_delta),
        "g4_walk_forward": g4_walk_forward(oos_delta),
        "g6_dsr_ledger": {"pass": None, "status": "MANUAL_STEP_REQUIRED",
                          "details": {"note": "Per prereg section 4 gate 6: positive Deflated-Sharpe ledger entry via "
                                              "scripts/preregister.py record into docs/data/eval_wave2_h1.json, trials "
                                              "charged = 1 (wave-2 budget w2h1:1). Recorded by operator AFTER auditor verdict.",
                                      "command_shape": "python scripts/preregister.py record <spec_path> --verdict <PASS|FAIL|HONEST_ABANDON> [--eval-path docs/data/wave2_h1_results.json]"}},
    }
    gates["g5_permutation_null"] = g5_permutation_null(oos_delta, oos_delta_sharpe)

    charter = {"oos_net_cagr_overlay": arms["overlay"]["oos"]["cagr"], "oos_net_cagr_spy": arms["spy"]["oos"]["cagr"],
               "oos_net_sharpe_overlay": arms["overlay"]["oos"]["sharpe"], "oos_net_sharpe_spy": arms["spy"]["oos"]["sharpe"]}
    charter["pass"] = bool(charter["oos_net_cagr_overlay"] > charter["oos_net_cagr_spy"]
                           and charter["oos_net_sharpe_overlay"] > charter["oos_net_sharpe_spy"])

    # Primary acceptance (unchanged from H3): margin >= +0.10 AND cagr > SPY AND charter
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
        "claim": ("Scaling the incumbent us_momentum_top5 portfolio by m_t = "
                  "clamp(0.15/sigma_hat_21d_ann, 0.25, 1.00) at month-ends produces a POSITIVE mean "
                  "daily net-return DELTA versus the unscaled incumbent that survives all five "
                  "statistical gates COMPUTED ON THE PAIRED DELTA SERIES, while the overlay still beats "
                  "SPY buy-and-hold on BOTH OOS net CAGR and Sharpe (charter bar unchanged) and retains "
                  "primary acceptance Sharpe margin >= +0.10 vs the incumbent."),
        "prereg": os.path.relpath(PREREG_PATH, BASE),
        "prereg_status": "FROZEN 2026-08-25 - LOCKED before any in-sample run",
        "paper_only": True,
        "verdict_authority": "RESERVED FOR AUDITOR SEAT - this output reports mechanical gate booleans only; no PASS claim is made by the runner",
        "config_echo": {
            "universe": {"definition": "snapshot map keys INTERSECT local OHLCV csv stems MINUS SPY (verbatim load_snapshot_tickers)",
                         "size": integrity["universe_size"], "verified_size": VERIFIED_UNIVERSE_SIZE,
                         "size_matches": bool(integrity["universe_size"] == VERIFIED_UNIVERSE_SIZE)},
            "benchmark": "SPY",
            "params_byte_identical_to": "strategies/us_momentum_top5.yaml",
            "engine_lineage": {"derived_from": ENGINE_SOURCE,
                               "month_end_source": MONTH_END_SOURCE,
                               "byte_identity_note": "both arms imported verbatim from wave-1 H3 runner; m_t formula byte-identical; zero parameter changes permitted (anti-p-hacking)",
                               "only_delta_vs_h3": "all five statistical gates computed on paired overlay-minus-incumbent delta series instead of absolute SPY-excess"},
            "windows": {"is_nominal": ["2019-01-02", "2023-12-31"], "oos_nominal": ["2024-01-01", "2026-08-07"],
                        "sim_start_rule": "bar index WARMUP=340 of union calendar (declared interpretation)",
                        "effective_evaluated_start": str(cal[start_i].date())},
            "stochastic_echo_from_engine_module": {
                "g2": {"mean_block": 21, "draws": 1000, "seed": 7},
                "g3": {"K": 6, "embargo_days": 10},
                "g4": {"fold_ends": ["2024-06-30", "2024-12-31", "2025-06-30", "2025-12-31", "2026-08-07"],
                       "endpoint_snap": "last_trading_bar_on_or_before", "max_fold_share": 0.60},
                "g5": {"block": 10, "draws": 1000, "seed": 7}},
            "data_integrity": integrity,
        },
        "arms": arms,
        "delta_series_summary": {"definition": "overlay NET daily returns minus incumbent NET daily returns (PAIRED: identical calendar, costs, fills), date-aligned",
                                 "is": excess_summary(is_delta), "oos": excess_summary(oos_delta),
                                 "full_evaluated": excess_summary(full_delta)},
        "m_series": overlay["m_series"], "m_stats": overlay["m_stats"],
        "gates": gates, "charter_bar": charter, "primary_acceptance": primary,
        "trades_baseline": baseline["trades"], "trades_overlay": overlay["trades"],
        "all_computed_gates_pass": bool(all_gates_pass),
        "notes": [
            "PRIOR ART: wave-1 H3 tested the BYTE-IDENTICAL m_t formula with ABSOLUTE SPY-excess gates and FAILED G2/G3/G5 honestly (docs/data/eval_wave1_h3.json); diagnosis: under dominant 2024-26 drift any long-biased path's absolute excess sits inside its own block-shuffle null.",
            "CHANGED CONDITIONS: hypothesis target moved to the paired overlay-minus-incumbent daily delta; all five statistical gates recomputed on that delta series (variance-reduced, drift-immune by construction). m_t formula untouched.",
            "SIZING LANE STAKE: if these delta gates FAIL, the deterministic-sizing lane CLOSES ENTIRELY per prereg section 5 (both m-form variants exhausted); reopening requires genuinely new data or new mechanism.",
            "Declared pairing: baseline arm = untargeted incumbent engine from the SAME script run (simulate()); overlay arm = simulate_voltarget(); both byte-identical imports from wave-1 H3 runner.",
            "G3 combination semantics declared inside gates.g3_cpcv.details (all non-empty proper subsets of K folds, embargo purged); G4 expanding-span semantics declared inside gates.g4_walk_forward.details.",
            "Descriptive controls (NOT gated, 0 trials charged): delta summary stats (IS/OOS/full) and m-series distribution echo.",
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
    print("WAVE-2 / W2-H1 VOL-TARGET SIZING DELTA TEST | PAPER-ONLY | FAIL-CLOSED | FROZEN PREREG")
    print("=" * 78)
    print(f"{'gate':<4} {'description':<44} {'statistic':>14} {'bar':>10} {'state':>7}")
    print("-" * 78)
    print(f"{'G1':<4} {'prereg frozen artifact':<44} {'artifact':>14} {'locked':>10} {yn(gates['g1_prereg_committed']['pass']):>7}")
    print(f"{'G2':<4} {'IS delta stationary bootstrap blk21 n1000 s7':<44} {g2['p_value']:>14.4f} {'<=0.05':>10} {yn(g2['pass']):>7}")
    print(f"{'G3':<4} {'CPCV on delta K=6 emb10 all-combos mean>0':<44} {g3['statistic']:>14.6f} {'>0':>10} {yn(g3['pass']):>7}")
    print(f"{'G4':<4} {'WF on delta 5 folds + 60pct share cap':<44} {g4['statistic']:>14.4f} {'>0/all':>10} {yn(g4['pass']):>7}")
    print(f"{'G5':<4} {'circ-block perm on delta vs p95':<44} {g5['statistic']:>14.4f} {('>p95 %.4f' % g5['threshold']):>10} {yn(g5['pass']):>7}")
    print(f"{'G6':<4} {'DSR ledger via preregister.py (operator)':<44} {'manual':>14} {'ledger':>10} {'PENDING':>7}")
    print("-" * 78)
    print(f"{'CHR':<4} {'OOS net CAGR>SPY AND OOS net Sharpe>SPY':<44} {charter['oos_net_sharpe_overlay'] - charter['oos_net_sharpe_spy']:>14.4f} {'both>':>10} {yn(charter['pass']):>7}")
    print(f"{'PRI':<4} {'Sharpe margin >=+0.10 vs baseline':<44} {primary['sharpe_margin']:>14.4f} {'>=+0.10':>10} {yn(primary['pass']):>7}")
    print("-" * 78)
    ms = overlay["m_stats"]
    print(f"eval start {cal[start_i].date()} | baseline trades {baseline['trades']} | overlay trades {overlay['trades']} | m months {ms['n_months']} mean {ms['mean']:.3f} cap_frac {ms['frac_at_cap']:.1%}")
    print(f"G3 combos failing: {g3['details']['combinations_failing']}/{g3['details']['combination_count']} | G4 max fold share: {g4['details']['max_fold_share']:.4f} (cap 0.60)")
    print(f"delta OOS ann-Sharpe {oos_delta_sharpe:.4f} | all_computed_gates_pass={all_gates_pass} | primary_pass={primary['pass']} | verdict authority: AUDITOR | G6 DSR ledger = manual")
    print(f"results -> {os.path.relpath(OUT_RESULTS, BASE)}")


if __name__ == "__main__":
    main()
