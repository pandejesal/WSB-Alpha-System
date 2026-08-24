"""Wave 2 / W2-H3 — Absolute-Momentum Gate inside Universe A (FROZEN PREREG RUNNER).

PAPER-ONLY. LIVE TRADING DISABLED. FAIL-CLOSED. Zero fitted parameters.

Implements docs/data/wave2_h3_absmom_gate_prereg.md (frozen 2026-08-25)
EXACTLY. Core arm = EXACT incumbent us_momentum_top5 rule on frozen mega-cap
Universe A (15 names, verbatim order from scripts/wave1_h1_test.py), invested
ONLY when the equal-weight Universe-A index's own 12-1 ABSOLUTE return

    r_gate = idx[t-63] / idx[t-315] - 1     (EW mean of close_ffill prices)

computed on the last bar of each month is > 0, holding cash otherwise
(force-flat at that month-end: full liquidation queued, fills next bar =
exec_delay 1 bar on ALL orders INCLUDING gate flips; re-entry at the next ON
month-end through normal selection queueing; NO SMA fallback permitted).

Gates are VERBATIM from wave1_h1_megacap_momentum_prereg.md section 4
(ABSOLUTE net-excess-vs-SPY forms, unlike W2-H1/H2 paired deltas): G2 IS
stationary bootstrap blk21/n1000/s7 p<=0.05; G3 CPCV K=6 emb10 all combos
mean>0; G4 five expanding folds net-excess Sharpe>0 each + max fold share
<=60%; G5 circular block shuffle blk10/n1000/s7 observed OOS annualized
excess Sharpe > null p95. All stochastic machinery IMPORTED VERBATIM from
scripts/wave1_h1_test.py. Charter bar: OOS net CAGR > SPY AND Sharpe > SPY.

This script NEVER self-certifies PASS; verdict authority = AUDITOR seat.

Outputs:
  docs/data/wave2_h3_results.json   (full numbers; deterministic, seeded)
Stdout: compact six-gate + charter summary table.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

try:
    from wave1_h1_test import (
        ANN,
        COST,
        DRIFT_BAND,
        INIT_EQUITY,
        IS_END,
        MIN_ORDER,
        OOS_START,
        TOP_N,
        UNIVERSE_A,
        WARMUP,
        arm_metrics,
        control_engine,
        excess_summary,
        g2_stationary_bootstrap,
        g3_cpcv,
        g4_walk_forward,
        g5_permutation_null,
        load_data,
        spy_engine,
    )
    ENGINE_SOURCE = "imported_verbatim:scripts/wave1_h1_test.py"
except Exception as exc:  # pragma: no cover - fail-closed
    raise SystemExit(
        f"FAIL-CLOSED: cannot import byte-identical engine parts from "
        f"scripts/wave1_h1_test.py ({exc}); refusing to re-implement"
    )

PREREG_PATH = os.path.join(BASE, "docs", "data", "wave2_h3_absmom_gate_prereg.md")
OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave2_h3_results.json")

# Frozen gate constants (declared ex ante; matching the incumbent's skip convention scaled)
GATE_SHORT_LAG = 63              # ~3 trading months skip
GATE_LONG_LAG = 315              # ~15 trading months (12-1 momentum convention)
FRED_REGIMES_PATH = os.path.join(BASE, "data", "cache", "fred_historical_regimes.json")
FROZEN_FINAL_BAR = pd.Timestamp("2026-08-07")

try:
    from ml_sl_exit_test import month_end_mask
    MONTH_END_SOURCE = "imported:scripts/ml_sl_exit_test.py"
except Exception:
    MONTH_END_SOURCE = "inline_verbatim_fallback"

    def month_end_mask(cal):
        periods = pd.Series(cal).dt.to_period("M")
        return ((periods != periods.shift(-1)).to_numpy())


def ew_index(panel):
    """Equal-weight mean of Universe-A close_ffill closes per calendar bar."""
    return np.mean([panel[t]["close_ffill"].to_numpy(dtype=float) for t in UNIVERSE_A], axis=0)


def simulate_absmom_gate(panel, cal, me_mask, start_i, end_i, idx):
    """wave1_h1_test.simulate() cloned line-for-line with ONE insertion: the
    absolute-momentum gate evaluated at each month-end BEFORE selection.

    Gate OFF at month-end => force-flat: queue full liquidation of every open
    position (fills NEXT bar - exec_delay 1 applies to gate flips exactly as
    to rank drops); no entries queued. Gate ON => the standard byte-identical
    top-5 selection block. Drift-band block unchanged (no-op while flat).
    """
    cash = INIT_EQUITY
    positions = {}
    pending_buys, pending_sells = [], []
    equity = np.empty(end_i - start_i + 1)
    n_trades = 0
    gate_log = {}   # month-end date -> {"r_gate": float, "gate_on": bool}

    def px(t, i):
        v = panel[t]["close_ffill"].iloc[i]
        return np.nan if pd.isna(v) else float(v)

    def mark(i):
        return cash + sum(rec["shares"] * px(t, i) for t, rec in positions.items())

    for i in range(start_i, end_i + 1):
        # 1) fills for sells queued on the previous bar (verbatim H1)
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

        # 2) fills for buys queued on the previous bar (verbatim H1)
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

        # 3) month-end signal: GATE first, then selection (the ONLY insertion)
        if me_mask[i] and i < end_i:
            r_gate = float(idx[i - GATE_SHORT_LAG] / idx[i - GATE_LONG_LAG] - 1.0)
            gate_on = bool(r_gate > 0)
            gate_log[str(cal[i].date())] = {"r_gate": r_gate, "gate_on": gate_on}

            if gate_on:
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
            else:
                # force-flat at this month-end; fills next bar (exec_delay 1)
                for t in list(positions):
                    pending_sells.append({"ticker": t, "shares": None,
                                          "reason": "absmom_gate_off"})

        # 4) drift-band rebalance (verbatim H1; no-op while flat)
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
            "trades": n_trades, "gate_log": gate_log}


def fred_overlap(gate_log):
    """Descriptive control (NOT gated): 2x2 overlap of gate ON vs FRED RISK_ON."""
    try:
        with open(FRED_REGIMES_PATH, encoding="utf-8") as f:
            regimes = json.load(f)
        lab = regimes.get("labels", regimes) if isinstance(regimes, dict) else regimes
        rows = []
        for date_str, rec in gate_log.items():
            d = pd.Timestamp(date_str)
            hits = [(k, v) for k, v in lab.items()
                    if pd.Timestamp(k) <= d] if isinstance(lab, dict) else []
            if not hits:
                continue
            k, v = max(hits, key=lambda kv: pd.Timestamp(kv[0]))
            risk_on = str(v).upper() == "RISK_ON"
            rows.append((bool(rec["gate_on"]), risk_on))
        n = len(rows)
        if n == 0:
            return {"available": False, "note": "no FRED labels matched month-ends"}
        both = sum(1 for g, r in rows if g and r)
        gate_only = sum(1 for g, r in rows if g and not r)
        fred_only = sum(1 for g, r in rows if not g and r)
        neither = sum(1 for g, r in rows if not g and not r)
        agree = both + neither
        return {"available": True, "n_month_ends": n,
                "table": {"gate_on_and_risk_on": both, "gate_on_not_risk_on": gate_only,
                          "risk_on_not_gate_on": fred_only, "neither": neither},
                "agreement_rate": agree / n}
    except Exception as exc:
        return {"available": False, "note": f"FRED regimes unavailable: {exc}"}


def main():
    panel, cal, spy_close, spy_ffill, integrity = load_data()
    if len(cal) <= WARMUP + 1:
        raise SystemExit(f"FAIL-CLOSED: calendar has {len(cal)} bars; warmup {WARMUP} leaves no evaluated history")
    if cal[-1] != FROZEN_FINAL_BAR:
        raise SystemExit(
            f"FAIL-CLOSED: data ends {cal[-1].date()} but frozen WF final endpoint is {FROZEN_FINAL_BAR.date()}"
        )
    start_i = WARMUP
    last_i = len(cal) - 1
    me_mask = month_end_mask(cal)
    idx = ew_index(panel)
    if np.isnan(idx[start_i + GATE_LONG_LAG:]).any():
        raise SystemExit("FAIL-CLOSED: NaN in EW Universe-A index within evaluated window (ffill failed)")

    gated = simulate_absmom_gate(panel, cal, me_mask, start_i, last_i, idx)
    passive_ew_a = control_engine(panel, cal, start_i, last_i)
    spy_eq = spy_engine(spy_ffill, start_i, last_i)

    gated_eq = gated["equity"]
    gated_r = gated_eq.pct_change()
    spy_r = spy_eq.pct_change()

    excess = (gated_r - spy_r).dropna()
    if excess.empty:
        raise SystemExit("FAIL-CLOSED: empty gated net-excess series")
    is_excess = excess[excess.index <= IS_END]
    oos_excess = excess[excess.index >= OOS_START]
    full_evaluated = excess
    if is_excess.empty or oos_excess.empty:
        raise SystemExit("FAIL-CLOSED: IS or OOS excess segment empty")

    arms = {}
    arms.update(arm_metrics(spy_eq, spy_r.dropna(), "spy"))
    arms.update(arm_metrics(passive_ew_a, passive_ew_a.pct_change().dropna(), "passive_ew_universe_a"))
    arms.update(arm_metrics(gated_eq, gated_r.dropna(), "gated_core"))

    g1_present = os.path.isfile(PREREG_PATH)
    g1_frozen = False
    if g1_present:
        with open(PREREG_PATH, encoding="utf-8") as f:
            head = f.read(4096)
        g1_frozen = ("FROZEN" in head.upper()) or ("LOCKED" in head.upper())

    oos_excess_sharpe = excess_summary(oos_excess)["annualized_sharpe"]
    gates = {
        "g1_prereg_committed": {"pass": bool(g1_present and g1_frozen), "statistic": "artifact_check",
                                "details": {"path": os.path.relpath(PREREG_PATH, BASE), "present": g1_present,
                                            "frozen_marker_found": g1_frozen}},
        "g2_is_stationary_bootstrap": g2_stationary_bootstrap(is_excess),
        "g3_cpcv": g3_cpcv(full_evaluated),
        "g4_walk_forward": g4_walk_forward(oos_excess),
        "g6_dsr_ledger": {"pass": None, "status": "MANUAL_STEP_REQUIRED",
                          "details": {"note": "Per prereg section 4 gate 6: positive Deflated-Sharpe ledger entry via "
                                              "scripts/preregister.py record into docs/data/eval_wave2_h3.json, trials "
                                              "charged = 1 (wave-2 budget w2h3:1). Recorded by operator AFTER auditor verdict.",
                                      "command_shape": "python scripts/preregister.py record <spec_path> --verdict <PASS|FAIL|HONEST_ABANDON> [--eval-path docs/data/wave2_h3_results.json]"}},
    }
    gates["g5_permutation_null"] = g5_permutation_null(oos_excess, oos_excess_sharpe)

    charter = {"oos_net_cagr_gated_core": arms["gated_core"]["oos"]["cagr"],
               "oos_net_cagr_spy": arms["spy"]["oos"]["cagr"],
               "oos_net_sharpe_gated_core": arms["gated_core"]["oos"]["sharpe"],
               "oos_net_sharpe_spy": arms["spy"]["oos"]["sharpe"]}
    charter["pass"] = bool(charter["oos_net_cagr_gated_core"] > charter["oos_net_cagr_spy"]
                           and charter["oos_net_sharpe_gated_core"] > charter["oos_net_sharpe_spy"])

    computed = [k for k in ("g1_prereg_committed", "g2_is_stationary_bootstrap", "g3_cpcv",
                            "g4_walk_forward", "g5_permutation_null")]
    all_gates_pass = all(gates[k]["pass"] for k in computed)

    gl = gated["gate_log"]
    on_frac = sum(1 for v in gl.values() if v["gate_on"]) / len(gl) if gl else None
    results = {
        "claim": ("Running the EXACT incumbent us_momentum_top5 rule on the frozen mega-cap Universe A, invested "
                  "ONLY when the equal-weight Universe-A index's own 12-1 absolute return (r = P_t-63/P_t-315 - 1 "
                  "on the last bar of each month) is > 0 and holding cash otherwise, produces OOS net-of-cost "
                  "performance beating SPY buy-and-hold on BOTH CAGR and Sharpe (identical engine/window/fees) "
                  "while passing all six edge gates"),
        "prereg": os.path.relpath(PREREG_PATH, BASE),
        "prereg_status": "FROZEN 2026-08-25 - LOCKED before any in-sample run",
        "paper_only": True,
        "verdict_authority": "RESERVED FOR AUDITOR SEAT - this output reports mechanical gate booleans only; no PASS claim is made by the runner",
        "config_echo": {
            "universe": {"definition": "UNIVERSE_A verbatim fixed-order 15 mega caps (imported from scripts/wave1_h1_test.py)",
                         "tickers": UNIVERSE_A},
            "benchmark": "SPY",
            "params_byte_identical_to": "strategies/us_momentum_top5.yaml via wave1_h1_megacap_momentum_prereg.md section 3",
            "engine_lineage": {"derived_from": ENGINE_SOURCE,
                               "month_end_source": MONTH_END_SOURCE,
                               "byte_identity_note": "simulate_absmom_gate clones wave1_h1_test.simulate() line-for-line; ONLY insertion is the gate evaluation at each month-end before selection",
                               "gate_rule": "r_gate = EW_UniverseA_idx[t-63]/idx[t-315] - 1 at monthly last bar; ON iff > 0; OFF => force-flat queued (fills next bar, exec_delay 1 incl. gate flips); no SMA fallback",
                               "core_rule": "exact incumbent monthly top-5 cross-sectional momentum, drift band 0.05, 5 bps/side"},
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
        "excess_series_summary": {"definition": "gated-core NET daily returns minus SPY-engine NET daily returns (identical fee accounting), date-aligned",
                                  "is": excess_summary(is_excess), "oos": excess_summary(oos_excess),
                                  "full_evaluated": excess_summary(full_evaluated)},
        "gate_stats": {"n_month_ends": len(gl), "on_fraction": on_frac, "log": gl},
        "descriptive_controls_not_gated": {
            "overlap_vs_fred_risk_on": fred_overlap(gl),
            "passive_ew_universe_a_oos": arms["passive_ew_universe_a"]["oos"],
        },
        "gates": gates, "charter_bar": charter,
        "trades_gated_core": gated["trades"],
        "all_computed_gates_pass": bool(all_gates_pass),
        "notes": [
            "PRIOR ART: wave-1 H1 bare mega-cap scoping FAILED all gates (docs/data/eval_wave1_h1.json); wave-1 H2 FRED-label gating FAILED all statistical gates despite charter pass (docs/data/eval_wave2_h2.json sibling eval_wave1_h2.json); regime stack closure 2026-08-14 left universe scoping outside its mandate.",
            "CHANGED CONDITIONS: universe-scoped core tested with a PRICE-DERIVED gate from the SAME traded universe (zero external label dependency, zero publication lag); distinct from closed SMA family (gate variable = trailing 12-1 return of the EW basket itself, skip-aligned, not an SMA of the benchmark).",
            "LANE STAKE: any gate FAIL closes the mega-cap-scoped-core lane ENTIRELY (bare scoping, macro-gated, price-gated all exhausted) per prereg section 5; no gate-variable substitution or per-month rescues permitted.",
            "Descriptive controls (NOT gated, 0 trials charged): gate ON-fraction; overlap matrix vs FRED RISK_ON labels; passive-EW-Universe-A echo.",
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
    print("WAVE-2 / W2-H3 ABS-MOMENTUM GATE INSIDE UNIVERSE A | PAPER-ONLY | FAIL-CLOSED | FROZEN PREREG")
    print("=" * 78)
    print(f"{'gate':<4} {'description':<44} {'statistic':>14} {'bar':>10} {'state':>7}")
    print("-" * 78)
    print(f"{'G1':<4} {'prereg frozen artifact':<44} {'artifact':>14} {'locked':>10} {yn(gates['g1_prereg_committed']['pass']):>7}")
    print(f"{'G2':<4} {'IS excess stationary bootstrap blk21 n1000 s7':<44} {g2['p_value']:>14.4f} {'<=0.05':>10} {yn(g2['pass']):>7}")
    print(f"{'G3':<4} {'CPCV K=6 emb10 all-combos mean>0':<44} {g3['statistic']:>14.6f} {'>0':>10} {yn(g3['pass']):>7}")
    print(f"{'G4':<4} {'5 expanding WF folds + 60pct share cap':<44} {g4['statistic']:>14.4f} {'>0/all':>10} {yn(g4['pass']):>7}")
    print(f"{'G5':<4} {'circ-block perm (blk10,n1000,s7) vs p95':<44} {g5['statistic']:>14.4f} {('>p95 %.4f' % g5['threshold']):>10} {yn(g5['pass']):>7}")
    print(f"{'G6':<4} {'DSR ledger via preregister.py (operator)':<44} {'manual':>14} {'ledger':>10} {'PENDING':>7}")
    print("-" * 78)
    print(f"{'CHR':<4} {'OOS net CAGR>SPY AND OOS net Sharpe>SPY':<44} {charter['oos_net_sharpe_gated_core'] - charter['oos_net_sharpe_spy']:>14.4f} {'both>':>10} {yn(charter['pass']):>7}")
    print("-" * 78)
    ov = results["descriptive_controls_not_gated"]["overlap_vs_fred_risk_on"]
    ov_txt = f"agree {ov.get('agreement_rate', float('nan')):.1%}" if ov.get("available") else "unavailable"
    print(f"eval start {cal[start_i].date()} | gated trades {gated['trades']} | gate ON fraction {on_frac:.1%} of {len(gl)} month-ends | FRED overlap: {ov_txt}")
    print(f"G3 combos failing: {g3['details']['combinations_failing']}/{g3['details']['combination_count']} | G4 max fold share: {g4['details']['max_fold_share']:.4f} (cap 0.60)")
    print(f"all_computed_gates_pass={all_gates_pass} | charter_pass={charter['pass']} | verdict authority: AUDITOR | G6 DSR ledger = manual")
    print(f"results -> {os.path.relpath(OUT_RESULTS, BASE)}")


if __name__ == "__main__":
    main()
