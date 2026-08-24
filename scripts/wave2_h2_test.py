"""Wave 2 / W2-H2 â€” Drawdown-Ratchet Sizing DELTA Test (FROZEN PREREG RUNNER).

PAPER-ONLY. LIVE TRADING DISABLED. FAIL-CLOSED. Zero fitted parameters.

Implements docs/data/wave2_h2_drawdown_ratchet_delta_prereg.md (frozen
2026-08-25) EXACTLY. Engine lineage: scripts/wave1_h3_test.py with the sizing
state VARIABLE replaced - m_t is no longer a function of realized volatility
but of the OVERLAY ARM'S OWN current drawdown from its trailing equity peak:

    m_t = clamp(1 - DD_t / 0.20, 0.25, 1.00)

recomputed ONLY at month-ends (same cadence as H3), DD_t measured on overlay
equity up to bar t-1 (0 when at peak), cold start m=1.00. Universe/params/
costs byte-identical to wave1_h3_voltarget_overlay_prereg.md section 3.
Baseline arm = untargeted us_momentum_top5 engine from the SAME script run
(paired by construction).

All five statistical gates G2-G5 are computed on the PAIRED daily
overlay-minus-incumbent DELTA series d_t = r_overlay,t - r_baseline,t using
gate machinery IMPORTED VERBATIM from scripts/wave1_h3_test.py (identical to
W2-H1's declared re-entry machinery). Charter bar unchanged; additional
FROZEN claim condition: overlay OOS maxDD shallower than -30%.

This script NEVER self-certifies PASS; verdict authority = AUDITOR seat.

Outputs:
  docs/data/wave2_h2_results.json   (full numbers; deterministic, seeded)
Stdout: compact six-gate + charter + PRIMARY MARGIN summary table.
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
        COST,
        DRIFT_BAND,
        INIT_EQUITY,
        IS_END,
        MIN_ORDER,
        OOS_START,
        TOP_N,
        VOL_CAP,
        VOL_FLOOR,
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
        spy_engine,
    )
    ENGINE_SOURCE = "imported_verbatim:scripts/wave1_h3_test.py"
except Exception as exc:  # pragma: no cover - fail-closed
    raise SystemExit(
        f"FAIL-CLOSED: cannot import byte-identical engine from "
        f"scripts/wave1_h3_test.py ({exc}); refusing to re-implement"
    )

PREREG_PATH = os.path.join(BASE, "docs", "data",
                           "wave2_h2_drawdown_ratchet_delta_prereg.md")
OUT_RESULTS = os.path.join(BASE, "docs", "data", "wave2_h2_results.json")

# Frozen spec constants (declared once, never tuned)
DD_NORMALIZATION = 0.20          # m_t = clamp(1 - DD_t/0.20, .25, 1.00)
FROZEN_FINAL_BAR = pd.Timestamp("2026-08-07")
VERIFIED_UNIVERSE_SIZE = 481
MAXDD_CLAIM_FLOOR = -0.30        # overlay OOS maxDD must be shallower than -30%

try:
    from ml_sl_exit_test import month_end_mask
    MONTH_END_SOURCE = "imported:scripts/ml_sl_exit_test.py"
except Exception:
    MONTH_END_SOURCE = "inline_verbatim_fallback"

    def month_end_mask(cal):
        periods = pd.Series(cal).dt.to_period("M")
        return ((periods != periods.shift(-1)).to_numpy())


def simulate_ddratchet(panel, cal, me_mask, start_i, end_i):
    """Overlay: wave1_h3_test.simulate_voltarget structure VERBATIM with the
    m_t state variable replaced by the drawdown ratchet rule.

    Differences vs simulate_voltarget (and NOTHING else):
      - m_t = clamp(1 - DD_t/0.20, 0.25, 1.00); DD_t = current drawdown of the
        overlay's own equity up to bar i-1 from its trailing peak (0 at peak).
      - Cold start m=1.00 before any history exists.
      - Tracks dd_series (month-end -> DD_t) for descriptive control echo.
    Trade queueing, scaling, drift-band handling, fills, costs: identical code
    paths to the H3 overlay loop.
    """
    cash = INIT_EQUITY
    positions = {}
    pending_buys, pending_sells = [], []
    equity = np.empty(end_i - start_i + 1)
    n_trades = 0
    m_series = {}
    dd_series = {}
    m_current = 1.0

    def px(t, i):
        v = panel[t]["close_ffill"].iloc[i]
        return np.nan if pd.isna(v) else float(v)

    def mark(i):
        return cash + sum(rec["shares"] * px(t, i) for t, rec in positions.items())

    for i in range(start_i, end_i + 1):
        # 1) fills sells (verbatim H3 overlay)
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

        # 2) fills buys (scaled) (verbatim H3 overlay)
        eq_mark = mark(i)
        for order in pending_buys:
            t = order["ticker"]
            p = px(t, i)
            if pd.isna(p) or t in positions:
                continue
            if order.get("notional") is not None:
                notional = order["notional"]
            else:
                notional = m_current * eq_mark / TOP_N
            notional = min(notional, max(cash, 0.0))
            if notional < MIN_ORDER:
                continue
            shares = notional / (p * (1.0 + COST))
            cash -= shares * p * (1.0 + COST)
            positions[t] = {"shares": shares}
            n_trades += 1
        pending_buys = []

        # 3) month-end signal: recompute selection AND m_t (DD-ratchet block)
        if me_mask[i] and i < end_i:
            hist_len = i - start_i
            if hist_len >= 1:
                eq_hist = equity[:hist_len]
                peak = float(np.max(eq_hist))
                last_eq = float(eq_hist[-1])
                if peak > 0 and not np.isnan(peak) and not np.isnan(last_eq):
                    dd_t = max(0.0, 1.0 - last_eq / peak)
                else:
                    dd_t = 0.0
            else:
                dd_t = 0.0
            m_current = float(np.clip(1.0 - dd_t / DD_NORMALIZATION, VOL_FLOOR, VOL_CAP))
            dd_series[str(cal[i].date())] = float(dd_t)
            m_series[str(cal[i].date())] = m_current

            scores = {}
            for t, d in panel.items():
                m = d["mom"].iloc[i]
                if not pd.isna(m) and d["hist_cnt"][i] >= WARMUP:
                    scores[t] = float(m)
            top = [t for t, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]]
            for t in list(positions):
                if t not in top:
                    pending_sells.append({"ticker": t, "shares": None, "reason": "rank_drop"})
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
                        pending_sells.append({"ticker": t, "shares": (-delta) / p, "reason": "dd_ratchet_down"})
                    elif delta > MIN_ORDER and delta <= cash + 1e-9:
                        buy_notional = min(delta, max(cash, 0.0))
                        if buy_notional >= MIN_ORDER:
                            pending_buys.append({"ticker": t, "notional": buy_notional, "reason": "dd_ratchet_up"})
                elif t not in positions:
                    notional = m_current * eq_now / TOP_N
                    if notional >= MIN_ORDER:
                        pending_buys.append({"ticker": t, "notional": notional, "reason": "entry_ddratchet"})

        # 4) drift-band rebalance scaled by m_current (verbatim H3 overlay)
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
                if tgt_scaled < 1e-9:
                    continue
                thresh = DRIFT_BAND * eq_now
                diff = val - tgt_scaled
                if diff > thresh:
                    sell_val = diff
                    if sell_val >= MIN_ORDER:
                        pending_sells.append({"ticker": t, "shares": sell_val / p, "reason": "drift_ddratchet"})
                elif diff < -thresh:
                    buy_val = min(-diff, max(cash, 0.0))
                    if buy_val >= MIN_ORDER:
                        pending_buys.append({"ticker": t, "notional": buy_val, "reason": "drift_ddratchet"})
        equity[i - start_i] = mark(i)

    m_vals = list(m_series.values())
    dd_vals = list(dd_series.values())
    m_stats = {"n_months": len(m_vals), "min": float(min(m_vals)) if m_vals else None,
               "max": float(max(m_vals)) if m_vals else None,
               "mean": float(np.mean(m_vals)) if m_vals else None,
               "frac_at_cap": float(sum(1 for v in m_vals if abs(v - VOL_CAP) < 1e-9) / len(m_vals)) if m_vals else 0,
               "frac_at_floor": float(sum(1 for v in m_vals if abs(v - VOL_FLOOR) < 1e-9) / len(m_vals)) if m_vals else 0,
               "frac_under_1": float(sum(1 for v in m_vals if v < 1.0 - 1e-9) / len(m_vals)) if m_vals else 0}
    dd_stats = {"n_months": len(dd_vals),
                "mean_month_end_dd": float(np.mean(dd_vals)) if dd_vals else None,
                "max_month_end_dd": float(np.max(dd_vals)) if dd_vals else None}

    return {"equity": pd.Series(equity, index=cal[start_i:end_i + 1]), "trades": n_trades,
            "m_series": m_series, "m_stats": m_stats, "dd_series": dd_series, "dd_stats": dd_stats}


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

    baseline = simulate(panel, cal, me_mask, start_i, last_i)
    overlay = simulate_ddratchet(panel, cal, me_mask, start_i, last_i)

    base_eq = baseline["equity"]
    over_eq = overlay["equity"]
    spy_eq = spy_engine(spy_ffill, start_i, last_i)

    base_r = base_eq.pct_change()
    over_r = over_eq.pct_change()
    spy_r = spy_eq.pct_change()

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
                                              "scripts/preregister.py record into docs/data/eval_wave2_h2.json, trials "
                                              "charged = 1 (wave-2 budget w2h2:1). Recorded by operator AFTER auditor verdict.",
                                      "command_shape": "python scripts/preregister.py record <spec_path> --verdict <PASS|FAIL|HONEST_ABANDON> [--eval-path docs/data/wave2_h2_results.json]"}},
    }
    gates["g5_permutation_null"] = g5_permutation_null(oos_delta, oos_delta_sharpe)

    charter = {"oos_net_cagr_overlay": arms["overlay"]["oos"]["cagr"], "oos_net_cagr_spy": arms["spy"]["oos"]["cagr"],
               "oos_net_sharpe_overlay": arms["overlay"]["oos"]["sharpe"], "oos_net_sharpe_spy": arms["spy"]["oos"]["sharpe"]}
    charter["pass"] = bool(charter["oos_net_cagr_overlay"] > charter["oos_net_cagr_spy"]
                           and charter["oos_net_sharpe_overlay"] > charter["oos_net_sharpe_spy"])

    # Additional FROZEN claim condition: overlay OOS maxDD shallower than -30%
    overlay_oos_maxdd = arms["overlay"]["oos"]["maxdd"]
    maxdd_claim = {"overlay_oos_maxdd": overlay_oos_maxdd, "floor": MAXDD_CLAIM_FLOOR,
                   "pass": bool(overlay_oos_maxdd > MAXDD_CLAIM_FLOOR)}

    sharpe_margin = arms["overlay"]["oos"]["sharpe"] - arms["baseline_incumbent"]["oos"]["sharpe"]
    primary = {"oos_sharpe_overlay": arms["overlay"]["oos"]["sharpe"], "oos_sharpe_baseline": arms["baseline_incumbent"]["oos"]["sharpe"],
               "sharpe_margin": float(sharpe_margin), "sharpe_margin_bar": 0.10,
               "sharpe_margin_pass": bool(sharpe_margin >= 0.10),
               "oos_cagr_overlay": arms["overlay"]["oos"]["cagr"], "oos_cagr_spy": arms["spy"]["oos"]["cagr"],
               "cagr_vs_spy_pass": bool(arms["overlay"]["oos"]["cagr"] > arms["spy"]["oos"]["cagr"]),
               "charter_pass": bool(charter["pass"]),
               "maxdd_claim_pass": bool(maxdd_claim["pass"])}
    primary["pass"] = bool(primary["sharpe_margin_pass"] and primary["cagr_vs_spy_pass"]
                           and primary["charter_pass"] and primary["maxdd_claim_pass"])
    primary["turnover_delta_trades"] = int(overlay["trades"] - baseline["trades"])

    computed = [k for k in ("g1_prereg_committed", "g2_is_stationary_bootstrap", "g3_cpcv", "g4_walk_forward", "g5_permutation_null")]
    all_gates_pass = all(gates[k]["pass"] for k in computed)

    results = {
        "claim": ("Scaling the incumbent us_momentum_top5 portfolio by m_t = clamp(1 - DD_t/0.20, 0.25, 1.00) "
                  "at month-ends - where DD_t is the overlay arm's own current drawdown from its trailing equity "
                  "peak - produces a POSITIVE mean daily net-return DELTA versus the unscaled incumbent that "
                  "survives all five statistical gates COMPUTED ON THE PAIRED DELTA SERIES, while the overlay "
                  "still beats SPY buy-and-hold on BOTH OOS net CAGR and Sharpe and achieves OOS maxDD "
                  "shallower than -30%."),
        "prereg": os.path.relpath(PREREG_PATH, BASE),
        "prereg_status": "FROZEN 2026-08-25 - LOCKED before any in-sample run",
        "paper_only": True,
        "verdict_authority": "RESERVED FOR AUDITOR SEAT - this output reports mechanical gate booleans only; no PASS claim is made by the runner",
        "config_echo": {
            "universe": {"definition": "snapshot map keys INTERSECT local OHLCV csv stems MINUS SPY (verbatim load_snapshot_tickers)",
                         "size": integrity["universe_size"], "verified_size": VERIFIED_UNIVERSE_SIZE,
                         "size_matches": bool(integrity["universe_size"] == VERIFIED_UNIVERSE_SIZE)},
            "benchmark": "SPY",
            "params_byte_identical_to": "strategies/us_momentum_top5.yaml via wave1_h3_voltarget_overlay_prereg.md section 3",
            "engine_lineage": {"derived_from": ENGINE_SOURCE,
                               "month_end_source": MONTH_END_SOURCE,
                               "byte_identity_note": "simulate_ddratchet clones the wave-1 H3 overlay loop line-for-line; ONLY the m_t state-variable block differs (own-equity drawdown depth instead of trailing-return volatility)",
                               "state_variable_rule": "m_t = clamp(1 - DD_t/0.20, 0.25, 1.00); DD_t = drawdown of overlay equity up to bar t-1 from trailing peak (0 at peak); recomputed only at month-ends; cold start m=1.00"},
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
        "dd_series": overlay["dd_series"], "dd_stats": overlay["dd_stats"],
        "gates": gates, "charter_bar": charter, "maxdd_frozen_claim": maxdd_claim,
        "primary_acceptance": primary,
        "trades_baseline": baseline["trades"], "trades_overlay": overlay["trades"],
        "all_computed_gates_pass": bool(all_gates_pass),
        "notes": [
            "PRIOR ART: wave-1 H3 vol-target sizing (sigma-state) FAILED G2/G3/G5 on absolute excess honestly (docs/data/eval_wave1_h3.json); W2-H1 (same-batch, tested first) failed ALL paired-delta gates with negative mean delta (docs/data/eval_wave2_h1.json).",
            "CHANGED CONDITIONS: different STATE VARIABLE - cumulative drawdown depth of the strategy's own equity curve (loss-ratchet de-risking) rather than recent return volatility (vol persistence); thresholds fixed ex ante at the H3-comparable floor/cap (0.25/1.00); DD normalization 0.20 declared once.",
            "SIZING LANE STAKE: if BOTH W2-H1 and W2-H2 fail, the entire deterministic-sizing lane CLOSES per preregs' section 5; no hybridizing post hoc.",
            "Descriptive controls (NOT gated, 0 trials charged): time-under-m<1 fraction (m_stats.frac_under_1); month-end DD-path echo (dd_series/dd_stats); delta summary stats (IS/OOS/full).",
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
    print("WAVE-2 / W2-H2 DRAWDOWN-RATCHET SIZING DELTA TEST | PAPER-ONLY | FAIL-CLOSED | FROZEN PREREG")
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
    print(f"{'MDD':<4} {'overlay OOS maxDD shallower than -30%':<44} {overlay_oos_maxdd:>14.4f} {'>-0.30':>10} {yn(maxdd_claim['pass']):>7}")
    print(f"{'PRI':<4} {'Sharpe margin >=+0.10 AND CHR AND MDD':<44} {primary['sharpe_margin']:>14.4f} {'all':>10} {yn(primary['pass']):>7}")
    print("-" * 78)
    ms, ds = overlay["m_stats"], overlay["dd_stats"]
    print(f"eval start {cal[start_i].date()} | baseline trades {baseline['trades']} | overlay trades {overlay['trades']} | m months {ms['n_months']} mean {ms['mean']:.3f} under1_frac {ms['frac_under_1']:.1%} | month-end DD mean {ds['mean_month_end_dd']:.3f} max {ds['max_month_end_dd']:.3f}")
    print(f"G3 combos failing: {g3['details']['combinations_failing']}/{g3['details']['combination_count']} | G4 max fold share: {g4['details']['max_fold_share']:.4f} (cap 0.60)")
    print(f"delta OOS ann-Sharpe {oos_delta_sharpe:.4f} | all_computed_gates_pass={all_gates_pass} | primary_pass={primary['pass']} | verdict authority: AUDITOR | G6 DSR ledger = manual")
    print(f"results -> {os.path.relpath(OUT_RESULTS, BASE)}")


if __name__ == "__main__":
    main()
