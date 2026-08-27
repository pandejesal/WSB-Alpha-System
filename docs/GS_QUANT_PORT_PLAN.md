# gs-quant → WSB-Alpha-System Port Plan (Grilling Output 2026-08-27)

> Every branch visited, frontier empty. This is the build manifest for Jules / OpenCode.

## Decision log (all Recommended, user-confirmed)

Q1 Vendored patterns, Q2 Expand to EqOption-only, Q3 Timeseries+Calendar first, Q4 GitHub-free invariant, Q5 EqOption single-leg PMCC, Q6 Cherry-pick 20 timeseries fns, Q7 NYSE GSCalendar + Window=TradingDays, Q8 BS hybrid shocks, Q9 Glossary accepted, Q10 Gate stays strict + IV/DTE filters, Q11 `src/gs_compat/` isolated layout.

## What NOT to port (explicitly rejected)

* `GsSession` / `GsRiskApi` / `GsDataApi` / `RiskRequest` RPC — credential-locked.
* `Instrument` 40-class hierarchy — only `EqOption` (see ADR-0002).
* `models/epidemiology` SIR/SEIR — irrelevant.
* Full `timeseries.algebra` DSL as mandatory pipeline — keep as utilities only.
* `dataclass_json(LetterCase.CAMEL)` + `handle_camel_case_args` — stay `pydantic`/`settings.yaml`.

## What TO port — concrete file map

### 1) `src/gs_compat/calendar.py` — pure, vendored from `gs_quant/datetime/*`

Functions (signatures kept, impl copied + Apache header):
`is_business_day(date, calendar='NYSE')`, `prev_business_date(date)`, `business_day_offset(date, n)`, `business_day_count(start, end)`, `date_range(start, end)` + `GSCalendar` (holiday JSON cached in `data/nyse_holidays.json`, no network).

**Fixes:**
* `src/backtest/validation.py:156` — `timedelta(days=90)` → `Window(90).to_dates(start)` via `business_day_offset`.
* `src/backtest/run_historic_backtest.py` — T+1 roll uses `business_day_offset`.

**Test:** add `tests/test_gs_calendar.py` — assert NYSE 2024-07-04 is not business day.

### 2) `src/gs_compat/timeseries/` — cherry-pick 20, vendored from `gs_quant/timeseries/*`

```
econometrics.py: returns, excess_returns, volatility(ann), correlation, beta, sharpe_ratio, max_drawdown, annualize, change
statistics.py:  mean, std, var, winsorize, zscores, percentile/percentiles, mode, generate_series, rolling LinearRegression helper
technicals.py:  moving_average, exponential_moving_average, bollinger_bands, relative_strength_index, exponential_volatility
algebra.py:     if_, filter_, weighted_sum   (utilities, not DSL)
helper.py:      Window, normalize_window, Interpolate
datetime.py:    align, interpolate, union
```

**Shim:** `src/alpha/indicators.py` stays public API; delegate inside: `from src.gs_compat.timeseries.technicals import relative_strength_index as gs_rsi`.

**Why not full DSL:** `BaseStrategy.generate_signals(df) -> df` is DataFrame-native; gs-quant algebra is Series→Series. Wrapping everything would force a rewrite; cherry-pick preserves idiom and keeps Actions import <1s.

### 3) `src/pricing/bs.py` — new, not vendored (gs-quant has no open BS; Marquee does)

```py
def bs_price(S, K, T, r, sigma, is_call: bool) -> float
def bs_greeks(S, K, T, r, sigma, is_call) -> {delta, gamma, theta, vega}
```

Pure `scipy.stats.norm.cdf/pdf`, guard `T<=0 or sigma<=0 → intrinsic`. Used by `Scenario` shocks.

### 4) `src/risk/scenario.py` — new, inspired by `gs_quant/risk/scenarios.py`

```py
@dataclass class ParametricShock(spot: float, vol: float)  # e.g., -0.2, +0.4
@dataclass class HistoricalScenario(start: date, end: date)
def apply_shock(instrument: Instrument, shock, greeks) -> shocked_price
```

Wire to `src/risk/circuit_breakers.py` + `src/risk/fred_macro_provider.py: RISK_OFF → ParametricShock`.

### 5) Validator delta — `src/backtest/validators/statistical.py`

Add `EqOptionValidator` subclass: `require iv_coverage >= 0.80` and `DTE > 7`, else `FAIL_CLOSED`. Keep `p < 0.01 IS, p < 0.05 WFO, WFE ≥ 0.7`.

## Implementation order (Jules-routable, one prompt per session)

1. **Calendar** — `src/gs_compat/calendar.py` + holiday JSON + `validation.py` Window fix + test. (No EqOption yet.)
2. **Timeseries cherry-pick** — `src/gs_compat/timeseries/{econometrics,statistics,technicals,helper}` + `indicators.py` shim + `metrics.py` delegation + tests against `safe_sharpe`.
3. **BS pricer** — `src/pricing/bs.py` + `tests/test_bs_greeks.py` (put-call parity, delta bounds).
4. **Scenario** — `src/risk/scenario.py` + wiring to `circuit_breakers` + `fred_macro_provider` + `docs/data` shock metric.
5. **EqOption** — `src/alpha/schemas.py` `Instrument` union, `DataProviderChain` yfinance chain branch, `AlpacaBroker` `supports_options_single_leg`, validator IV filter, one PMCC strategy under `src/alpha/`.

## Risks & mitigations (from Q2)

* **IV sparsity → fantasy Sharpe** — mitigated by 80% coverage gate, fail-closed.
* **Gamma singularity near expiry** — mitigated by DTE>7 block.
* **Parameter explosion** — mitigated by keeping Darwin 5-param vector, options add only `delta` filter via trial_ledger deflation.
* **Actions minutes** — mitigated by lazy import, duckdb cache, vendored holidays (no network on test).

## Verification (must pass before merge)

```
PYTHONPATH=. pytest tests/test_gs_calendar.py tests/test_bs_greeks.py -v
ruff check src/gs_compat src/pricing src/risk/scenario.py
bandit -r src/gs_compat src/pricing -lll
PYTHONPATH=. pytest tests/test_session4_lookahead.py -v  # T+1 still holds with TradingDay
```

## References

* gs-quant commit `fa9dd42`, Apache-2.0, `pyproject.toml` deps: numpy<2.4, scipy, statsmodels, pandas≥1.4
* Local: `CONTEXT.md`, `docs/adr/0001..0003`, `wsb_factual_research_data.csv` (no synthetic data), `docs/OPTIMIZATION_PLAYBOOK.md`, `docs/HUNT_PROTOCOL.md`
