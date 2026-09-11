# Pre-registration: tail_risk_sentinel
Cycle: 22
Date: 2026-09-11 16:12:00
Spec-SHA256: 84fc26e7744c93c2a613d353b37d56ea03ea61e320a894432a1269af1e72699d

## Claim
H7: always-invested stress rotation (tmin=1.00 by construction) — 100pct SPY calm / 100pct equal-weight duration/metals-4 (4 lowest trailing-252d-beta names among fixed sleeve [TLT,GLD,SLV,HYG,UUP], monthly month-end, excl equities) under stress = (SPY<SMA200 OR trailing-60d ret<-10pct), past-only shift1, T+1, tiered W5 costs — cuts SPY maxDD to <=25pct while holding identical-window excess>=+0.03pp (harder non-equity INTO-leg fixes H5 defensive-8 52pct DD failure), Sharpe>=.55, OOS>=.35, DSR>=.75 (fam N=54), trips>=6, perm/boot<=.05 (Track 4 tail_risk_sentinel; fallback Track 2 DW DD<=35pct excess>=0.10)

## Strategy Spec
```yaml
id: tail_risk_sentinel_h7
name: "Tail Risk Sentinel H7 (SPY->duration/metals-4 stress rotation, always-invested)"
family: tail_risk_sentinel
venue: alpaca
universe: "SPY + fixed duration/metals defensive sleeve [TLT, GLD, SLV, HYG, UUP] from market_data_2019_2026/ohlcv/*.csv, daily OHLCV 2019-01-02..2026-08-07, T=1910 bars; local CSVs only"
pre_registration_ref: "docs/data/cycle22_prereg_tail_risk_sentinel.md (freeze BEFORE backtest; bytes frozen)"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "hunts/tail_risk_sentinel/20260911-h7-tailsentinel/results/eval_tail_risk_sentinel_h7.json"
status: "paper"
version: 1
signal:
  entry: "Calm: 100% SPY. Stress (past-only shift1): SPY close < SMA200 OR SPY trailing-60d return < -10% -> 100% equal-weight duration/metals-4 (4 lowest trailing-252d-beta names vs SPY among fixed sleeve [TLT, GLD, SLV, HYG, UUP], monthly month-end selection, T+1). NEVER cash (tmin=1.00 by construction)."
  exit: "Stress clears when SPY back above SMA200 AND 60d return >= -10% -> rotate back to 100% SPY next bar (T+1)"
  sizing: "100% gross always (calm SPY / stress duration/metals-4 equal-weight 1/4 each); deleverage never, leverage never"
  caps:
    max_concurrent_positions: 4
  rebalance: "regime switches + monthly duration/metals-4 reselection, forward-filled daily"
parameters:
  sma_slow: 200
  drawdown_trigger_60d: -0.10
  beta_lookback: 252
  defensive_k: 4
  defensive_sleeve:
    - TLT
    - GLD
    - SLV
    - HYG
    - UUP
  selection: monthly_month_end
  exec_delay: 1
  fam_trials_N: 54
  dd_cap_choice: "(a) duration/metals-only INTO-leg"
indicators:
  - "SPY SMA200 (past-only, shift1)"
  - "SPY trailing-60d return (past-only, shift1)"
  - "Trailing-252d beta vs SPY per sleeve name (past-only, monthly)"
position_sizing:
  - "Always-invested 100% gross: SPY in calm, equal-weight duration/metals-4 in stress"
  - "Fractional shares via Alpaca paper API"
fee_model: "tiered W5 (equities 5-7bps slippage +2.5bp commission vol-scaled, T+1)"
risk:
  live_trading_enabled: false
  paper_only: true

```
