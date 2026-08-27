# ADR 0002 — EqOption-only expansion (single-leg American)

**Date:** 2026-08-27
**Status:** Accepted (grilling Q2+Q5, "Expand but tell me the risks" → narrow to EqOption)
**Context:** Current universe is cash equities/ETFs (`universe.json` + `DataProviderChain` OHLCV + `BaseStrategy`). gs-quant offers 40+ derivatives (`IRSwap`, `FXBinary`, `EqCliquet`, `CommodOTCSwap`…). Unbounded expansion explodes data (OPRA/IV surface, rate curves), pricing (vol cube), risk (margin/assignment), execution (multileg), and overfit surface, violating `docs/OPTIMIZATION_PLAYBOOK.md` gate and `BIAS_AND_RISK_ANALYSIS.md` honest-claims policy.

**Decision:** Expand **only to single-leg American `EqOption`** in v1:

```
Instrument = Equity | EqOption(underlying: Equity, right, strike, expiry, style=American)
```

* First strategies: collar / PMCC (`ib-pmcc-advisor`, `scanner-pmcc` aligned) on existing equity universe.
* IR/FX/Commod/futures deferred; amendment requires new ADR and EqOption WFO pass.
* Data: `yfinance` option chain + cached IV (fill 0 if sparse → fail-closed); no Marquee.
* Pricing: `src/pricing/bs.py` Black-Scholes + greeks (delta/gamma/theta/vega) pure `scipy`; DTE ≤ 7 blocked.

**Consequences:**
* + Bounded scope: 1 new instrument class, not 40.
* + Reuses `AlpacaBroker` options paper + existing `capability` gate (add `supports_options_single_leg`).
* − Still needs IV coverage discipline; backtests without ≥80% IV will be rejected by validator.
* − No multi-leg spreads until single-leg edge proven (WSB `trial_ledger` gate).

**Alternatives rejected:**
* Full derivatives hierarchy — rejected: data/pricer vacuum.
* Stay equity-only forever — considered but rejected; PMCC is adjacent and high-ROI.

**Glossary impact:** Defines `Equity`, `EqOption`, `Instrument`, `Order`, `Position` in `CONTEXT.md`.
