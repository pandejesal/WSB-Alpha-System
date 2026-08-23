# Harness Upgrade Research — WSB-Alpha-System → Auto-Trading AI + Trading Harness

**Date:** 2026-08-19
**Scope:** Research only — no code changes. Every repo claim cites a file path; every product claim cites a URL.
**Canonical checkout used:** `WSB-Alpha-System-build` (origin `github.com/pandejesal/WSB-Alpha-System`).

---

## 1. Context & Constraints

Goal: evolve the current scheduled-paper-trading system into an "Auto-Trading AI + Trading Harness":

| Constraint | Requirement |
|---|---|
| Infrastructure | **$0 infra** — GitHub Actions only. No local daemon, no VPS. |
| Brain | **Hybrid**: deterministic math core (signals, sizing, stops) + LLM analysis (debate, research). No LLM decides order size/price. |
| Markets | US equities + **BTC/ETH spot via Alpaca** (paper-first). |
| Safety | Paper-first with deterministic gate (already exists: G1–G7) + human flip for live. |
| Cadence | Event-driven: price/news alerts + auto stops (OCO/bracket where venue supports; client-side polling where not). |
| Portfolio | Mixed multi-strategy portfolio (7 sleeves already live in code). |

---

## 2. Landscape Scan (6 references)

### 2.1 Swiftward AI Trading Agents Harness
- **Source:** https://ai-trading.swiftward.dev — repo: https://github.com/disciplinedware/swiftward-ai-trading-agents
- **What it is:** a production agent-trading harness whose landing page is literally titled "AI Trading Agents Harness". Three pillars: multi-agent analysis, MCP trading platform, declarative risk engine. On-chain ERC-8004 evidence hash chain (~4,772 trades registered), 45 MCP tools, 31 risk-control rules.
- **Relevant patterns:**
  - **"Pure math core — no hallucination where it matters"**: their *Deterministic Quant Trader* agent does size/entry math in code; the LLM agents (momentum + regime analysis, multi-agent debate with 5 subagents) only produce analysis. Directly validates our hybrid design.
  - **Declarative versioned risk rules** (YAML, draft→candidate→active→archived lifecycle, graduated risk tiers) — gap 3.
  - **Evidence hash chain** (append-only, keccak256-linked) — gap 5.
  - Conditional orders: price alerts, news-keyword alerts, **auto SL/TP linked to entry (OCO)**, trailing stops — gap 2.

### 2.2 EigenTrader OS
- **Source:** https://eigentrader.com (Reinforce Market Labs; brokerage via Alpaca Securities + Alpaca Crypto LLC)
- **What it is:** governed "fleet of agents" harness running on Alpaca — the closest live proof that our exact venue+model combo works in production.
- **Relevant patterns:**
  - Per-strategy P&L attribution + quant stats (per-strategy circuit breakers, auto-halt enforced **server-side**).
  - Policy gate: budget & limits, exposure, drawdown; immutable append-only system of record with deterministic replay.
  - Agent Builder / BYOA via MCP. Dynamic model-driven policies (de-risk book on regime shift).

### 2.3 QuantClaw
- **Source:** https://quantclaw-ai.com — repo: https://github.com/quantclaw-ai/QuantClaw
- **What it is:** campaign-driven agent harness with 12 "crewmates" (Scheduler cron daemon, Sentinel reactive alert guardian, Researcher LLM factor-hypothesis search, Ingestor range-aware cache, Miner evolutionary factor discovery in sandbox, Validator held-out replay with overfit verdict, Executor, Risk Monitor veto, Compliance rule engine, Debugger).
- **Relevant patterns:**
  - **Paper-first state machine**: a campaign advances to paper only after held-out validation passes; pauses on drawdown breach.
  - Sentinel = alert-triggered reactive analysis — the "event-driven" half of our event loop.
  - Sandboxed code execution (AST validation, resource caps) for generated strategies.
  - Caveat: QuantClaw is **not $0 infra** — it runs on your machine. We borrow its patterns, not its deployment.

