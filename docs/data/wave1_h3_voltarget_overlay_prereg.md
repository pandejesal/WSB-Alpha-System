# Wave 1 / H3 — Volatility-Targeted Sizing Overlay (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-24. Status: LOCKED before any in-sample run. Any change after
first backtest disqualifies the claim unless written as a delta BEFORE the affected
run. LIVE TRADING DISABLED — paper only, fail-closed.

## 1. Hypothesis (falsifiable)

Scaling the incumbent `us_momentum_top5` portfolio by an inverse-realized-vol
multiplier at each month-end (target 15% annualized strategy vol) improves OOS
net-of-cost Sharpe vs the untargeted incumbent by a margin that ALSO keeps OOS
net CAGR above SPY buy-and-hold (identical engine/window/fees), while passing all
six edge gates. Sizing lane — explicitly one of the lanes left open by the
2026-08-14 closure.

## 2. Prior art + changed conditions

| Prior attempt | Outcome | Source |
|---|---|---|
| Improvement regime closure | exits/sizing/data/claim-scoping declared OUTSIDE mandate = OPEN lanes | improvement_regime_conclusion.md |
| ML overlays incl. sizing-flavored variants | FAIL 17/17 (topic 07) — all were LEARNED models; none was a closed-form vol target | decision 2026-08-16-ml-overlay.md |

Changed conditions: first test in this library of a CLOSED-FORM deterministic
sizing rule (no learning, no parameters fitted to data). Overlaps no listed
failed family.

## 3. Frozen specification

- TARGET CORE DECLARED NOW (anti-cherry-pick): `us_momentum_top5` incumbent as-is.
  If another wave-1 candidate passes its full gate chain before H3 executes, H3
  still binds to us_momentum_top5 — retargeting requires a NEW prereg.
- Rule (4 declared constants, no search): at each month-end rebalance date t,
  m_t = min(0.25 floor … cap) with
  m_t = clamp( 0.15 / σ̂_t , 0.25 , 1.00 );
  σ̂_t = annualized (√252) std of the STRATEGY's daily net returns over the
  trailing 21 trading days ending t−1.
- Cap 1.00 is binding by account law: $100 paper cash account, NO margin — the
  overlay can only de-lever. Positions scaled by m_t via fractional shares;
  residual sits in cash at 0%.
- Costs: only weight DELTAS trade at rebalance bars, 5bps/side on delta notional;
  all other engine conventions identical to strategies/us_momentum_top5.yaml.
- Window/benchmark: IS 2019-01-02..2023-12-31 · OOS 2024-01-01..2026-08-07;
  SPY buy-and-hold same engine/window/fees, net. Baseline arm = untargeted
  incumbent run on the identical machinery in the same session.

## 4. Six gates (verbatim thresholds)

1. This prereg precedes any run.
2. IS significance: block bootstrap (block 21d, 1000 draws, seed 7) on IS daily
   net excess vs SPY-engine for the OVERLAY arm; p ≤ 0.05; borderline = FAIL.
3. CPCV: K=6 folds, embargo 10 trading days; overlay-arm mean net excess > 0 in
   every combination (rule is parameter-free once constants are frozen).
4. WF: 5 expanding folds (ends 2024-06-30 → 2026-08-07); overlay net excess
   Sharpe > 0 every fold; ≤60% single-fold share of cumulative excess.
5. Permutation: circular block shuffle (block=10, 1000 draws, seed 7); observed
   OOS excess Sharpe > null p95.
6. DSR: positive entry in docs/data/eval_wave1_h3.json via scripts/preregister.py
   record; trials charged = 1.

PRIMARY ACCEPTANCE (declared): OOS Sharpe(overlay) − Sharpe(incumbent) ≥ +0.10
AND OOS net CAGR(overlay) > SPY AND charter bar met (CAGR and Sharpe both > SPY).
Secondary reported descriptively: maxDD delta, turnover delta.

## 5. Kill criteria

Any gate or primary-margin FAIL ⇒ honest FAIL entry; overlay is dropped, incumbent
stands. No re-fitting of σ*, window, floor, or cap after results; a different
target-vol value is a NEW prereg with changed conditions.
