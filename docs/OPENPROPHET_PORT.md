# OpenProphet → WSB-Alpha-System Port (rebuilt 2026-09-04 after disk wipe)

Source: https://github.com/JakeNesler/OpenProphet (107 stars, 39 forks,
branch main @ 3d0f09c, last push 2026-07-24). Autonomous AI trading agent:
Node heartbeat harness + MCP tool server + Go/Alpaca-paper backend +
SQLite + ChromaDB trade memory. Featured in Bloomberg 2026-05-01 (mixed
results). Author warns: experimental, paper trading only.

## What OpenProphet is

1. Phased heartbeat loop (agent/harness.js, 884 lines): wakes an LLM agent
   on per-phase intervals — pre_market 900s, market_open 120s, midday 600s,
   market_close 120s, after_hours 1800s, closed 3600s (ET).
2. Layered system prompt: agent identity + TRADING_RULES.md + curated tool
   menu (agent/tool-catalog.js). Default identity trades "a real brokerage
   account with no human approving your actions."
3. MCP server (mcp-server.js, 81KB): ~40 tools — Trading, Options, Market
   Data, News, Intelligence, Agent Config, Heartbeat, Logging, Trade
   History, Utility.
4. Go backend (port 4534, paper-api.alpaca.markets default): managed
   positions (stop-loss / take-profit / trailing / partial exits), TA
   service (SMA20/50, RSI-14, MACD, momentum, volume → BUY/SELL/HOLD +
   confidence), news + Gemini AI, activity logger.
5. Memory: SQLite (orders/bars/positions/trades/snapshots/signals) +
   ChromaDB embeddings for find_similar_setups.
6. TRADING_RULES.md (344 lines): aggressive discretionary OPTIONS trading —
   15% per position, 40% sector, 10 positions, PDT scalping, 50-120 DTE
   swings, delta 0.40-0.70, -15% cut, -5% daily halt, 50-70% cash.

## Mapping (Go/JS → Python)

| OpenProphet | Port | Notes |
|---|---|---|
| harness.js PHASE_DEFAULTS + getCurrentPhase | src/ops/openprophet_heartbeat.py | identical table + ET weekends-closed; pure scheduler, no LLM |
| technical_analysis.go Analyze/generateSignal | src/signals/openprophet_technical.py | same indicators, weights, +/-1 thresholds; see fix below |
| position_manager.go + DBManagedPosition | src/execution/openprophet_positions.py | same lifecycle PENDING→ACTIVE→PARTIAL→CLOSED/STOPPED_OUT |
| TRADING_RULES risk rules | RiskConfig + check_pre_trade (fail-closed) | 15%→10% default, halt -5%, 10/day, limit-only, revenge cooldown |
| models.go SQLite tables | src/research/openprophet_journal.py (stdlib sqlite3) | signals/trades/snapshots/activity/decisions |
| vectorDB find_similar_setups | journal.find_similar_setups (feature match) | no ChromaDB/embeddings dep; Mnemosyne covers semantic recall |
| orchestrator per-sandbox runtimes + dashboard :3737 | NOT ported (no server; run_beats replay for backtest) | no open ports, no auth surface |
| MCP server / Gemini / news feeds | NOT ported | no API keys, no network in beats; local CSV data |

## Deliberate fixes and rejections

1. MACD signal line: upstream uses `ema12 * 0.85` (placeholder, not a
   signal line). Port computes a real 9-period EMA of the MACD line.
2. REJECTED: options-only aggressive style (DTE/theta/delta rules, PDT
   scalping, 15% concentration). User mandate is safe Alpaca stock trading
   that beats SPY. Stocks only, no shorts, no leverage.
3. REJECTED: autonomous live trading ("no human approving your actions").
   Beats are deterministic, paper-only, emit intended orders as dicts;
   opening positions requires the checklist AND repo 5-gate validation.
4. REJECTED: always-on daemon + dashboard server. Beats run on demand
   (`scripts/openprophet_beat.py`); nothing listens, nothing auto-trades.

## Verification (rebuilt copy re-verified 2026-09-04, real data)

- `pytest tests/test_openprophet_port.py` — 5 passed.
- `ruff check` on all six files — clean. `bandit` — 0 issues.
- Beat `--symbols SPY --beats 1 --phases midday` on
  data/spy_ohlcv_2019_2026.csv: SPY 773.26, SMA20 750.17 > SMA50 746.61,
  RSI 69.6 → BUY 60.0, 0 actions, checklist pass, status paper.
- TA test asserts RSI 0-100, SMA20/50 > 0, signal in set on full SPY history.
- Lifecycle test: partial at +25%, stop-to-breakeven, STOPPED_OUT at 490,
  revenge guard blocks re-entry for 2 bars. Take-profit test closes at +52%.
- Journal test: signal log → similarity rank → trade P&L (+500) → stats.
- Rebuild note: committed on branch `ports/2026-09-04` + backed up to
  `port-backups/` outside the repo (original wiped by `git clean -fd`).
