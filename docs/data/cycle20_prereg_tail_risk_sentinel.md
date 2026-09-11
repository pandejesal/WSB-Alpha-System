# Pre-registration: tail_risk_sentinel
Cycle: 20
Date: 2026-09-11 15:22:50
Spec-SHA256: 026de63c1e02aa5b36b3fc467ed862e330ad0d932a2b52b604e34da373421a24

## Claim
H5: always-invested stress rotation (tmin=1.00 by construction) — 100pct SPY calm / 100pct equal-weight defensive-8 (8 lowest trailing-252d-beta panel names, monthly month-end, excl SPY/VIX/BTC/ETH) under stress = (SPY<SMA200 OR trailing-60d ret<-10pct), past-only shift1, T+1, tiered W5 costs — cuts SPY maxDD to <=25pct while holding identical-window excess>=+0.03pp (zero calm-drag vs H1 cash-park -0.47..-166.8pp and H3 ladder -127.96pp), Sharpe>=.55, OOS>=.35, DSR>=.75 (fam N=53), trips>=6, perm/boot<=.05 (Track 4 tail_risk_sentinel; fallback Track 2 DW DD<=35pct excess>=0.10)

## Strategy Spec
```yaml
id: tail_risk_sentinel_h5
name: "Tail Risk Sentinel H5 (SPY->defensive8 stress rotation, always-invested)"
family: tail_risk_sentinel
venue: alpaca
universe: "SPY + broad local panel market_data_2019_2026/ohlcv/*.csv (441 full-history names), daily OHLCV 2019-01-02..2026-08-07, T=1910 bars; local CSVs only"
pre_registration_ref: "docs/data/cycle20_prereg_tail_risk_sentinel.md (freeze BEFORE backtest; bytes frozen)"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "hunts/tail_risk_sentinel/20260911-h5-tailsentinel/results/eval_tail_risk_sentinel_h5.json"
status: "paper"
version: 1
signal:
  entry: "Calm: 100% SPY. Stress (past-only shift1): SPY close < SMA200 OR SPY trailing-60d return < -10% -> 100% equal-weight defensive-8 (8 lowest trailing-252d-beta names vs SPY, monthly month-end selection, T+1). NEVER cash (tmin=1.00 by construction)."
  exit: "Stress clears when SPY back above SMA200 AND 60d return >= -10% -> rotate back to 100% SPY next bar (T+1)"
  sizing: "100% gross always (calm SPY / stress defensive-8 equal-weight 1/8 each); deleverage never, leverage never"
  caps:
    max_concurrent_positions: 8
  rebalance: "regime switches + monthly defensive-8 reselection, forward-filled daily"
parameters:
  sma_slow: 200
  drawdown_trigger_60d: -0.10
  beta_lookback: 252
  defensive_k: 8
  selection: monthly_month_end
  exec_delay: 1
  fam_trials_N: 53
indicators:
  - "SPY SMA200 (past-only, shift1)"
  - "SPY trailing-60d return (past-only, shift1)"
  - "Trailing-252d beta vs SPY per panel name (past-only, monthly)"
position_sizing:
  - "Always-invested 100% gross: SPY in calm, equal-weight defensive-8 in stress"
  - "Fractional shares via Alpaca paper API"
fee_model: "tiered W5 (equities 5-7bps slippage +2.5bp commission vol-scaled, T+1)"

```
