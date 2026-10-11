# WSB-Alpha-System — Audit Remediation Plan (2026-10-11)

**STATUS: Phase 1 IMPLEMENTED — commit `7f3a2f1` on branch `fix/audit-remediation-phase1` (local, not pushed).**

Source: external audit of commit `f176056`, verified against local main
(`1072fea`) on 2026-10-11. All file:line references were current at
implementation time in `WSB-Alpha-System-build/`.

**Standing rule: live trading stays disabled until Phase 2 statistical work
is verified.**

## Phase 1 — Execution safety (Critical) — ✅ DONE (commit 7f3a2f1)

### P1.1 Fix gate↔executor fill schema (audit Finding 3) — ✅
- New `src/ops/artifacts.py`: the single artifact contract — fills wrapper
  `{"run_id", "fills": [...]}`, canonical `sleeve_id` key, required fields
  (client_order_id/sleeve_id/status), numeric-type checks, known-status
  check. Helpers: `extract_fills` / `is_confirmed_fill` / `sleeve_of`
  (legacy `sleeve` fallback) / `make_fill_record`.
- Executor writes the wrapper with `sleeve_id`; only broker-confirmed fills
  enter fills.json. Gate reads through `extract_fills`, fails closed to []
  on malformed artifacts; G1/G2 count confirmed fills only.
  `reconcile.py` + `baseline_paper_track.py` use the shared contract.
- Tests: `tests/ops/test_artifacts.py` (schema) +
  `tests/ops/test_paper_executor_gate_integration.py` (executor→gate).

### P1.2 Broker-backed idempotency + fill semantics + reconciliation (Finding 4) — ✅
- `client_order_id` now reaches the broker: BaseBroker contract, Alpaca
  `MarketOrderRequest(client_order_id=...)`, CCXT `clientOrderId` param,
  ExecutionWrapper forwards it (backoff retries stay idempotent).
- Order intent persisted BEFORE the broker call (SUBMITTING); full state
  machine incl. UNKNOWN. Ambiguous outcomes (exception mid-call) are never
  resubmitted; `BaseBroker.get_order` (Alpaca implemented) resolves prior
  ambiguity on the next run.
- Recon derives deltas from before/after position snapshots vs fill-implied
  expectations; position-fetch failure → status `unknown` (never clean);
  mismatches + unconfirmed orders reported; WARN alert on non-clean.

### P1.3 Paper/live isolation + schedule (Finding 2) — ✅
- `PaperExecutor` default broker is `AlpacaBroker(paper=True)`; live config or
  an injected live broker (`is_paper=False`) is a hard RuntimeError.
- `paper_trade.yml`: weekday-only cron `55 20 * * 1-5`; live-flag
  pass-through removed. `run_paper_execution.py` skips non-NYSE-trading days
  via `gs_compat.calendar.is_business_day`.
- Test: `tests/test_paper_execution_calendar.py`.

### P1.4 Risk limits enforced (Finding 1) — ✅ (user-approved: default ON)
- `position_sizing.py`: `PRM_HARD_STOP_ENABLED`/`CIRCUIT_BREAKER_ENABLED`
  default ON (env opt-out preserved); limits back to 5%/10%/15%.
- Sizer rejects invalid/non-positive inputs and non-positive Kelly edge
  (no fallback-to-1%); enforces 1% per-trade risk cap (hard stop on), 25%
  position cap, equity umbrella, and the concurrent-position limit.
- Tests: `tests/test_risk_enforcement.py`.

### P1.5 Kill-switch flat semantics (Finding 5) — ✅
- `flat` renamed `halt_only` (killswitch, executor, watch.py `/flat` command,
  rehearsal script); legacy `flat` in ops_state.yaml fails closed to
  `halt_new_orders` with a CRITICAL log. Real flattening remains explicitly
  unimplemented.

**Fixed while wiring the contract:** executor aliased the broker's live
positions list (recon "before" saw post-fill state) — now snapshotted;
`reconcile.py` crashed on the wrapper format, silently reporting every
planned target missing — now parses via the shared extractor.

**Pre-existing failures NOT caused by this work (repo came dirty):**
`tests/ops/test_preregistration.py` (3), `test_h1_regime.py` (1),
`test_hunt_runner.py` (3), `test_strategy_specs.py` (1) — all fail
identically with this commit stashed. Unrelated WIP files
(`src/ops/preregistration.py`, `scripts/preregister.py`,
`scripts/hunt_runner.py`, `scripts/evolve_generations.py`,
`src/signals/tail_hedge_signal.py`) left untouched.

## Phase 2 — Backtest trust (High)
1. **F6** `run_historic_backtest.py:128,52` — missing/neutral sentiment must
   not default to short. 4-state policy; missing ⇒ no trade; tests for all four.
2. **F7** `validation.py:80,83` — replace summed return + post_date grouping
   with an equity-curve (positions+cash) → daily portfolio returns → metrics;
   known-answer tests.
3. **F8** exit assumptions — gap-through-stop fill model; independent exit
   slippage; explicit short-hold clamp flag; benchmark interval alignment.
4. **F9** `walk_forward_engine.py` + `validation.py:174-177` — real
   fit-on-train/evaluate-on-test loop, advance, aggregate OOS only, purge/gap
   across the boundary.
5. **F10** `permutation_tester.py:14,57-60,127` — default null must satisfy its
   documented claim (circular roll with one shared lag doesn't);
   p=(k+1)/(N+1); synthetic-data tests; align with `validation.py:151,246`.
6. **F11** `cache_engine.py:132-166` + `chain.py:36-43` — per-ticker coverage
   validation incl. internal gaps; delisted ≠ cached; parameterized SQL
   (`:56-61,107,115,147`); expose freshness; refuse incomplete inputs.
7. **F12** `gate_evaluator.py:58-61` — document null/alternative/statistic/
   direction/promotion condition; unit tests from known cases.

## Phase 3 — CI trust
- F13: reproduce + fix the pytest collection failure (latest visible run died
  at the collect-only gate).
- F14 `ci.yml:28-56`: add `pull_request` trigger; full suite hard gate; remove
  `|| true` from gating steps; remove the fallback-to-small-suite line;
  publish coverage and failure-log artifacts; shrinking Ruff baseline.

## Phase 4 — Consolidate (after 1-3)
Position-sizing/portfolio-risk paths, broker executors, reconciliation
schemas, backtest metrics, validation interfaces, promotion gates.