### 2.4 TraderHarness (HephaestLab)
- **Source:** https://hephaestlab.github.io/TraderHarness — repo: https://github.com/HephaestLab/TraderHarness (Apache-2.0)
- **What it is:** "A fair historical market for LLM trading agents" — a backtesting environment that enforces point-in-time evidence: data filtered by simulated clock, **deterministic date/entity masking** (dates become `D+0`, companies get pseudonyms so the model cannot recognize a company/date from training data), progressive 5-minute bar revelation, one controlled order path (`TradingBus.place_order()`), read-only portfolio views for agents, fingerprinted replay, fail-closed matching, full-fidelity trajectories + `traderharness audit`.
- **Relevant patterns:** exactly the **LLM-agent backtest arena** (gap 6) — and its masking design is the fix for the "model recognizes AAPL 2026-03-14" leakage problem. Research-only; no broker connection.
- **Adoption cost:** heavy (Python package, China A-share dataset focus). We should borrow the *concept* (point-in-time enforcement, single order path) and implement a minimal walk-forward arena against our own Alpaca/yfinance data — see roadmap P3.

### 2.5 FinRL-X / FinRL-Trading
- **Source:** https://github.com/AI4Finance-Foundation/FinRL-Trading (3.6k stars, Apache-2.0)
- **What it is:** AI-native modular quant infrastructure. **Weight-centric contract** `w = T(A(S(x)))` (signal → allocator → timing → weights) kills strategy-execution drift; auto data-source selection; allocators (uniform 1/N, mean-variance, DRL); regime layer (26-week trend + VIX slow regime + 3-day fast risk-off); trailing/absolute stop-loss + cooldowns; **deploys to Alpaca paper** (`./deploy.sh --strategy adaptive_rotation --mode paper --dry-run`); public paper results Oct 2025–Mar 2026 (+19.76% vs SPY −2.51%).
- **Relevant patterns:** composite signal pipeline (S→A→T) mirrors our sleeve architecture; Alpaca paper as first deployment target; **regime-gated risk** (their 26-week + VIX slow regime / 3-day shock fast risk-off maps onto our existing regime-scaled circuit breakers).

### 2.6 AgenticTrading (BenPomme)
- **Source:** https://github.com/BenPomme/agentictrading (AGPL-3.0, paper-only badge)
- **What it is:** "autonomous trading research factory"; flagship reference app for the Meerkat + mobkit + Goldfish stack.
- **Relevant patterns:**
  - **Lineage lifecycle**: idea → proposal → model design → backtest → walkforward → shadow → **paper** → retired; **deterministic gates (never LLM-only) decide promotion/retirement** — same philosophy as our G1–G7 gate.
  - **Lineage-scoped paper accounts**: per-strategy paper accounts so results are not pooled.
  - Goldfish = durable provenance/experiment memory. **Live trading hard-disabled in the public repo** — they publish the harness, not the money path. Mirrors our "paper-first, human flip" constraint.

### 2.7 Landscape synthesis
| Pattern | Where seen | Verdict for us |
|---|---|---|
| LLM analyzes, math executes | Swiftward (core pillar), FinRL-X (weights contract) | **Adopt** — this is the hybrid brain |
| Declarative versioned risk rules | Swiftward (YAML lifecycle), EigenTrader (policy gate) | Adopt (P2) |
| Evidence/audit hash chain | Swiftward (ERC-8004), EigenTrader (immutable ledger), AgenticTrading (Goldfish) | Adopt simplified (P2) |
| Event loop via polling + alerts | QuantClaw (Scheduler+Sentinel), Swiftward (alerts/OCO) | Adopt via GH Actions cron (verified feasible, §4.1) |
| Paper-first promotion gates | QuantClaw, AgenticTrading, our G1–G7 | Already have — keep |
| LLM backtest arena with anti-leakage | TraderHarness (masking), FinRL-X (no-lookahead) | Minimal walk-forward port (P3) |
| Server-side per-strategy breakers | EigenTrader | Partially have (circuit_breakers.py) — extend |

