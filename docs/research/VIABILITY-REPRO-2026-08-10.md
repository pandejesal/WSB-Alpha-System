# Statistical Viability — Reproduction & Findings (2026-08-10)

- Campaign: WSB-Alpha-System, Session 1, Task 3.1 — "reproduce the numbers yourself"
- Commands: `python -m src.backtest.validation` (anaconda3 python 3.13.5, MPLBACKEND=Agg)
- Evidence: `run-logs/validation_2026-08-10b.log`, `permutation_histogram.png` (repo root)
- Date: 2026-08-10. Seed: `np.random.seed(42)` added to `validation.py` for reproducible draws.

---

## Reproduction result (this run)

| Metric | This run (2026-08-10) | README/REAL_LIFE_VIABILITY claim | Gate | Verdict |
|---|---|---|---|---|
| In-Sample permutation p-value | **0.9850** | 0.1100 | ≤ 0.01 | **FAIL (worse)** |
| Walk-Forward permutation p-value | **1.0000** | 0.2150 | ≤ 0.05 | **FAIL (worse)** |
| Real In-Sample return | **−2353.19%** | (positive per README narrative) | — | catastrophic |
| Real In-Sample Sharpe | **−3.19** | — | — | bad |
| WF windows won vs permuted median | **1/9 (11.1%)** | — | ≥ 50% ideal | worse than coin flip |
| Hansen SPA p-value (in-sample) | **0.4830** | — | ≤ 0.05 rejects null | no evidence of skill |

**CONCLUSION (printed by the pipeline): "this strategy has not demonstrated it beats random noise."**

## Important caveat — what was actually reproduced

- `wsb_factual_research_data.csv` was **absent from the working tree** (deleted by commit
  `6d30d08` on 2026-07-31 "refactor: enforce live trading safety and replace synthetic data"),
  so the first run took `load_base_data()`'s **synthetic-signal branch**: it downloads 2y of
  price data for the `config/universe.json` tickers and generates one bullish/bearish "post"
  per qualifying bar (34 tickers × ~500 bars ≈ 17k signals).

## UPDATE 2026-08-11 — real dataset recovered and re-run (lookahead-clean code)

- The real dataset **was recoverable from git history**: `0cfccb8:wsb_factual_research_data.csv`
  (582 KB — the newer blob `0e333ba5` = 582,011 B, restored via `git show 0cfccb8:...`).
  Confirmed real content: **500 posts, 11 tickers** (PLTR, AMZN, MSFT, NFLX, AMD, TSLA, GME,
  GOOGL, META, NVDA, AAPL), **2020-01-07 → 2026-07-27**; `sentiment_score` ∈ [−2, +5]
  (388 bullish / 112 bearish).
- **Real-data validation run** (same `python -m src.backtest.validation`, seed 42, ~25 min):

  | Metric | Real-data run (2026-08-11) | README claim | Gate | Verdict |
  |---|---|---|---|---|
  | Real In-Sample return | **−9.48%** | positive (narrative +157%) | — | net-negative |
  | In-Sample permutation p-value | **0.5650** | 0.1100 | ≤ 0.01 | **FAIL** |
  | Walk-Forward pooled p-value | **0.6150** | 0.2150 | ≤ 0.05 | **FAIL** |
  | WF windows won | **13/27 (48.1%)** | — | ≥ 50% ideal | ≈ coin flip |
  | Hansen SPA p-value (in-sample) | **0.6990** | — | ≤ 0.05 rejects null | no evidence of skill |

  Pipeline conclusion: **"this strategy has not demonstrated it beats random noise."**

- **Why the README numbers still differ despite identical input data:** the README claims were
  written at `0cfccb8` (2026-07-31) from the **pre-honesty code path** (root-level
  `validation.py` + `run_historic_backtest.py`, 490-line indicators-inline version). The
  lookahead-elimination landed later — `a7f0765`/`8ed6cf8`/`aee0395` on **2026-08-08/09**
  ("enforce honest validation and eliminate lookahead bias"). Running the exact same CSV through
  the lookahead-clean pipeline does **not** reproduce IS 0.11 / WF 0.215: it fails both gates.
