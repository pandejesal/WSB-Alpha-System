# ARCHITECTURE.md — Institutional Spec for the Autonomous Paper-Trading System

> Companion to `docs/build/PLAN.md` (decisions) — this file is the **how**:
> audit trail, kill-switch, alerting, reconciliation, repo-as-truth.
> Baseline `origin/main` @ `04705db`. Design frozen by /grilling 2026-08-17.

---

## 1. Principles

1. **Repo = truth.** Every artifact a run produces lives in the repo
   (`docs/data/ops/*.json`). No external DB. The runner is the **single
   writer** — enforced by the `docs-data-writers` concurrency group and
   run_id dedupe.
2. **Fail closed, always.** Any gate failure → zero orders that run.
   The default is to do nothing.
3. **Never trust the submit response.** Fills come from polling
   `GET /v2/orders/{id}` until terminal state or a 30 s budget
   (`FILL_POLL_BUDGET_SEC=30`, matches harness convention).
4. **Honest numbers.** No stubs in the paper path (E-1 fixed), fills at
   T+1 (E-2 fixed), sandbox P&L labeled TOY_SANDBOX and excluded (E-6
   fixed). If a number is an estimate, it carries an estimator tag.
5. **Kill-switch is 3-tier and never auto-flat.** Machine truth in
   `config/ops_state.yaml`; `flat` requires `manual_override: true`.
6. **Idempotent everywhere.** `client_order_id` on every order; startup
   reconciliation dedupes crashed-run leftovers before new orders.
7. **Auditable end-to-end.** Every order/fill/position change carries a
   correlation id from run → order → fill → position → P&L line.

## 2. Correlation IDs and the audit trail

`run_id = <YYYY-MM-DDTHH:MM:SSZ>-<git_short_sha>` (existing pattern, kept).

```
run_id ──► order_id = <run_id>-<sleeve>-<ticker>-<seq>
   │            │
   │            └──► fill_record {client_order_id, venue_order_id, qty, px, fee, ts}
   │
   └──► audit.jsonl line per event: {run_id, ts, event, entity, id, payload}
   │
   └──► metrics.json line: {run_id, sleeve, realized_pnl, unrealized_pnl,
                             attribution_pct, dd_hwm, dd_from_hwm}
```

Artifacts written per run (all under `docs/data/ops/`, committed by the
workflow):

| File | Schema (top-level) | Written at | Notes |
|---|---|---|---|
| `plan.json` | `{run_id, date, mode, sleeves:[{id, signal, targets:[{ticker, qty, side, reason}], merged_positions:[…]}]}` | ORDERS, before any order | single source of "intended" |
| `orders.json` | `{run_id, orders:[{client_order_id, venue_order_id, sleeve, ticker, side, qty, type, submitted_at, status}]}` | FILLS | appended per order |
| `fills.json` | `{run_id, fills:[{client_order_id, venue_order_id, qty, avg_px, fee, ts, side, ticker, sleeve}]}` | FILLS | per fill (possibly multiple per order) |
| `recon.json` | `{run_id, before:{positions}, after:{positions}, deltas:[{ticker, side, qty, expected, actual, status}], mismatches:[…]}` | POSITIONS | mismatch → WARN alert, never auto-repair |
| `metrics.json` | `{run_id, date, sleeves:[{id, equity, daily_pnl, realized, unrealized, attribution_pct, dd_from_hwm}], account:{equity, cash, buying_power, margin_used}}` | P&L | appended per run (append-mode) |
| `heartbeat.json` | `{run_id, ts, mode, result: ok\|failed, orders_submitted, alerts:[]}` | AUDIT | existing schema, extended with `result_detail` |
| `alerts.json` | `{ts, severity, source, message, run_id}` | any point | append-mode; degraded path when Telegram down (F9) |
| `audit.jsonl` | one JSON line per event | any point | raw event log, unbounded (trimmed to last 30 days) |

## 3. Kill-switch (3-tier, from Ops-Design, amended)

Machine truth: `config/ops_state.yaml` (committed; written only by the
watch workflow or manual repo edit).

```yaml
state: off                  # off | halt_new_orders | flat
set_at: 2026-08-17T00:00:00Z
set_by: manual              # manual | telegram | workflow
manual_override: false      # REQUIRED true to enter/exit flat
reason: ""
```

| Tier | Mechanism | Latency | Orders today | Flattening |
|---|---|---|---|---|
| T1 (manual) | repo edit of `ops_state.yaml` + `workflow_dispatch` | ~minutes | blocked | **flat** only if `manual_override: true` (never automated) |
| T2 (telegram) | `ops_watch.yml` polls `getUpdates` every 15 min for `/kill`, `/halt`, `/flat`; writes ops_state.yaml | ≤15 min | blocked at next poll+run | `/flat` writes state only; flattening happens on next daily run |
| T3 (machine) | per-sleeve HWM DD breaker trips → `halt_new_orders` for that sleeve | same run | that sleeve blocked | **never** — machines do not flatten |

Resume gate (daily run, in `GATE` state): `state != halt_new_orders` AND
(if `flat`: `manual_override: true` AND human re-set `state: off`) AND data
fresh (≤3 d) AND API reachable AND breaker open. Fail → zero orders.

Kill-switch matrix K1–K6 (Ops-Design): K1 off→halt, K2 halt→off, K3
off→flat (manual only), K4 flat→off (manual only), K5 telegram /halt, K6
telegram /kill — each exercised in P5 with a test run before go-live.

## 4. Alerting (Telegram)

