# Jules Task Brief — Autonomous Paper-Trading System (P2–P5)

Implementation contract for the autonomous paper-trading system. Read `docs/build/PLAN.md` and `docs/build/ARCHITECTURE.md` first — they are the frozen design (grilled and confirmed 2026-08-17). Read `docs/build/PAPER-GATE.md` for the operational gate. Follow this brief phase by phase; each phase is one PR.

## Global constraints (all phases)

- Repo: `pandejesal/WSB-Alpha-System`. Work on a branch, one PR per phase, conventional commit messages (`feat(ops): ...`, `fix(backtest): ...`).
- **Never** store secrets in files. Env vars / GH Actions secrets only (see PLAN.md env spec; existing secrets: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`).
- Alpaca is the ONLY broker used by the live system. ccxt/Binance code stays dormant (no keys).
- Market orders only. Every order carries a deterministic `client_order_id` (correlation ID per ARCHITECTURE.md) for idempotent reconciliation.
- Never auto-flat positions. Kill-switch = 3 tiers (Telegram stop command → `config/ops_state.yaml` repo edit → manual workflow dispatch).
- The honest T+1 engine (`src/backtest/run_historic_backtest`) is the only engine validation/reporting may bind to. `src/backtest/legacy_backtest.py` is `LEGACY_REFERENCE_ONLY` — never import it for production reporting.
- All state and logs are files in `docs/data/ops/` (repo-as-truth). Artifacts must match the schemas in ARCHITECTURE.md.
- Keep `tests/test_p0_fixes.py` green — it locks the audit fixes.

## Phase 2 — Signals (P2)

Build the signal layer that turns daily market data into sleeve signals.

- `src/signals/` module. Input: daily OHLCV for the 7-sleeve universe (see roster in PLAN.md; `dual_momentum` is `inactive` — exclude). Output: one `docs/data/ops/signals.json` per run with schema per ARCHITECTURE.md (`run_id`, `date`, `mode`, per-sleeve `{id, signal: LONG|FLAT|SHORT|HOLD, confidence, params}`).
- Sleeve roster (7): `lowvol`, `pead`, `breakout` (ported from existing strategy code in the repo — reuse `strategies/` YAMLs where they exist), `us_momentum_top5`, `spy_sma200`, `spy_rsi2`, `btc_vol_target_sma100`. `dual_momentum` → `status: inactive` in the registry.
- Each sleeve must expose `signal(date, data) -> Signal` and be unit-testable with a fixed fixture (no network in tests).
- Fail-closed: missing/stale data for a sleeve → that sleeve emits `FLAT` + a warning entry, never a guess.
- Acceptance: unit tests per sleeve (fixture-based), signals.json written atomically with `run_id`, CI green.

## Phase 3 — Paper execution (P3)

- `src/execution/` paper broker: Alpaca paper API wrapper (`alpaca-py`), market orders only, `client_order_id` = correlation ID, poll fills <= 30 s, record fill receipt.
- Daily cron (existing workflow patterns in `.github/workflows/`): 7-day schedule, equities sleeves weekday-gated (spy_sma200/spy_rsi2 only on trading days), BTC sleeve daily.
- Order path per PLAN.md state machine: IDLE → GATE → SIGNALS → ORDERS → FILLS → POSITIONS. Every transition appended to `docs/data/ops/audit.log` (JSONL, one event per line, schema in ARCHITECTURE.md).
- Idempotency: re-running a day with the same `run_id` must not double-order (reconciliation compares plan vs fills).
- Sizing: 7 equal-risk sleeves, 10% vol target, sum cap 60%, 40% cash floor; per-sleeve drawdown breaker auto-halts new orders at 1.5 x modeled DD (`halt_new_orders: true` in `config/ops_state.yaml`).
- Acceptance: sandbox-mode dry run of one full day (plan → orders → mock fills → audit log), `tests/paper_trading/test_execution_bridge.py` extended for idempotency, CI green.

## Phase 4 — Monitoring & kill-switch (P4)

- `src/monitoring/telegram_bot.py` exists — extend it: heartbeat on every workflow run, severity ladder per ARCHITECTURE.md, `getUpdates` polling via `ops_watch.yml` (every 15 min) for stop commands.
- Kill-switch tiers: (1) Telegram stop → writes `config/ops_state.yaml` `stopped: true`; (2) repo edit of `config/ops_state.yaml`; (3) manual `dispatch` of `ops_stop.yml`. All tiers log to `docs/data/ops/audit.log`.
- Reconciliation job `ops_reconcile.yml`: compares plans vs fill receipts daily; mismatch → CRITICAL alert, artifact `docs/data/ops/reconciliation.json`.
- Position/P&L: merged-position pro-rata accounting per ARCHITECTURE.md; `docs/data/ops/plan.json` heartbeat schema preserved.
- Acceptance: kill-switch rehearsal script (`scripts/kill_switch_rehearsal.py`) documented in PAPER-GATE.md G6, Telegram alerting unit tests (mocked HTTP), CI green.

## Phase 5 — Paper gate & reports (P5)

- Daily/weekly report workflows (extend `daily_research.yml` patterns): honest-engine tearsheet via `src/backtest/validation.py` `TEARSHEET_ENGINE` (already fixed), Sharpe with CI for the paper P&L series → `docs/data/paper/sharpe.json`.
- Full 200-permutation protocol run weekly, results into `docs/data/permutation_study.json` (replaces the bounded 40-perm confirmation).
- Gate evaluator `ops_gate.yml`: computes G1–G7 from artifacts (PAPER-GATE.md); on G1/G2/G3 failure → CRITICAL alert + auto-halt new orders (never auto-flat). Gate flip itself is a human decision.
- Acceptance: gate evaluator is a pure function of `docs/data/ops/*` artifacts (unit-tested with fixture artifacts), CI green.

## Definition of done per phase

1. Code + tests + CI green.
2. Artifacts conform to ARCHITECTURE.md schemas.
3. Audit log events present for the phase's state transitions (fixture-level).
4. PR description lists acceptance criteria checked and any deviations with rationale.
5. No secrets, no auto-flat, no engine rebinding to legacy.

Questions / deviations from PLAN.md or ARCHITECTURE.md: stop and ask via PR comment or message; do not silently redesign.