---

## 3. Gap Analysis — Current vs Target

### Gap 1 — Mock debate vs real LLM debate
- **Current:** `src/research/debate_engine.py:10` `run_debate()` calls `_simulate_bull_agent` (line 75), `_simulate_bear_agent` (line 106), `_simulate_neutral_agent` (line 136). Personas are hardcoded heuristics that mirror `base_score["classification"]` — no LLM, no real disagreement, output is a weighted consensus Q-score.
- **Already real elsewhere:** `src/research/strategy_research_agent.py:83` (real Gemini + function calling, `DDGSearchProvider`), `src/research/agents/workflow.py:25` (LangGraph research→spec→code→reflection), `src/utils/gemini_provider.py:27,44` (`model='gemini-2.5-flash'`), `src/utils/gemini_client.py:111,139` (newer `gemini-3.5-flash` / `-lite` — two providers exist; pick one).
- **Target:** keep the `DebateEngine` Q-score contract; swap the `_simulate_*` bodies for bounded Gemini calls (persona system-prompt + same inputs). Deterministic entry sizing/stops never enter the LLM prompt (see §5.1).

### Gap 2 — No event loop, no server-side OCO
- **Current cadence** (`.github/workflows/`): `paper_trade.yml` cron `'30 14 * * *'` (daily 14:30 UTC), `ops_daily.yml` `'0 21 * * 1-5'`, `ops_watch.yml` `'0 12 * * 1-5'` (Telegram poll), `ops_gate.yml` `'0 17 * * 5'`, `ops_reconcile.yml` `'0 16 * * 1-5'`, `api_health_check.yml` `'0 0 * * *'`, `daily_research.yml` `'0 8 * * 1'`, `sandbox.yml` `'55 20 * * 1-5'`; dispatch-only: `generate_strategies.yml`, `ops_reports.yml`, `self_improvement.yml`. Existing concurrency groups (`docs-data-writers`, `ops-runner`, `pages`) + heartbeat pattern (`src/ops/heartbeat.py`) already model run-idempotency.
- **Orders:** `src/execution/alpaca_broker.py:56` `place_order()` supports market + optional single-leg `StopLossRequest` (line 79) — **no take-profit, no bracket/OCO**.
- **Target:**
  - 5-min trigger workflow (verified feasible — §4.1) that polls prices, checks resting stops, and fires deterministic triggers; debate/execution steps run only when a trigger fires.
  - **Equities:** server-side `order_class=bracket` with `take_profit` + `stop_loss` (supported — §4.2) → fully event-driven exits, no polling needed.
  - **Crypto:** bracket **not supported** (§4.2) → entry market order + immediate resting `stop_limit` exit via the poll job (client-side stop; see risk §6.3).

### Gap 3 — Python risk classes vs declarative versioned rules
- **Current:** `src/risk/position_sizing.py:10-18` (`ACCOUNT_BASE_CAPITAL=100.0`, `MAX_RISK_PER_TRADE_PCT=0.01`, `MAX_POSITION_SIZE_PCT=0.25`, `MAX_CONCURRENT_POSITIONS=4`); `src/risk/circuit_breakers.py` daily 5% / weekly 10% / total 15%, regime-scaled (low_volatility 1.2, high_volatility 0.6); gates in `src/ops/gate_evaluator.py:11-14` (`MIN_PAPER_TRADES=50`, `MIN_TRADES_PER_SLEEVE=10`, `SMA200_EXEMPT="spy_sma200"`, `MIN_CONSECUTIVE_HEARTBEAT_DAYS=7`). All are Python constants — not versioned, not auditable, no lifecycle.
- **Target:** `config/risk_rules.yaml` — versioned rule file (draft→active→archived), read at load by the same breakers/gates, SHA-256 pinned in the evidence chain so "what rules were active on date X" is provable. (Swiftward-style lifecycle, EigenTrader-style policy gate.)

