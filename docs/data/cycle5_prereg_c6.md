# Cycle 5 — Claim C6: Regime-Gated Multi-Asset Trend Following (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-16. Status: LOCKED. No backtest has been run against
this document; every number, parameter and gate below is fixed before any
engine execution. Any change requires a pre-registered delta written
before the affected run (Q28 discipline, unchanged).

## 1. Claim (user directive, /grilling round 2 Q8 + round 3 Q11)

C2's exact mechanism — SMA200 long/cash time-series trend on 12 instruments,
weekly, equal weight — PLUS a portfolio-level macro regime gate: positions
are allowed only when the FRED-derived regime is RISK_ON; otherwise the
portfolio holds all cash. Hypothesis (pre-registered): the trend-following
signal demonstrated OOS performance pre-null in Cycle 2 (Sharpe 1.59 before
the null gate) but showed regime fragility (C3 low-vol claim DOA on train;
C2 2024 OOS year weak at +0.09%/wk). Gating exposure to RISK_ON periods
removes the non-RISK_ON drawdown-heavy segments and should improve both the
null-relative OOS mean and the year-median consistency. Fail-closed by
design: gate gaps default to cash, never to exposure.

## 2. Clarification (declared pre-run, 2026-08-16)

Earlier session wording "dual momentum (SMA200 + 12-1 momentum)" was a
descriptive error: the actual C2 mechanism (engine = spec,
scripts/cycle3_multiasset_engine.py, cycle3_prereg_multiasset.md) is
SMA200 long/cash ONLY — there is no MOM12-1 component in C2. This document
implements the engine's exact mechanism. No feature is added or removed
relative to C2.

## 3. Appendix A — FROZEN SPECIFICATION

### A.1 Universe and data

- Instruments (fixed, 12): SPY QQQ IWM EFA EEM TLT GLD SLV HYG UUP
  BTC-USD ETH-USD. Source: market_data_2019_2026/ohlcv/<SYM>.csv (adjusted
  closes; window 2019-01-01..2026-08-07; zero gaps — C2 Appendix A facts).
- No snapshot concept: 12 fixed instruments, no survivorship.

### A.2 Signal and portfolio

- Per instrument: price > SMA200 (rolling 200-day mean of adjusted close,
  min_periods=200, each instrument's own daily calendar) -> LONG; else
  CASH. Weeks before the 200th bar: no SMA -> CASH (fail-closed).
- Rebalance: last trading bar of each ISO week (SPY calendar); crypto
  reindexed to the same Fridays (C2 convention).
- Portfolio: equal weight across LONG instruments at each rebalance; weeks
  with k=0 instruments LONG contribute 0.0 return.

### A.3 Regime gate (portfolio-level, NEW — the only mechanism change vs C2)

- Source: data/cache/fred_historical_regimes.json — daily regime labels
  from T10Y2Y and T10YIE per the classification in
  src/risk/fred_macro_provider.py (RISK_ON / RISK_OFF / STAGFLATION /
  NEUTRAL; RISK_ON = spread >= 0 and inflation < 2.5).
- Rule: at each rebalance date d, regime(d) = last label with date <= d
  (as-of lookup, no lookahead). If regime(d) == "RISK_ON" -> weights as
  computed in A.2; else -> all cash (k=0 week, 0.0 return).
- Missing label (no FRED date <= d): fail-closed -> all cash. Cache
  coverage fact (checked 2026-08-16): 5909 daily labels, 2003-01-02 ..
  2026-08-14; the full claim window is covered. Refresh at 2026-09-17 /
  end-2027 uses the then-current cache (declared).
- The gate is a portfolio-level exposure switch. It never inverts signals,
  never re-weights instruments, and is never tuned.

### A.4 Costs

- C2 tiered: 5bps/side equity/index (SPY QQQ IWM EFA EEM TLT GLD SLV HYG
  UUP), 10bps/side crypto (BTC-USD ETH-USD); charged at each rebalance on
  weight change vs prior rebalance (start from cash); no final liquidation
  cost (no return week after last date).

### A.5 Train / OOS split

- Train: 2019-01-01 .. 2023-12-31. OOS: 2024-01-01 .. 2026-08-07 (2.6
  years; 3 complete years when 2026 ends; 2027 not computable -> earliest
  possible pass end-2027, pre-registered structural constraint).

### A.6 Gates / bar (SAME frozen bar as all prior claims)

| Gate | Pass condition |
|------|----------------|
| sign_gate_train | strategy mean weekly net return on train > 0 (wrong sign = DOA, no tuning) |
| oos_median_3of4_years | OOS median > 0 in >= 3 of the 4 COMPLETE OOS years {2024, 2025, 2026, 2027} |
| oos_sharpe_ge_1 | annualized Sharpe (x sqrt(52)) >= 1.0 |
| oos_maxdd_le_25 | max drawdown >= -25% |
| oos_cagr_ge_15 | net CAGR >= 15% |
| null_p95 | OOS mean weekly net return > p95 of 1000x block-shuffle null (permutation of the full weekly net series, OOS-mean statistic, RNG seed 7) |

### A.7 Kill rules (Q28, unchanged)

- Any change to this document after the first backtest = disqualification
  unless written as a delta BEFORE the affected run.
- Wrong train sign = dead on arrival. No tuning, no re-scoring, no
  re-ranking after seeing results. Losers reopenable only via a NEW
  pre-registered delta.

## 4. Outputs

- Engine: scripts/cycle5_c6_engine.py (this pre-reg is the contract).
- docs/data/cycle5_c6_evaluation.json (gate verdicts + bar_pass) and
  docs/data/cycle5_c6_results.json (weekly net returns, train/oos weeks,
  data-handling log).
- Refresh schedule: 2026-09-17 interim, end-2027 final (same as C4R).
- Program done criterion (R8): C6 passes the full frozen bar end-2027 AND
  Track P process certified; C4R is measurement-only (cycle5_prereg_c4r.md).