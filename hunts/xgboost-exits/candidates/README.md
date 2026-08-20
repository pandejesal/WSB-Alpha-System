# XGBoost Exits - Candidates

This directory contains candidate specifications for meta-strategies applying XGBoost-based exits to existing baseline signals (Momentum and Mean Reversion).

## Candidate 1: XGBoost Exit on Momentum (xgboost_exits_momentum_v1)
* **Model Design:** Classifier targeting forward 5-day return > 0. Features include SPY SMA200 distance (regime), asset 14-day ATR (volatility), and 5-day RSI. Walk-forward trained on expanding window.
* **Why it should beat baseline:** Baseline momentum uses a static monthly rank-exit. XGBoost can preemptively exit positions when local volatility spikes or mean-reversion risk is high before the month-end check.
* **What invalidates it:** Overfitting to the 2020-2021 bull run volatility patterns. Fails if trading costs from early exits exceed the drawdown savings.

## Candidate 2: XGBoost Exit on RSI2 (xgboost_exits_rsi2_v1)
* **Model Design:** Classifier targeting 2-day forward return > 0. Features: VIX level, SPY 2-day RSI, and current asset intraday momentum. Walk-forward train/val split (80/20 per year).
* **Why it should beat baseline:** Standard RSI2 exits rigidly on a simple SMA crossover. XGBoost adds regime awareness to hold winners longer in strong trends or cut losers faster in bear regimes.
* **What invalidates it:** Model degradation in unseen regimes. High false-positive exit rate destroying the core mean-reversion edge.

## Candidate 3: XGBoost Exit on Momentum (Alternative Features) (xgboost_exits_momentum_v2)
* **Model Design:** Classifier targeting forward 5-day return > 0. Features: sector relative strength, 5-day volume trend, and 60-day beta. Walk-forward trained on expanding window.
* **Why it should beat baseline:** Exploits cross-sectional flow and beta regimes to exit momentum names that are losing sector support or experiencing volume exhaustion.
* **What invalidates it:** Feature correlation with base momentum ranking negating the exit edge. Sector definitions failing to capture actual flow dynamics.