### Gap 4 — No crypto execution path (Alpaca)
- **Current:** `src/execution/alpaca_broker.py` is equities-only (no crypto symbols). Crypto exists but on other venues: `src/execution/live_crypto_executor.py:11` (Bybit perps via ccxt), `src/execution/ccxt_broker.py:8` (Binance). `src/execution/universal_broker.py:107` already routes by asset class (`AlpacaExecutor` line 54, `CryptoExecutor` line 81) and `src/execution/base_broker.py:38-42` already exposes capability flags (`supports_market_orders`, `supports_stop_limit`, `supports_paper`) — **the seam exists, the Alpaca crypto leg doesn't.** `src/ops/portfolio.py` runs the `btc_vol_target_sma100` sleeve (signal-only today).
- **Target:** implement Alpaca crypto leg (`BTC/USD`, `ETH/USD`, §4.2 format) in `AlpacaBroker` or a sibling class behind the same `BaseBroker` interface; wire into `UniversalBroker`.

### Gap 5 — No evidence chain
- **Current:** `src/ops/audit.py` (`AuditLogger`, atomic `write_artifact`, `generate_client_order_id` → `docs/data/ops/audit.jsonl`); `src/ops/killswitch.py` states `off|halt_new_orders|flat` (fails closed); `src/ops/watch.py` Telegram `/kill /halt /flat` → `config/ops_state.yaml` (`state: off`); heartbeat staleness detection. Good audit *trail*, but entries are independent — tamper-evident link missing.
- **Target:** append-only JSONL where each entry carries `sha256(prev_entry_hash + payload)`; daily Merkle-root commit (workflows already commit `docs/data/`). Matches Swiftward/EigenTrader immutability patterns at zero infra cost.

### Gap 6 — No LLM-agent backtest arena
- **Current:** `scripts/run_permutation_study.py`, `scripts/generate_sharpe.py`, `docs/research/FEATURE-GAP-MATRIX.md` (2026-08-09) exist; `src/research/skill_executor.py` has Gemini context caching — but no point-in-time replay of *agent decisions*.
- **Target (minimal, P3):** walk-forward arena: for each candidate strategy, fetch data **as-of decision date** (Alpaca historical bars / yfinance), run deterministic signals; optionally run LLM debate on masked dates/entities (TraderHarness-style `D+0` masking, §2.4) and compare decisions vs hindsight. Not a TraderHarness port — borrow its invariants: single order path, no future bars, read-only portfolio view.

---

## 4. Feasibility Verification (primary sources)

### 4.1 GitHub Actions scheduled workflows
Source: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows (fetched 2026-08-19)
- **5-minute minimum** — "The shortest interval you can run scheduled workflows is once every 5 minutes."
- POSIX cron; UTC by default, optional IANA timezone.
- **Runs on the latest commit of the default branch** → the trigger workflow must live on `main`.
- **Delays under load:** "The `schedule` event can be delayed during periods of high loads… High load times include the start of every hour. If the load is sufficiently high enough, some queued jobs may be dropped. To decrease the chance of delay, schedule your workflow to run at a different time of the hour." → offset the 5-min grid (e.g., `3-58/5`) and accept worst-case gaps; trading loop tolerates 5–15 min (crypto stops are client-side — mitigated by resting `stop_limit` orders, §4.2).
- **60-day auto-disable:** "scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." → this repo commits `docs/data/` daily via ops workflows, so activity persists; keep one guaranteed committer alive as a watchdog.
- **Verdict: feasible at $0.** Public-repo hosted-runner minutes and cron are free; concurrency groups already prevent overlap.

