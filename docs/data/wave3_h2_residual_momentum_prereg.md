# Wave 3 / H2 — Residual (Market-Model) Momentum Core
# (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-25. Status: LOCKED before any in-sample run. LIVE TRADING
DISABLED — paper only, fail-closed. FREE TIER ONLY (local OHLCV panel).

## 1. Hypothesis

A monthly top-5 core ranked by RESIDUAL MOMENTUM — trailing 12-1 idiosyncratic
return from a per-name market-model regression on SPY (alpha + beta-residualized
cumulative return) — beats SPY buy-and-hold net-of-cost on BOTH OOS net CAGR and
Sharpe and passes all six gates.

Mechanism family: firm-specific information underreaction (Blitz-Huij-Martens
2011). NEW in this repo.

## 2. Prior art + changed conditions

| Prior attempt | Outcome | Source |
|---|---|---|
| Incumbent raw-price 12-1 momentum top5 | canonical incumbent | strategies/us_momentum_top5.yaml |
| ML on entries / overlays | FAIL | cycle3_ml_evaluation.json; topic07 |
| Mega-cap scoping of momentum core | lane CLOSED wave-1/2 | eval_wave1_h1.json; §4 v5 |

Changed conditions: ranking signal is the REGRESSION RESIDUAL component of the
same 12-1 window (market co-movement stripped via per-name OLS beta on SPY), not
raw price momentum and not a universe scoping or sizing change. Single-factor
market model computed from LOCAL panel only — no external factor data.

## 3. Frozen specification

- Estimation: per name, OLS of daily returns on SPY daily returns over bars
  [t-252, t-21] (12-1 window); requires >= 180 valid paired observations in-window
  else name excluded that month (counted). Signal = sum of residuals over the
  window (= residualized cumulative return).
- Ranking/rebalance/costs/benchmark/window: byte-identical to H1 §3 (month-end,
  top-5 desc, exec_delay 1, drift 0.05, warmup 340, 5bps/side, SPY net,
  IS/OOS inherited).

## 4. Six gates

Verbatim wave1_h1 §4 machinery (imports from scripts/wave1_h3_test.py). Positive
DSR entry in docs/data/eval_wave3_h2.json. Trials charged: 1.

## 5. Kill criteria

Standard five (p>0.05 IS; WF fail; permutation miss; param bloat; post-hoc
changes). Zero search: one regression spec, one window, no variants.
