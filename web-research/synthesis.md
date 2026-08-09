# WSB-Alpha-System — Research Synthesis & Build-Out Backlog

Date: 2026-08-09
Source: 12 web-research docs (`strategies`, `financial-data-sources`, `indicators`, `quant-validation-best-practices`, `execution-ops`, `small-account-risk`, `regime-detection`, `autod-trading-failures`, `paper-pipeline-infra`, `llm-quota-ops`, `jules-agentic-workflow-research`, `skills-best-practices`) cross-checked against the repo (verified status per claim).

## 1. Executive Summary

Research confirms the repo's core engine exists (data providers, alpha strategies, backtests, validators, execution brokers, GitHub Actions pipeline, Pages dashboard) but has four classes of weak points: (1) **validation dishonesty** — `spa_test` is a mislabeled t-test, permutation null is invalid for mean-reversion, CPCV has no embargo; (2) **single-source data fragility** — yfinance is used in 24 files / 60 call sites and is unreliable in 2026; FRED runs on a placeholder key; (3) **execution gap** — paper fills ~100% vs live <=40%, no reconciliation of partial/unknown fills, no client-order-id dedup; (4) **missing risk/regime layers** — no drawdown guardrail, no MC drawdown envelope, no vol-target regime governor, $100 account = cash-only semantics (PDT rule dead as of Jun-4-2026; repo has zero PDT references — assumption-only, no code to change).

## 2. Verified Cross-Check (research claim -> repo reality)

