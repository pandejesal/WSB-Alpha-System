# H1 Regime Detection System

This document explains the implementation of the H1 Regime Detection system for the WSB-Alpha-System.

## HMM Architecture

The system uses a Hidden Markov Model (HMM) to classify market states into distinct regimes.

```text
Features (SMA20 Slope, SMA50 Slope, Realized Vol, RSI, VIX)
       │
       ▼
┌───────────────────────────┐
│     HMM Component         │  ◄── persistence heuristic smooths
│   (4 Gaussian States)     │      <10 day transitions
└────────────┬──────────────┘
             │
       regime_label
             │
             ▼
┌───────────────────────────┐
│     Regime Filter         │  ◄── reads `regime_config.yaml`
│ (Blocks/Allows Signals)   │
└────────────┬──────────────┘
             │
     filtered_signals
```

## Regime Labels

The HMM classifies the market into 4 distinct regimes:
- `0` - **bull**: Strong upward momentum, low-to-moderate volatility.
- `1` - **bear**: Strong downward momentum.
- `2` - **high_vol**: Extremely high volatility (e.g., market crashes, exogenous shocks).
- `3` - **range**: Mean-reverting, sideways market action.

## Configuration Schema

The system uses `config/regime_config.yaml` to govern feature normalization and per-regime sizing/rules. Example:

```yaml
regime:
  n_states: 4
  features:
    - sma20_slope
    - sma50_slope
    - realized_vol_20d
    - rsi_14d
    - vix_level
  normalization: zscore
  regime_labels:
    0: bull
    1: bear
    2: high_vol
    3: range
  regime_config:
    bull:
      position_multiplier: 1.2
      allow_signals: [long, short, mean_reversion]
    bear:
      position_multiplier: 0.8
      allow_signals: [short]
    high_vol:
      position_multiplier: 0.5
      allow_signals: []
    range:
      position_multiplier: 1.0
      allow_signals: [mean_reversion]
```

## Integration with MetaStrategy

The system is encapsulated within a `RegimeDetector` which exposes `apply_regime_filter()`. The `MetaStrategy` class calls this prior to running further parameter grid selections or signal generation steps.
The signal DataFrame is enriched with a `regime_context` column (e.g. `bull` or `bear`) and a `position_multiplier` column. Signals that violate the `allow_signals` logic for the given regime are safely zeroed out (`flat`).

## Backtest Comparison

(To be appended based on ongoing backtests comparing the Sharpe and Max Drawdown with versus without the regime filter).