### 4.2 Alpaca — paper trading, crypto, bracket/OCO
Sources: https://docs.alpaca.markets/us/docs/paper-trading.md, https://docs.alpaca.markets/us/docs/crypto-orders.md, https://docs.alpaca.markets/us/reference/postorder.md (OpenAPI), all fetched 2026-08-19.
- **Paper trading:** free, available to all users worldwide via **Paper Only Account** (email signup, no funding); **simulates crypto as well**; fills at NBBO, marketable-only; $100k default balance, reset/delete-account available; separate keys, base URL `https://paper-api.alpaca.markets`.
- **Crypto orders:** same `POST /v2/orders` endpoint; supported types **`market`, `limit`, `stop_limit`**; TIF `gtc`, `ioc`; fractional via `notional` or `qty`; symbols like `BTC/USD`, `ETH/USD` (legacy `BTCUSD` in assets API).
- **Bracket/OCO:** the `OrderClass` schema states: *"Equity trading: simple (or ""), oco, oto, bracket. Options: … mleg. **Crypto trading: simple (or "")**."* → **bracket/oco/oto orders are NOT supported for crypto.** `CreateOrderRequest` does include `take_profit` (`limit_price`) and `stop_loss` (`stop_price`/`limit_price`) fields — usable for equities bracket orders.
- **Notional:** "Can only work for market order types and day for time in force" — relevant for crypto fractional entries.
- **Verdict:** equities exits = server-side bracket (fully event-driven). Crypto exits = entry + resting `stop_limit` + poll-job verification (client-side, 5-min granularity). Both feasible; crypto path needs the polling job to be reliable — that's the design's weakest link (§6.3).

### 4.3 Gemini free tier (gemini-2.5-flash)
Sources: https://ai.google.dev/gemini-api/docs/rate-limits (official, fetched 2026-08-12 snapshot via search) + community snapshots (Google forum thread https://discuss.ai.google.dev/t/limits-of-free-tier-api-vs-ai-studio/94918, 2025-07; multiple 2026-04→06 snapshots).
- Official page: limits are the three dimensions **RPM (requests/minute), TPM (tokens/minute input), RPD (requests/day)**; exceeding any returns a rate-limit error; spend-based limits are N/A on Free tier; tier qualification Free = active project or free trial, **no credit card, no expiry**; "Rate limits depend on a variety of factors… and can be viewed in Google AI Studio." The official page no longer prints the row-by-row free table — **verify your project's actual numbers in AI Studio** (they vary by region/account).
- Best public snapshot for **Gemini 2.5 Flash** free tier (2026-04→06, consistent): **~15 RPM / 1,500 RPD / 1M TPM** (some accounts show 10 RPM / 250k TPM — the 2025-07 forum snapshot; check yours). 2.5 Flash-Lite: 30 RPM / 1,500 RPD / 1M TPM. 2.5 Pro free: 5 RPM / 50 RPD — trial-only, avoid.
- Caveats: free-tier prompts may be used for model training (EU/CH/UK exempt); reports of `429 RESOURCE_EXHAUSTED` with `0 RPM/0 RPD` quota display (account-standing/rollout issues, not just overuse).
- **Budget math for the harness** (model: 2.5-flash, pessimistic 250 RPD floor, realistic 1,500 RPD):
  - One debate = 3 persona calls + 1 synthesis = **4 calls**.
  - Trigger-gated cadence (2 debates/day + daily research ~20 calls + weekly generation ~30) ≈ **<50 calls/day** → 3% of the 1,500 RPD budget; even 12 debates/day ≈ 68 calls/day → 4.5%. **Free tier is a non-issue at this scale.**
  - The repo's own `gemini_client.py` already targets `gemini-3.5-flash` — if that model has different free limits, re-verify in AI Studio before P1.

---

## 5. Target Design

