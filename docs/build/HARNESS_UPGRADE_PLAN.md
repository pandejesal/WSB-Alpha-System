# HARNESS_UPGRADE_PLAN.md — Auto-Trading AI + Trading Harness

> Status: **PLANNED** (design frozen by /grilling 2026-08-19; research
> grounding: `docs/HARNESS_UPGRADE_RESEARCH.md`). No implementation yet —
> "plan only" per user decision. Supersedes nothing; extends the daily-paper
> build (`docs/build/PLAN.md`) with an event-driven harness layer.
> Prerequisite reading for implementers (repo rule): `docs/OPTIMIZATION_PLAYBOOK.md`,
> `docs/HUNT_PROTOCOL.md`, `docs/build/PAPER-GATE.md`.

---

## 1. Mission

Evolve the scheduled-paper-trading system into an Auto-Trading AI + Trading
Harness under hard constraints: **$0 infra, fully online (GitHub Actions only,
no local/VPS daemon), hybrid brain (deterministic math core + LLM analysis —
LLM never decides size/price), US equities + BTC/ETH spot via Alpaca paper,
paper-first with deterministic gate + human flip, event-driven trading
(price/news alerts + auto stops) over a mixed strategy portfolio.**

Pre-registered claims:
(a) 5-min event loop runs on GH Actions cron with repo-persisted idempotent
state (no daemon);
(b) real Gemini debate per trade candidate, costing **$0** (free tier,
single-call persona pattern, mock fallback on quota error);
(c) equities exits are server-side bracket orders; crypto exits are resting
`stop_limit` + poll verification;
(d) every decision links into a tamper-evident hash chain;
(e) risk rules move from Python constants to a versioned `risk_rules.yaml`;
(f) live flip remains a human decision behind G1–G7 + `state: live`.

## 2. Settled decisions (grilling + research)

| # | Decision | Rationale / source |
|---|---|---|
| D1 | Event loop = GH Actions cron `3-58/5 * * * *` (offset grid) | 5-min min; hour-start delay/drop risk; public repo = free unlimited minutes (research §4.1) |
| D2 | State bus = repo commits (existing ops pattern: heartbeat, ops_state.yaml, watch offset) | Proven in repo; idempotent by design |
| D3 | Hybrid brain: deterministic triggers + LLM debate → deterministic decision (conviction ≥ 0.6, gate pass, killswitch off); sizing/stops math-only | Swiftward "no hallucination in the core" (research §2.1, §5.1) |
| D4 | Debate = **single Gemini call per debate** (3 personas + synthesis in one prompt), Flash-Lite default, mock fallback on 429 | User constraint: free tier only; 4x cheaper than 4-call design (research §4.3); final model choice gated on P0 quota check (D4a) |
| D4a | If AI Studio shows <250 RPD on the real key → debate stays mock; revisit at P2 | Research §4.3 pessimistic floor; decision gate, user-owned |
| D5 | Equities: bracket orders (take_profit + stop_loss). Crypto: market entry + immediate resting `stop_limit`; poll job verifies resting order exists each run | Bracket/OCO/OTO = equities only; crypto = market/limit/stop_limit (research §4.2) |
| D6 | Evidence chain: `audit.jsonl` entries carry `sha256(prev_hash + payload)`; daily root committed | Swiftward/EigenTrader pattern, $0 (research §5.3) |
| D7 | Declarative rules: `config/risk_rules.yaml` (draft→active→archived), SHA-256 pinned in evidence chain | Swiftward lifecycle, EigenTrader policy gate (research §2.7, Gap 3) |
| D8 | Capital discipline: current constants calibrated for ~$1,000; at $100 → ≤2 positions, 25–50% caps, ATR stops (max 2×ATR, 1.5×daily vol), fractional/notional orders | Research §5.4 |
| D9 | Live flip: G1–G7 pass (≥50 paper trades, ≥10/sleeve, 7 heartbeat days) + `state: live` + live keys; region caveat: Alpaca live crypto = US only | Gate already in `src/ops/gate_evaluator.py:11-14`; research §6.6 |

## 3. Phase gates (every phase)

- Implementation routes **exclusively through Jules** (repo AGENTS.md rule),
  one PR per phase, AUTO_CREATE_PR off (review gate first).
- Review gate: read the diff myself; gates = `PYTHONPATH=. pytest`,
  `ruff check .`, `bandit -r src/` (repo verified commands); fail-closed
  behavior preserved (no stubs, no mock credentials).
- Each phase ends with merged, gated code on `main`; heartbeat + state
  commit patterns intact (60-day cron auto-disable watchdog).

## 4. P0 — Verify (USER task, no code)

- [ ] Check real Gemini free-tier quota in Google AI Studio (RPM/RPD/TPM for
      the actual project key; note 2.5-flash vs flash-lite vs 3.5-flash rows)
      → decides D4 vs D4a.
