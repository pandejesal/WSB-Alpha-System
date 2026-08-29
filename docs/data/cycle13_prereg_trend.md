# Pre-registration: trend
Cycle: 13
Date: 2026-08-29 19:36:54

## Claim
Gold walk-forward 10y train/6m test trend-momentum with fractional Kelly sqrt-impact gamma 0.02 + ATR exits delivers Sharpe 2.88 net vs buy-hold per 2511.08571

## Strategy Spec
```yaml
id: gold_trend_kelly
name: Gold Forecast-to-Fill Walk-Forward Kelly (paper 2511.08571)
family: trend
venue: alpaca
universe: [GLD]
description: >
  Implements 2511.08571 rolling 10y train / 6m test walk-forward on gold. Smoothed trend-momentum
  regime signal → vol-targeted fractional Kelly with sqrt-impact gamma=0.02 + ATR exits. Reported Sharpe
  2.88 net 0.7bp linear + impact, maxDD 0.52%, CAGR 43%/alpha 37% at 15% vol. Billion-dollar capacity.
indicators:
  - trend: SMA(50) / SMA(200) smoothed
  - momentum: 63d return
  - ATR: 20
  - realized_vol: 20
parameters:
  train_years: 10
  test_months: 6
  kelly_fraction: 0.5
  impact_gamma: 0.02
  atr_exit_k: 2.5
  vol_target: 0.15
  linear_cost_bps: 0.7
  warmup_days: 250
  exec_delay: 1
entry_rules:
  - rolling walk-forward: fit trend-momentum regime on 10y window, test next 6m OOS (frozen params)
  - smoothed regime = EWMA(trend + momentum); long only when regime >0
  - position = fractional Kelly * volTarget / realized_vol * sqrt-impact adjustment
exit_rules:
  - ATR stop: exit if close < entry - k*ATR; regime flip to short regime closes
position_sizing:
  - volTarget 15%, Kelly 0.5, max 100% GLD; fractional shares; $1 min
fee_model:
  commission: 0
  slippage: 0.0007
  impact: sqrt model gamma 0.02
benchmark: GLD buy-hold, same walk-forward window/fees
prereg: docs/data/cycle_prereg_gold_kelly.md

```
