# OpenBB → WSB-Alpha-System Port Plan (Grilling `grill-me` 2026-08-27)

> Second session, user explicitly allowed new scope beyond prior ADR-0002. All 7 questions settled as Recommended.

## Decision log

Q1 Clean-room `ProviderAdapter` (+ opt-in deps, never vendored AGPL), Q2 +fmp+sec+finviz, Q3 `openbb-platform-api` REST locally, MCP deferred, Q4 Amend to `Equity|EqOption|Crypto`, Q5 clean-room rename `ProviderAdapter`, Q6 Registry wraps chain, Q7 separate `Crypto` type.

## What NOT to port

* `openbb_core/provider/abstract/fetcher.py` text — AGPL trap; reimplement semantics only.
* `extensions/commodity`, `fixedincome`, `currency` — deferred behind Crypto WFO.
* `providers/bls/cftc/oecd/...` macro — deferred.
* `openbb-mcp-server` — deferred.
* Copy of `standard_models/*.py` — reimplement as `StandardQuery`/`StandardData` with Pydantic.

## What TO port — concrete file map

### 0) `src/data/openbb_compat/base.py` — NEW, clean-room, MIT

```py
class StandardQuery(BaseModel): ...
class StandardData(BaseModel): ...
class ProviderAdapter(Generic[Q,R]):
    def to_query(self, params: dict) -> Q: ...
    def fetch(self, query: Q, creds: dict|None) -> Any: ...  # or async afetch
    def to_records(self, query: Q, raw: Any) -> list[R] | AnnotatedResult
    @classmethod
    def fetch_data(cls, params, creds=None) -> list[R]: ...
```

500 lines max, Pydantic, no import from `openbb_core`. Mirrors `Fetcher` TET but renamed to prove clean-room. Include `EmptyDataError`, `AnnotatedResult`.

### 1) `src/data/openbb_compat/registry.py` — NEW

```py
class Registry: providers: dict[str, ProviderAdapter]
class RegistryLoader:
    @staticmethod
    def from_entrypoints() -> Registry: ...  # reads entry_points("wsb.providers")
    @staticmethod
    def default() -> Registry: ... # pre-registers chain, yfinance, fmp, sec, finviz, fred
```

`Registry.default()` builds: `chain` (see 2), `yfinance`, `fmp`, `sec`, `finviz`, `fred` — each is a thin `ProviderAdapter` wrapping existing provider modules.

### 2) `src/data/openbb_compat/providers/{yfinance,fmp,sec,finviz,fred}.py` — NEW wrappers

* `yfinance` — wrap existing `src/data/providers/yfinance_provider.py` + add `interval`, `adjustment`, `split_ratio/dividend` fields (from `openbb_yfinance/models/equity_historical.py`) to `StandardData`.
* `fred` — wrap `src/risk/fred_macro_provider.py`; expose as `FredSeriesQuery(symbol="T10Y2Y")` → `FredSeriesData`.
* `fmp` — NEW alternative to Tiingo for equities; implements `EquityHistoricalQuery(fmp)`, `EquityScreenerQuery`, `BalanceSheetQuery`. Uses `FRED_API_KEY`/`FMP_API_KEY` from `src/utils/config.py`; fail-closed.
* `sec` — NEW filings provider; `CompanyFilingsQuery(symbol, use_cache=True, pit_mode=True, include_preliminary=True)`.
* `finviz` — NEW screener provider; `ScreenerQuery(filters)`.

Each provider reads credentials via `src/utils/config.py` pydantic-settings, never hardcodes.

### 3) `src/data/providers/chain.py` — MODIFY (wrap, not replace)

Add `class ChainAdapter(ProviderAdapter[EquityHistoricalQuery, list[EquityHistoricalData]])` that delegates to existing `DataProviderChain` (Alpaca→Tiingo→Binance→yfinance) and `CacheEngine` (duckdb). Register as `registry.get("chain")` default. Keep `yf.download` call sites working; new hunt code uses `registry.get("fmp")`.

### 4) `src/alpha/schemas.py` — MODIFY

Amend `Instrument` union: `Equity | EqOption | Crypto` (per CONTEXT.md). Crypto has `venue` and uses 24/7 calendar (bypass `is_business_day`).

### 5) `pyproject.toml` / `requirements.txt` — MODIFY (opt-in, not mandatory)

```toml
[tool.poetry.dependencies]
openbb-core = {version="^1.6.13", optional=true}
openbb-yfinance = {version="^1.6.3", optional=true}
openbb-fred = {version="^1.6.2", optional=true}
openbb-fmp = {version="^1.6.1", optional=true}
openbb-sec = {version="^1.6.7", optional=true}
openbb-finviz = {version="^1.5.1", optional=true}
openbb-platform-api = {version="^1.3.6", optional=true}
[tool.poetry.extras]
openbb = ["openbb-core","openbb-yfinance","openbb-fred","openbb-fmp","openbb-sec","openbb-finviz"]
```

Actions free tier still passes without them (all `ProviderAdapter.fetch` fail-closed with warning).

### 6) `scripts/run_research.py` + `src/research/*` — MODIFY (optional, Step 3)

If `openbb-platform-api` installed, `skill_executor.py` can call `http://0.0.0.0:8000/api/v1/equity/price/historical` instead of direct import — same data, tool-call friendly for LLM hunts.

## Implementation order (Jules-routable, one prompt per lane)

1. **Compat base + registry** — `base.py` + `registry.py` + unit test `tests/test_openbb_compat_base.py` (no provider network).
2. **yfinance + fred wrappers + chain wrap** — `providers/yfinance.py`, `providers/fred.py`, modify `chain.py` to expose `ChainAdapter`; `registry.default()` test.
3. **fmp + sec + finviz** — three new `ProviderAdapter`s; integration test marked `@pytest.mark.integration` (skipped on CI without keys), fail-closed assertion with no creds.
4. **Crypto instrument** — `schemas.py` amendment + `binance_public_provider` as `crypto` adapter + `tests/test_crypto_instrument.py` (24/7 calendar bypass).
5. **REST hook** — `docs` note + `make openbb-api` target; no code change to Actions workflows.

## Verification

```
ruff check src/data/openbb_compat
bandit -r src/data/openbb_compat -lll
PYTHONPATH=. pytest tests/test_openbb_compat_base.py tests/test_gs_calendar.py -v  # calendar from Step 1
PYTHONPATH=. pytest -m "not integration"  # no network
```

No AGPL text in repo; `pyright`/`ruff` must not flag `openbb_core` import in `src/` (only in optional wrappers when dep installed, guarded by `try: import openbb_core`).

## Relationship to gs-quant plan

`GS_QUANT_PORT_PLAN.md` Steps 1–5 remain: calendar (Jules 778798697557805121 IN_PROGRESS) → timeseries → BS pricer → scenario → EqOption. OpenBB Steps 1–5 run *in parallel* as a separate lane — they share `CONTEXT.md` `Instrument`/`Window` definitions and `src/data/` but do not block each other.
