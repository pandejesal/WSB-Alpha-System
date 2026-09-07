# NextTrade → WSB-Alpha-System Port (rebuilt 2026-09-04 after disk wipe; see §Verification)

Source: https://github.com/austin-starks/NextTrade (1,776 stars, 286 forks,
branch master @ 53a3c2a, last push 2025-05-15). Predecessor to NexusTrade.
Stack: Node/TypeScript + MongoDB + Tradier brokerage + React client.

## What NextTrade is (5 features)

1. Composable conditions → compound conditions → strategies
   (e.g. QQQ 1SD below 5-day mean AND buying power > $8000 → buy $3000 SPY).
2. Unlimited portfolios of strategy combinations.
3. Backtesting on historical data (Tradier OHLC; SPY buy-hold baseline hardcoded).
4. Genetic-algorithm parameter optimization (population, mutation rate,
   training/validation windows; fitness = gain / sortino / sharpe / maxDD).
5. One-click live deployment + forward-test controller.

Core engine files ported: `models/conditions/*.ts` (12 leaf + And/Or/compound/
then), `models/strategy`, `models/portfolio/*` (allocation caps, paper vs live
configs), `models/backtester/index.ts` (618 lines), `models/optimization/
index.ts` (1,441 lines), `models/statistics`, `models/brokerage/
BacktestBrokerage.ts` (cache wrapper) + `AlpacaBrokerage.ts` (stub — most
methods `null` / "not implemented").

## Mapping (TS → Python)

| NextTrade | Port | Notes |
|---|---|---|
| conditions/abstract + factory | src/signals/nexttrade_conditions.py `create()` | dict specs replace Mongo docs |
| SimplePrice / MovingAverage / BuyingPower / HavePosition / PortfolioValue / PositionPct / Profitable / EnoughTime | same file, one class each | rolling stats `.shift(1)`, no lookahead |
| And / Or / Then | same file | Then = latch(max_bars) & confirm |
| strategy + MockPortfolio | BacktestConfig + state machine | long/flat single-symbol only |
| backtester + SPY baseline | src/backtest/nexttrade_backtest.py | T+1 + 5bps slippage added |
| statistics (sharpe/sortino/maxDD) | WSB safe_sharpe/safe_sortino | NextTrade raw formula explodes near-zero sd; safe version guards |
| BacktestBrokerage cache | load_prices() one-frame load | local CSV, zero network |
| optimization GA + trainValidationRatio 0.8 | scripts/nexttrade_optimize.py | same fitness set + elite/crossover/mutation; train/val chronological |
| README QQQ/SPY example | strategies/nexttrade_composable_example.yaml | paper only, gates 0/5 |

## Deliberately NOT ported

- MongoDB, Mongoose schemas, user auth, React client, PM2 — replaced by
  YAML specs + local CSVs.
- Tradier / Coinbase / options / debit-spreads / shorting / leverage —
  user mandate is Alpaca only; AlpacaBrokerage upstream is an unimplemented
  stub anyway (`getPrices` returns null).
- Live deployment + forward-test worker — WSB rule: paper only, never
  auto-live. Optimizer `--emit-yaml` writes `status: paper`,
  `gates_passed: 0/5`, `verdict: UNVERIFIED_PAPER`.
- Parametrize-everything GA over options chains — overfit surface; port
  searches only window/sd/statistic/allocation with train/val split.

## Safety adaptations (user: "safe and amazing", beat SPY)

1. No lookahead: all rolling bands shifted 1 bar (NextTrade's getHistory
   slices inclusive of current bar in places).
2. Costs: T+1 execution + 5 bps slippage per turnover day (NextTrade
   backtester has no cost model visible).
3. Buying-power guard fail-closed (NextTrade assumes fills).
4. SPY buy-hold over identical window always reported with excess %.
5. Optimizer fitness ≠ promotion: output still needs WSB 5 gates
   (pre-register, walk-forward, permutation, DSR, min trades) before
   registry; registry entries stay paper.

## Verification (rebuilt copy re-verified 2026-09-04, real data)

- `PYTHONPATH=. pytest tests/test_nexttrade_conditions.py` — 3 passed.
- `ruff check` on all four files — clean. `bandit -r src/signals`
  (ValueError validation, no asserts) — 0 issues.
- Canonical backtest MovingAverage SPY 5d/-1sd, $3k of $100k, T+1 + 5bps,
  2019-2026 (1,910 bars, data/spy_ohlcv_2019_2026.csv): 392 trades,
  Sharpe 0.70, Sortino 1.10, maxDD 0.6%, +1.99% vs SPY buy-hold +245.5%
  (excess -243.5%). Honest verdict: dip-buy with 3% allocation does NOT
  beat SPY — needs 5-gate validation, stays paper.
- Optimizer smoke `--generations 2 --population 6 --seed 7` runs end to
  end; val Sharpe negative — same honest conclusion, no promotion.
- Rebuild note: original 2026-09-04 port was wiped from disk (apparent
  `git clean -fd` by another process; tracked tree untouched). Rebuilt
  from Hermes session record; this copy is committed on branch
  `ports/2026-09-04` + backed up to `port-backups/` outside the repo.