### 5.1 Hybrid LLM-debate pattern
```
deterministic trigger (price/indicator/news-keyword)   ← math, code
        │
        ▼
LLM debate (3 personas + synthesis)   ← Gemini 2.5-flash, bounded inputs (quotes, regime, headlines, NOT positions/sizes)
        │   output: stance + conviction (0..1) + rationale
        ▼
deterministic decision layer: conviction ≥ 0.6 AND gate G-pass AND killswitch==off
        │   size = f(equity, ATR, risk budget)   ← math only
        ▼
execute (Alpaca paper): equities → bracket(order_class=bracket, take_profit, stop_loss)
                        crypto  → market entry + resting stop_limit
```
- Personas get *facts, not freedom*: fixed input schema (last N bars summary, regime label, headline list), strict output schema (Pydantic, same as `gemini_provider.generate_json`). No price suggestions, no sizes.
- Keeps the existing `DebateEngine` Q-score contract → `src/ops/daily.py` / paper executor wiring unchanged.

### 5.2 Event-loop architecture (GH Actions, $0)
| Piece | Implementation |
|---|---|
| Trigger | `.github/workflows/event_loop.yml`, cron `3-58/5 * * * *` (offset from hour-start per §4.1), concurrency group `ops-runner`, writes `docs/data/ops/heartbeat.json` + intent artifacts (pattern exists in `src/ops/heartbeat.py`) |
| Poll/stop-watch job | fetch quotes (Alpaca data API / yfinance), verify resting crypto `stop_limit` orders exist, read `ops_state.yaml` (killswitch), check triggers |
| Debate step | runs only when a trigger fires (idempotent: intent file → decision file, `generate_client_order_id` pattern in `src/execution/paper_executor.py`) |
| Execution step | existing `PaperExecutor.execute_plan()` path with gate + killswitch |
| Evidence | `audit.jsonl` gains prev-hash linking (§5.3); nightly workflow commits `docs/data/` (already the norm) |
| Watchdog | `ops_reports.yml`-style weekly run keeps repo active (60-day auto-disable, §4.1) |

### 5.3 Evidence chain (minimal)
`docs/data/ops/audit.jsonl` entry: `{ts, event, payload, prev_hash, hash: sha256(prev_hash + canonical_payload)}`. Verification script re-derives the chain from genesis; failure ⇒ alert via existing `src/ops/alerts.py` Telegram path. Daily Merkle root written to `docs/data/ops/evidence_root.json` and committed.

### 5.4 Capital discipline — $100 → $1,000
Current constants (`src/risk/position_sizing.py:10-18`, `src/ops/portfolio.py:6-7`): 1% risk/trade, 25% position cap, 4 concurrent, 60% total exposure, 40% cash buffer; breakers 5/10/15%.

| Account | Risk/trade | Position cap | Concurrent | Notes |
|---|---|---|---|---|
| $100 | 0.5–1% ($0.50–$1.00) | 25–50% ($25–$50) | **≤2** | 4×25% violates the 60% exposure cap; 2 positions × 40–50% ≈ 80–100% > 60% cap → actually ≤1–2 at ≤$30 each; prefer 1–2 positions with ATR stops (~2×ATR), fractional shares/notional orders |
| $250 | 0.75% | 40% | ≤2–3 | same exposure cap math |
| $500 | 0.5–0.75% | 30% | ≤3 | |
| $1,000 | 0.5% ($5) | 25% | ≤4 | original constants become valid at ~$1,000 |

- **The existing constants are calibrated for ~$1,000, not $100.** The harness must scale risk *fractionally* (percent-of-equity everywhere — already true) and scale *positions* via the exposure cap + concurrent-position cap (already enforced by `src/ops/portfolio.py:91` `max_allowed = equity * MAX_TOTAL_EXPOSURE_PCT`).
- ATR-based stops: stop distance = max(2×ATR, 1.5×daily vol) — never LLM-chosen; entry sized so `size × (entry−stop) ≤ risk budget`.
- Breakers stay %-based (scale naturally: 5% of $100 = $5, of $1,000 = $50).
- Human flip to live: requires G1–G7 pass (`gate_evaluator.py:11-14`: ≥50 paper trades, ≥10/sleeve, 7 consecutive heartbeat days), `state: live` in `config/ops_state.yaml` + live keys — no other code path change.

