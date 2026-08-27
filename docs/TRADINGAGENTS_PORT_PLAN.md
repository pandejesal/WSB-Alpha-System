# TradingAgents → WSB-Alpha-System Port Plan (Grilling `grill-me` 2026-08-27)

> Third session, user allowed `opencode-zen` + latest Gemini free. Q7 Recommended = clean-room `src/research/debate/` (not vendored `tradingagents/`).

## Decision log

Q1 Wholesale debate subgraph scoped to `01_hypothesis`, Q2 Two-tier `gemini-3.5-flash-lite` quick / `gemini-3.7-flash` deep + `zen` + `openrouter` fallback + free-only, Q3 Schemas as validation layer, Q4 Deliberative + mechanical risk, Q5 zen as first-class provider, Q6 quick=3.5-lite / deep=3.7 / fallback 2.5, Q7 `src/research/debate/` clean-room.

## What NOT to port

* `tradingagents/` subtree verbatim — 13 deps (`langchain-anthropic/google/redis/backtrader`), naming collision.
* `langchain-aws` Bedrock unless `ALLOW_PAID`.
* `models/epidemiology`-style extras (none here).

## What TO port — concrete file map (5 steps, parallel to GS_QUANT + OPENBB)

### 0) `src/dataflows/safe_ticker.py` — NEW, vendored logic from `tradingagents/dataflows/utils.py`

```py
_TICKER_PATH_RE = re.compile(r"^[A-Za-z0-9._\-\^=+]+$")
def safe_ticker_component(value: str, max_len=32) -> str: ... # dot-only reject, ValueError
```

Shared by `ProviderAdapter.fetch` and `TradingAgentsGraph`; add `tests/test_safe_ticker.py`.

### 1) `src/research/debate/schemas.py` — NEW, clean-room from `tradingagents/agents/schemas.py`

Pydantic `ResearchPlan`, `TraderProposal`, `PortfolioRating` + `_NULLISH_FLOAT` coerce + `render_*`→markdown. Header MIT "Inspired by TauricResearch/TradingAgents, not vendored". Fallback `invoke_structured_or_freetext` if `bind_structured` unsupported by provider.

### 2) `src/research/debate/llm_clients.py` — NEW, clean-room from `tradingagents/llm_clients/`

`create_llm_client(provider: "gemini"|"zen"|"openrouter"|"anthropic", model, backend_url)` — Gemini via `src/utils/gemini_provider.py`, zen via `opencode zen` local endpoint (`http://localhost:4096`), `_coerce_max_retries`, `llm_max_retries` guard. Config consumed from `workspace/_config/llm.yaml`.

### 3) `src/research/debate/graph/` — NEW, clean-room from `tradingagents/graph/`

```
graph/conditional_logic.py  # should_continue_debate / should_continue_risk_analysis / should_continue_{market,social,news,fundamentals}
graph/setup.py              # GraphSetup(quick_llm, deep_llm, tool_nodes, conditional_logic).setup_graph(selected_analysts) -> StateGraph
graph/trading_graph.py      # TradingAgentsGraph(selected_analysts, config, callbacks) — deep+quick, TradingMemoryLog, ToolNodes, Propagator, Reflector, SignalProcessor
graph/analysts/{market,sentiment,news,fundamentals}.py # each calls Registry (yfinance/fmp/fred/sec) + get_verified_market_snapshot
graph/research_manager.py + trader.py + risk_mgmt/ (3 debators + portfolio_manager)
graph/reporting.py          # write_report_tree(final_state, ticker, save_path) -> 1_analysts/2_research/3_trading/4_risk/complete_report.md
```

Opt-in `langgraph>=0.4.8` dep only when `tradingagents` extra installed; otherwise graph falls back to sequential call.

### 4) `workspace/_config/llm.yaml` + `workspace/stages/01_hypothesis/CONTEXT.md` — MODIFY

```yaml
# _config/llm.yaml
llm_provider: gemini
quick_think_llm: gemini-3.5-flash-lite   # 150/250K/500 free
deep_think_llm: gemini-3.7-flash         # 50/250K/20 free
fallback_llm: gemini-2.5-flash
max_debate_rounds: 1
max_risk_discuss_rounds: 1
zen_model: gemma-4-31b
allow_paid: false
```

Stage 01 CONTEXT: add prior-art debate step referencing `TradingMemoryLog`.

### 5) `workspace/stages/01_hypothesis/output/` — MODIFY

`debate_report.md` (rendered ResearchPlan + TraderProposal) attached alongside `hypothesis_brief.yaml` before `02_backtest` admission gate validates against schemas.

## Implementation order (Jules-lanes, one per prompt)

1. **safe_ticker + schemas** — `safe_ticker.py` + `debate/schemas.py` + `tests/test_debate_schemas.py` (no LLM).
2. **llm_clients + config** — `llm_clients.py` + `llm.yaml` + `tests/test_llm_clients.py` (mock Gemini, no network).
3. **conditional_logic + reporting** — `conditional_logic.py` + `reporting.py` + `tests/test_reporting.py`.
4. **graph setup + analysts** — `setup.py` + `trading_graph.py` + 4 analysts wiring to `Registry`; integration test `test_debate_graph_smoke.py` with `zen` mock.
5. **risk team + trader** — `research_manager.py`, `trader.py`, `risk_mgmt/`, end-to-end `workspace` smoke with `OPENCODE_ZEN=1`.

## Verification

```
ruff check src/research/debate src/dataflows/safe_ticker.py
bandit -r src/research/debate -lll
PYTHONPATH=. pytest tests/test_debate_schemas.py tests/test_safe_ticker.py -v
PYTHONPATH=. pytest -m "not integration"   # no Gemini key needed, zen mock
```

No vendor copy of `tradingagents/agents/schemas.py` text; `langgraph` is optional.
