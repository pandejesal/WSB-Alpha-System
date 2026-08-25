# Wave 3 / H1 — 52-Week-High Proximity Cross-Sectional Core
# (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-25. Status: LOCKED before any in-sample run. LIVE TRADING
DISABLED — paper only, fail-closed. FREE TIER ONLY (local OHLCV panel).

## 1. Hypothesis

A monthly-rebalanced top-5 portfolio ranked by PROXIMITY TO THE 52-WEEK HIGH
(close_t / rolling-max(close, 252 trading bars), descending) on the snapshot∩local
panel beats SPY buy-and-hold net-of-cost on BOTH OOS net CAGR and Sharpe (identical
engine/window/fees) and passes all six edge gates.

Mechanism family: anchoring/friction underreaction (George-Hwang 2004). NEW signal
family in this repo — never tested in any cycle/round/wave.

## 2. Prior art + changed conditions

| Prior attempt | Outcome | Source |
|---|---|---|
| RSI(2)-entry family | saturated, 0 pass | hunt-lessons.md |
| TA-rule variants (EMA/MACD/RSI2-stop) | FAIL | round1_consolidation.json |
| Confluence/trend/surge stack | CLOSED 2026-08-14 | improvement_regime_conclusion.md |

Changed conditions: 52wH proximity is a LEVEL-vs-SALIENT-ANCHOR signal, not a
rate-of-change indicator (RSI/MACD/EMA measure change; 52wH measures distance to a
salient price anchor). None of the closed families measured anchor proximity.

## 3. Frozen specification

- Universe: snapshot∩local−SPY panel VERBATIM (same set as wave-1/2 engines;
  loaded via load_snapshot_tickers()).
- Signal: prox_t = close_ffill_t / max(close_ffill over previous 252 bars inclusive);
  requires >= 252 non-NaN history bars else excluded that month (counted).
- Rebalance: month-end mask, top-5 descending prox, exec_delay 1 bar, drift band
  0.05, warmup 340 — all byte-identical to incumbent engine constants.
- Costs: 5bps/side entry+exit; benchmark SPY same-engine B&H, net.
- Window: full local calendar through frozen G4 endpoint (2026-08-07); IS/OOS split
  IS_END 2023-12-31 / OOS_START 2024-01-01 (inherited constants).

## 4. Six gates (verbatim machinery)

Identical to wave1_h1 §4: block bootstrap IS p<=0.05; CPCV K=6 embargo 10d
all-positive; WF 5 expanding half-year folds all-positive with share cap 0.60;
circular-block permutation (block=10, 1000 draws, seed 7) p95 survival on OOS excess
Sharpe; positive DSR ledger entry in docs/data/eval_wave3_h1.json. Trials charged: 1.

## 5. Kill criteria

p > 0.05 IS; WF fail; permutation miss; parameter bloat; any post-hoc universe/
window/signal change. One frozen configuration only — zero search.
