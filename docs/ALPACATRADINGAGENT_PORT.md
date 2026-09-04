# AlpacaTradingAgent → WSB-Alpha-System Port (rebuilt 2026-09-04 after disk wipe)

Source: https://github.com/huygiatrng/AlpacaTradingAgent (259 stars,
89 forks, main @ 8d9d770, 160 commits). Independent enhancement of
TauricResearch/TradingAgents: 5 parallel LLM analysts → bull/bear debate
→ trader → risky/safe/neutral risk debate → risk manager → typed
TradeIntent → Alpaca paper/live execution. Deterministic pytest suite,
no-network tests.

## What was portable (deterministic, no keys, no network)

The repo's best idea is its safety maxim: the LLM decides direction,
deterministic layers decide size and permission. Ported:

| Upstream | Port | Notes |
|---|---|---|
| safety/guardrails.py (406 lines) | src/risk/alptrading_safety.py | kill-switch file, notional + concentration caps, daily-loss + HWM-drawdown + rejection-streak breakers, NaN-safe parsing, risk-reducing bypass |
| risk/position_sizing.py (245 lines) | src/risk/alptrading_sizing.py | Wilder ATR, fractional Kelly w/ shrunk edges, 5-cap min, fallback stop; near-verbatim |
| graph/conditional_logic.py debate rounds | src/research/alptrading_debate.py | bull/bear judging at 2N, risk rotation at 3N; LLM rhetoric → score arithmetic, ties → HOLD |
| agents/schemas.py TradeIntent + protective-price rule | same file | absolute prices only; relative/qualitative → None, never guessed |
| graph/signal_processing.py (deterministic part) | extract_signal() | proposal-pattern + tail-keyword parse; NO LLM fallback → HOLD |
| memory.py + TradingMemoryLog + reflection | src/research/alptrading_memory.py | append-only markdown log + resolve() with realized return; no ChromaDB (Mnemosyne covers semantic recall) |
| TradingAgentsGraph propagate() | scripts/alptrading_debate.py | analysts fed by real local indicators; prints TradeIntent JSON, paper only |

## Deliberately NOT ported

- LangGraph + 12 LLM provider clients + prompt templates (no API keys,
  no paid calls; free-tier mandate).
- Live execution, margin/shorts, crypto, auto-execution scheduler —
  user mandate: Alpaca stocks, paper only, never auto-live.
- WebUI/CLI, news/Reddit/FINNHUB/CoinDesk feeds, Gemini cleaning —
  analysts that need feeds ABSTAIN (score 0, "no feed — abstain") rather
  than inventing data. Two of five analysts abstain today; the debate
  still resolves because the judge uses margins, documented below.
- LLM token budget guard (no LLM calls here to budget).

## Safety deltas (tightened defaults)

Notional cap 25k→10k, concentration 25%→20%, daily halt 10%→5%,
drawdown halt 15%→10%. SELL means close-only; SHORT never opens.
Debate ties/thin margins (<0.15) → HOLD. Guard blocks → HOLD.

## Verification (rebuilt copy re-verified 2026-09-04, real data)

- `pytest tests/test_alptrading_port.py` — 8 passed (incl. upstream
  reference values: ATR(3)=66.5/27, half-Kelly 0.125, kelly-cap 12.5k).
- `ruff check` six files — clean. `bandit` four src files — 0 issues.
- CLI `--symbol SPY --equity 100000 --request 8000` on
  data/spy_ohlcv_2019_2026.csv: TA BUY 60 / RSI 69.6 → debate bull
  margin 0.45 → Kelly-sized 7,538.46, stop 755.50, all 6 guard checks
  pass, memory entry 1, status paper, live false.
- Memory test: record → resolve +10.0% → stats win_rate 1.0.
- Rebuild note: committed on branch `ports/2026-09-04` + backed up to
  `port-backups/` outside the repo (original wiped by `git clean -fd`).
