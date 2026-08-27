# CONTEXT.md — WSB-Alpha-System Ubiquitous Language

> Glossary, not spec. No implementation detail. Sources: grilling 2026-08-27 `goldmansachs/gs-quant` (ADR-0001..0003) + `OpenBB-finance/OpenBB` 4.7.3 (ADR-0004) + `TauricResearch/TradingAgents` v0.3.1 (ADR-0005). Second/third sessions override prior "no expansion" guardrail per user.

## Core Trading Concepts

| Term | Definition |
|------|------------|
| **Equity** | Cash stock or ETF identified by `ticker` in `universe.json`. Priced via `Registry` → `ProviderAdapter` OHLCV. |
| **EqOption** | Single-leg American equity option: `underlying: Equity` + `right (Call/Put)` + `strike` + `expiry`. No spreads, no second leg until EqOption passes WFO gate. Priced via `src/pricing/bs.py` (Black-Scholes) or historical replay; no Marquee. |
| **Crypto** | 24/7 spot crypto: `{symbol: "BTCUSD" \| "ETHUSD", venue: binance\|coinbase}`. Shares OHLCV `StandardData` shape with Equity but uses crypto calendar (no NYSE). Priced via `CCXTBroker`/Binance public. |
| **Instrument** | Closed union `Equity \| EqOption \| Crypto`. Amended by ADR-0004 (was EqOption-only per ADR-0002). Commodity/FixedIncome/IRSwap/FXOption etc. remain **out of scope** until Crypto WFO passes. |
| **Signal** | `{instrument, direction (Long/Short), entry_bar, thesis_id, sentiment_score}` — one row from `BaseStrategy.generate_signals(df)`. Decision at `entry_iloc-1`, fill at `Open[next TradingDay]`. |
| **Order** | `{instrument, quantity, limit_price?, expiry}`. Quantity = `floor_to_increment(min(cash//price, target_qty), broker_min_increment)`; never negative/zero. |
| **Position** | `Instrument` + signed `quantity` + `entry_price` + `risk_key (date, market)` . |
| **Portfolio** | Set of Positions with aggregate `delta_exposure`, `margin`. |

## Time & Calendar

| Term | Definition |
|------|------------|
| **TradingDay** | NYSE business day per vendored `GSCalendar` (holiday-aware). Not a calendar day. |
| **Window** | `N` TradingDays (e.g., `Window(90)` = 90 NYSE days). Replaces `timedelta(days=90)` in `validation.py` and WFO folds. |
| **T+1** | Execution rolls to next TradingDay open, ATR-slippage clamped 0.1%–2.5%. Asserted in `tests/test_session4_lookahead.py`. |

## Risk & Validation

| Term | Definition |
|------|------------|
| **Scenario** | `HistoricalScenario` (replay past bars, e.g., 2020-03) \| `ParametricShock(spot: float, vol: float)` applied to EqOption via BS greeks. No `GsRiskApi`. |
| **Shock** | Multiplicative perturbation of spot/IV used in `circuit_breakers` and `fred_macro_provider` (RISK_OFF → shock). |
| **Walk-Forward Efficiency** | `OOS_sharpe / IS_sharpe` . Target ≥ 0.7 (`docs/OPTIMIZATION_PLAYBOOK.md`). |
| **Permutation Gate** | `p < 0.01` IS and `p < 0.05` pooled WFO; EqOption adds `IV coverage ≥ 80%` and `DTE > 7` filter. |
| **Defensive Overfit Guard** | `trial_ledger` deflated Sharpe + `StatisticalValidator.spa_test`. |

## Data Abstraction (OpenBB-inspired, clean-room)

