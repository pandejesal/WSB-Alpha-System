# Wave 1 / H1 — Mega-Cap-Only Momentum Top-5 (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-24. Status: LOCKED before any in-sample run. Any change after
first backtest disqualifies the claim unless written as a delta BEFORE the affected
run (Q28 discipline). LIVE TRADING DISABLED — paper only, fail-closed.

## 1. Hypothesis (falsifiable)

Restricting the EXACT incumbent `us_momentum_top5` rule (monthly top-5 by
126d-return-skip-21d, equal weight, drift-rebal 5%, exec delay 1 bar) to the
frozen mega-cap **Universe A** produces OOS net-of-cost performance beating SPY
buy-and-hold on BOTH CAGR and Sharpe (identical engine/window/fees) while passing
all six edge gates — i.e. the 3× observed mega-cap B-gate conditioning advantage
generalizes from the closed confluence stack to the momentum core.

## 2. Prior art + changed conditions (standing-rule compliance)

| Prior attempt | Outcome | Source |
|---|---|---|
| Rounds 1/2/2b/3 `A_megacap_base` | cleared B-gates 3× independently while laggard-universe variants failed | round1/2/2b/3_results.json |
| Mega-cap-only claim variant | NOT adopted — flagged as CLAIM CHANGE requiring own prereg | improvement_regime_conclusion.md §45, round2_preregistration.md L116 |
| Confluence/trend/surge stack | regime CLOSED 2026-08-14 | improvement_regime_conclusion.md |

Changed conditions: (1) DIFFERENT CORE — cross-sectional momentum top-5, never
tested inside the closed confluence family closure; (2) explicit claim-scoping
prereg exactly as reserved by §45; (3) full-OHLCV panel + six-gate machinery now
exist (did not at closure time). Nearest failed relative is the confluence stack;
overlap is universe-scoping only, which the closure explicitly placed OUTSIDE its
mandate.

## 3. Frozen specification

- Universe: `Universe A` verbatim from round1_preregistration.md L13 =
  AAPL MSFT GOOGL AMZN NVDA META TSLA JPM V JNJ WMT MA UNH XOM DIS (15),
  intersected with the 481-name snapshot and local panel availability.
  This list is a PRE-EXISTING frozen artifact (defined 2026-08-13 era); reusing
  it verbatim avoids post-hoc universe cherry-picking.
- Selection/rule/costs: byte-identical to strategies/us_momentum_top5.yaml
  (top_n=5, lookback 126, skip 21, warmup 340, monthly last-bar rebalance,
  drift_rebal 0.05, exec_delay 1, slippage 5bps/side, $0 commission, T+1).
- Window: IS 2019-01-02..2023-12-31 · OOS 2024-01-01..2026-08-07 (house convention).
- Benchmark: SPY buy-and-hold, same engine/window/fees, net.
- Declared caveat: Universe A membership reflects 2026 hindsight (universe
  lookahead); accepted because it is the identical list behind the 3× prior
  passes — the claim is scoped to THIS cohort definition.
- Pre-declared descriptive control (NOT gated, 0 trials): equal-weight passive
  buy-and-hold of Universe A, same window/costs — distinguishes "momentum adds
  edge inside mega-caps" from "mega-caps beat SPY".

## 4. Six gates (verbatim thresholds)

1. Prereg committed before any in-sample run (this document).
2. IS significance: two-sided stationary block bootstrap on IS daily NET EXCESS
   returns vs SPY-engine baseline (mean block 21 trading days, 1000 draws,
   seed 7); p ≤ 0.05 required. Borderline ≈0.05 = FAILURE, never encouragement.
3. Combinatorially purged CV: K=6 folds, embargo 10 trading days; mean net
   excess return positive in EVERY training-combination-held-out evaluation.
   Rule is parameter-free (no fitting): folds evaluate the fixed rule.
4. Walk-forward: 5 expanding OOS folds ending 2024-06-30 / 2024-12-31 /
   2025-06-30 / 2025-12-31 / 2026-08-07; net excess Sharpe > 0 in every fold;
   no single fold contributes >60% of cumulative OOS net excess.
5. Permutation null: circular block shuffle (block=10 days, 1000 draws, seed 7)
   of daily net excess returns; observed OOS annualized excess Sharpe must
   exceed null p95.
6. DSR: positive Deflated-Sharpe ledger entry via scripts/preregister.py record
   into docs/data/eval_wave1_h1.json; trials charged = 1 (control arm excluded,
   descriptive only).

Charter bar additionally: OOS net CAGR > SPY AND OOS net Sharpe > SPY.

## 5. Kill criteria

Any gate FAIL ⇒ honest FAIL ledger entry (recorded like topic07 / H-SLX-1).
Over-parameterization: N/A (zero fitted params) — any temptation to alter the
rule after seeing results is itself a kill. Static canonical configs stay
canonical until beaten under these rules.