`src/monitoring/telegram_bot.py` (exists) extended per severity ladder;
config via `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` (GH secrets exist).

| Severity | Channel | Examples |
|---|---|---|
| INFO | daily digest (1 msg, compact) | run ok, N orders, fills summary, account snapshot |
| WARN | direct msg | recon mismatch (F4), fill timeout (F3), heartbeat stale (F8), breaker trip (F7), 3 consecutive failures (F1/F2) |
| CRIT | direct msg + repeated | kill-switch engaged, API auth failure, unexpected exception in ORDERS/FILLS |

Digest failure (F9) degrades to `alerts.json` file only — trading
**unaffected**, next run resends digest. No secrets in messages (tickers
and amounts only).

## 5. Reconciliation and idempotency (startup + post-trade)

**Startup (ORDERS entry), Nautilus pattern:**
1. `GET /v2/positions` + `GET /v2/orders?status=open` → local state map.
2. For every open/SUBMITTED order whose `client_order_id` starts with a
   **prior** run_id: poll once; if terminal → record fill; if still open
   → cancel-and-resubmit under a **new** client_order_id for this run
   (dedupe; never double-submit the same id).
3. Reconcile target state → build `plan.json`.

**Post-trade (POSITIONS):** full position sync; every delta compared to
planned; mismatch → WARN + recon.json entry; **no blind repair**
(positions are adjusted next run by normal target logic, or by human).

**Run dedupe:** workflow concurrency group `docs-data-writers` (exists) +
`run_id` recorded in heartbeat; if heartbeat for today's run_id already
exists at GATE entry, exit with WARN (F11).

## 6. Merged-position accounting (correlation guard)

- Same-ticker targets from different sleeves **merge** into one market
  order (`qty = Σ targets`), issued under the **higher-ranked** strategy's
  client_order_id prefix (`rank` from `strategies/registry.json`).
- Fill attribution: **pro-rata** by each strategy's target weight at
  plan time (`attribution_pct` per sleeve in metrics.json).
- Combined-weight cap: Σ merged target weights for a ticker ≤ cap
  (param, default 5 % of account); breach → lower-ranked strategy's
  component skipped + logged (F6), higher-ranked trades.
- Exit: sleeve exits are separate orders (per-sleeve logic), but a
  **flat-requested** ticker's remaining merged quantity is closed by the
  requesting sleeve with full attribution.
- P&L lines per sleeve carry `attribution_pct` so per-strategy gate
  evaluation uses only attributed P&L (honest per-sleeve numbers).

## 7. Order lifecycle taxonomy (broker layer, P2)

States (normalized across brokers): `SUBMITTED → PARTIAL → FILLED` |
`CANCELED` | `REJECTED` (error taxonomy: AUTH, RATE_LIMIT, INSUFFICIENT,
INVALID_PARAM, VENUE_DOWN, TIMEOUT). Poll until terminal or
`FILL_POLL_BUDGET_SEC=30`; non-terminal → `UNFILLED-TIMEOUT` (F3).

Broker seam (LIVE_DESIGN §1/§2, adopted): `BaseBroker.get_capabilities()`
returns venue flags (`streaming: False`, `fractional: True`,
`paper: True`, `crypto: True`) — conformance tested in
`tests/brokers/test_broker_capability.py` (exists). The **order gate**
(every order passes min-notional, $2k-short rule, weight caps, state
checks) runs **inside the broker** before REST submission, so it cannot be
bypassed by a caller.

## 8. Sizing and risk internals (P3)

- Sleeve equity `E_i = min(account_equity, 100000_paper_cap) × 0.60/7`
  (equal-risk nominal), vol-targeted: `qty = (E_i × 0.10) / (σ_i ×
  sqrt(252)) / px`, `σ_i` = realized vol window from strategy YAML.
- Combined sleeve notional ≤ 60 % account; residual 40 % cash.
- Per-sleeve HWM tracker: `dd_from_hwm = (HWM - equity)/HWM`; breaker at
  `1.5 × MODEL_DD` (MODEL_DD from strategy YAML `expected_metrics`);
  trip → `halt_new_orders` (T3); release on HWM recovery or manual
  override. `MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT=0.15` (risk_config) finally
  enforced at account level (was declared, never wired — LIVE_DESIGN §3).
- $100-feasibility: `min_notional` guard ≤ $1; fractional shares on;
  `$100 simulation test in CI` (P4) proves every sleeve trades at $100.

## 9. ops_watch.yml (P5)

```yaml
cron: "*/15 * * * *"
jobs:
  - poll Telegram getUpdates (since_offset persisted in docs/data/ops/watch_state.json)
  - parse /kill | /halt | /flat | /status
  - write config/ops_state.yaml (state, set_at, set_by=telegram, reason)
  - commit + push (same concurrency group)
```
Read-only w.r.t. orders — it can never place orders, only set state.
`/status` replies with last heartbeat summary (read of repo files).

## 10. Repo-as-truth mechanics

- Every write path: write temp file → atomic rename → `git add` → commit
  with run_id in message → push. Single writer via concurrency group.
- Push conflicts (rare double-run) → re-read + merge artifacts by run_id,
  then re-push (idempotent by run_id dedupe).
- History: artifacts retained 30 days (audit.jsonl trimmed); metrics.json
  append-mode is the long-term P&L ledger.
- API health: `docs/data/ops/apiHealth.json` already maintained by
  existing workflow; heartbeat consumes it at GATE (API reachable check).

*Recorded 2026-08-17. Frozen by /grilling; changes via decision note only.*