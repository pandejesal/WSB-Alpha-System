# Wave 3 / H3 — Turn-of-Month Concentration on the Incumbent Core
# (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-25. Status: LOCKED before any in-sample run. LIVE TRADING
DISABLED — paper only, fail-closed. FREE TIER ONLY (local OHLCV panel).

## 1. Hypothesis

Confining the incumbent us_momentum_top5 portfolio's INVESTED TIME to the classic
turn-of-month window — long at the close of the LAST trading day of each month,
flat after the close of the 4th trading day of the next month — beats SPY
buy-and-hold net-of-cost on BOTH OOS net CAGR and Sharpe and passes all six gates.

Mechanism family: turn-of-month liquidity/salary-flow seasonality
(Lakonishok-Smidt 1988; Ariel 1987). Execution-TIMING claim: signals, sizing,
universe identical to incumbent; only the invested calendar changes.

## 2. Prior art + changed conditions

| Prior attempt | Outcome | Source |
|---|---|---|
| SMA200 regime gate (spy_sma200) | registry legacy; price-regime gating closed for MEGA-CAP lane | strategies/registry.json; §4 v6 |
| Absolute-momentum cash gate inside Universe A | FAIL all gates (W2-H3) | eval_wave2_h3.json |
| Deterministic SIZING overlays | lane CLOSED wave-2 | eval_wave2_h{1,2}.json |

Changed conditions: NO gate/regime/sizing mechanism whatsoever — a fixed
CALENDAR window (-1/+4 trading days around month start), applied to unchanged
incumbent signals. Calendar timing is orthogonal to every closed family (none
conditioned on month-turn dates).

## 3. Frozen specification

- Signals: incumbent monthly top-5 scores computed exactly as baseline engine.
- Invested windows: from close of final TD of month M-1 to close of 4th TD of
  month M.
- At each window entry: buy current top-5 equal-weight (exec_delay 1 bar);
  NO intra-window drift trades, NO rebalance; exit full at window end close
  (T+1 exec on entry leg; window-end close exit executes that close directly).
- Flat otherwise; cash yield 0%; costs 5bps/side per entry/exit (~24 sides/yr).
- Benchmark SPY same-engine B&H over the SAME evaluated calendar, net;
  IS/OOS split inherited (2023-12-31 / 2024-01-01); G4 endpoints inherited.

## 4. Six gates

Verbatim wave1_h1 §4 machinery imports from scripts/wave1_h3_test.py. Positive
DSR entry in docs/data/eval_wave3_h3.json. Trials charged: 1.

## 5. Kill criteria

Standard five (IS p>0.05; WF fail; permutation miss; param bloat; post-hoc
changes). Declared structural risk (disclosed, not a kill): part-time exposure
handicaps the CAGR leg vs SPY B&H; gates decide honestly.
