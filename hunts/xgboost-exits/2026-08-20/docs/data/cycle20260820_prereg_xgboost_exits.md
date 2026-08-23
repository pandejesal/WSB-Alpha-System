# Pre-registration: xgboost_exits
Cycle: 20260820
Date: 2026-08-20 05:43:47

## Claim
Replacing static trailing stops or fixed-window exits on mean-reversion (e.g. RSI2) and momentum strategies with an XGBoost classifier (features: volatility regime, forward-return probability, relative strength) will improve the net Sharpe ratio by >10% and reduce maximum drawdown by >15% at an equivalent Deflated Sharpe Ratio (DSR) threshold.

## Strategy Spec
```yaml
acceptance: Edge claim pre-registered. Candidate specs parse correctly. Walk-forward
  testing passed out-of-sample (2023+). Survives permutation test (p < 0.05). DSR
  ledger entry is positive.
edge_gate_params:
  max_p_value: 0.05
  min_dsr: 1.5
  walk_forward_oos_sharpe_min: 1.0
family: xgboost_exits
hypothesis: 'Replacing static trailing stops or fixed-window exits on mean-reversion
  (e.g. RSI2) and momentum strategies with an XGBoost classifier (features: volatility
  regime, forward-return probability, relative strength) will improve the net Sharpe
  ratio by >10% and reduce maximum drawdown by >15% at an equivalent Deflated Sharpe
  Ratio (DSR) threshold.'
lookback_constraints: 2019-2026 daily OHLCV
universe: broad US large-cap liquid equities (~100 names from yfinance, price > $1)
  or SPY alone depending on base strategy

```
