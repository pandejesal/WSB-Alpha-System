# AgentQuant Port Documentation

## Overview

This is a deterministic, local-LLM-free port of [AgentQuant](https://github.com/OnePunchMonk/AgentQuant) integrated into the WSB-Alpha-System-build repository as **Worker 1** of 5.

## What Was Ported

### Regime Detection (`src/signals/agentquant_regime.py`)

Replaces AgentQuant's VIX-dependent regime detection with a fully local approach:

| Feature | Source |
|---|---|
| Volatility regime (low/mid/high/crisis) | Realized volatility percentile over 252 days |
| Trend regime (Bull/Bear/Sideways) | 200/50 SMA crossover |
| Momentum regime (Bull/Bear) | 63-day and 21-day momentum |
| Drawdown signal | Max drawdown calculation |

**No API calls. No VIX dependency. All computed from SPY price data.**

Key functions:
- `compute_regime_features(df)` — adds volatility, momentum, SMA, drawdown columns to DataFrame
- `detect_regime(features_row)` — returns `"{VolRegime}-{TrendRegime}"` string
- `detect_regime_full(features)` — returns full `RegimeSignals` dataclass

### Harness Evolution (`src/evolution/agentquant_harness.py`)

Grid-based strategy evolution with 5 families:

| Family | Key Parameters |
|---|---|
| `momentum` | lookback (5–60), entry_threshold (0.01–0.10), exit_threshold (-0.05–0.02) |
| `mean_reversion` | lookback (10–50), z_entry (1.5–3.5), z_exit (0.0–1.0) |
| `volatility` | lookback (10–60), entry_mult (0.5–3.0), target_vol (0.08–0.25) |
| `trend_following` | short_window (5–20), medium_window (20–50), long_window (50–200) |
| `breakout` | lookback (5–40), threshold (0.005–0.05), atr_mult (0.5–2.0) |

Key functions:
- `sample_grid(family)` — random parameter draw from grid
- `backtest_strategy(df, params, family)` — vectorized backtest with `.shift(1)` T+1 enforcement, 5 bps slippage
- `walk_forward_eval(df, params, family, n_splits)` — expanding-window walk-forward
- `HarnessEvolution.evolve(df)` — mutation + crossover grid search

**All signals use `.shift(1)` to prevent lookahead. No LLM involvement.**

### Critic Agent (`src/evolution/agentquant_critic.py`)

Proposal validation via 5 checks (no LLM):

| Check | Description |
|---|---|
| Deduplication | Near-duplicate params rejected (Hamming distance < 0.001) |
| Window ordering | `short_window < medium_window < long_window` for trend_following |
| Parameter sanity | Values within valid bounds per family |
| Walk-forward efficiency | Must exceed `min_wfe` threshold (default 0.3) |
| Minimum trade count | Must exceed `min_trades` threshold (default 10) |

### Entry Point (`scripts/agentquant_evolve.py`)

```
PYTHONPATH=. python scripts/agentquant_evolve.py
PYTHONPATH=. python scripts/agentquant_evolve.py --family momentum --generations 10
PYTHONPATH=. python scripts/agentquant_evolve.py --family momentum mean_reversion --population 30 --seed 42
```

## Constraints Enforced

| Constraint | Implementation |
|---|---|
| SPY only | Data loader reads only SPY CSV |
| Paper only | No live trading code |
| No API keys/network | All data from local CSV, no external calls |
| No lookahead | All signals use `.shift(1)` |
| T+1 execution | Position at t depends on data at t-1 |
| 5 bps slippage | Applied to every trade in backtest |
| SPY baseline always reported | Runner script prints SPY Sharpe, drawdown, return |
| File prefix `agentquant_` | All ported files use `agentquant_` prefix |

## Data Format

```csv
Date,"('Close', 'SPY')","('High', 'SPY')","('Low', 'SPY')","('Open', 'SPY')","('Volume', 'SPY')"
```

The port normalizes this format automatically.

## Tests

```bash
PYTHONPATH=. pytest tests/test_agentquant_port.py -v
```

Tests cover:
- Regime detection (features, regime string, empty data)
- Grid sampling (all families, invalid family)
- Harness genome creation
- Backtest strategy runs
- T+1 enforcement
- Walk-forward evaluation
- Full evolution pipeline
- Critic approval/rejection
- Deduplication
- Window ordering
- Batch critique
- Integration test (regime → evolution → critic)

## Differences from Original AgentQuant

| Aspect | Original AgentQuant | WSB Port |
|---|---|---|
| Regime detection | VIX-based (external API) | Realized vol (local) |
| Evolution strategy | Grid search + LLM | Grid search only (no LLM) |
| Critic | LLM-based screening | Dedup + validation only |
| Data source | Alpaca API | Local CSV |
| Walk-forward | Regime-aware splits | Standard expanding window |
| Universe | Multi-asset | SPY only |
| Entry script | Not a standalone script | CLI with argparse |

## File Inventory

```
src/signals/agentquant_regime.py      — Regime detection
src/evolution/agentquant_harness.py   — Harness evolution
src/evolution/agentquant_critic.py    — Critic agent
scripts/agentquant_evolve.py          — Entry point script
tests/test_agentquant_port.py         — Test suite
docs/AGENTQUANT_PORT.md               — This file
```

## Verification (2026-09-04, Hermes audit + real CLI run)

- `pytest tests/test_agentquant_port.py` — 22 passed.
- `ruff check` — clean after Hermes fixed 7 worker Lint errors
  (unused imports, unused variable, f-string, type comparison,
  ambiguous `l` variable incl. its second use at exit logic).
- `bandit` — 0 medium/high.
- Real CLI run (`PYTHONPATH=. python scripts/agentquant_evolve.py`,
  SPY 2019-2026, regime LowVol-Neutral): best = mean_reversion
  (lookback 30, z_entry 1.5, z_exit 0.0, stop 3.0z) — OOS Sharpe 1.26
  vs train 0.55, Sortino 0.20, maxDD 28%, win rate 50.5%, profit
  factor 1.15, 24 trades, WFE 2.31, critic APPROVED. SPY baseline
  Sharpe 0.90, maxDD 33.7%, total +203%.
- Flags (not blockers, must-read): OOS Sharpe ABOVE train Sharpe is
  unusual — favorable OOS window or subtle leak, needs walk-forward
  scrutiny; 24 trades is thin; Sortino 0.20 is weak vs the Sharpe.
  This is NOT a 5-gate pass. Status: paper research only.
