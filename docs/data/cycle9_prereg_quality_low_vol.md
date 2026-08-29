# Pre-registration: quality_low_vol
Cycle: 9
Date: 2026-08-25 10:59:34

## Claim
Quality LowVol Top-10: Two-step pipeline quality filter D/E<2 OPM>0 FCF>0 then rank by rv20 bottom 10 lowest-vol equal-weight monthly beats SPY OOS net Sharpe CAGR and passes bootstrap CPCV WF permutation DSR. AQR QMJ+BAB basis.

## Strategy Spec
```yaml
id: quality_lowvol_top10
name: US Quality + Low-Volatility Hybrid Top-10
family: quality_low_vol
venue: alpaca
universe: "100-stock liquid large-cap panel (same as us_momentum_top5)"
pre_registration_ref: "docs/data/cycle1_prereg_quality_lowvol.md"
gates_passed: "0/5"
verdict: "PENDING_EVAL"
eval_records: "docs/data/eval_quality_lowvol.json"
signal:
  entry: >
    Two-step pipeline: (1) Symbolic safety pre-filter: Debt/Equity <2.0,
    Operating Margin >0, FCF >0. (2) Rank survivors by 20-day realized vol
    (std log-returns * sqrt252); hold bottom 10 lowest-vol names. Equal weight 1/10.
  exit: >
    At each month-end: drop names falling out of bottom-10 vol rank or failing
    quality re-screen. No intra-month exits except drift-band (>5%).
  sizing: >
    Equal weight 1/10, full investment, fractional shares.
  caps:
    max_concurrent_positions: 10
parameters:
  quality_filter:
    debt_equity_max: 2.0
    operating_margin_min: 0.0
    fcf_positive: true
  vol_lookback_days: 20
  top_n: 10
  rebalance: "monthly (last trading bar of month)"
  exec_delay: 1
  drift_rebal: 0.05
  warmup_days: 340
indicators:
  - "rv20: 20-day realized vol (std log-returns * sqrt252)"
  - "debt_equity: Total Debt / Total Equity (latest quarterly)"
  - "operating_margin: Operating Income / Revenue (trailing 4Q)"
  - "fcf: Free Cash Flow = Operating CF - CapEx (trailing 4Q)"
entry_rules:
  - "At each month-end: apply quality filter to 100-stock panel"
  - "Reject any name where D/E >=2.0, OPM <=0, or FCF <=0"
  - "From survivors, rank by trailing 20-day realized vol ascending"
  - "Hold bottom 10 lowest-vol names; equal weight 1/10"
exit_rules:
  - "Drop at next month-end if falls below bottom-10 vol rank"
  - "Drop immediately if fails D/E, OPM, or FCF re-screen"
  - "Drift-based rebalance only (>5%)"
position_sizing:
  - "$100 account: 10 x ~$10 equal-weight; fractional shares"
  - "min order $1; no margin, no PDT"
fee_model:
  - commission: "$0 (Alpaca)"
  - slippage: "0.05% per side"
  - settlement: "T+1 cash; min $1"
benchmark_result:
  benchmark: "SPY buy-and-hold"
  full: "TBD - pending edge gate"
  oos_2023plus: "TBD"
feasibility_at_100:
  - "10 x ~$10 fully invested; fractional shares"
  - "Monthly rebalance ~2 rebalances/mo x 10 orders; fee drag ~$0"
risks:
  - "Quality trap, low-vol reversal gap, factor crowding, data staleness, survivorship bias, 10-name concentration"
version: 1
status: "pending_hunt"

```
