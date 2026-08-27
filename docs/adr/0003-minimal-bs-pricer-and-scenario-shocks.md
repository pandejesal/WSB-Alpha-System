# ADR 0003 — Minimal BS pricer and scenario shocks on free infra

**Date:** 2026-08-27
**Status:** Accepted (grilling Q8+Q10+Q11)
**Context:** gs-quant stress tests via `MarketDataShock`/`CompositeScenario`/`RiskRequest` RPC to Marquee pricer. We must run shocks on Actions free tier with no network and no vol cube. `fred_macro_provider` already classifies RISK_ON/OFF/STAGFLATION/NEUTRAL and `circuit_breakers` can consume shocks, but there is no pricer and `validation.py` permutation windows are naive `timedelta(days=90)`.

**Decision:** Hybrid offline shock engine:

* `src/pricing/bs.py` — `bs_price(S,K,T,r,sigma,is_call)`, `bs_greeks(S,K,T,r,sigma)` (delta/gamma/theta/vega), pure `scipy.stats.norm`, ~80 lines, `numpy<2.4` compatible.
* `Scenario = HistoricalScenario` (replay 90-TradingDay crash bars) `|` `ParametricShock(spot, vol)` applied analytically via BS.
* Wiring: `fred_macro_provider` RISK_OFF → `ParametricShock(spot=-0.2, vol=+0.4)`; `circuit_breakers` consumes greeks; validator adds hard filters `IV_coverage ≥ 80%` and `DTE > 7` (no gamma singularity), gate thresholds stay `p < 0.01 IS, p < 0.05 WFO` (no loosening).

**Consequences:**
* + Deterministic, cached, <50ms per 1k options on Actions 2-core.
* + Defended: `trial_ledger` deflated Sharpe still applies; shocks are diagnostics, not signal.
* − No smile/skew; BS is sufficient for single-leg risk but not for spread pricing.
* − Requires `business_day_offset` fix so T+1 → next `TradingDay` (not calendar day).

**Alternatives rejected:**
* Historical replay only — rejected: can't test unseen combos like vol spike without spot crash.
* Full vol surface bootstrap — rejected: needs OPRA tick data, not free.

**Glossary impact:** Defines `Scenario`, `Shock`, `TradingDay`, `Window`.
