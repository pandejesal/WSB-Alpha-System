# Wave 2 / W2-H2 — Drawdown-Ratchet Sizing DELTA Test (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-25. Status: LOCKED before any in-sample run. Any change after
first backtest disqualifies the claim unless written as a delta BEFORE the affected
run (Q28 discipline). LIVE TRADING DISABLED — paper only, fail-closed.

## 1. Hypothesis (falsifiable)

Scaling the incumbent `us_momentum_top5` portfolio by m_t = clamp(1 -
DD_t/0.20, 0.25, 1.00) at month-ends — where DD_t is the overlay arm's own
current drawdown from its trailing equity peak (0 when at peak) — produces a
POSITIVE mean daily net-return DELTA versus the unscaled incumbent that survives
all five statistical gates COMPUTED ON THE PAIRED DELTA SERIES, while the
overlay still beats SPY buy-and-hold on BOTH OOS net CAGR and Sharpe and
achieves OOS maxDD shallower than -30%.

## 2. Prior art + changed conditions (standing-rule compliance)

| Prior attempt | Outcome | Source |
|---|---|---|
| Wave-1 H3 vol-target sizing (sigma-state) | FAIL G2/G3/G5 on absolute excess; economic improvement real (maxDD -23.3% vs -38.3%) | `eval_wave1_h3.json` |
| ML overlays/exits incl. SL-adjusted labels | FAIL 17/17 + all decisive gates | `2026-08-16-ml-overlay.md`, H-SLX-1 eval |

Changed conditions: (1) DIFFERENT STATE VARIABLE — cumulative drawdown depth of
the strategy's own equity curve, not recent return volatility; mechanism differs
(loss-ratchet de-risking vs vol persistence). (2) Delta-series gate machinery
identical to W2-H1's declared re-entry logic (increment attributable to sizing,
immune to drift-dominated absolute nulls). (3) Thresholds fixed ex ante at the
H3-comparable floor/cap (0.25/1.00); DD normalization constant 0.20 declared
once, never tuned.

## 3. Frozen specification

- Overlay arm: wave1_h3_test.py engine lineage with m_t replaced by the
  drawdown rule above; recomputed ONLY at month-ends (same cadence as H3);
  DD_t from overlay equity ffilled closes to date t-1; cold start m=1.00;
  universe/params/costs byte-identical to §3 of wave1_h3_voltarget_overlay_prereg.md.
- Baseline arm: byte-identical us_momentum_top5 engine from same run.
- Delta series d_t = r_overlay,t - r_baseline,t daily NET.
- Window/split/benchmark identical to W2-H1 §3.
- Descriptive controls (NOT gated): time-under-m<1 fraction; DD-path echo.

## 4. Six gates (verbatim thresholds)

Identical machinery to W2-H1 §4 gates 2-5 applied to THIS arm's delta series:
G2 stationary block bootstrap p<=0.05 (blk21, n1000, s7); G3 CPCV K=6 emb10 all
combinations mean delta > 0; G4 five expanding folds mean delta > 0 each AND max
incremental fold share <= 60%; G5 circular block shuffle (blk10, n1000, s7)
observed annualized delta-Sharpe > null p95; G6 DSR ledger entry into
docs/data/eval_wave2_h2.json trials charged = 1.

Charter bar additionally: overlay OOS net CAGR > SPY AND OOS net Sharpe > SPY.
Additional frozen claim condition: overlay OOS maxDD > -30% (shallower).

## 5. Kill criteria

Any gate FAIL => honest FAIL ledger entry. No DD-threshold tuning, no cadence
changes, no hybridizing with W2-H1 post hoc. If both W2-H1 and W2-H2 fail, the
entire deterministic-sizing lane CLOSES per W2-H1 §5.
