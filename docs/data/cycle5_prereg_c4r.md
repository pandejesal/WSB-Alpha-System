# Cycle 5 — Claim C4R: C4 "ML hybrid" reopen delta (MEASUREMENT TRACK — PRE-REGISTRATION, FROZEN)

Date frozen: 2026-08-16. Status: LOCKED. No engine run against this document:
C4R re-evaluates the EXISTING frozen C4 run (scripts/cycle3_ml_engine.py,
spec in docs/data/cycle3_prereg_ml.md) on a new verdict schedule only.

## 1. What this is

A Q28 reopen delta on C4 ("ML hybrid price-only decile long-short") — the
only near-miss claim of Cycles 1-4 (OOS mean +0.254%/wk vs null p95
+0.2653%/wk; null fail by 0.011pp; 3 of 4 OOS years positive; maxDD -12.4%).

Reclassified during freeze review (2026-08-16, user-confirmed): the
train_consistency gate is IMMUTABLE — its value (-0.1405%/wk train mean)
is measured on the CLOSED train window (rebalance dates < 2023-12-31) and
cannot change. Under the frozen bar (train mean > 0 required), C4R's final
verdict is therefore a DETERMINISTIC FAIL regardless of OOS growth
(kill rule: wrong train sign = dead on arrival, unchanged). Per user
decision, C4R is retained as a MEASUREMENT TRACK — not a pass-candidate.
The Fix Program's done criterion (R8) rests on C6 alone.

## 2. Delta scope (exactly two changes; everything else frozen)

| # | Change | Value |
|---|--------|-------|
| D1 | Verdict schedule | Interim refresh 2026-09-17; FINAL verdict end-2027, evaluated on the full accumulated OOS window (2024-01-01 .. end-2027). More OOS weeks narrow the null p95 band (statistic = OOS mean, SE ~ sigma/sqrt(n)), giving a fairer measurement of the 0.011pp gap. |
| D2 | (nothing else) | Explicitly UNCHANGED: 12 price features, GBR hyperparameters, decile L/S, 10bps/side, MIN_N=20, weekly rebalance, rank-normalized target/features, train window, weekly block-shuffle null (seed 7), train_consistency gate definition. The Track P per-frequency null fix does NOT apply here (C4 is a WEEKLY claim; its null was already weekly block-shuffle). |

## 3. Gate state as of freeze (measured 2026-08-07 OOS, from
docs/data/cycle3_ml_evaluation.json — recorded, not re-scored)

| Gate | Value | Verdict (frozen bar) |
|------|-------|----------------------|
| train_consistency | train mean -0.1405%/wk | FAIL (immutable) |
| oos_median_3of4_years | 2024 T, 2025 T, 2026 T (partial), 2027 not computable | pass so far |
| oos_sharpe_ge_1 | 0.938 | FAIL |
| oos_maxdd_le_25 | -12.36% | pass |
| oos_cagr_ge_15_net | 12.98% | FAIL |
| null_p95 | p95 +0.2653%/wk vs OOS mean +0.254%/wk | FAIL (0.011pp) |

## 4. Measurement outputs at each refresh (2026-09-17, end-2027)

- docs/data/cycle5_c4r_measurement.json: OOS mean vs narrow-band null p95
  (recomputed on the accumulated window, seed 7), per-year OOS medians,
  Sharpe / maxDD / CAGR trajectory, weeks added since prior refresh.
- Verdict field is recorded; expected value is FAIL (train gate immutable).

## 5. Kill rules (Q28, unchanged)

- No change to this document after any refresh = disqualification.
- No tuning, no re-scoring, no re-ranking.
- C4R's frozen spec may only be altered by a NEW pre-registered delta.