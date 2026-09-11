# Pre-registration: tail_risk_sentinel
Cycle: 17
Date: 2026-09-11 13:41:03
Spec-SHA256: ad61fd1ff5fe8abe69927904cee4051bbdd1ba0f1a9fcfb03f14008c3d73fefa

## Claim
VIX30<=24 + ATR2.5x stop + vol cap 0.20 as SPY long/flat tail hedge cuts SPY maxDD to <=25% while preserving identical-window excess >= +0.03pp; interior grid point (30,24,2.5,0.20); priors v1-v3 failed excess gate

## Strategy Spec
```yaml
id: tail_risk_sentinel_v4
name: "Tail Risk Sentinel v4 (VIX30/24 ATR2.5 vol0.20)"
family: tail_risk_sentinel
venue: alpaca
universe: "SPY + 100-stock liquid large-cap panel with VIX proxy (market_data_2019_2026/ohlcv/^VIX.csv)"
pre_registration_ref: "hunts/tail_risk_sentinel/20260911-h1-tail-sentinel/docs/data/H1_tail_risk_sentinel_v4_prereg.md"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "hunts/tail_risk_sentinel/20260911-h1-tail-sentinel/results/eval_tail_risk_sentinel_v4.json"
status: "paper"
version: 1
signal:
  entry: "VIX30 <=24 and SPY 20d vol <=0.20 then long SPY else cash"
  exit: "ATR 2.5x stop: if daily TR >2.5*ATR20 then flat next bar; re-enter when gate clears"
  sizing: "100% SPY vs cash"
  caps:
    max_concurrent_positions: 1
  rebalance: "daily"
parameters:
  vix_window: 30
  vix_entry: 24
  atr_stop: 2.5
  vol_regime_cap: 0.20
  exec_delay: 1
indicators:
  - "VIX 30-day rolling mean (past-only, shift1)"
  - "SPY 20d realized vol annualized cap 0.20 (past-only, shift1)"
  - "ATR20 true-range proxy (high-low/close, past-only, shift1)"

```
