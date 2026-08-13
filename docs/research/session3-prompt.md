# Session 3 — Jules Task Prompt (DRAFT v1)

Branch: main | Source: sources/github/pandejesal/WSB-Alpha-System | Auto PR: yes

---

## MISSION

Build a real multi-provider OHLCV fallback chain into the repo's data layer so the engine stops depending on
`yfinance` as its primary (and only reliable) source. The current state: `YFinanceProvider` is the engine's
workhorse and `OpenBBProvider` merely wraps it — every provider currently bottoms out in
`yf.download(...)`, which is rate-limited and unreliable in 2026. There is already a `BaseDataProvider`
ABC with a single interface (`fetch_ohlcv`, `fetch_sentiment_feed`) — keep that contract stable.

## READ FIRST (committed to main in web-research/)

1. `web-research/financial-data-sources.md` — the source of truth for provider facts (Alpaca data API,
   Tiingo, Binance public endpoints, free tiers, rate limits, auto-adjust semantics).
2. `web-research/synthesis.md` — section "P1 Data & Execution Reliability", item 5 (migration plan) and
   section 2 row 4 (verified call-site count: 60 matches / 24 files).
3. `web-research/execution-ops.md` and `web-research/autod-trading-failures.md` — retry/backoff and
   fail-closed discipline; do not contradict them.
4. Current code, in this order: `src/data/providers/base.py`, `src/data/providers/yfinance_provider.py`,
   `src/data/providers/openbb_provider.py`, `src/data/cache_engine.py`, `src/data/schemas.py`,
   `src/data/market_data.py`, `src/data/nautilus_catalog.py`, `config/universe.json`.

## SCOPE

### A. Provider chain (new module `src/data/providers/chain.py`)

Implement `DataProviderChain(BaseDataProvider)`:

- Fallback ORDER (from the research doc): Alpaca data API -> Tiingo -> Binance public (US-safe) -> yfinance
  LAST RESORT. Each step: try a **bounded per-call** fetch with a short timeout; on failure (network,
  4xx/5xx, empty DataFrame, wrong-schema), log a concise warning and move to the next provider. Do NOT wrap
  the whole chain in one giant try/except that swallows errors from every step without testing each one.
- **Alpaca step** (`src/data/providers/alpaca_data_provider.py`): use `alpaca-py` (already in
  `requirements.txt`, pinned `alpaca-py==0.35.0`) — the historical data REST client. Pay attention to:
  - `ORIGINAL:true` vs `ADJUSTED` — research doc says yfinance `auto_adjust=True` today; decide the default
    and note it in the docstring.
  - Equity vs crypto symbol translation: repo tickers are `BTC-USD`/`ETH-USD`/`SOL-USD` style in several
    places; Alpaca uses `BTC/USD` syntax `BTC/USD` for crypto. Implement a small `normalize_symbols` map; keep alias support.
  - Pagination: `limit` + per-frame; decide `start`/`end` handling and default timeframe day.
  - Timezone index handling — the schema expects a `Date` column (see `src/data/schemas.py`).
- **Tiingo step** (`src/data/providers/tiingo_provider.py`): free tier, needs `TIINGO_API_KEY` env. If the
  env var is missing in a run: log a warning and skip Tiingo — never block the chain.
- **Binance public step** (`src/data/providers/binance_public_provider.py`): free public REST, no key; US-
  safe: use `https://data-api.binance.vision/api/v3/klines` (the public data API for US customers).
  Crypto only (BTC/ETH/SOL style) — equities must skip this step. Interval 1d, limit for range, UTC Timezone
  handling (klines are UTC ms).
- **yfinance step**: deprecate-but-keep the existing `YFinanceProvider` as the LAST resort; it must remain
  loadable with the same schema.

### B. Wire the chain into the live path

- `src/data/market_data.py` and `src/data/nautilus_catalog.py` currently call `yfinance` directly
  (verified: `src/data/market_data.py:36`, `src/data/nautilus_catalog.py:27`). Route them through a
  singleton `get_provider()` (cache the chain instance per-process) instead of the raw import.
- Keep `cache_engine` interaction: write through the SAME `CacheEngine` the current provider uses
  (`determine_missing_ranges` / `get_ohlcv` / `store_ohlcv` — see `yfinance_provider.py` for the existing
  flow). Do not double-write.
- Do NOT touch `src/backtest/validators/statistical.py`, `src/backtest/permutation_tester.py`,
  `src/risk/fred_macro_provider.py` (another session owns them; keep out of scope).

### C. Scripts (lower priority, do last)

Update the four scripts that call `yf.download` directly to use the chain:
`scripts/run_full_backtest.py`, `scripts/paper_trading_sandbox.py`, `scripts/generate_strategy_data.py`,
`scripts/comprehensive_backtest_report.py`. If time is short, convert the first two and leave the last two
with the minimal (commented) pointer — the later session can finish them. Only that. Do not go wild about
every test.

## HARD CONSTRAINTS

1. Do NOT modify: `src/backtest/validators/statistical.py`, `src/backtest/permutation_tester.py`,
   `src/risk/fred_macro_provider.py`.
2. Do NOT change any risk constants or config (`config/risk_config.py`, `config/settings.yaml` untouched).
3. Do NOT add new dependencies beyond what's already in `requirements.txt` (note: if `tiingo` is required
   at tiny sink, use a plain `requests` against their REST — it's a simple path; `ccxt` is optional — prefer a
   tiny `requests`-based client where possible to avoid new pinned deps).
4. Keep every public function signature backwards compatible where callers exist. Search for callers before
   renaming.
5. Never invent API endpoints or params — if the doc doesn't confirm them, write `VERIFY:` reminders inside
   the code for the human.
6. No heavy refactors: only the chain + providers + the two wiring points + the two scripts.
7. Follow existing style: file-level `logger = logging.getLogger(__name__)`, docstrings, type hints
   (the repo uses them).

## DELIVERABLES

- New files: `src/data/providers/chain.py`, `src/data/providers/alpaca_data_provider.py`,
  `src/data/providers/binance_public_provider.py`, (+ `tiingo_provider.py` optional; it may be a light
  wrapper of requests).
- Modified: `src/data/providers/__init__.py` (expose at will), `src/data/market_data.py`,
  `src/data/nautilus_catalog.py`, `scripts/run_full_backtest.py`, `scripts/paper_trading_sandbox.py`
- Tests: test files for each provider step: mocked HTTP responses (no live network!), a test that the chain
  order is respected (simulate first provider returning empty DataFrame -> second called), and
  a test that yfinance step is last.
- Update: extend the docs in `docs/research` if needed for providers with `VERIFY` notes.

## PR EXPECTATION

- ONE pr;'small, reviewable; squash-like. CI runs are automatically checked — keep it green.
- PR body: what changed, which call sites now route to the chain, which ones remain on direct yfinance
  (migration percentage), and the exact `VERIFY` items on provider API/limits leftover for humans.

## Good luck — ground everything in web-research/financial-data-sources.md. If any naming above is
inconsistent with the repo (files differ), adapt your plan and note it in the PR instead of refusing.