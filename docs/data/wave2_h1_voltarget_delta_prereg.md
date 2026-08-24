# Wave 2 / W2-H1 — Vol-Target Sizing DELTA Test (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-25. Status: LOCKED before any in-sample run. Any change after
first backtest disqualifies the claim unless written as a delta BEFORE the affected
run (Q28 discipline). LIVE TRADING DISABLED — paper only, fail-closed.

## 1. Hypothesis (falsifiable)

Scaling the incumbent `us_momentum_top5` portfolio by m_t =
clamp(0.15/sigma_hat_21d_ann, 0.25, 1.00) at month-ends produces a POSITIVE mean
daily net-return DELTA versus the unscaled incumbent that survives all five
statistical gates COMPUTED ON THE PAIRED DELTA SERIES, while the overlay still
beats SPY buy-and-hold on BOTH OOS net CAGR and Sharpe (charter bar unchanged)
and retains primary acceptance Sharpe margin >= +0.10 vs the incumbent.

## 2. Prior art + changed conditions (standing-rule compliance)

| Prior attempt | Outcome | Source |
|---|---|---|
| Wave-1 H3 identical m_t formula, gates on ABSOLUTE excess | FAIL G2 (p=0.082), G3 (fold-5-alone neg), G5 (obs 1.374 < null MEAN 1.384) | `eval_wave1_h3.json`, `wave1_h3_results.json` |
| ML overlays on cores, 17 variants | FAIL 17/17 | decision `2026-08-16-ml-overlay.md` |

Changed conditions: (1) HYPOTHESIS TARGET moved from absolute SPY-excess to the
paired overlay-minus-incumbent daily delta — directly addressing the diagnosed
failure mode (under 2024-26 drift, ANY long-biased path's absolute excess sits
inside its block-shuffle null; only the sizing INCREMENT is attributable to the
overlay). (2) All five statistical gates computed on the delta series (paired by
construction, variance-reduced). (3) m_t formula BYTE-IDENTICAL to H3 — zero
parameter changes permitted (anti-p-hacking). Sizing lane remains open per v3
ledger; this is the declared re-entry.

## 3. Frozen specification

- Overlay arm: byte-identical reproduction of wave1_h3_test.py overlay engine
  (universe snapshot-intersect-local minus SPY, 481 names; params byte-identical
  to strategies/us_momentum_top5.yaml; m_t from trailing 21d OVERLAY returns,
  cold start m=1.00, cap binding no margin).
- Baseline arm: byte-identical us_momentum_top5 engine from the SAME script run
  (paired by construction — identical calendar, costs, fills).
- Delta series: d_t = r_overlay,t - r_baseline,t, daily NET returns.
- Window: effective evaluated start post-warmup (2020-05-08 era), IS/OOS split
  2023-12-31 / 2024-01-01, OOS end 2026-08-07 (house convention).
- Benchmark for charter bar: SPY buy-and-hold, same engine/window/fees, net.
- Pre-declared descriptive controls (NOT gated, 0 trials): delta summary stats;
  m-series distribution echo.

## 4. Six gates (verbatim thresholds)

1. Prereg committed before any in-sample run (this document).
2. IS significance ON DELTA: two-sided stationary block bootstrap (Hall-Wilson),
   mean block 21 trading days, 1000 draws, seed 7; p <= 0.05 required against
   null mean(d)=0. Borderline ~0.05 = FAILURE.
3. CPCV ON DELTA: K=6 contiguous folds, embargo 10 trading days; mean delta > 0
   in EVERY non-empty proper-subset held-out combination.
4. Walk-forward ON DELTA: 5 expanding folds ending 2024-06-30 / 2024-12-31 /
   2025-06-30 / 2025-12-31 / 2026-08-07 (snap last trading bar on/before);
   mean delta > 0 in EVERY fold; no single incremental fold contributes >60% of
   cumulative OOS sum-of-delta.
5. Permutation null ON DELTA: circular block shuffle (block=10 days, 1000 draws,
   seed 7) of daily delta; observed ANNUALIZED SHARPE OF DELTA must exceed null
   p95.
6. DSR: positive Deflated-Sharpe ledger entry into docs/data/eval_wave2_h1.json;
   trials charged = 1 (wave-2 budget {w2h1:1, w2h2:1, w2h3:1}; h4 carried 3).

Charter bar additionally: overlay OOS net CAGR > SPY AND OOS net Sharpe > SPY.
Primary acceptance: OOS net Sharpe(overlay) - Sharpe(incumbent) >= +0.10.

## 5. Kill criteria

Any gate FAIL => honest FAIL ledger entry. No threshold nudging, no sigma-window
retuning, no clamp changes, no lag changes — any temptation is itself a kill.
If delta gates fail, the sizing lane CLOSES entirely (both m-form variants
exhausted); reopening requires genuinely new data or new mechanism, not new
statistics on the same arms.
