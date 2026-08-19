# TA Rules Candidates

## RSI(2) with Protective Stop Loss
**Hypothesis:** Extreme short-term oversold conditions (RSI(2) < 10) in liquid large-caps indicate temporary liquidity vacuums that quickly revert to the mean (SMA(5)).
**Parameters:** Entry RSI of 10 and 5-day hold period are classic Larry Connors parameters, combined with a 2% stop-loss to protect against broader market meltdowns.
**Invalidation:** If walk-forward Sharpe falls below 0.5 or permutation passes < 60%, it implies the mean-reversion edge has degraded into a noise-following strategy.

## EMA(10/50) Cross with Regime Filter
**Hypothesis:** Short-to-medium-term momentum (EMA 10 crossing 50) correctly captures persistent trends in individual equities only when the broader regime is bullish (Close > SMA 200).
**Parameters:** 10/50 EMAs provide a balanced responsiveness to emerging trends without excessive whipsaw, while the 200 SMA is the canonical long-term trend filter.
**Invalidation:** Consistent negative returns during volatile but overall uptrending regimes, or a permutation pass rate < 60%, would indicate the crossover is too lagging.

## MACD Histogram Momentum
**Hypothesis:** Accelerating momentum, indicated by the MACD histogram turning positive and expanding for two consecutive days, precedes sustained directional price movement.
**Parameters:** Standard MACD settings (12, 26, 9) are robust baselines; requiring 2 days of expansion filters out single-day false breakouts.
**Invalidation:** If the strategy suffers from excessive whipsaw resulting in a negative Deflated Sharpe Ratio (DSR), it shows the signal lacks genuine predictive power.