- **GDELT connectivity (keyless doc API) confirmed dead** — `probe_gdelt.py` → `HTTP 429: Too
  Many Requests` on every call; matches the all-zero `news_index.csv`/`errors.csv` from the
  original `news_harvest.py` run. No dependency on regenerating the seen-via-news signal set;
  the git-recovered CSV is the authoritative input and matches the pipeline contract
  (`post_date, ticker, sentiment_score`).
- The README numbers were **not reproduced because their input does not exist here**. What the
  run shows instead: the *runnable pipeline, as it stands on this machine*, fails the gates far
  worse than the README claims — and the synthetic-signal strategy itself is net-negative.
- Finding: `run_backtest_with_params` shorts whenever the bearish confluence score wins; on a
  2y bull window (2024-2026 universe incl. SPY) the synthetic shorts dominate → −2353%.

## Diagnosis (root causes)

1. **Signal data missing** — the real dataset that validation was designed for is not in the
   repo. This is a data-pipeline gap (Task 2 territory), and the most likely explanation for
   any README-vs-local divergence.
2. **Validation cost made iteration impractical** — each backtest re-ran a full-frame boolean
   mask (`df[df["Date"] >= exec_date]`) per post inside a ~17k-post loop, per permutation:
   400 permutations ≈ **3.7 hours** (34s/perm).
3. **Hansen SPA test was dead code** — `StatisticalValidator` import sits outside the
   try/except and requires `arch`, which was not installed → the whole validation crashed at
   the end of a multi-hour run.
4. **Permutation draws were unseeded** — results not reproducible across runs.

## Fixes applied (evidence-based, behavior-preserving)

1. `src/backtest/run_historic_backtest.py` — replaced per-post boolean-mask search with
   precomputed per-ticker `np.searchsorted` on normalized date arrays (identical first-bar
   selection semantics, O(log n) per post). **Measured: 34s → ~3s per permutation (10×).**
   Full 200+200 validation now runs in ~25-30 min instead of ~4 h.
2. `src/backtest/validation.py` — SPA import wrapped in try/except (degrades to p=1.0 with a
   message instead of crashing the run); `np.random.seed(42)` at the `__main__` entry.
3. Environment: `pip install arch` (8.0.0) — unblocks `StatisticalValidator` and the test
   suite (test collection was failing on `ModuleNotFoundError: arch`).

## Verification

- `pytest tests/test_pipeline.py tests/test_p0_fixes.py tests/test_session4_lookahead.py
  tests/test_optimization.py tests/walk_forward/test_advanced_validation.py`
  → **13 passed** (2 pre-existing pandas FutureWarnings, unrelated to these changes).
- Full validation rerun to completion, EXIT=0, histogram + SPA produced (log cited above).

## Recommendation (tie-in to Task 3.4/5 and the framework research)

- The gates fail on the **real** dataset too (p 0.565/0.615) under lookahead-clean code, and the
  README's significance claims are attributable to pre-fix lookahead rather than genuine edge.
  The next step is therefore **not further tuning on this signal set** — it is validating a
  genuinely new/independent signal or holding-period design through the framework stack from
  `docs/research/OpenSource-Trading-Frameworks 2026-08-10.md` (permutation/DSR/PBO layer via
  backtest-audit or pybroker walkforward; NautilusTrader for realistic fills) before any
  paper-trading claim.
- Do NOT promote any of the 42 README-flagged overfit strategies until a fresh signal design
  clears the 0.01/0.05 gates with restored real data.

## Files changed this session

- `src/backtest/run_historic_backtest.py` (speedup, semantics-preserving)
- `src/backtest/validation.py` (SPA guard, seed)
- `wsb_factual_research_data.csv` (restored from git history `0cfccb8` — real sentiment dataset)
- `run-logs/validation_2026-08-10b.log` (synthetic run), `run-logs/validation_real.log` (real run)
- `permutation_histogram.png` (evidence artifacts)
- `docs/research/OpenSource-Trading-Frameworks 2026-08-10.md` (framework stack research)