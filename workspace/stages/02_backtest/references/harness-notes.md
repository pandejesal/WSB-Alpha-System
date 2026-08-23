# Harness Notes (Layer 3)

## What stage 02 actually runs
`scripts/run_backtest.py` (this workspace) is a thin wrapper around the repo's
`scripts/evaluate_candidate.py`. Evaluation logic lives THERE — never reimplement
gates, indicators, or validation in the workspace.

## evaluate_candidate.py interface
- Positional: path to candidate spec YAML
- `--tickers T1,T2` optional override
- `--days N` data window (default 60)
- `--seed N` (default 42), `--permutations N` (default NUM_PERMUTATIONS)
- Internally: validate_spec -> signals from registry rules -> provider chain ->
  run_in_sample_test + run_walk_forward_test (src/backtest/validation.py)

## Known constraints
- Panel universes exclude SPY/QQQ/AGG/BND/IWM from panel candidates; SPY-only
  specs evaluate on SPY alone.
- Entry rules normalize to canonical keys: rsi2 | macd_histogram | ema_cross |
  momentum | sma_entry. Specs whose prose entry doesn't map will fall back to raw
  string — check results.json for the resolved key.
- Crypto specs: universe.json crypto_tickers; session gate + freshness validation
  apply (src/ops/strategy_registry.py).
- Data/provider failures are fail-closed: report exact error, propose fix, do not
  patch the harness from inside a run.

## Output contract
Raw evaluator JSON goes verbatim to output/results.json. The summary md is your
interpretation layer — numbers must be copied, not paraphrased.
