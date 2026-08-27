# ADR 0004 — OpenBB clean-room Registry + ProviderAdapter (not vendored)

**Date:** 2026-08-27
**Status:** Accepted (grilling `grill-me` Q1–Q7, all Recommended; explicitly overrides prior "no expansion" guardrail per user)
**Context:** `OpenBB-finance/OpenBB` 4.7.3 (`72376★, AGPL-3.0-only) provides a mature `Fetcher[Q,R]` TET (transform_query → extract_data → transform_data) + `StandardModel` (Pydantic QueryParams/Data) + `Registry` (entry_points plugin map) + 35 providers (fmp, fred, yfinance, sec, finviz, …) + auto REST + `openbb-platform-api`. Our `DataProviderChain` (Alpaca→Tiingo→Binance→yfinance + `CacheEngine` duckdb) is hardcoded fallback; hunt/research scrapers are ad-hoc. Previous ADR-0002 locked `Instrument = Equity|EqOption`; user invited broader scope.

**Decision:**
1. **Posture: clean-room, not vendored.** Do NOT copy `openbb_core/provider/abstract/fetcher.py` or `standard_models/*.py` into repo — that triggers AGPL-3.0 conveyance if pushed to GitHub. Instead clean-room `src/data/openbb_compat/base.py` as `ProviderAdapter[Q,R]` with renamed API `to_query`/`fetch`/`to_records` (MIT), Pydantic `StandardQuery`/`StandardData` mirroring OpenBB semantics but not text. Optional runtime dep `pip install openbb-core + openbb-yfinance + openbb-fred + openbb-fmp + openbb-sec + openbb-finviz` as *deps* (not vendored) — no AGPL conveyance when used as library/REST loopback.

2. **Providers: +fmp, +sec, +finviz.** Keep `yfinance` + `fred` (free); add `fmp` (screener/balance_sheet/analyst_estimates/government_trades), `sec` (filings, `pit_mode`, `use_cache` — fixes survivorship bias flagged in `BIAS_AND_RISK_ANALYSIS.md`), `finviz` (screening, replaces HTML scrapes in `hunts/`). Free tiers. Defer `bls/cftc/commodity/fixedincome` until Crypto WFO passes.

3. **Registry wraps chain.** `DataProviderChain` becomes one `ProviderAdapter` named `chain` (preserves `CacheEngine` + `fred_macro_provider` RISK_ON/OFF). Each leaf provider also registered. Default calls go via `chain`; research/hunts can call `registry.get("fmp").fetch(...)` directly. `openbb-platform-api` REST (`/api/v1/equity/price/historical?provider=yfinance`) runs locally for hunts; Actions stays file-based; MCP deferred.

4. **Amend instrument:** `Instrument = Equity | EqOption | Crypto` (separate `Crypto(symbol, venue)` with 24/7 calendar, shared `StandardData` OHLCV shape so `indicators`/`validation` permutation unchanged). Commodity/FixedIncome remain deferred.

**Consequences:**
* + Pydantic validation (`symbol→UPPER`, `date` parse, `EmptyDataError`) and `AnnotatedResult` wrapper replace manual DataFrame checks.
* + 5 free providers without new scrapers; sec `pit_mode` hardens WFO.
* + Clean-room avoids AGPL; dependency option preserves OpenBB upgrades.
* − New abstraction to learn; chain→registry migration is incremental.
* − Adding `openbb-*` deps increases `poetry` lock size (mitigated by opt-in).

**Alternatives rejected:**
* Copy-paste `fetcher.py` → `src/openbb_compat/` — rejected: AGPL trap.
* `pip install openbb` monolith only — rejected: heavy, pulls 21 extensions.
* Replace chain outright — rejected: would break `CacheEngine` and require rewriting every `yf.download` site synchronously.

**Glossary impact:** Defines `StandardQuery`, `StandardData`, `ProviderAdapter`, `Registry`, `Chain`, `Crypto`, `REST (local)` in `CONTEXT.md`; amends `Instrument`.