---

## 6. Open Risks & Unknowns

1. **Crypto exit latency** — no server-side bracket for crypto (§4.2); a 5–15 min poll gap means gap-risk on `stop_limit` fills (gap down through stop). Mitigations: resting `stop_limit` immediately after entry, `ioc` limit re-entry logic on gap, smaller crypto sleeves. **This is the design's weakest link.**
2. **Gemini quota variance** — free limits differ by region/account and change over time; `0 RPM`/`429` reports on free tier (§4.3). Mitigation: verify in AI Studio at P0; debate is non-critical path (trigger-gated, mock fallback keeps the loop alive).
3. **Schedule-event delay/drops** (§4.1) — under load, a run can be dropped; all steps must be idempotent (existing client_order_id pattern) and heartbeat staleness must alert (existing behavior).
4. **60-day cron auto-disable** (§4.1) — if all commit-capable workflows stop, cron dies. Watchdog weekly workflow with a guaranteed commit.
5. **Free-tier data training** (§4.3) — never put positions/sizes/keys in prompts; personas receive only public market data.
6. **Alpaca live crypto is region-restricted** (Alpaca Crypto LLC, US) — paper is global; if the user is outside supported regions, live BTC/ETH spot flip may be impossible (fall back to keeping crypto paper-only, or equities-only live).
7. **Two Gemini clients in repo** (`gemini_provider.py` 2.5-flash vs `gemini_client.py` 3.5-flash) — consolidate to one before P1 to avoid double quota math.

---

## 7. Phased Roadmap (paper-first, each phase ends with merged, gated code)

- **P0 — Verify (no code):** AI Studio quota check for the real project key; create/reset Alpaca paper account; confirm paper crypto symbols resolve via `/v2/assets`.
- **P1 — Real debate + crypto leg (foundation):** swap `_simulate_*` for Gemini personas behind `DebateEngine` (fallback to mocks on quota error); implement Alpaca crypto leg behind `BaseBroker` + wire `btc_vol_target_sma100` paper execution; add resting `stop_limit` exit + poll job (daily → intraday cadence).
- **P2 — Harness:** 5-min `event_loop.yml` (trigger → debate → decision → execute, all idempotent); declarative `config/risk_rules.yaml` read by breakers/gates with version pinning; evidence-chain prev-hash in `audit.py` + daily root commit; equities entries switch to server-side brackets.
- **P3 — Arena:** walk-forward backtest harness (point-in-time bars, single order path, commit-pinned data); optional masked-LLM debate replay (TraderHarness concept, minimal port).
- **P4 — Live flip (human decision):** gate pass + `state: live` + live keys; same code path; risk profile per §5.4; weekly reconciliation (`ops_reconcile.yml` already exists).

---

## 8. Sources
- https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows (scheduled events: 5-min min, UTC, default-branch run, delay/drop under load, 60-day auto-disable)
- https://docs.alpaca.markets/us/docs/paper-trading.md · https://docs.alpaca.markets/us/docs/crypto-orders.md · https://docs.alpaca.markets/us/reference/postorder.md (OrderClass: crypto = simple only)
- https://ai.google.dev/gemini-api/docs/rate-limits · https://discuss.ai.google.dev/t/limits-of-free-tier-api-vs-ai-studio/94918
- https://ai-trading.swiftward.dev · https://eigentrader.com · https://quantclaw-ai.com · https://hephaestlab.github.io/TraderHarness · https://github.com/AI4Finance-Foundation/FinRL-Trading · https://github.com/BenPomme/agentictrading
- Repo prior research: `docs/research/FEATURE-GAP-MATRIX.md`, `docs/research/COMPARABLE-REPOS.md`, `docs/LIVE_DESIGN.md`