| # | Research doc | Claim | Repo status (verified) | Evidence |
|---|---|---|---|---|
| 1 | quant-validation | `spa_test` is a plain t-test mislabeled as SPA | **CONFIRMED — bug** | `src/backtest/validators/statistical.py:61-69` uses `stats.ttest_1samp(excess, ...)`; real Hansen SPA available via `arch` (already a dependency) |
| 2 | quant-validation | CPCV purges without embargo | **CONFIRMED — gap** | `statistical.py:78-111`: only `purge_length`, no `embargo` parameter, no embargo-side pruning |
| 3 | quant-validation | Permutation test destroys serial correlation (invalid null for mean-reversion) | **CONFIRMED — bug** | `src/backtest/permutation_tester.py:55-60`: independent `np.random.permutation` of gaps and intra-bar geometry; no circular-shift / block-preserving null; unseeded RNG |
| 4 | financial-data-sources | yfinance is the fragility point; migrate to Alpaca data API + Tiingo + Binance public REST | **CONFIRMED — pervasive** | 60 matches in 24 files: `scripts/run_full_backtest.py:186`, `src/data/providers/yfinance_provider.py:39`, `src/execution/live_alpaca_executor.py:209`, `src/alpha/macro_regime.py:25`, `src/data/market_data.py:36`, `src/research/agents/workflow.py:75`, etc. Fallback chain exists (`openbb_provider.py:43`) but primary is yfinance |
| 5 | financial-data-sources | FRED needs a real key | **CONFIRMED — placeholder** | `src/risk/fred_macro_provider.py:20`: `self.api_key = "DEMO_KEY_OR_ENV_VAR"` |
| 6 | financial-data-sources | Reddit JSON endpoints dead | **NOT VERIFIED — low exposure** | No `reddit.com`/`.json` matches under `src/research/`; scraper appears absent or uses another API; de-prioritize |
| 7 | execution-ops | Paper fills ~100% vs live <=40%, random partials, IOC status undoc | **PARTIAL — code review needed** | `src/execution/alpaca_broker.py`, `ccxt_broker.py`, `execution_wrapper.py` exist; fill-parity and reconciliation behavior not yet audited line-by-line |
| 8 | execution-ops | PDT rule eliminated; $100 account is cash-only (no margin/shorts, T+1/T+2) | **CONFIRMED — no code change needed** | Zero PDT/day-trade references in repo; only assumptions in docs/config to update |
| 9 | small-account-risk | 1% risk/trade, 2R-3R daily, heat cap, fractional orders | **PARTIAL** | `src/risk/position_sizer.py`, `position_sizing.py`, `circuit_breakers.py`, `config/risk_config.py` exist; thresholds need $100-basis review |
| 10 | regime-detection | Vol-targeting strongest (R² 45-60%); VIX percentile + MA200/ADX governor | **PARTIAL** | `src/alpha/macro_regime.py` exists but is yfinance-backed (see #4) |
| 11 | autod-trading-failures | 12 failure archetypes; lookahead is #1 killer | **PARTIAL** | `src/backtest/engines/*`, `vectorbt_engine.py`, `walk_forward_engine.py` exist; lookahead audit not yet run |
| 12 | strategies | Top-10 families ranked (TSMOM, momentum, pairs, etc.); F21 = backtest-overfitting guard | **PARTIAL** | `docs/data/strategy_rankings.json` exists with `likely_overfit` flags; strategy candidates for Session-2 filtering ready |
| 13 | indicators | 36-indicator catalog, warmup tables, lookahead pitfalls | **PARTIAL** | `src/alpha/indicators.py` exists; needs gap-list vs catalog (warmups, range-vol estimators Parkinson/GK/RS, MFI+MACD combo) |
| 14 | jules-agentic-workflow | One session = one strategy = one PR; dedup by sha256 + open-PR check; never delegate risk constants; 30s->60s poll; hard deadlines | **READY** | Jules PR #95 (session 2227628593194915806) COMPLETED; gate "wait for PR #1" is now OPEN |

## 3. Ranked Build-Out Backlog

### P0 — Correctness & Risk (do before any new strategy work)
1. **FRED real key** — replace `DEMO_KEY_OR_ENV_VAR` with env-var load (`FRED_API_KEY`); unblocks macro regime provider. 5-min fix.
2. **SPA swap** — replace t-test in `statistical.py:61` with `arch.bootstrap.SPA`; keep API shape.
3. **Permutation null fix** — `permutation_tester.py`: circular-shift / block-preserving permutation, seeded RNG (`np.random.default_rng`), keep OHLC geometry shuffle as a secondary check, not the null.
4. **CPCV embargo** — add `embargo` parameter alongside `purge_length` (research: 1-5 bars for daily).

### P1 — Data & Execution Reliability
5. **yfinance migration plan** — this is the biggest item (24 files). Incremental: (a) extend `src/data/providers/yfinance_provider.py` to a true multi-provider fallback chain: Alpaca data API -> Tiingo -> Binance (public, ccxt) -> yfinance last resort; (b) sweep scripts one by one (`run_full_backtest.py`, `paper_trading_sandbox.py`, `comprehensive_backtest_report.py`, `generate_strategy_data.py`); (c) retire direct `yf.download` calls in `src/alpha/macro_regime.py`, `src/execution/live_alpaca_executor.py`, `src/data/market_data.py`, `src/research/*`.
6. **Order lifecycle layer** — client-order-id on every order, status reconciliation after partial/unknown fills, idempotent retries with backoff, 5xx = unknown -> reconcile (per `execution-ops.md` + `autod-trading-failures.md`).
7. **$100 risk baseline** — review `position_sizer`/`circuit_breakers`/`risk_config.py` against small-account rules: 1% risk ($1), 2R-3R daily cap, heat cap 3%, fractional-order min-notional handling, cash-only semantics.
8. **Drawdown guardrail** — MC drawdown envelope in `circuit_breakers.py` (P(DD > X | strategy vol)) so the engine stalls before ruin, not after.

### P2 — Validation Honesty
9. **Trial ledger + DSR** — persist every experiment in a ledger (hash, params, result, data range); run Deflated Sharpe Ratio (or at minimum Bonferroni) before promotion; ties into existing `strategy_rankings.json` `likely_overfit` flags.
10. **Walk-forward embargo** — apply #4 in `walk_forward_engine.py` too.

### P3 — Extension
11. **Regime governor** — VIX percentile + term structure, MA200/ADX gate, vol-target sizing; build on top of #5 (needs clean data first).
12. **Indicators gap list** — diff `src/alpha/indicators.py` against the 36-indicator catalog; add warmup handling, Parkinson/GK/RS range-vol estimators, MFI+MACD combo.
13. **Jules batch bridge** — blueprint from `jules-agentic-workflow-research.md`: one strategy = one session = one PR, dedup ledger, never-delegate risk constants, hard deadlines.
14. **Skills packaging** — package the runbooks as Agent Skills (3-level progressive disclosure per `skills-best-practices.md`); use cheap classifier model for triage per `llm-quota-ops.md`.

## 4. Quick Wins (no delegation needed)
- FRED env-var key (#1)
- `docs` assumptions: PDT rule removed (cash-only $100), paper-vs-live fill caveat
- Seed the trial ledger schema so future runs write to it (#9 start)

## 5. Open Items (verify later, low priority)
- Reddit scraper status (no `reddit.com` hits — confirm what feeds sentiment today)
- Line-by-line execution parity audit of `alpaca_broker.py` / `ccxt_broker.py` (needed for #6)
- Lookahead audit of backtest engines (for #11/12 inputs)
