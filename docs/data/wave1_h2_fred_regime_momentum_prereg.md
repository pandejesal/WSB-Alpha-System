# Wave 1 / H2 — FRED-Regime-Conditioned Momentum Top-5 (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-24. Status: LOCKED before any in-sample run. Any change after
first backtest disqualifies the claim unless written as a delta BEFORE the affected
run. LIVE TRADING DISABLED — paper only, fail-closed.

## 1. Hypothesis (falsifiable)

Gating the EXACT incumbent `us_momentum_top5` rule (full snapshot universe,
unchanged) to be invested ONLY when the FRED historical macro regime label is
`RISK_ON` (else 100% cash) improves OOS net-of-cost risk-adjusted performance so
that the gated strategy beats SPY buy-and-hold on BOTH CAGR and Sharpe
(identical engine/window/fees) while passing all six edge gates.

## 2. Prior art + changed conditions

| Prior attempt | Outcome | Source |
|---|---|---|
| RSI(2)-era regime variants | saturated family; 8 candidates, 0 pass (round 3.5) | hunt-lessons.md |
| us_momentum_top5 SMA regime sweep {100/150/200/250} | none/SMA150/SMA200/SMA250 passed gates; UNFILTERED adopted — price-MA filters add nothing on this core | strategies/us_momentum_top5.yaml robustness_notes |
| Confluence/trend/surge stack | CLOSED 2026-08-14 (different signal family entirely) | improvement_regime_conclusion.md |

Changed conditions: (1) DIFFERENT CORE than RSI2-era variants — momentum top-5;
(2) DIFFERENT REGIME SOURCE — exogenous FRED macro composite, not price-derived
SMA state; the prior sweep tested only endogenous price filters on this core.
Macro-conditioned exposure on THIS core is untested. Cited per standing rule.

## 3. Frozen specification

- Core rule/costs/window/benchmark: byte-identical to strategies/us_momentum_top5.yaml
  and to H1 §3 (IS 2019-01-02..2023-12-31 · OOS 2024-01-01..2026-08-07;
  slippage 5bps/side; SPY same-engine benchmark).
- Regime data: `data/cache/fred_historical_regimes.json` — {ISO date: label},
  labels {RISK_ON, NEUTRAL, RISK_OFF, STAGFLATION}, 2003-01-02..2026-08-14
  daily (path corrected from mega-prompt §7 `data/…` during prereg verification).
- Exposure rule (ZERO tuned parameters): day-t portfolio exposure = full weight
  iff regime(t−1) == RISK_ON, else cash. One binary rule; NEUTRAL / RISK_OFF /
  STAGFLATION are all flat. No scaling grid, no per-label treatment.
- Point-in-time guard (both branches pre-declared NOW): BEFORE any in-sample
  run, MAIN must inspect the generating pipeline (src/research/ FRED macro
  builder) and verify labels use only data publishable by each date's close.
  IF verified ⇒ branch A: application lag = 1 trading day (as written above).
  IF NOT verifiable ⇒ branch B becomes primary: mandatory 5-trading-day
  application lag. The executed branch is recorded in the eval JSON; no other
  variant may be run.
- Cash earns 0%; re-entry/exit trades at next bar open+delay convention of the
  engine; extra turnover costs charged at 5bps/side on switched notional.

## 4. Six gates (verbatim thresholds)

Identical machinery to wave1_h1 §4: block bootstrap IS p≤0.05 (block 21d,
1000 draws, seed 7, net excess vs SPY-engine); CPCV K=6 embargo 10d all-positive;
WF 5 expanding folds all-positive excess Sharpe with ≤60% single-fold share;
circular-block permutation p95 survival (block=10, 1000 draws, seed 7);
positive DSR entry in docs/data/eval_wave1_h2.json via scripts/preregister.py
record; trials charged = 1 (the single executed point-in-time branch).
Charter bar additionally: OOS net CAGR > SPY AND OOS net Sharpe > SPY.

## 5. Kill criteria

Any gate FAIL ⇒ honest FAIL ledger entry. If gating destroys the CAGR bar while
improving Sharpe, verdict is FAIL for this claim (bar is conjunctive) — no
re-tuning of thresholds, no per-label rescues, no post-hoc lag changes.
