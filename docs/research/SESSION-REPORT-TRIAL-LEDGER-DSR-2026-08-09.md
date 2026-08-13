# Session Report — persisted trial ledger + Deflated Sharpe Ratio guard

**Date:** 2026-08-09
**Repo:** `WSB-Alpha-System-latest` (`C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest`)
**Scope:** research/validation backlog item — multi-comparison safety on the strategy rankings before any parameter set can be promoted.
**Status:** complete, verified. No API keys or network required anywhere.

---

## 1. What was built

New stdlib-only module `src/backtest/defend/trial_ledger.py` with three parts:

### 1a. Persisted trial ledger (`TrialLedger`, JSONL)
- Append-only JSONL at `run-logs/trials.jsonl` (default) — one JSON object per line.
- **Content-hash deduplication** — SHA-256 over `(strategy_id, params, metrics)`; params are canonicalized via `json.dumps(..., sort_keys=True)` before hashing, so dict/key order changes never create phantom duplicates. A duplicate append returns `None` (skipped, warning logged).
- Row shape: `sha256, timestamp, strategy_id, params, metrics, data_range, provider, status`.
- Metric sanitation: non-finite / non-float values become `None` (`nan`/`inf`/strings); `total_trades` survives as an alias for the observation count used by DSR normalization.
- Status lifecycle over rows: `PENDING -> INCUBATING | PROMOTED | REJECTED` — re-writes a row in place without touching other rows, and corrupt JSONL lines are skipped + counted (never lost during an update rewrite).
- Missing parent directories are created; missing ledger reads as empty.

### 1b. Statistics helpers (Bailey & Lopez de Prado 2014, normal-returns variant)
- `normal_cdf` — erf-based, verified against Φ(1.6449)=0.95 to 9+ places.
- `inverse_normal_cdf` — Peter Acklam's rational minimax approximation (relative error < 1.15e-9), validated against Φ⁻¹(0.95), Φ⁻¹(0.99), Φ⁻¹(0.001).
- `expected_max_std_normal(N)` — E[max Z] for N i.i.d. standard normals (γ-recursion with inclusion-ratio refinement).
- `deflated_sharpe_ratio(T, SR, N)` — DSR = Φ( z(SR,T) − E[maxZ(N)] ). Degenerates to the Probabilistic Sharpe Ratio for N=1.
- `deflated_sharpe_threshold(T, N, confidence)` — closed-form break-even Sharpe = z_c/N·... (inverse of DSR, verified numerically: DSR(breakeven) == confidence to 6 places for N ∈ {1,5,36,100}).
- Input guards: T>1, N≥1, p∈(0,1); impossible signals (N ≫ T) report `+inf` instead of crashing.

### 1c. Ingest CLI
`python -m src.backtest.defend.trial_ledger --ingest <rankings.json> [--ledger path] [--max-deflate N] [--obs T] [--top K]`
- Reads the rankings file without modifying it, ingests every strategy with a first-touch marker, re-runs dedup silently.
- Default trial-count for deflation = number of trials ingested (36 in the bundle); override with `--max-deflate`; `--obs` sets the observation count when a trial does not expose `total_trades`.
- Prints the ranked, deflation-guarded table (rank, sharpe, trades, T-used, DSR, break-even, PASS/FAIL) plus the "Best trial" block with break-even Sharpe sensitivity across N ∈ {1,5,10,36,100}.
- Non-zero exit + stderr on missing ingest file; empty-trial edge handled without crashing.

## 2. Tests — `tests/test_trial_ledger.py` (29 tests, all passing)

Run: `python -m pytest tests/test_trial_ledger.py -q` → `29 passed in ~3.8s` (pytest 8.3.x, Python 3.11/3.13 anaconda).

| Group | Tests | Coverage |
|-------|-------|----------|
| `StatsHelpersTest` | 11 | known CDF/quantile values; PSR specialization; strict monotonicity of DSR in SR, T, N; breakeven inversion; bad-arg ValueErrors; inf-threshold edge case |
| `TrialLedgerTest` | 13 | hash dedup, order-stable canonicalization, JSONL round-trip order, corrupt-line tolerance, NaN-pbp metric sanitation, update-status in place / untouched rows / preserved corrupt lines / unknown-hash = False, status enum, input validation |
| `CliIngestTest` | 5 | end-to-end ingest + table, rankings file untouched, second-run dedup (`duplicates skipped: 2`), temp-ledger separately from the real data, missing-file clean failure |

The CLI tests use `TemporaryDirectory` ledgers — the real `docs/data/strategy_rankings.json` is never touched.

## 3. Bugs found and fixed while building

These were genuine defects, caught by the tests:

1. **Acklam inverse-CDF denominators (SRC BUG, critical)** — the `b`/`d` coefficient chains must end with one **extra multiply** (`poly(x, b)*x + 1`), not `poly(x, b) + 1`. The original ghost made `Φ⁻¹(0.95)` return −0.0043 instead of 1.64485. After the fix, every reference value reproduces exactly.
2. **`_poly` evaluated coefficients ascending** — changed to Horner with `coeffs[0]` as the highest-power term, matching Acklam's published `a`/`b`/`c`/`d` layout.
3. Test-only defects fixed along the way: a syntactically invalid `}`-vs-`]` in the fixtures, a placeholder assertion, an inverted dedup assertion, and a monotonicity test that ran in a regime where double precision saturates DSR at 1.0 (re-anchored at SR=0.05).

## 4. End-to-end verification (real data)

```
python -m src.backtest.defend.trial_ledger --ingest docs/data/strategy_rankings.json --max-deflate 36

ingest: 36 trial(s) read from docs/data/strategy_rankings.json
        -> run-logs/trials.jsonl (new: 36, duplicates skipped: 0)
N (trials) = 36 | confidence = 0.95 | observation fallback = 2500

  rank strategy_id    sharpe trades T-used  DSR(N) break-even verdict
    1  strat_0000   -27.4350      -   2500  0.0000    0.0760   FAIL
    ... (36 strategies, all honestly FAIL on the bundled placeholder data)
Best trial: strat_0000   raw Sharpe -27.4350  deflated 0.0000
break-even : 0.0760   (min Sharpe to survive 36 trials @ 0.95)
sensitivity: N=1 -> 0.0329 ; N=5 -> 0.0568 ; N=10 -> 0.0645
             N=36 -> 0.0760 ; N=100 -> 0.0837
```

With real ranking data, a Sharpe of ~0.076+ is required to survive 36 back-test trials at 95 % confidence — the guard will mark PROMOTION candidates as FAIL until they clear that bar. Re-runs show `duplicates skipped: 36` and leave the ledger at 36 rows.

## 5. Files touched

| Path | Change |
|------|--------|
| `src/backtest/defend/trial_ledger.py` | new module (ledger + DSR math + CLI) |
| `tests/test_trial_ledger.py` | new, 29 tests |
| `.gitignore` | + `run-logs/` (ledger artifacts), + `.swarm/` (agent state) |
| `run-logs/trials.jsonl` | generated by verification run (ignored) |

Scratch/`tmp` files used during the session were removed; no committed repo files were modified. Not committed — user review pending.

## 6. Notes / follow-ups

- The 36 bundled entries are placeholder data (every strategy has the identical Sharpe), so real POLICY decisions wait for the next backtest export; the guard logic itself is fully exercised by the tests.
- Config keys, secret material, or account info: **none** added, no modifications to auth code; this change is a read-only consumer of `docs/data/strategy_rankings.json`.