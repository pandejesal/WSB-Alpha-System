# ADR 0005 — TradingAgents debate graph (LangGraph, Gemini free + zen, clean-room)

**Date:** 2026-08-27
**Status:** Accepted (grilling `grill-me` TradingAgents Q1–Q7, Q2/Q6 overrides for opencode-zen + latest Gemini free; Q7 Recommended)
**Context:** `TauricResearch/TradingAgents` v0.3.1 (MIT, LangGraph) provides a multi-agent debate graph: 4 analysts (Market/Social/News/Fundamentals) × ToolNode → Bull/Bear researchers ↔ ResearchManager (`ResearchPlan` 5-tier) → Trader (`TraderProposal` Buy/Hold/Sell) → Aggressive/Conservative/Neutral risk debators ↔ PortfolioManager, with `ConditionalLogic` routers, `TradingMemoryLog`/`Reflector`/`SignalProcessor`, `checkpointer` (sqlite), `write_report_tree` (1_analysts/2_research/3_trading/4_risk), `safe_ticker_component`, structured `bind_structured`. Our `workspace/stages/01_hypothesis` is solo-agent (`hypothesis_brief.yaml`); `self_improvement_agent` mutates one param; risk is mechanical only (`fred_macro_provider` + `circuit_breakers`).

**Decision:**
1. **Wholesale debate subgraph scoped to `01_hypothesis`.** Clean-room `src/research/debate/` (not vendored `tradingagents/`): `graph.py` (`StateGraph(AgentState)` wire via `GraphSetup`), `conditional_logic.py` (`should_continue_debate` 2×max_debate_rounds, `should_continue_risk_analysis` 3×max_risk_discuss_rounds), `analysts/*.py` (4 nodes calling existing `reddit_scraper`/`google_search_provider`/`fred_macro_provider` + new `Registry` data), `reporting.py` → `workspace/stages/01_hypothesis/output/debate_report.md`. LangGraph/LangChain deps opt-in only.
2. **Two-tier LLM + zen + latest Gemini free.** `quick_think_llm = gemini-3.5-flash-lite` (150 RPM · 250K TPM · 500 RPD free, analysts/debators), `deep_think_llm = gemini-3.7-flash` (50 RPM · 250K TPM · 20 RPD, manager/portfolio), `fallback = gemini-2.5-flash` (same quota). `opencode-zen` as provider `zen` (Gemma 4 31B 300/16K/14.4K locally) when `OPENCODE_ZEN=1` or `GEMINI_API_KEY` missing → fail-closed `Hold` if none. Free-only (`ALLOW_PAID=0`), `_coerce_max_retries` guard, `NO_EXTERNAL_TOOLS` prompt discipline. Config in `workspace/_config/llm.yaml` + `.env` overrides (`deep_think_llm`, `quick_think_llm`, `llm_provider`, `backend_url`), merging one-level deep like `dataflows/config.py`.
3. **Structured handoffs as validation.** `src/research/debate/schemas.py` clean-room `ResearchPlan{recommendation: Buy/Overweight/Hold/Underweight/Sell, rationale, strategic_actions}`, `TraderProposal{action, reasoning, entry/stop/sizing}`, `PortfolioRating`, with `_NULLISH_FLOAT` coercion + `render_*`→markdown so memory/display stay prose. Validate `hypothesis_brief.yaml` against `ResearchPlan` before `02_backtest` admission.
4. **Deliberative + mechanical risk.** Keep `circuit_breakers`/`position_sizing` as hard caps (cannot be debated away); add 3-way risk debate in `03_review` pre-human gate producing `RiskPlan` with dissent logged alongside `quantstats` tearsheet. Default `Hold` if inconclusive.
5. **Isolation.** Do not vendor `tradingagents/` subtree; add `src/dataflows/safe_ticker.py` (`safe_ticker_component` regex `^[A-Za-z0-9._\-\^=+]+$` + dot-only reject + max_len 32) shared by all `ProviderAdapter.fetch`.

**Consequences:**
* + Error-correction via debate; structured schemas catch hallucinated `Instrument` identity (via `resolve_instrument_identity` LRU cache).
* + Cheap: 4 analysts on `flash-lite` (150/500) vs old `flash` (50/20) = 3× RPM, 25× RPD.
* + Auditable 4-folder report tree parallel to `docs/reports/strategy-*.html`.
* − LangGraph adds ~13 deps when enabled (opt-in, not on Actions free CI without keys).
* − Extra LLM calls in `01` increase latency (mitigated by `max_debate_rounds=1` default).

**Alternatives rejected:**
* Bolt only Manager+Trader — rejected: loses debate correction.
* Vendor `tradingagents/` verbatim — rejected: heavy, 13 deps, naming collision with `gs_compat`/`openbb_compat`.
* Replace breakers with debate — rejected: debate cannot enforce caps.

**Glossary impact:** Defines `Debate Graph`, `quick/deep_think_llm`, `zen`, `ResearchPlan`, `TraderProposal`, `PortfolioRating`, `safe_ticker_component` in `CONTEXT.md`.
