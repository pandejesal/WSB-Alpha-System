# Comprehensive Bias & Risk Analysis Report

This document details how the WSB-Alpha-System identifies, mitigates, and handles critical quantitative trading biases and risks. The architecture has been explicitly engineered to counteract these common pitfalls.

## 1. Overfitting (Curve Fitting)
**Risk:** Tuning a model too closely to historical data, leading to poor live performance.
**Mitigation:** The system uses Combinatorial Purged Cross-Validation (CPCV) and Walk-Forward Optimization (WFO) in `src/backtest/validators/statistical.py`. Strategies are evaluated on out-of-sample data. The fitness scorer in `darwin_engine.py` penalizes strategies where Out-of-Sample Sharpe drops significantly compared to In-Sample Sharpe, identifying them as `likely_overfit: true`.

## 2. Look-Ahead Bias
**Risk:** Using information in the backtest that would not have been available at the time of the trade.
**Mitigation:** The backtesting engines (`VectorBTEngine` and `NautilusEngine`) strictly enforce a **T+1 Execution Rule**. Signals generated at the close of day $T$ can only execute at the open or close of day $T+1$, ensuring zero future data leakage.

## 3. Survivorship Bias
**Risk:** Only backtesting on assets that exist today, ignoring companies that went bankrupt or were delisted.
**Mitigation:**
1. The historical data universe pulls point-in-time data and handles missing symbols gracefully.
2. The embedded DuckDB cache (`src/data/cache_engine.py`) explicitly incorporates **delisting detection** by flagging tickers whose data ends >30 days early, forcing the system to account for them.

## 4. Data-Snooping Bias
**Risk:** Testing thousands of rules on the same dataset until one works by pure luck.
**Mitigation:** Handled via **White's Reality Check (Bootstrap Reality Check)** and **Hansen's Superior Predictive Ability (SPA) Test** (implemented via `arch.bootstrap.StationaryBootstrap`). The system adjusts p-values for multiple comparisons, requiring a much higher standard of statistical significance to graduate a strategy.

## 5. Ignoring Transaction Costs
**Risk:** Assuming zero friction in trading, turning a theoretical winner into a live loser.
**Mitigation:** Both backtesters enforce strict fees and slippage models:
- Commission: Modeled at Bybit 0.04% base or Alpaca $0 structure.
- SEC/TAF regulatory fees are approximated on sell-side transactions.
- Slippage is dynamically modeled based on volatility: `0.05% + 0.1 * 20-day ATR%`.

## 6. Poor Data Quality
**Risk:** Missing data, stock splits, or incorrect OHLCV leading to false signals.
**Mitigation:**
- Data fetchers enforce graceful degradation and strict schema validation using `pandera.DataFrameModel` (`OHLCVSchema`, `SentimentPostSchema`).
- Data points violating schema constraints are purged before signal generation.

## 7. Small Sample Size
**Risk:** A strategy looks great over 10 trades but fails over 1,000.
**Mitigation:** The `incubation_manager.py` enforces a strict minimum threshold of 100 trades and 30 days of live market exposure before a strategy can graduate from INCUBATION to LIVE status.

## 8. Market Regime Changes
**Risk:** A strategy built for a bull market fails during high volatility.
**Mitigation:** The system uses a `RegimeDetector` (based on Garman-Klass volatility). Position sizing is dynamically scaled based on the current regime (low, normal, high volatility), and the strategy itself is an "Adaptive Auto-Regime Switcher".

## 9. Execution Latency and Slippage
**Risk:** Price moving between signal generation and actual execution.
**Mitigation:** Volume-weighted slippage and minimum Average Daily Volume (ADV) filters (e.g., >$1M) are applied to avoid trading illiquid periods where slippage would be severe. In live trading, `AsyncExecutor` reduces local execution latency.

## 10. Psychological Tolerance Bias
**Risk:** Humans panicking and turning off the bot during drawdowns.
**Mitigation:** 100% autonomous execution headless on GitHub actions. Strict, emotionless hard drawdown circuit breakers (`DAILY_LOSS_CIRCUIT_BREAKER_PCT`, `MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT`) are coded into `src.risk.position_sizing`. A 15% Max DD halves risk; 20% halts trading entirely.

## 11. Multiple Testing Bias
**Risk:** Similar to Data-Snooping; running too many statistical tests increases false positives.
**Mitigation:** Timothy Masters' Monte Carlo Permutation Testing strictly utilizes logarithmic returns and accounts for the ensemble of tests, requiring an out-of-sample p-value > 5% for viability.

## 12. Optimization Bias
**Risk:** Over-parameterizing a strategy so it perfectly fits historical noise.
**Mitigation:** The AI Darwinian Evolution engine explicitly forces heuristic mutation and crossover. It relies on out-of-sample Walk-Forward optimization to penalize over-parameterization.

## 13. Data Leakage
**Risk:** Information from the test set leaking into the training set.
**Mitigation:** Strict chronologically separated Walk-Forward periods (e.g., Train 2019-2020, Test 2021). The `CPCV` module strictly purges overlap periods to prevent autocorrelation leakage between train and test splits.

## 14. Black Swan Reconciliation
**Risk:** Rare, catastrophic events wiping out the portfolio.
**Mitigation:** Purchasing power guardrails ensure total notional value never exceeds the account balance (no margin/leverage). 95% CVaR minimization via Riskfolio-Lib minimizes expected shortfall in extreme tail events.

## 15. Inaccurate Price Simulation
**Risk:** Backtester fills orders at prices that never existed.
**Mitigation:** Nautilus Trader backend matches at exact Bar boundaries. Monte Carlo simulation utilizes logarithmic returns to prevent negative synthetic asset prices.

## 16. Change in Contract Specifications
**Risk:** Tick sizes, margin requirements, or multipliers changing over time.
**Mitigation:** Handled generically by the `BaseBroker` architecture. Order sizing is strictly cast to whole-share integer quantities (`qty = int(...)`) dynamically at execution time based on real-time asset prices to comply with Alpaca constraints.

## 17. Cost of Carry and Holding Costs
**Risk:** Overnight financing rates destroying long-term positions.
**Mitigation:** The system primarily models unleveraged cash equities via Alpaca where holding costs are negligible, and utilizes the Risk-free rate (e.g., 4.5% in 2024) to accurately calculate Sharpe ratios relative to cash.

## 18. AI Model Drift
**Risk:** The LLM's understanding of language changing over time.
**Mitigation:** Sentiment scoring relies on a hard-coded, tested version of `FinBERT` for foundational scoring, with LLMs used for higher-level consensus debate that degrades gracefully to neutral stances if models drift or fail.

## 19. Feature Engineering Bias
**Risk:** Injecting human prejudice into the indicators.
**Mitigation:** AI-guided heuristic mutation allows the `skill_executor.py` loop to discover feature combinations autonomously, decoupling the indicators from pure human intuition.

## 20. Non-Stationarity of Financial Data
**Risk:** The statistical properties (mean, variance) of stock prices change constantly.
**Mitigation:** The system explicitly avoids absolute price thresholds. All signals use relative metrics (percentage returns, normalized RSI, rolling Z-scores, ATR-relative bands) which are invariant to non-stationary price levels.
