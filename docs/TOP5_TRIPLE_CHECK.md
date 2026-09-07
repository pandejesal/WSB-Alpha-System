# Top-5 Triple Check (2026-09-04, Hermes inline — worker 6 stalled)

Scope: top 5 UNIQUE (family, params) paper entries by stored OOS Sharpe.
16 repeat promotions found and set aside (dedupe gap — fixed in
evolve_real.py: identical alive family+params now skip promotion).

## Method (independent reimplementation, not imported from evolve_real.py)

- scripts/top5_check.py rebuilds each family signal from params in pandas:
  RSI-2 entry/exit/max-hold, SMA crossover; T+1, 5bps, SPY baseline on
  identical 1,910-bar window. Read-only vs registry. Paper only.
- C1 RECOMPUTE: stored Sharpe ±0.05 AND exact trip count.
- C2 ROBUSTNESS: params ±10%, first/second-half splits, 10bps costs —
  excess-vs-SPY must stay positive and Sharpe > 0.5 throughout.
- C3 INTEGRITY: honest gate on recomputed numbers.

## Results

| # | Strategy | Stored (Sharpe/OOS/trips) | Recomputed | C1 | C2 | C3 | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | spy_rsi2(12,76,7) | 0.926/1.633/189 | 0.926/1.633/189 | PASS | FAIL | PASS | FAIL |
| 2 | spy_rsi2(11,76,7) | 0.912/1.633/189 | 0.912/1.633/189 | PASS | FAIL | PASS | FAIL |
| 3 | spy_sma(127) | 0.862/1.624/27 | 0.862/1.624/27 | PASS | FAIL | PASS | FAIL |
| 4 | spy_rsi2(11,78,7) | 0.934/1.609/187 | 0.934/1.609/187 | PASS | FAIL | PASS | FAIL |
| 5 | spy_rsi2(12,78,7) | 0.948/1.608/187 | 0.948/1.608/187 | PASS | FAIL | PASS | FAIL |

Reference: SPY buy-hold same window +245.5%, Sharpe 0.94.

## The honest verdict (read this)

C1 is a perfect match down to the trip count — the stored metrics are
REAL, no computation bug, no lookahead found. The loop is honest.

But every strategy FAILS C2 because excess-vs-SPY is -70% to -137%.
These are low-exposure timing overlays: Sharpe ~0.9 matches SPY's 0.94
on risk-adjusted terms, while absolute return trails by a mile (they sit
in cash most of the time). This is the exact trap the user warned about:
strategies that look good on Sharpe and fail the only benchmark that
matters — beating SPY.

Recommendation: keep paper, flag all five KEEP-PAPER-DO-NOT-SIZE. The
honest gate needs a 6th fitting: absolute excess-vs-SPY > 0 (or Sharpe
measured against time-in-market-matched SPY). Until then the loop will
keep promoting elegant losers. Promotions remain paper-only regardless.

## Verification of the checker itself

- tests/test_top5_check.py — 5 passed (determinism, gate logic, dedupe,
  no-lookahead spot, unknown-family rejection).
- ruff + bandit — clean (probe guards fail closed; nosec only on
  non-crypto RNG with justification).
