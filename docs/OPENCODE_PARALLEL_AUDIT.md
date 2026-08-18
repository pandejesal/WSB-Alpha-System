# OpenCode Parallel Sub-Agent Audit — WSB-Alpha-System

- **Date:** 2026-08-09
- **Basis:** READ-ONLY multi-lane audit (6 parallel lanes). No edits, no commits, no dependency installs, no paid network calls.
- **Repo state audited:** branch `fix/self-improvement-fallback-paths` at `8424589`, including uncommitted working-tree edits (verified: cosmetic only — line-wrap/import cleanup; every substantive finding reproduces against committed main, confirmed via readonly `git diff` per lane).
- **Method:** Each claim cited `file:line` and was cross-checked against current `main` state. "Stated in docs" vs "verified in code" separated throughout.

## 1. Executive Summary — Top 5 Actions (ranked: risk × likelihood)

| # | Action | Risk | Likelihood |
|---|--------|------|-----------|
| 1 | ~~**Fix crypto executor position cap (logs-only, proceeds to open new orders)** `live_crypto_executor.py:292-293`~~<br>RESOLVED 2026-08-18: max-positions guard returns since 8bab4faa; gate chain extracted to gates_allow_trading(); regression coverage in tests/test_crypto_executor_caps.py (PR #154) | CRITICAL (real-money capacity overshoot; cap is decorative in the only crypto live path) | HIGH — every rebalance run at cap |
| 2 | **Degenerate metrics propagate to users** — Sharpe `-9.6e16` committed in `docs/data/backtest_report.json:75,676` and `docs/data/strategy_rankings.json:20-25` (division by near-zero std, 1-trade samples); `oos_sharpe` aliased to in-sample at `generate_strategy_data.py:357-358`/`run_full_backtest.py:73-74` so the Darwin promotion gate is constant ×0.1 | HIGH (metrics published as fact; README claims have no JSON provenance) | CERTAIN (present in committed data today) |
| 3 | **`api_health_check.yml` burns ~26,000–52,000 min/mo** vs 2,000/mo free tier (`cron */5`, 8,755 runs/mo, full pip install per run) | HIGH (CI budget exhaustion kills all workflows) | CERTAIN |
| 4 | **Enable a real pre-trade gatekeeper** — no `check_order_allowed()` exists; `position_sizer.py:26,55` defaults to 2% and never clamps, contradicting the declared 1% cap (`position_sizing.py:13`) | HIGH (up to 6% equity risk per trade on the bridge path) | MEDIUM (path requires a live signal) |
| 5 | **Reconcile README numbers with committed data** — README claims (108.16%/484 tr/Sharpe 1.01) vs `backtest_report.json` (−0.30%/1 tr/Sharpe −27.44); +1,479.92% (README.md:113) vs +1,700% (REAL_LIFE_VIABILITY.md:95) — neither appears in any JSON | MEDIUM (reputational/data-integrity) | CERTAIN |

## 2. Per-Lane Findings

### Lane 1 — CI/CD & Actions budget

| workflow | trigger | est min/mo | issue | fix |
|---|---|---|---|---|
| api_health_check.yml | cron `*/5 * * * *` (:6) | 26,000–52,000 | ~8,755 runs/mo; full pip install + 4 API calls; **13–26× free tier** | hourly/daily cron; pip cache; external uptime monitor |
| daily_research.yml | cron `0 8 * * *` (:5) | 300–600 | `playwright install chromium` every run (:44) | cache; install-only-if-needed |
| paper_trade.yml / sandbox.yml | cron `55 20 * * 1-5` (:5/:6) | 130–220 each | identical crons (serialized by concurrency group); runs on holidays | stagger or merge; market-hours gate |
| generate_strategies.yml | cron `0 7 * * 0` (:5) | ~50 | — | — |
| self_improvement.yml | cron `0 12 * * 6` (:5) | 25–65 | `git commit -am` at :49 sweeps in unrelated edits — agent first edits `run_historic_backtest.py` **then** `-am` | drop `-a`; commit staged only |
| pages.yml | push + `workflow_run` (:3-13) | ~120 | fires on failed workflow_run completions | guard `conclusion == 'success'` |
| ci.yml | push main (:3) | per-push | — | — |

- **Commit scoping:** all 6 auto-commit steps use `git commit -am` (api_health:108, daily_research:58, generate_strategies:38, paper_trade:162, sandbox:53, self_improvement:49). No `git add -A` / `git add .` anywhere. `-a` stages every modified tracked file — makes targeted staging impossible.
- **Secrets:** `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN` referenced; `TELEGRAM_BOT_TOKEN` used in exactly 1 workflow (api_health:33) and `ALPACA_SECRET_KEY` is missing from README secret docs (README.md:103-108).
- **requirements.txt:** duplicate `nautilus_trader==1.218.0` (:71) vs `nautilus-trader==1.218.0` (:167); unpinned `defusedxml` (:168); ~110 zero-import transitive deps in what is otherwise a pip-freeze file; **missing**: `aiohttp`, `ccxt`, `feedparser`, `openbb`, `streamlit` are imported but absent.
- **Actions:** all 18 `uses:` are unpinned major tags (`@v4` etc.), none SHA-pinned.
- Commit-dashboard step copy-pasted in 5 workflows; checkout+setup-python+pip preamble in all 8.

### Lane 2 — Risk & Execution safety

**Single source of truth: five independent copies.**

| # | location | status |
|---|---|---|
| A | `src/risk/position_sizing.py:7-21` (LIVE_TRADING_ENABLED=False, CAPITAL=100.0, RISK=0.01, MAX_POS=4, DAILY=0.05, WEEKLY=0.10, DD=0.15) | **de facto** — executors import this |
| B | `config/risk_config.py:1-8` (identical + `MAX_POSITION_SIZE_PCT=0.25` :4) | **dead** — zero imports; `agent_skills_registry.py:139` imports non-existent `RISK_PER_TRADE_PCT` → ImportError |
| C | `src/risk/position_sizer.py:26,55` (`base_risk_pct=0.02`, no clamp) | **contradicts 1% cap; wins on bridge path** (`execution_bridge.py:35`) |
| D | `src/utils/config.py:24-26` (pydantic) | separate system, used by alpaca/ccxt brokers |
| E | `circuit_breakers.py:10-12` | hardcoded 0.05/0.10/0.15, regime-scaled |

**Order-path gating matrix:**

| Entry point | gate | verdict |
|---|---|---|
| `live_alpaca_executor.py:167-191,198-200` | flag+CB+cap (cap BLOCKS via return) | GATED (except MAX_DRAWDOWN) |
| `live_crypto_executor.py:281-293` | CB yes; **cap BLOCKS via return** | GATED (cap BLOCKS via return; regression-tested) |
| `execution_adapter.py:79-97` | none | UNGATED |
| `execution_bridge.py:16-40` | CB only | UNGATED for flag/cap |
| `main_live.py:193-198` | none (`PAPERBROKER_URL` in env, default localhost) | UNGATED |
| `universal_broker.py:93` | risk-amount only | UNGATED |
| `execution_wrapper.py:46` | fails-closed on exception only | UNGATED |
| `alpaca_broker.py:82` / `ccxt_broker.py:88` | live/paper baked at `__init__` only | UNGATED at order time |
| `async_executor.py:10-17` | none (fan-out) | UNGATED |

Key findings:

| file:line | sev | finding |
|---|---|---|
| `src/risk/position_sizer.py:26,55` | CRITICAL | 2% default contradicts declared 1% cap; no `min()` clamp; worst case ≈6% risk/trade (`execution_bridge.py:35` live path) |
| `src/execution/live_crypto_executor.py:292-293` | RESOLVED | prints then **proceeds** (RESOLVED: cap BLOCKS via return; regression-tested) |
| `config/risk_config.py:1-8` | HIGH | dead duplicate; orphan `MAX_POSITION_SIZE_PCT`; `RISK_PER_TRADE_PCT` mis-import (:139) breaks `agent_a` |
| `alpaca_broker.py:82`, `ccxt_broker.py:88` | HIGH | real sinks with zero runtime gating |
| `main_live.py:192-198` + `execution_adapter.py:97` | MED | ungated orchestrator path; no LIVE_TRADING_ENABLED check |
| `position_sizing.py:21` / executors | MED | `MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT=0.15` defined, never enforced |
| whole repo | MED | `check_order_allowed()` does NOT exist. Hook belongs before: `alpaca_broker.py:82`, `ccxt_broker.py:88`, `live_crypto_executor.py:203/211/222`, `execution_bridge.py:40`, `execution_adapter.py:97`, `async_executor.py:14` |
| `live_crypto_executor.py:231-233` | LOW | dead abort check (impossible conjunction) |

### Lane 3 — Backtest & validation stack

| validation | exists? | wired into main pipeline? |
|---|---|---|
| Permutation | YES — `permutation_tester.py:8`, `validation.py:100` (`run_in_sample_test`, 200 runs) | STANDALONE only (tests/own `__main__`; `self_improvement_agent.py:148`) |
| White's Reality Check | YES — `whites_reality_check.py:6`, `validators/statistical.py:12` | STANDALONE only (tests only) |
| Monte Carlo | **ABSENT** — 0 matches repo-wide; README claims it (README.md:21,114-115) | n/a — does not exist |
| Walk-forward / OOS | YES — `walk_forward_engine.py:9`, `optimization/walk_forward.py:7`, `validation.py:161` | PARTIAL — only `self_improvement_agent.py:153`; main pipeline runs none |
| CPCV | YES — `validators/statistical.py:78` | DEAD CODE — requires `historical_data`, all callers omit it; Darwin gate never fires |
| Darwin "Monte Carlo" gate | `darwin_engine.py:80-92` reads `oos_p_value` | INERT — `oos_p_value` never produced; defaults 1.0 → constant ×0.1 penalty |

**Degenerate committed artifacts:**

| file | exact value |
|---|---|
| `docs/data/strategy_rankings.json:20-25` (all strats) | `is_sharpe: -9.609804245794894e+16`, `oos_sharpe: -7.687837710323362e+16` |
| `docs/data/backtest_report.json:75-76` | `avg_is_sharpe/avg_oos_sharpe` at 1e16 magnitudes |
| `docs/data/backtest_report.json:82-88` | `strategy_return_pct: -0.3005` vs `spy_return_pct: 213.1`, `alpha: -213.4`, Sharpe −27.4 |
| `docs/data/portfolio.json:4-8` | `total_pnl_pct: 99900.0` with `total_trades: 0` |

Producer cause: `comprehensive_backtest_report.py` ~590-597 `get_sharpe` `(excess.mean()/std×sqrt(252)) if std > 0 else 0` — the guard catches only exactly-0 std; near-zero/1-trade std → 1e16 magnitude. **`oos_sharpe` aliased to `train_sharpe`:** `generate_strategy_data.py:357-358`, `run_full_backtest.py:73-74` → `darwin_engine.py:77` `wf_efficiency ≡ 1.0`, promotion gate (:112) always passes. README p-values (`0.1100`/`0.2150`, README.md:114-115) have **zero backing artifacts**.

### 4 — Research

| component | real-or-mock | failure behavior |
|---|---|---|
| `search_strategy_concepts_online` | **MOCK** — `src/research/strategy_research_agent.py:14-20`, returns canned 2-concept JSON; no network | research_agent claims "gemini-2.5-flash" but tool only resolves mock (:111-113); no key → early return (:80-82) |
| `debate_engine` | **MOCK** — `debate_engine.py:10-166` deterministic persona heuristics | — |
| `research_agent` | REAL (injected providers; DDG + Gemini real) | fails open — "mock JSON schema" comment stale (:39) |
| `browser_scraper` | REAL — `browser_scraper.py:18` `feeds.finance.yahoo.com/rss` | 429/5xx → exp backoff (1.0*2^n, 3 retries, :50-54); never raises |
| `agentic_scraper` | REAL — Playwright → DDG fallback → browser_scraper (:25-106) | — |
| yfinance / OpenBB / Reddit | REAL | **yfinance has NO 429/backoff** — `yfinance_provider.py:84-85` bare (chunk failure swallows silently `pass`; <252d tickers silently dropped) |
| gemini_client | REAL | throttle 5 RPM/20 RPD/13s; RPD exceeded → silently passes (:73-75); **model drift: `gemini-3.5-flash` vs `gemini-2.5-flash`** |
| FRED | REAL | 429/5xx retry ≤3; `regime_mult=1.0` fallback |

- **Provider failure mid-pipeline:** `run_research.py:30-35` FRED → `regime_mult=1.0`; per-ticker exceptions logged, loop continues (:70-71). Fail-open throughout.
- **Validation gap (generation → dashboard):** schema mismatch — generator writes `{"strategies": [...]}` (`generate_strategy_data.py:195-203`) but dashboard reads `data.population` (`docs/js/app.js:61`) → always "No active strategies". No threshold gates: zero-trade strategies get all-zero metrics (:315) and pass through. `oos_sharpe`/`train_sharpe` are the same value by construction (:357-358). No validation layer exists between generation and display (confirmed absent).

### Lane 5 — Docs, Dashboard

**Claim table (all vs committed JSON provenance):**

| claim | README/RLV value | backtest_report.json value | contradictions |
|---|---|---|---|
| Final value | $3,434.60 (README:33) | `final_equity: 1645.04` (:93) | none |
| Total return | 108.16% (README:34) | `total_return_pct: -0.3005` (:94) | README vs data |
| CAGR | 10.14% (README:35) | `cagr: -0.0396` (:95) | yes |
| Max DD | 13.76% at 2022-02-11 (README:36) | `0.30%, 2026-08-07` (:96-97) | strong |
| Sharpe | 1.01 (README:37) | `-1.09` (:98) + 1e16 artifacts | strong |
| trades | 484 (README:40) | 1 trade (:103, trade_history.json has exactly 1) | **strong** — 108%:484 vs −0.3%:1 |
| win rate | 52.1% (README:39) | `0.0` (:101) |
| PF | 1.38 (README:41) | `0.0` (:102) |
| raw backtest | +1,479.92% (README:113; RLV:220) | no JSON has 1479.92 | **RLV says +1,700%+ at RLV:95** — two different numbers, neither has provenance |

**update_readme.py idempotency — NOT idempotent:** `scripts/update_readme.py:124` does `replace('## Setup Instructions', section + '## Setup Instructions')` — inserts duplicate blocks every run (no deletion of prior blocks, no markers). Additionally breaks on current schema: reads `report["best_strategy"]["parameters"]["holding_days"]` (:30) which no current JSON has (`atr_trailing_mult`... present). Not wired to any workflow.

**Dashboard freshness:**

| json | regenerated by | stale? |
|---|---|---|
| backtest_report.json / equity_curve.json / quarterly_performance.json / strategy_rankings.json / trade_history.json | daily_research.yml:40 | fresh; **content is deposit artifact** (33.33% = 50/150) |
| research_sentiment.json | run_research.py:76 (daily_research:50) | fresh |
| **strategies.json** | generate_strategies.yml:30 + daily_research:41 | **STALE/ERROR — `"error": "No data available"`** (`docs/data/strategies.json:3-4`, error fallback `_write_empty_strategies()` :362-372) |
| portfolio.json / trades.json | paper_trade.yml | fresh but schema mismatch with consumer |
| apiHealth.json | api_health_check.yml | fresh; `rate_limited`/`not_configured` match producer |

**Dashboard consumer mismatches:** `app.js:61` reads `data.population` (producer writes `data.strategies`); `app.js:24,32-36` reads `wf_efficiency/oos_p_value/active_hypothesis` (paper producer writes none); `app.js:41,47` reads `positions[].symbol` (producer writes `open_positions[].ticker`); `app.js:91` `t.symbol` vs producer `ticker`. Dashboard consumes only **3 of 9** generated JSONs.

**Reconciled values (provenance-first):** $3,434.60 → **$1,645.04** (only JSON equity); 108.16% / +1,479.92% / 1,700%+ → **−0.30%** (only JSON total-return; the README claims have zero JSON provenance and contradict each other); 484 trades → **1** (trade_history.json); 52.1% win → **0.0%**; regime 19/465/0 → **0/1/0**; overfit 42/45/0.49 → **36 overfit / 0 robust / avg 0.0**.

### 6 — Tests, Secrets & Hygiene

- **Tests:** 6 of 15 test files fail to collect locally (`test_quant.py`, `test_nautilus_catalog.py`, `test_data.py`, `backtesting/test_engines.py`, `analytics/test_reporting.py`, `test_agents_and_evolution.py`) — 11 pinned deps (vectorbt, nautilus-trader, alpaca-py, pandera, duckdb, arch, riskfolio-lib, quantstats, langgraph, ccxt, cvxpy) absent from the env; CI passes locally only. `test_pipeline.py` collects 0; `test_backtest_real.py` has 2 pass-only stubs; `test_execution.py` monkeypatches `requests` at module level.
- **Root cruft:** `patch_*.py` ×14, `fix_indent*.py` ×3, `update_auth.py`, root `test_*.py` ×3, `rejected_strategies.log`, `.with-markers`: all **orphans** — zero references in .github/scripts/docs/README (rg-verified). Only `permutation_histogram.png` is referenced (RLV:92); `man_ahl_backtest_equity.png` orphaned. `.acp-ping.txt` untracked & non-gitignored. No CODEOWNERS.
- **Secrets:** No plaintext keys in config/workflows/src (placeholders only). **ONE HIGH:** `update_auth.py:11` commits plaintext dashboard password `WSB-Alpha-2026` + its SHA-256 (:47) — scrub from history and rotate.

## 3. Contradiction List

| # | claim A | claim B | reconciled | basis |
|---|---|---|---|---|
| 5-C1 | $3,434.60 (README:33) | 1,645.04 (JSON) | **1,645.04** | only JSON equity |
| 5-C2/C18/C19 | 108.16% (README:34) · +1,479.92% (README:113) · +1,700%+ (RLV:20) | −0.30% (JSON) | **−0.30%** | only JSON total-return; README says are provenance-free and contradict each other |
| 5-C3-9 | Sharpe 1.01 / 484 trades / 52.1% win / PF 1.38 | / | **−27.44 / 1 trade / 0 / 0** | trade_history has 1 trade |
| 5-C15 | per-year table (64-72 tr/yr) | monthly all-0.0 (deposit artifacts) | **no per-year data exists** | JSON monthly_returns |
| 5-C22 | RLV thresholds 1%/5% | README.md:117 thresholds 1%/1% | **inconsistent across docs** | direct quote |
| 3 | `+1,479.92%` claims Monte-Carlo-validated | MC code absent + artifact −0.3% | **no statistical validation exists** — corpus false | Lane 3 |

## 4. Mapping — Findings → Future Jules Sessions

Session 1 PR (already tracked — **NOT re-reported as new**): risk-config consolidation, API-health cron, README numbers.

**New / carry-forward recommendations that belong in future sessions:**

| Session | findings to include |
|---|---|
| Session 2 — risk-live gates | `live_crypto_executor.py:292-293` return-gate (CRITICAL); `position_sizer.py:26,55` clamp to single source; `MAX_DRAWDOWN` enforcement; remove dead `risk_config.py` + fix `agent_skills_registry.py:139` wrong import; hook list for `check_order_allowed` |
| Session 3 — validation wiring | wire `run_in_sample_test`/`run_walk_forward_test`/Whites into `generate_strategy_data.py` + `run_full_backtest.py`; fix `oos_sharpe` aliasing (generate_strategy_data.py:357-358, run_full:73-74); near-zero-std guard in `get_sharpe` (report <1e-12 → 0); correct README Monte-Carlo claims |
| Session 4 — dashboard contract | fix schema (`data.strategies` vs `data.population`, `oos_p_value`, `positions.symbol/ticker`, `tradese`); `_write_empty_strategies` should never ship to dashboard; guard DEGENERATE values at write; wire `update_readme.py` idempotent block-remove + new schema; reconcile all README/RLV numbers to the JSON |
| Session 5 — hygiene/docs | scrub `WSB-Alpha-2026` from `update_auth.py` + git history; delete orphan patch_*/fix_indent*/root test_*/`update_auth.py`; gitignore `.acp-ping.txt` + `rejected_strategies.log`; remove `aiohttp/ccxt/feedparser/openbb/streamlit` from requirements + dedupe nautilus-trader + pin `defusedxml`; SHA-pin actions; drop `-am` from all 6 commit steps; add `conclusion == 'success'` to pages.yml; stagger/merge paper/sandbox crons; playwright-chromium only-if-missing |

## Append — Verified Highlights (spot-`grep` reconfirmed by orchestrator)

- `.github/workflows/api_health_check.yml:6` → `cron: '*/5 * * * *'`; `:108` → `git commit -am`
- `.github/workflows/self_improvement.yml:49` → `git commit -am`
- `scripts/generate_strategy_data.py:357-358` → `train_sharpe/oos_sharpe = float(sharpe)` ✓ alias
- `README.md:34` → `Total Return 108.16%`, `:40` → `Total Trades 484`, `:113` → `+1,479.92%`
- `src/execution/live_crypto_executor.py:292-293` → print-only guard at cap (RESOLVED: returns since 8bab4faa, gate chain extracted to gates_allow_trading() and regression-tested)
- `docs/data/backtest_report.json` → `report_date 2026-08-08`; is_sharpe/oos_sharpe 1e16 magnitudes