| Term | Definition |
|------|------------|
| **StandardQuery** | Pydantic `QueryParams` for a dataset (e.g., `EquityHistoricalQuery(symbol, interval, start_date, end_date, provider)`). Validates `symbol→UPPER`, `date` parse. |
| **StandardData** | Pydantic `Data` row `date, open, high, low, close, volume, vwap (+ split_ratio/dividend for adjusted)`. Shared shape for Equity/Crypto. |
| **ProviderAdapter[Q,R]** | Clean-room TET: `to_query(params) → Q` → `fetch(Q, creds) → raw` → `to_records(Q, raw) → R`. Renamed from OpenBB `Fetcher` to prove clean-room; MIT, no AGPL text. |
| **Registry** | Plugin map `name → ProviderAdapter` loaded via entry_points (`RegistryLoader.from_extensions()` analogue). Call `registry.get("yfinance").fetch(...)` or `registry.get("chain")` for fallback. |
| **Chain (fallback)** | Existing `DataProviderChain` (Alpaca→Tiingo→Binance→yfinance) retained as one `ProviderAdapter` named `chain`; `CacheEngine` (duckdb) stays for incremental backfill. |

## Infrastructure

| Term | Definition |
|------|------------|
| **Vendored Math** | Pure `numpy/pandas/scipy/statsmodels` functions copied from `gs-quant` under `src/gs_compat/` with Apache-2.0 header; no `GsSession`, no `dataclass_json` camelCase, no network at test time. |
| **OpenBB Dependency (opt-in)** | `pip install openbb-core + openbb-yfinance + openbb-fred + openbb-fmp + openbb-sec + openbb-finviz` as *deps*, not vendored (AGPL-3.0 trap if vendored). Clean-room adapter avoids AGPL conveyance. |
| **REST (local)** | `openbb-platform-api` FastAPI `http://0.0.0.0:8000/api/v1/...` for local hunts/research; Actions stays file-based. MCP deferred. |
| **GitHub-Free Invariant** | All tests and backtests must pass on Actions free tier (no keys, no Marquee, cached holidays/IV). Missing credentials → fail-closed with warning, not mock. |

## Debate & LLM (TradingAgents-inspired, clean-room)

| Term | Definition |
|------|------------|
| **Debate Graph** | `StateGraph(AgentState)` scoped to `workspace/stages/01_hypothesis/` — Market/Social/News/Fundamentals analysts × ToolNode → Bull/Bear researchers → Research Manager → Trader → Aggressive/Conservative/Neutral risk debators → Portfolio Manager. Conditional routers `should_continue_debate` (2×max_debate_rounds) / `should_continue_risk` (3×max_risk_discuss_rounds). |
| **quick_think_llm** | `gemini-3.5-flash-lite` (150 RPM · 250K TPM · 500 RPD free, 2026-08 quota) — analysts + debators. Lite = cheap, high throughput. |
| **deep_think_llm** | `gemini-3.7-flash` (50 RPM · 250K TPM · 20 RPD free) — Research Manager + Portfolio Manager + Trader reasoning. `fallback = gemini-2.5-flash`. No `pro` unless `ALLOW_PAID=1`. |
| **zen** | Local `opencode-zen` provider (`Gemma 4 31B` 300/16K/14.4K) used when `OPENCODE_ZEN=1` or `GEMINI_API_KEY` missing; zero token cost, offline-capable. Chain: Gemini → zen → fail-closed `Hold`. |
| **ResearchPlan** | Pydantic `{recommendation: Buy/Overweight/Hold/Underweight/Sell, rationale, strategic_actions}` validated via `bind_structured` `json_schema`; `render_research_plan`→markdown for memory/display. |
| **TraderProposal** | Pydantic `{action: Buy/Hold/Sell, reasoning, entry/stop/sizing}` from Trader anchored to `ResearchPlan`. |
| **PortfolioRating** | 5-tier `Buy/Overweight/Hold/Underweight/Sell` from Portfolio Manager after risk debate. |
| **safe_ticker_component** | Regex `^[A-Za-z0-9._\-\^=+]+$` + dot-only reject + `max_len=32`; tickers from CLI/LLM tool calls must pass before `Path / ticker` interpolation (prevents `../../../etc` escape). |

## Anti-terms (do not use)

* `Priceable` (gs-quant generic) — use `Instrument` here.
* `AssetClass.Cash / AssetType.Currency` — not our domain until FX.
* `RiskKey.provider/market/scenario` — we keep `RiskRequest` RPC out; use `Scenario`.
