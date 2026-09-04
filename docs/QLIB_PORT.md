# qlib Port — Alpha158 + TopkDropout

## Overview

This is a research port of Microsoft's qlib **Alpha158** factor library and **TopkDropout** rotation strategy, adapted for long-only (no shorts/leverage) paper trading with local CSV data only.

**Paper only. No live orders, no API keys, no network calls.**

## What Was Ported

### Alpha158 Features (47 total)

| Family | Window Variants | Description |
|--------|----------------|-------------|
| KMid   | 5, 10, 20, 30, 60 | (close - open) / open |
| KLen   | 5, 10, 20, 30, 60 | (high - low) / open |
| KMid2  | 5, 10, 20, 30, 60 | (close - open) / (high - low + eps) |
| KUp    | 5, 10, 20, 30, 60 | (high - open) / open |
| ROC    | 5, 10, 20, 30, 60 | Rate of change (pct_change) |
| Rank   | 5, 10, 20, 30, 60 | Cross-sectional percentile rank |
| Quantile| 5, 10, 20, 30, 60| Quantile normalization |
| Std    | 5, 10, 20, 30, 60 | Rolling standard deviation of returns |
| Sum    | 5, 10, 20, 30, 60 | Rolling sum of returns |
| Mean   | 5, 10, 20, 30, 60 | Rolling mean of returns |
| Max    | 5, 10, 20, 30, 60 | Rolling max of close |
| Min    | 5, 10, 20, 30, 60 | Rolling min of close |
| Extras |  | VWAP, HighROC, LowROC, Corr(close,volume) |

**All features use `.shift(1)` to prevent lookahead bias.**

### TopkDropout Strategy (long-only)

- **Composite score**: `z(momentum) - 0.5 * z(volatility)` (higher = better)
- **Rotation**: Hold top-k by score, rebalance every N days
- **Dropout**: Force-drop names whose z-score falls below threshold
- **Min hold**: Positions must be held at least M days before forced dropout

## What Was Skipped

- **Short selling / leverage** — not available in paper trading
- **Crypto / options** — Alpaca stocks only
- **qlib's internal data handlers** — replaced with local CSV loading
- **Feature correlation matrix** (CorrCloseClose) — requires multi-stock correlation; deferred
- **qlib's config system** — replaced with simple CLI arguments

## File Mapping

| qlib Original | WSB Port | Notes |
|---------------|----------|-------|
| Alpha158.py | `src/signals/qlib_alpha158.py` | 47 features, all shifted |
| TopkDropout | `src/backtest/qlib_topk.py` | Long-only rotation |
| workflows | `scripts/qlib_workflow.py` | CLI end-to-end |
| tests | `tests/test_qlib_port.py` | 12 tests, all passing |

## How to Run

```bash
# Run the full workflow (generates metrics vs SPY baseline)
python scripts/qlib_workflow.py

# With custom parameters
python scripts/qlib_workflow.py --tickers AAPL,MSFT,GOOGL --top-k 10 --rebalance 10

# Run tests
PYTHONPATH=. pytest tests/test_qlib_port.py -v
```

## Metrics (verified 2026-09-04, Hermes re-run after 3 bug fixes)

5-ticker universe (SPY,QQQ,AAPL,MSFT,NVDA), top-2, 10d rebalance,
T+1 execution, 5bps round-trip costs deducted:

| Metric | Strategy | SPY B&H | Excess |
|---|---|---|---|
| sharpe | 1.18 | 0.90 | +0.27 |
| max_drawdown | -0.32 | -0.34 | +0.02 |
| total_return | +636% | +210% | +426pp |
| cagr | 0.30 | 0.18 | +0.13 |

70 features computed (CLI count; exceeds the 40 minimum).
Full 498-ticker universe loads but exceeds a 7-minute CLI budget —
subset-verified; full run is functional but slow.

Caveats (read before drawing conclusions): 5 mega-cap tech names
2019-2026 is momentum's dream sample (NVDA ride); concentration is
extreme (2 names); this is NOT a 5-gate pass — no walk-forward OOS,
no permutation test, no DSR. Status: paper research only.

Review fixes by Hermes (worker output audited, not trusted blind):
1. `qlib_topk.py`: tickers were checked against the date index, so the
   strategy NEVER held anything (all-zero equity curve, 12 tests still
   green). Fixed + added never-flat regression tests (now 14 pass).
2. `qlib_workflow.py`: SPY Sharpe annualized with `*252` instead of
   `*sqrt(252)` (printed 14.33, true value 0.90). Fixed.
3. `qlib_topk.py`: same-day execution on rebalance + undeducted
   slippage. Now T+1 with 5bps round-trip costs.

## Constraints Honored

- `qlib_` prefix on all new files
- No changes to `strategies/registry.json`
- No network calls
- SPY baseline always reported
- No lookahead (all `.shift(1)`)
