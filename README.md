# WSB-Alpha-System

An autonomous, agentic quantitative trading system that turns retail-sentiment signals into a validated, statistically-hardened strategy pipeline -- fully hosted on GitHub's free infrastructure (Actions + Pages).

It scrapes public sentiment (Reddit / web research), prices a universe of stocks through a multi-provider OHLCV fallback chain, runs lookahead-free backtests with honest statistical validation, evolves parameters with a DERM-style evolutionary gate, paper-trades every weekday, and publishes a static dashboard.

## How it works

```
Social & web research        Reddit scraper (PRAW), web-search providers, Gemini-2.5-flash
        │
        ▼
Sentiment & thesis signals ──► src/research/  (ticker extraction, NLP scoring)
        │
        ▼
OHLCV market data ──► DataProviderChain: Alpaca → Tiingo → Binance (public) → yfinance
        │              CacheEngine (duckdb) dedup + incremental backfill
        ▼
Backtest engines ──► run_historic_backtest.py (T+1, ATR slippage, GK-vol shield)
        │              VectorBT / Nautilus engines for evolution runs
        ▼
Statistical validation ──► src/backtest/ validation, permutation tests, walk-forward,
        │                     deflated Sharpe (trial ledger / DSR helper)
        ▼
Evolution & selection ──► src/evolution/darwin_engine.py  (promotion only on OOS evidence)
        ▼
Execution / paper trading ──► AlpacaBroker, CCXTBroker, paper_trading_sandbox.py
        │                        (risk-capped, ATR stops, position sizing)
        ▼
Dashboard & monitoring ──► docs/ static GitHub Pages dashboard, Telegram alerts, API health checks
```

## Repository layout

| Path | Purpose |
|------|---------|
| `src/data/` | Market-data providers and the fallback chain: `providers/chain.py` (`DataProviderChain`), `providers/alpaca_data_provider.py`, `providers/tiingo_provider.py`, `providers/binance_public_provider.py`, `providers/yfinance_provider.py`, `cache_engine.py` (duckdb), `market_data.py`, `nautilus_catalog.py` |
| `src/backtest/` | `run_historic_backtest.py` (honest backtest engine), `validation.py` (in-sample + walk-forward permutation p-values), `metrics.py` (`safe_sharpe` / `safe_sortino`), `permutation_tester.py`, `walk_forward_engine.py`, `whites_reality_check.py`, `engines/` (vectorbt, nautilus) |
| `src/evolution/` | `darwin_engine.py` (evolutionary strategy selection with complexity penalty + promotion gate), `strategy_selector.py` |
| `src/risk/` | `fred_macro_provider.py` (FRED regime classification: RISK_ON / RISK_OFF / STAGFLATION / NEUTRAL), `position_sizing.py`, `portfolio_manager.py`, `circuit_breakers.py` |
| `src/research/` | `reddit_scraper.py`, `ticker_extractor.py`, `nlp_utils.py`, `strategy_research_agent.py`, `self_improvement_agent.py`, `skill_executor.py`, `google_search_provider.py`, `agentic_scraper.py` (Playwright) |
| `src/execution/` | `base_broker.py`, `alpaca_broker.py`, `ccxt_broker.py`, `execution_wrapper/bridge/adapter.py`, `live_alpaca_executor.py`, `live_crypto_executor.py` |
| `src/monitoring/` | `telegram_bot.py` (notifications; returns `False` + warning on missing credentials), `dashboard.py` (deprecated stub -- real dashboard lives in `docs/`) |
| `src/utils/` | `config.py` (pydantic-settings, `.env` + `config/settings.yaml`), `gemini_provider.py` / `gemini_client.py` (Google `google-genai`, `gemini-2.5-flash`) |
| `config/` | `universe.json` (ticker universe), `settings.yaml` (trading flags) |
| `scripts/` | `run_full_backtest.py`, `generate_strategy_data.py`, `comprehensive_backtest_report.py`, `paper_trading_sandbox.py`, `run_research.py`, `check_market_data.py` |
| `tests/` | pytest suite covering indicators, data, providers, backtest, validation, execution, risk, evolution, sandbox |
| `docs/` | Static dashboard (GitHub Pages) + `data/*.json` artifacts (backtest_report, strategies, equity_curve, trades, portfolio, apiHealth, ...) |
| `.github/workflows/` | 8 scheduled / triggered pipelines (see below) |

