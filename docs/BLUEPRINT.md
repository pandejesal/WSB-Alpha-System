# WSB Alpha System - Quantitative Overhaul Blueprint

## 1. ALPHA GENERATION & EDGE EXPLOSION

### Smart Money Concepts (SMC) Definitions
We will implement rigorous mathematical definitions for SMC:
- **Fair Value Gaps (FVGs):** A 3-candle imbalance. A Bullish FVG occurs when Candle 1 High < Candle 3 Low, and the gap size is at least a minimum threshold (e.g., >= 0.5 * ATR or relative to median gap). A Bearish FVG occurs when Candle 1 Low > Candle 3 High.
- **Order Blocks (OB):** The last opposite-color consolidation candle before a significant displacement impulse move. Displacement is defined as a move >= 1.5x the median ATR over a lookback window.
- **Liquidity Sweeps:** A wick that pierces a recent swing high or low (defined by local extrema over a rolling window) and then closes back within the range.

### Multi-Timeframe Confluence
- **Higher Timeframe (e.g., Daily):** Dictates the macro regime (Bullish, Bearish, Volatile).
- **Lower Timeframe (e.g., H1, H4):** Used for precise entry execution.
- Entries are only permitted in the direction of the Higher Timeframe regime.

### Dynamic Position Sizing
- **Fractional Kelly Criterion:** Allocates a fraction (0.1 to 0.25) of the full Kelly bet per trade.
- **Micro-Account Constraints:** Hard cap of US$ notional risk <= 1% of equity. Hard max notional umbrella to ensure total exposure does not exceed the $100 account balance (no margin).
- **Regime Volatility Scaling:** The Kelly fraction and max risk adjust based on the current regime (e.g., Garman-Klass volatility). Zero-size trades when confidence is below a threshold.

### Signal Combination
- Require confluence: (Sentiment Velocity Regime > Threshold AND SMC Alignment) OR (Momentum Backstop).
- Signals are weighted, aggregated, and passed through the higher timeframe regime filter.

## 2. ELIMINATING OVERFITTING & MONTE CARLO RIGOR

### Hardened Optimization (src/evolution/darwin_engine.py)
- **Complexity Penalty:** Introduce an economic-complexity penalty (count of active free parameters / degrees of freedom) scaled by a tunable `lambda`.
- **AIC/BIC Fitness:** Fitness = `Score_oos + lambda * complexity_penalty`. Heavily penalize in-sample-only gains.
- **Walk-Forward Validation:** Use true rolling train -> next-test windows. Target Walk-Forward Efficiency (OOS_sharpe / IS_sharpe) >= 0.7.
- **Statistical Gate:** Require Permutation/Bootstrap p-value < 0.01 for the OOS period. A parameter set is only promoted if it survives multiple independent walk-forward blocks (>= 3) and maintains a minimum OOS Sharpe floor.

## 3. EXECUTION & FRICTION HARDENING

### Resilient Execution Strategy
- Implement exponential backoff retry loops with jitter for API calls (Alpaca, CCXT, Data Providers). Configurable `max_retries` and `timeout`.
- **Fails-Closed Mechanism:** If retries are exhausted, immediately cancel open orders for the symbol, block new entries for that symbol for the current cycle, and log/alert.

### Abstract BaseBroker & CCXT Integration
- Standardize the `BaseBroker` interface.
- Implement `CCXTBroker` matching the exact signature of `AlpacaBroker`.
- Orchestrate both through a single hardened execution wrapper.

### Fractional Rounding & Dynamic Stops
- Calculate trade quantities as: `floor_to_increment(min(available_cash // price, target_qty), broker_min_increment)`. Ensure quantity is never negative or zero.
- Dynamic stop-loss placement scaled by ATR but hard-capped to not exceed total collateral risk limits.

## 4. ACTIONS & DASHBOARD SUPERCHARGING

### Single Workflow Optimization
- Optimize `daily_research.yml` to run as a single, fast workflow.
- Implement robust caching for Python dependencies (`pip cache`) and avoid matrix spam.
- Lazy-load heavy libraries (e.g., `FinBERT`) only when sentiment analysis is actively required.

### Static Dashboard Supercharging
- Upgrade `docs/index.html` and `docs/app.js` using vanilla JS (no build step).
- **New Metrics:** Real-time Monte Carlo p-values, Walk-Forward efficiency, Regime-by-ticker breakdown matrix, and active skill-loop hypotheses (with confidence and last OOS result).
- Ensure data is fetched dynamically from the committed JSON artifacts.

## 5. COMPLETE REPO REFACTOR
- Provide modular, type-hinted, and unit-tested Python code.
- Ensure strict compliance with the project's static analysis tools (`pytest`, `ruff`, `bandit`).
