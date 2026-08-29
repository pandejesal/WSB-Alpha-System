# Pre-registration: rotation
Cycle: 12
Date: 2026-08-29 19:36:42

## Claim
Continuous softplus+tanh+EWMA macro score allocates G vs D (growth vs defensive) and beats binary FRED RISK_ON on risk-adjusted and drawdown per 2605.20636

## Strategy Spec
```yaml
id: continuous_growth_defensive
name: Continuous Growth-Defensive Timing (paper 2605.20636)
family: rotation
venue: alpaca
universe: [QQQ, VUG, XLK, VTV, XLP, XLU, TLT]
description: >
  Implements 2605.20636 continuous timing vs binary FRED RISK_ON. Signal = softplus(rate relief) +
  softplus(SPY drawdown depth) + softplus(high-VIX relief) - softplus(crowding) → tanh → EWMA(10).
  Fama-French G-D is style portfolio (beta 0.273, HML -0.552, mom 0.117, alpha 1.95% t0.81).
indicators:
  - fedFunds_change
  - spy_drawdown
  - vix
  - crowding
parameters:
  softplus_k: 1.0
  tanh_scale: 1.5
  ewma_span: 10
  rebalance: daily
  drift_rebal: 0.03
  exec_delay: 1
entry_rules:
  - daily compute macro score: softplus(fedFunds Δ) + softplus(SPY DD) + softplus(VIX) - softplus(crowding)
  - map score via tanh(scale*score) to [-1,1]; EWMA span 10 → smoothed score
  - w_G = (1 + tanh_smoothed)/2, w_D = 1 - w_G; allocate G=[QQQ,VUG,XLK] equal-weight within G, D equal-weight within D
exit_rules:
  - continuous weights; drift rebalance >3%
position_sizing:
  - 100% gross, long-only; fractional shares; $1 min
fee_model:
  commission: 0
  slippage: 0.0005
benchmark: fred_risk_on_gate (binary) and SPY, same window/fees
prereg: docs/data/cycle_prereg_growth_defensive.md

```
