# Wave 2 / W2-H3 — Absolute-Momentum Gate inside Universe A (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-25. Status: LOCKED before any in-sample run. Any change after
first backtest disqualifies the claim unless written as a delta BEFORE the affected
run (Q28 discipline). LIVE TRADING DISABLED — paper only, fail-closed.

## 1. Hypothesis (falsifiable)

Running the EXACT incumbent `us_momentum_top5` rule on the frozen mega-cap
Universe A, invested ONLY when the equal-weight Universe-A index's own 12-1
absolute return (252-day lagged 63 trading days: r = P_t-63/P_t-315 - 1 computed
on the last bar of each month, matching the incumbent's skip convention scaled)
is > 0 and holding cash otherwise, produces OOS net-of-cost performance beating
SPY buy-and-hold on BOTH CAGR and Sharpe (identical engine/window/fees) while
passing all six edge gates — i.e. price-derived absolute gating rescues the
mega-cap-scoped core where macro-label gating (H2) and bare scoping (H1) failed.

## 2. Prior art + changed conditions (standing-rule compliance)

| Prior attempt | Outcome | Source |
|---|---|---|
| Wave-1 H1 bare mega-cap scoping | FAIL all gates | `eval_wave1_h1.json` |
| Wave-1 H2 FRED RISK_ON label gate (full universe) | FAIL all gates despite charter pass | `eval_wave1_h2.json` |
| SMA regime sweep {100..250} on full universe | SMA150/200/250 passed; none adopted as separate claim | us_momentum_top5.yaml robustness_notes |
| Regime stack closure | confluence/trend/surge CLOSED 2026-08-14 | improvement_regime_conclusion.md |

Changed conditions: (1) UNIVERSE-SCOPED core (A) never tested with ANY gate —
H1 proved bare scoping insufficient, H2 proved macro labels fail-closed-laggy;
absolute momentum is price-derived from the SAME traded universe, zero external
label dependency, zero publication lag. (2) Distinct from the closed SMA family:
gate variable is cross-sectional-momentum-convention-aligned trailing return of
the EW basket itself, not an SMA of the benchmark. (3) Full six-gate machinery +
charter bar now exist and are applied unchanged. Closure overlap is regime-
gating only; the closure explicitly left universe scoping outside its mandate.

## 3. Frozen specification

- Core arm: byte-identical to wave1_h1_megacap_momentum_prereg.md §3 (Universe A
  verbatim 15 names; rule/costs byte-identical to strategies/us_momentum_top5.yaml).
- Gate series: EW mean of Universe-A close_ffill prices -> index; monthly last-bar
  r_gate = idx_{t-63}/idx_{t-315} - 1 (12-1 absolute momentum, skip aligned);
  gate ON iff r_gate > 0 else force-flat at that month-end (sell to cash, 5bps,
  re-enter next ON month-end); exec_delay 1 bar on ALL orders incl. gate flips.
- Window/split/benchmark identical to H1 §3 (IS ..2023-12-31, OOS 2024-01-01..
  2026-08-07, SPY engine net).
- Descriptive controls (NOT gated): gate ON-fraction; overlap matrix vs FRED
  RISK_ON labels; passive-EW-A echo.

## 4. Six gates (verbatim thresholds)

Identical to wave1_h1_megacap_momentum_prereg.md §4 verbatim (G2 IS stationary
bootstrap blk21/n1000/s7 p<=0.05 on daily NET EXCESS vs SPY-engine baseline;
G3 CPCV K=6 emb10 all combinations mean>0; G4 five expanding folds net-excess
Sharpe > 0 each + max fold share <=60%; G5 circular block shuffle blk10/n1000/s7
observed OOS annualized excess Sharpe > null p95; G6 DSR ledger entry into
docs/data/eval_wave2_h3.json trials charged = 1).

Charter bar additionally: OOS net CAGR > SPY AND OOS net Sharpe > SPY.

## 5. Kill criteria

Any gate FAIL => honest FAIL ledger entry AND the mega-cap-scoped-core lane
closes entirely (bare scoping, macro-gated, price-gated all exhausted). No gate
threshold change, no gate-variable substitution (no SMA fallback), no per-month
rescues.
