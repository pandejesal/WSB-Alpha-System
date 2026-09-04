# gplearn → WSB-Alpha-System Port (rebuilt 2026-09-04 after disk wipe; Hermes inline build)

Source: https://github.com/trevorstephens/gplearn (1.9k stars: genetic
programming, sklearn-style SymbolicRegressor/Transformer/Classifier,
parsimony pressure, train/test fitness, program export).

Note: OpenCode worker 4 died 3 times (exit 127 twice, JSC
memory-exhaustion crash once), so Hermes implemented this port directly.
gplearn 0.4.3 pip-installed (with --no-deps; the venv numpy is locked by
running processes).

## Mapping

| gplearn | Port |
|---|---|
| SymbolicRegressor + function_set | src/signals/gplearn_factors.py evolve() (pop 100, gen 5, seed 7) |
| parsimony_coefficient | required 0.01 + init_depth (2,4) |
| train/test fitness | fitness = OOS Sharpe of sign() long/flat, T+1 + 5bps |
| program export | expression string + program_to_pandas() renderer |
| sklearn API | EvolveConfig dataclass (population, generations, seed, ratios) |

## Safety deltas

- Terminals are past-only rolling features, all .shift(1): ret_1, ret_5,
  sma5/20 ratios, centered RSI-14, volume ratio, range ratio.
- Fitness is OOS-only; min-trades floor (10); winner sanitized
  (inf/nan → flat, never garbage).
- Evaluation uses a direct tree interpreter (_parse/_apply) — no eval(),
  so bandit is clean. Rendered pandas code is for human audit.
- Paper only. Output is a signal expression, not an order.

## Verification (rebuilt copy re-verified 2026-09-04, real SPY 2019-2026)

- `pytest tests/test_gplearn_port.py` — 4 passed (incl. fast GP smoke
  pop 10/gen 2, no-lookahead check, parser rejection, evaluator match).
- `ruff check` + `bandit` — clean (ValueError validation, eval→interpreter).
- CLI `--generations 5 --population 100 --seed 7`: parsimony collapsed
  the winner to just `X0` (yesterday's return — pure momentum).
  OOS (567 bars): Sharpe 0.14, 276 trades, +2.0% vs same-window SPY
  buy-hold +55.3%. Honest verdict: does NOT beat SPY. Stays paper.
- Rebuild note: committed on branch `ports/2026-09-04` + backed up to
  `port-backups/` outside the repo (original wiped by `git clean -fd`).
