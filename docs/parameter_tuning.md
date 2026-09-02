# Parameter Tuning Scaffold

This document outlines the usage of the parameter tuning scaffold in the `WSB-Alpha-System`. The tuning scaffold enables systematic optimization of strategy parameters via grid search and integration with `vectorbt`.

## Parameter Grid Configuration

The configuration for parameter grids is driven by a YAML file located at `config/param_grids.yaml`.

### YAML Schema

The schema of `param_grids.yaml` is a simple key-value mapping where the top-level keys represent strategy names (e.g., `momentum_breakout_v2`, `mean_reversion_enhanced`), and the values are dictionaries representing parameters to tune. Each parameter maps to a list of values to evaluate during grid search.

**Example `config/param_grids.yaml`:**
```yaml
momentum_breakout_v2:
  lookback: [20, 50, 100]
  breakout_threshold: [0.02, 0.03, 0.05]

mean_reversion_enhanced:
  rsi_period: [14, 21]
  rsi_oversold: [30, 35]
  rsi_overbought: [65, 70]

trend_following_v3:
  ema_fast: [10, 20]
  ema_slow: [50, 100]
  atr_multiplier: [1.5, 2.0, 2.5]

btc_vol_target_sma100:
  vol_target: [0.15, 0.20]
  sma_period: [50, 100, 200]
```

## Usage

The parameter tuning scaffold is accessible via the `ParameterTuner` class located in `src/alpha/meta_strategy.py`.

### Tuning Process

1. **Initialization:** Ensure `config/param_grids.yaml` is correctly populated.
2. **Execution:** Create an instance of `ParameterTuner` and call the `tune` method with the desired strategy names, historical data (as a pandas DataFrame), and output path.
3. **Output:** The tuner performs a grid search, combining all parameter variations for the specified strategies. It runs backtests using `vectorbt` for each combination and compiles the performance metrics.
4. **Results:** The metrics are saved to a CSV file containing columns for the strategy name, parameter dictionary, Sharpe ratio, maximum drawdown, win rate, and total trades.

### Example Code

```python
import pandas as pd
from src.alpha.meta_strategy import ParameterTuner

# Assuming 'df' is a pandas DataFrame with historical market data containing a 'Close' column
df = pd.DataFrame(...) # Load your data here

tuner = ParameterTuner(grid_config_path="config/param_grids.yaml")
results_csv_path = "tuning_results.csv"

tuner.tune(
    strategies=["momentum_breakout_v2", "mean_reversion_enhanced"],
    data=df,
    output_csv=results_csv_path
)

print(f"Tuning complete. Results saved to {results_csv_path}")
```
