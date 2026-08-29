# Pre-registration: factor_momentum
Cycle: 7
Date: 2026-08-25 10:59:32

## Claim
Factor Momentum Top-3: Monthly long top-3 by trailing 12-month factor-momentum composite (MOM 12-1, VAL 1/PE, QUA ROE stability) on 100-stock panel equal-weight beats SPY OOS net Sharpe and CAGR and passes bootstrap p<=0.05 CPCV K=6 walk-forward permutation DSR. Gupta-Kelly TSFM 0.84 basis.

## Strategy Spec
```yaml
id: factor_momentum_top3
name: Factor Momentum Top-3 (Gupta-Kelly style, long-only)
family: factor_momentum
venue: alpaca
universe: 100-stock liquid large-cap US panel (same as us_momentum_top5, excludes SPY/QQQ/AGG/BND/SHY/GLD/VTI/IWM)
pre_registration_ref: "docs/data/cycle6_prereg_factor_momentum.md"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "docs/data/eval_factor_momentum_top3.json"
signal:
  entry: >
    Monthly factor-momentum rotation. Compute 3 factor returns: (1) MOM 12-1
    (126d skip 21d), (2) VAL inverse P/E z-rank, (3) QUA ROE/stability z-rank.
    Rank each factor, compute stock composite = avg of 3 z-scores. Select top 3
    by trailing 12-month rolling mean of monthly factor returns (factor momentum).
    Long only top 3, equal weight.
  exit: >
    Dropped at next monthly rebalance if falls out of top 3. Drift-band (>5%)
    only intra-month.
  sizing: "Equal weight 1/3 per position; fractional shares on Alpaca"
  caps:
    max_concurrent_positions: 3
  rebalance: "monthly, last trading bar of month"
parameters:
  mom_lookback_days: 252
  mom_skip_days: 21
  mom_window_days: 126
  val_metric: "inverse_pe"
  quality_metric: "roe_stability"
  factor_mom_lookback: 12
  factor_mom_skip: 1
  top_n: 3
  rebalance: "monthly"
  exec_delay: 1
  drift_rebal: 0.05
  warmup_days: 340
indicators:
  - "momentum_12_1: 12-month return skipping last 21 days (126d window)"
  - "value_hml: inverse P/E cross-sectional z-rank"
  - "quality_qm: ROE / std(quarterly ROE, 8Q) z-rank"
  - "factor_momentum_composite: trailing 12-month mean of monthly factor z-scores"
entry_rules:
  - "at each month-end, compute factor returns for MOM, VAL, QUA across panel"
  - "rank factors by trailing 12-month factor momentum (skip 1 month)"
  - "hold top 3 by factor-momentum composite, equal weight 1/3"
exit_rules:
  - "dropped when falls out of top-3 at next month-end"
  - "drift-based rebalance only (>5%)"
position_sizing:
  - "$100 account: 3 x ~$33.33 fractional shares"
  - "min order $1; no margin, no PDT"
  - "equal weight at each rebalance"
fee_model:
  - commission: "$0 (Alpaca)"
  - slippage: "0.05% per side"
  - settlement: "T+1 cash; min $1"
benchmark_result:
  benchmark: "SPY buy-and-hold, same engine, same window"
  full: "PENDING"
  oos_2023plus: "PENDING"
  expected_range: "Gupta & Kelly 2019 TSFM Sharpe 0.84 (1M) / 0.70 (12M); long-only 3-name expected 0.6-1.0 IS, 0.3-0.7 OOS after decay"
feasibility_at_100:
  - "3 x ~$33 fractional, $0 commissions, monthly rebalance"
  - "cash account avoids PDT"
risks:
  - "factor crowding, 3-name concentration variance, survivorship bias, fundamentals staleness, no short leg"
version: 1
status: "hunting"

```