- [ ] Create/reset Alpaca **paper** account (Paper Only, no funding, free);
      confirm `BTC/USD`, `ETH/USD` resolve via `GET /v2/assets`.
- [ ] Confirm repo secrets present: `ALPACA_API_KEY/SECRET` (paper), `GEMINI_API_KEY`.
- [ ] Record results back in this file (P0 checklist) — do NOT start P1 until done.

## 5. P1 — Real debate + crypto leg (foundation)

Tasks (Jules brief):
1. **DebateEngine real personas** — replace `_simulate_*` bodies
   (`src/research/debate_engine.py:10,75,106,136`) with one bounded Gemini
   call (persona system-prompt ×3 + synthesis in a single prompt, strict
   Pydantic output schema reusing `gemini_provider.generate_json`); same
   inputs (quotes summary, regime label, headlines — **never positions/sizes**);
   keep Q-score contract (`src/ops/daily.py` wiring unchanged); mock fallback
   on quota error keeps loop alive. Consolidate the two Gemini clients
   (`gemini_provider.py` 2.5-flash vs `gemini_client.py` 3.5-flash) — pick one
   (research §6.7).
2. **Alpaca crypto leg** — `BTC/USD`, `ETH/USD` behind `BaseBroker`
   capability flags (`src/execution/base_broker.py:38-42`; universal_broker
   seam at `src/execution/universal_broker.py:107`); wire
   `btc_vol_target_sma100` sleeve paper execution (`src/ops/portfolio.py`);
   entry = market/notional; exit = resting `stop_limit` immediately after
   entry.
3. **Poll/stop-watch job** — extend cadence (daily → intraday) to verify
   resting crypto `stop_limit` exists each run; re-place if missing; alert on
   staleness (existing heartbeat/alerts pattern).
4. Tests for all three; acceptance = debate returns valid Q-score with/without
   API key; crypto order path round-trips in paper; poll job detects missing
   stop within one run.

## 6. P2 — Harness

1. **`event_loop.yml`** — cron `3-58/5 * * * *`, concurrency group `ops-runner`;
   steps: poll quotes (Alpaca data/yfinance) → check killswitch
   (`config/ops_state.yaml`) → evaluate deterministic triggers (price levels,
   news keywords, indicator events) → if fired: debate → decision → execute via
   existing `PaperExecutor.execute_plan()` path; all idempotent
   (`generate_client_order_id` pattern); heartbeat + intent/decision artifacts
   committed.
2. **`config/risk_rules.yaml`** — versioned rules (per-sleeve limits, tier
   scaling, breakers) read by `circuit_breakers.py` +
   `gate_evaluator.py:11-14`; lifecycle draft→active→archived; SHA-256 pinned
   in evidence chain.
3. **Evidence chain** — `src/ops/audit.py` gains prev-hash linking; daily
   Merkle root → `docs/data/ops/evidence_root.json` committed; verification
   script re-derives chain, failure → Telegram alert (`src/ops/alerts.py`).
4. **Equities brackets** — `alpaca_broker.place_order`
   (`src/execution/alpaca_broker.py:56-79`) gains `order_class=bracket` +
   take_profit/stop_loss; exits become server-side.
5. Capital discipline per D8 (position_sizing constants → fractional,
   concurrent-position cap enforced via `src/ops/portfolio.py:91` exposure cap).

## 7. P3 — Walk-forward arena (LLM-agent backtest, minimal)

- Point-in-time walk-forward harness: data as-of decision date (Alpaca
  historical bars / yfinance), single order path, no future bars, read-only
  portfolio view (TraderHarness invariants, research §2.4 — not a port);
  optional masked-date/entity LLM debate replay; results vs hindsight compared.
- Acceptance: candidate strategies replay deterministically; leakage check
  (no bar later than decision time reachable) asserted in tests.

## 8. P4 — Live flip (HUMAN decision, out of scope until invoked)

- Gate pass + `state: live` + live keys; same code path (D9); weekly
  reconciliation (`ops_reconcile.yml` exists); region check for crypto (D9).

## 9. Risks carried from research (§6)

Crypto exit gap risk (5–15 min poll window, no server-side bracket) — resting
`stop_limit` + gap re-entry logic; schedule drop/delay — idempotent runs +
heartbeat staleness alert; 60-day cron auto-disable — watchdog committer;
free-tier data training — never send positions/sizes/keys in prompts;
Gemini quota variance — D4a decision gate + mock fallback.

## 10. Sequence

P0 (user) → P1 (Jules) → review → P2 (Jules) → review → P3 (Jules) → review →
P4 (human). No phase starts before the previous review gate passes. Nothing
delegated to Jules until the user says go.