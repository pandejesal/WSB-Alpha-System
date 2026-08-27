# ADR 0001 — Vendored gs-quant math, not Marquee transport

**Date:** 2026-08-27
**Status:** Accepted (grilling Q1+Q4, unanimous "Recommended")
**Context:** `goldmansachs/gs-quant` grilling session — repo `WSB-Alpha-System-build` is a sentiment-driven cash-equity system running on GitHub free infra. gs-quant couples its valuable math to `GsSession`/`GsRiskApi`/`GsDataApi`/`dataclass_json`+`camelize` which require Marquee credentials and break `fail-closed, no mocks` invariant. Adding `gs-quant` as a dep would import `numpy<2.4`, `scipy`, `statsmodels`, `pydash`, `lmfit`, `cachetools`, plus network session state for ~60% locked APIs.

**Decision:** **Do not add `gs-quant` as a dependency.** Vendor only the pure, offline math under `src/gs_compat/` with Apache-2.0 headers and re-export via existing shims:

* `src/gs_compat/timeseries/` — cherry-picked 20 functions (returns, volatility, beta, correlation, sharpe, max_drawdown, zscores, winsorize, percentile, EMA/SMA/RSI/BB, align/interpolate, `Window`) — no `algebra` DSL mandate.
* `src/gs_compat/calendar.py` — `is_business_day`, `prev_business_date`, `business_day_offset`, `business_day_count`, `date_range` + cached `GSCalendar` (NYSE holidays JSON, no network).
* No `GsSession`, no `RiskRequest` RPC, no `dataclass_json(LetterCase.CAMEL)`, no `Priceable.resolve()`.

**Consequences:**
* + Runs on Actions free tier, cached, <2s import, no secrets.
* + Attribution clean, `ruff`/`bandit` lintable separately.
* − We own the vendored code (must backport fixes manually).
* − No auto-updates from upstream; pin vendored commit `fa9dd42`.

**Alternatives rejected:**
* `pip install gs-quant` — rejected: credential coupling + version pin fragility.
* Patch `indicators.py` directly — rejected: loses provenance.

**Glossary impact:** Defines `Vendored Math` and `GitHub-Free Invariant` in `CONTEXT.md`.
