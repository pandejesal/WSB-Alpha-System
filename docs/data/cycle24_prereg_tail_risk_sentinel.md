# Pre-registration: tail_risk_sentinel
Cycle: 24
Date: 2026-09-11 16:54:02
Spec-SHA256: 975c7cf564264b175189b48b3fddf89755585f6df7b66a9d828124fcd587b89e

## Claim
H9: always-invested stress rotation (tmin=1.00 by construction) — 100pct SPY calm / 100pct equal-weight duration/metals-4 (4 lowest trailing-252d-beta names among fixed sleeve [TLT,GLD,SLV,HYG,UUP], monthly month-end) under stress = (SPY<SMA200 OR trailing-60d ret<-8pct looser single-trigger), past-only shift1, T+1, tiered W5 costs, PLUS DD CAP (sleeve equal-weight trailing-60d DD>10pct -> INTO-leg 0.5x remainder SPY, still always-invested) — cuts SPY maxDD to <=25pct while holding identical-window excess>=+0.03pp (looser trigger harvests more crisis alpha; cap stops correlated sleeve drawdowns; fixes H7 cycle22 HONEST_ABANDON sharpe1.066/dd0.2851/excess-63.30pp/dsr0.7344/perm0.14 and H5 defensive-8 dd0.5214), Sharpe>=.55, OOS>=.35, DSR>=.75 (fam N=55), trips>=6, perm/boot<=.05 (Track 4 tail_risk_sentinel; fallback Track 2 DW DD<=35pct excess>=0.10)

## Strategy Spec
```yaml
id: tail_risk_sentinel_h9
name: "Tail Risk Sentinel H9 (SPY->duration/metals-4 stress rotation, looser -8% trigger + DD cap, always-invested)"
family: tail_risk_sentinel
venue: alpaca
universe: "SPY + fixed duration/metals defensive sleeve [TLT, GLD, SLV, HYG, UUP] from market_data_2019_2026/ohlcv/*.csv, daily OHLCV 2019-01-02..2026-08-07, T=1910 bars; local CSVs only"
pre_registration_ref: "docs/data/cycle24_prereg_tail_risk_sentinel.md (freeze BEFORE backtest; bytes frozen)"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "hunts/tail_risk_sentinel/20260911-h9-tailsentinel/results/eval_tail_risk_sentinel_h9.json"
status: "paper"
version: 1
signal:
  entry: "Calm: 100% SPY. Stress (past-only shift1): SPY close < SMA200 OR SPY trailing-60d return < -8% -> 100% equal-weight duration/metals-4 (4 lowest trailing-252d-beta names vs SPY among fixed sleeve [TLT, GLD, SLV, HYG, UUP], monthly month-end selection, T+1). DD CAP (past-only shift1): when the sleeve equal-weight index trailing-60d DD exceeds 10%, scale INTO-leg to 0.5x with remainder in SPY. NEVER cash (tmin=1.00 by construction)."
  exit: "Stress clears when SPY back above SMA200 AND 60d return >= -8% -> rotate back to 100% SPY next bar (T+1)"
  sizing: "100% gross always (calm SPY / stress duration/metals-4 equal-weight 1/4 each, or 0.5x capped + 0.5 SPY under cap); deleverage never, leverage never"
  caps:
    max_concurrent_positions: 4
  rebalance: "regime switches + monthly duration/metals-4 reselection, forward-filled daily"
parameters:
  sma_slow: 200
  drawdown_trigger_60d: -0.08
  beta_lookback: 252
  defensive_k: 4
  defensive_sleeve:
    - TLT
    - GLD
    - SLV
    - HYG
    - UUP
  selection: monthly_month_end
  dd_cap_trigger_60d: -0.10
  dd_cap_scale: 0.5
  exec_delay: 1
  fam_trials_N: 55
  dd_cap_choice: "(c) looser -8% single-trigger + 0.5x INTO-leg cap on sleeve 60d DD>10%"
indicators:
  - "SPY SMA200 (past-only, shift1)"
  - "SPY trailing-60d return (past-only, shift1)"
  - "Trailing-252d beta vs SPY per sleeve name (past-only, monthly)"
  - "Sleeve equal-weight index trailing-60d drawdown (past-only, shift1)"
position_sizing:
  - "Always-invested 100% gross: SPY in calm, equal-weight duration/metals-4 in stress, 0.5x cap + 0.5 SPY when sleeve itself draws down >10% over 60d"
  - "Fractional shares via Alpaca paper API"
fee_model: "tiered W5 (equities 5-7bps slippage +2.5bp commission vol-scaled, T+1)"
risk:
  live_trading_enabled: false
  paper_only: true

```
