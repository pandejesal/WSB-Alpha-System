# Pre-registration: trend
Cycle: 12
Date: 2026-08-29 19:36:41

## Claim
Large-tick (tick/ATR20 top 50% rank) futures/equities exhibit positive 5-20d trend following alpha; small-tick do not — microstructural feedback loop per 2607.01550

## Strategy Spec
```yaml
id: cta_tick_filtered
name: CTA Tick-Size Filtered Trend (paper 2607.01550)
family: trend
venue: alpaca
universe: sp500_481_frozen
description: >
  Implements 2607.01550 microstructural finding: short-term trend collapsed since 2009 only on small-tick
  futures, large-tick intact. Discriminant is volatility-normalised tick size (tick / ATR20). Strategy trades
  only large-tick regime (top 50% rank) with SMA20> SMA50 trend, volTarget 15%. Fixes C2 SMA200 null failure.
indicators:
  - ATR: 20
  - tickProxy: tick / ATR20 (tick=0.01 for equities)
  - SMA: [20, 50]
parameters:
  atr_period: 20
  tick: 0.01
  tick_rank_threshold: 0.5
  sma_fast: 20
  sma_slow: 50
  vol_target: 0.15
  atr_stop_k: 2.0
  warmup_days: 60
  rebalance: daily
  exec_delay: 1
entry_rules:
  - compute tickProxy = 0.01 / ATR20 for each name; rank cross-sectionally daily
  - large_tick = rank > 0.5
  - trend = SMA20 > SMA50
  - enter long only if large_tick and trend on close; equal-weight filtered names (max 10)
exit_rules:
  - exit when SMA20 < SMA50 or tick rank falls below 0.5 or ATR stop hit (close < entry - 2*ATR)
position_sizing:
  - volTarget 15% annualized per name, fractional Kelly overlay 0.3 cap if used
  - max_k: 10
  - min order notional $1; fractional shares
fee_model:
  commission: 0
  slippage: 0.0005
  settlement: T+1
benchmark: spy_sma200 (unfiltered) and SPY buy-hold, same engine/window
prereg: docs/data/cycle_prereg_cta_tick_filtered.md

```