## Data providers

OHLCV data is fetched through an ordered fallback chain (**Alpaca → Tiingo → Binance (public) → yfinance**) so a single provider outage never blocks the pipeline:

- `AlpacaDataProvider` -- requires `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`; disabled (empty) without keys.
- `TiingoProvider` -- requires `TIINGO_API_KEY`; retries (`429` / 5xx) with exponential back-off.
- `BinancePublicProvider` -- public REST endpoints, no keys required (weight-limited).
- `YFinanceProvider` -- last-resort fallback, cached via `CacheEngine`.
- `CacheEngine` -- duckdb-backed local cache; deduplicates and backfills only the missing ranges.

FRED macro data (`T10Y2Y` term spread + `T10YIE` inflation) is used for regime classification; it fails closed to `NEUTRAL` when `FRED_API_KEY` is unset or data is unavailable.

## Backtesting & validation

The system takes an aggressive anti-overfit stance:

- **No look-ahead:** entries are decided on the last closed bar (`decision_iloc = entry_iloc - 1`) and filled at the **next** bar's open; execution rolls to the next business day (`T+1`), asserted in `tests/test_session4_lookahead.py`.
- **Realistic frictions:** ATR(14)-based slippage clamped to 0.1%-2.5% per side, SEC/TAF regulatory fees, small-cap spread assumptions. See "Assumptions" in the backtest report.
- **Statistical gates:** in-sample + multi-year rolling walk-forward Monte-Carlo permutation tests (`permutation_tester.py`, Timothy Masters' methodology) with p-value thresholds (`< 0.01` IS, `< 0.05` WF for promotion).
- **Safe metrics everywhere:** `safe_sharpe` / `safe_sortino` (`src/backtest/metrics.py`) return `0.0` instead of astronomical values when returns have near-zero std.
- **No aliased metrics:** `generate_strategy_data.py` computes true out-of-sample Sharpe per candidate (80/20 partition) and reports walk-forward efficiency (`OOS_sharpe` vs `IS_sharpe`); the dashboard marks likely-overfit strategies.

## Evolution & self-improvement

- **`darwin_engine.py`** evolves populations of `(rsi_low, rsi_high, min_confluence, holding_days, gk_vol_limit)` parameter sets. Promotion requires out-of-sample evidence; strategies marked likely-overfit are not promoted.
- **`src/research/self_improvement_agent.py`** proposes exactly one parameter change against the strategy engine, logs the proposal to `self_improvement_log.md`, and the change is committed to `src/backtest/run_historic_backtest.py` by the `Bounded Self-Improvement Loop` workflow.
- **`strategy_research_agent.py`** performs real web searches (DuckDuckGo + `google_search_provider.py`) -- no mock search stubs.

## Execution

| Mode | Where | Details |
|------|-------|---------|
| Paper (GitHub) | `paper_trade.yml` / `paper_trading_sandbox.py` | Weekday 3:55 PM EST simulated portfolio, saved to `docs/data/` |
| Sandbox | `sandbox.yml` | 5-day scripted sandbox (pre-trading simulations) |
| Live (optional) | `live_alpaca_executor.py`, `live_crypto_executor.py` | Requires `LIVE_TRADING_ENABLED=True` and real broker credentials; defaults to **disabled** |

All brokers implement risk controls: position sizing (`position_sizing.py`), ATR-based stops, circuit breakers, and fails-closed behavior when credentials are missing (no dummy/mock credentials or silent mock fallbacks -- ccxt broker raises `ValueError`/`ImportError` on config miss).

## GitHub Actions pipelines

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| `ci.yml` | on push to `main` | `pytest tests/ -v --cov=src`, `bandit`, `ruff` |
| `daily_research.yml` | 08:00 UTC daily | Runs `comprehensive_backtest_report.py` + `generate_strategy_data.py` + `run_research.py`; commits dashboard JSON |
| `generate_strategies.yml` | 07:00 UTC Sunday | Regenerates `docs/data/strategies.json` from the evolution pipeline |
| `paper_trade.yml` | 20:55 UTC Mon-Fri | Daily paper trading (3:55 PM ET) with real mark-to-market |
| `sandbox.yml` | 20:55 UTC Mon-Fri | Runs the 5-day paper sandbox |
| `self_improvement.yml` | 12:00 UTC Saturday | LLM proposes one parameter change; commits if accepted |
| `api_health_check.yml` | hourly | Pings external data APIs and records status to `docs/data/apiHealth.json` |
| `pages.yml` | on `docs/**` push | Deploys `docs/` as GitHub Pages |

The static dashboard (`docs/index.html` + vanilla JS) reads the committed JSON artifacts in `docs/data/` and is published automatically.

## Setup

**Requirements:** Python 3.12, Git, GitHub Actions (for scheduled runs).

### 1. Install

```bash
git clone https://github.com/pandejesal/WSB-Alpha-System.git
cd WSB-Alpha-System
python -m venv .venv && .venv\Scripts\activate   # Windows
# or: source .venv/bin/activate                    # Linux/macOS
pip install -r requirements.txt
```

### 2. Environment variables

Copy `.env.example` to `.env` and fill in what you need:

```dotenv
# Trading Configurations
LIVE_TRADING_ENABLED=False
PAPER_TRADING_ENABLED=True

# API Keys
ALPACA_API_KEY=""        # paper/live equities + market data
ALPACA_SECRET_KEY=""
GEMINI_API_KEY=""        # LLM research + self-improvement loop
ANTHROPIC_API_KEY=""     # optional alternate LLM
OPENROUTER_API_KEY=""
APIFY_TOKEN=""           # optional scraping
REDDIT_CLIENT_ID=""      # sentiment source (PRAW)
REDDIT_CLIENT_SECRET=""
BINANCE_API_KEY=""       # crypto (optional)
BINANCE_SECRET_KEY=""
TELEGRAM_BOT_TOKEN=""    # notifications (optional; missing => disabled with warning)
```

For GitHub Actions, set the same names as **repository secrets** (at least `GEMINI_API_KEY` for research flows, `ALPACA_*` for data/paper trading, `TIINGO_API_KEY` for the Tiingo tier).

### 3. Run locally

```bash
# Backtest report (writes docs/data JSON)
PYTHONPATH=. python scripts/comprehensive_backtest_report.py

# Dashboard strategy data
PYTHONPATH=. python scripts/generate_strategy_data.py

# Paper-trading day (1-5)
PYTHONPATH=. python scripts/paper_trading_sandbox.py --day 1

# Daily research (sentiment + regime)
PYTHONPATH=. python scripts/run_research.py
```

### 4. Quality gates

```bash
pytest tests/ -v --cov=src
bandit -r src/ -lll -c bandit.toml
ruff check src/
```

## Known limitations & honest-claims policy

- **Historical backtest claims** in this README are replaced by the live report pipeline: see `docs/data/backtest_report.json`, `docs/data/strategies.json` and the published Pages dashboard for the current, freshly computed numbers.
- Strategy returns can show an edge in-sample only; the walk-forward permutation p-value is the published viability metric (see `REAL_LIFE_VIABILITY.md`).
- Survivorship bias: the current ticker universe is used, delisted tickers excluded.
- Daily OHLCV only; no intraday. Spread/slippage are modeled, not measured.
- The report pipeline has had historical metric bugs (near-zero-std Sharpe artifacts); `safe_sharpe`/`safe_sortino` + permutation gates are now the guardrails (see `AUDIT_REPORT.md` for the full audit trail).

## Also in docs/

- `docs/BLUEPRINT.md` -- quantitative overhaul blueprint (SMC definitions, position sizing, walking-speed gates)
- `AUTOMATION.md`, `PROMPT_ENGINEERING.md` -- design notes
- `PAPER_BROKER_SETUP.md` -- paperbroker walkthrough
- `BIAS_AND_RISK_ANALYSIS.md` -- bias & risk review
- `REAL_LIFE_VIABILITY.md` -- statistical viability findings
- `web-research/*.md` -- researched corpus used for strategy and infra decisions
- `self_improvement_log.md` -- audit log of every applied self-improvement change