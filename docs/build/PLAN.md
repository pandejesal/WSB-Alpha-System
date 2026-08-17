# PLAN.md — Autonomous Paper-Trading System (Build Prompt 13)

> Status: **PLANNED (design frozen by /grilling 2026-08-17)** — shared
> understanding confirmed; P0+P1 in progress. Supersedes
> `docs/LIVE_DESIGN.md` (reconciled: its broker-seam, capability-flag and
> reconciliation guidance is adopted; its hedge and live-engine sections are
> out of scope for the paper build and deferred).
> Baseline: `origin/main` @ `04705db` (PRs #133/#135–#140 merged; PR #134
> closed as superseded — all its files already on main).

---

## 1. Mission

Design and build the autonomous trading system for the WSB-Alpha-System
flagship library, running on **real paper accounts** (Alpaca paper for US
equities + BTC/USD), engineered so switching to real money is a **config
change behind a strict go-live gate** (`docs/build/PAPER-GATE.md`).
Everything works: strategies produce signals, orders execute, positions
track, P&L accrues, heartbeats beat, alerts fire, kill-switch works — and
every number is honest (no stubs, no lookahead, no toy P&L).

Pre-registered claim (unchanged): (a) all gate-passing winner strategies
trade on Alpaca paper, (b) every fill is real (broker API), (c) audit
findings E-1/E-2/E-6 fixed first with regression tests, (d) paper
performance validated against the same 5 strategy gates, (e)
monitoring/heartbeat/alerts/kill-switch work end-to-end, (f) real-money
go-live is a config change behind an explicit gate.

## 2. Runtime model (settled by grilling)

- **GH Actions is the sole 24x7 trader.** OpenCode runs locally for
  build/research/backtesting only. No local trading, ever.
- **One daily run, 7 days a week** (extend `paper_trade.yml` cron from
  `55 20 * * 1-5` to `55 20 * * 0-6`). Equities sleeves are weekday-gated
  (US market closed Sat/Sun); the BTC sleeve runs every day.
- **Alpaca paper only.** Crypto sleeve trades BTC/USD on Alpaca (24/7
  venue, immediate fills at run time). `ccxt_broker.py` stays dormant.
- **No streaming** — GH Actions runners are ephemeral; fill confirmation
  is poll-based (`GET /v2/orders/{id}`) with a 30 s budget, matching the
  harness convention "never trust submit response filled_qty".
- **Repo = truth.** Every run commits artifacts to `docs/data/ops/*.json`
  (single writer: the Actions runner).

## 3. Architecture (ASCII)

```
                         ┌──────────────────────────────────────────────┐
                         │              GitHub Actions                   │
                         │                                              │
 cron 55 20 * * 0-6 ───► │  paper_trade.yml  (daily run, 7-day)        │
                         │  ┌────────────────────────────────────────┐  │
                         │  │ src/ops/daily.py  (extended engine)     │  │
                         │  │  1. resume-gate: kill_switch + DD +    │  │
                         │  │     data freshness (fail-closed)       │  │
                         │  │  2. fetch data (yfinance v8, 100-name  │  │
                         │  │     universe, OPS_V8_SPACING≈0.75s)    │  │
                         │  │  3. signals (src/ops/signals.py)       │  │
                         │  │  4. reconcile positions vs Alpaca      │  │
                         │  │  5. build order plan (merged positions │  │
                         │  │     + correlation guard)               │  │
                         │  │  6. execute via src/execution/         │  │
                         │  │     alpaca_broker.py (client_order_id  │  │
                         │  │     idempotency, poll fills)           │  │
                         │  │  7. P&L mark + audit trail write       │  │
                         │  └────────────────────────────────────────┘  │
                         │                                              │
 cron */15 * * * * ────► │  ops_watch.yml  (lightweight watch)          │
                         │  • polls Telegram getUpdates for /kill       │
                         │    /halt /flat commands                      │
                         │  • writes config/ops_state.yaml (machine     │
                         │    truth for kill-switch, no order ability)  │
                         └──────────────┬───────────────────────────────┘
                                        │ REST (paper-api.alpaca.markets,
                                        │   crypto: data.alpaca.markets)
                                        ▼
                              ┌──────────────────────┐
                              │  Alpaca PAPER        │   equities + BTC/USD
                              │  $100k paper account │   market orders,
                              └──────────────────────┘   fractional shares
                                        │
        Telegram bot ───── alerts ───────┤  ops artifacts
                                        ▼
                              docs/data/ops/*.json  (committed, repo = truth)
                              docs/data/ops/heartbeat.json (every run)
                              config/ops_state.yaml (kill-switch state)
```

## 4. Module ownership

| Module (new in bold) | Owner | Responsibility |
|---|---|---|
| `src/ops/daily.py` | exists (check-mode) + **extend P3** | daily loop: resume gate, data, signals, reconcile, orders, fills, P&L, audit |
| `src/ops/signals.py` | exists | per-strategy signal functions (5 ported; +3 in P4) |
| `src/execution/base_broker.py` | exists | broker contract: capabilities, `place_order(client_order_id, …)`, `get_order`, `get_positions`, `get_account`, order-state taxonomy |
| `src/execution/alpaca_broker.py` | exists, **harden P2** | Alpaca paper adapter: idempotent placement, fill polling, position sync, error taxonomy, **order gate runs inside broker** (LIVE_DESIGN §2) |
| `src/execution/ccxt_broker.py` | exists | dormant (no venue configured) |
| **`src/ops/portfolio.py`** | P3/P4 | sleeve definitions (7), equal-risk sizing to 10 % vol, ≤60 % total, merged-position accounting (pro-rata attribution), correlation guard |
| **`src/ops/risk.py`** | P3 | per-sleeve HWM DD tracker, `halt_new_orders` at 1.5×MODEL_DD, resume gate, circuit breaker wiring (`MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT` finally enforced — LIVE_DESIGN §3) |
| **`src/ops/audit.py`** | P3 | correlation IDs, audit trail (`docs/data/ops/{plan,orders,fills,recon,metrics}.json`), run receipts |
| **`src/ops/heartbeat.py`** | P5 | heartbeat.json every run; staleness detection (>2 missed runs → WARN alert) |
| **`src/ops/alerts.py`** | P5 | Telegram severity ladder + daily digest (token/chat from env/GH secrets) |
| **`src/ops/killswitch.py`** | P5 | reads `config/ops_state.yaml` (off\|halt_new_orders\|flat); enforces; never auto-flat |
| **`src/ops/watch.py`** | P5 | `ops_watch.yml` entrypoint: Telegram getUpdates poll → write ops_state.yaml |
| `scripts/run_full_backtest.py` | P0 fix | E-2: fills at Open[t+1] |
| `src/backtest/run_historic_backtest.py` | P0 fix | E-2: fills at Open[t+1] |
| `src/backtest/validation.py` | P0 fix | E-1: rebind to real engine; weekly permutations stay honest |
| `scripts/paper_trading_sandbox.py` | P0 fix | E-6: TOY_SANDBOX label, excluded from reporting |
| `strategies/registry.json` + `strategies/*.yaml` | P4 (Jules) | +3 YAMLs (us_lowvol_top30, us_pead_top5, breakout_burst), registry entries; dual_momentum → `status: inactive` |
| **`docs/build/`** | session (P1) | PLAN.md, ARCHITECTURE.md, PAPER-GATE.md, JULES-TASKS.md |
| `.github/workflows/paper_trade.yml` | P3/P5 (Jules) | cron → 7-day; run full engine; commit artifacts |
| **`.github/workflows/ops_watch.yml`** | P5 (Jules) | 15-min Telegram watch |

## 5. State machine (per run; persists across runs via state files)

```
IDLE ──run──► GATE ──pass──► SIGNALS ──► ORDERS ──► FILLS ──► POSITIONS ──► P&L ──► AUDIT ──► FLAT-IDLE
              │ fail                                                            (halted)    │
              ▼ fail-closed (no orders)                                                       ▼
            ALERT ──► FLAT-IDLE(no orders)                              kill_switch=flat ──► FLATTEN
                                                                                              (manual only)
```

Per-run states:

| State | Entry check | Exit / behavior |
|---|---|---|
| `GATE` | resume gate: kill_switch off; data fresh (≤3 d); API reachable; DD breaker open | fail → ALERT, **zero orders** (fail-closed), heartbeat written |
| `SIGNALS` | per-strategy signal from day-T close (v8 bars) | no signal / stale data → strategy skipped, logged |
| `ORDERS` | reconcile: current Alpaca positions vs targets; merged-position guard; combined-weight cap; no-short <$2k rule; per-sleeve caps | plan.json written **before** any order |
| `FILLS` | poll each order ≤30 s; record fills with venue order id + correlation id | unfilled/timeout → marked, alert, next-run retry via client_order_id dedupe |
| `POSITIONS` | post-trade position sync vs Alpaca; recon report (orders/fills/positions/P&L deltas) | mismatch → WARN alert, never blind-repair |
| `P&L` | mark sleeves to model (fills + fees/slippage model), daily delta, HWM update | DD breach → breaker trips `halt_new_orders` (auto; never flat) |
| `AUDIT` | commit artifacts + heartbeat; digest to Telegram | always last, atomic-ish (write-then-commit) |

**Idempotency:** every order carries `client_order_id = <run_id>-<strategy>-<ticker>-<seq>`.
Startup reconciliation (Nautilus pattern, LIVE_DESIGN §4) dedupes
SUBMITTED/PARTIAL state from prior crashed runs before placing anything new.
`plan.json` is the single source for "what this run intended"; `fills.json`
is the source for "what happened"; `recon.json` reconciles them.

## 6. Failure modes + fail-closed paths

| # | Failure | Detection | Behavior (fail-closed) | Recovery |
|---|---|---|---|---|
| F1 | Data fetch error / 429 exhaustion | fetch layer raises, freshness check | **no orders that day** + WARN alert; heartbeat marked failed | next run retries; 3 consecutive → halt_new_orders auto |
| F2 | Alpaca API outage/timeout | request error taxonomy | run aborts at ORDERS; no orders; heartbeat failed + WARN | retry next run; 3 consecutive → halt_new_orders auto |
| F3 | Fill timeout / order stuck | poll budget exhausted | order marked UNFILLED-TIMEOUT; alert; no blind cancel | next-run reconciliation dedupes via client_order_id |
| F4 | Position mismatch (recon) | post-trade sync delta | WARN alert; no auto-repair; report in recon.json | human review via /status; next-run targets handle drift |
| F5 | Signal missing/stale for a strategy | freshness + NaN guard | that strategy skipped (logged), others trade | next run |
| F6 | Correlation-guard breach | combined-weight cap | lower-ranked strategy's order skipped; higher-ranked trades | logged; guard matrix reviewed monthly |
| F7 | DD breaker trip (1.5×MODEL_DD sleeve) | HWM tracker | `halt_new_orders` for that sleeve (auto); never auto-flat | release when HWM recovers or human override via ops_state.yaml |
| F8 | GH cron missed/delayed | heartbeat staleness | WARN + dispatch nudge (Ops-Design I1) | manual `workflow_dispatch` |
| F9 | Telegram unreachable | send raises | alerts degrade to file (`docs/data/ops/alerts.json`); trading unaffected | next run re-sends digest |
| F10 | Kill-switch engaged | ops_state.yaml read | `halt_new_orders` → no new orders; `flat` → flatten all (human-initiated only) | human disengages via Telegram or repo edit |
| F11 | Duplicate run (concurrency) | `docs-data-writers` concurrency group + run_id dedupe | second run exits GATE with WARN | n/a |

## 7. Env config spec (no secrets in repo, ever)

| Variable | Local `.env` | GH secret | Purpose |
|---|---|---|---|
| `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` | ✓ (exists) | ✓ | Alpaca **paper** auth (REST base forced to `https://paper-api.alpaca.markets` whenever `LIVE_TRADING_ENABLED=False` — existing behavior, keep) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | optional (alert drills) | ✓ (exist) | Telegram alerts + watch-poll |
| `OPS_V8_SPACING` | default ≈0.75 | — | yfinance v8 pacing (429-safety) |
| `LIVE_TRADING_ENABLED` | `False` (default) | `False` | **The only switch for real money**; go-live gate = flip to `True` + real endpoint + re-verify |
| `PAPER_TRADING_ENABLED` | `True` | `True` | paper mode marker |
| Binance vars | absent | absent | dormant (ccxt adapter present, no keys anywhere) |

Endpoint enforcement: broker base URL derived from `LIVE_TRADING_ENABLED` only;
a **go-live guard** asserts `LIVE_TRADING_ENABLED=False` before any paper run
places orders (defense in depth; same assertion in the workflow).

## 8. Strategy roster + sleeves (settled)

| Strategy | YAML | Sleeve | Notes |
|---|---|---|---|
| us_momentum_top5 | `strategies/us_momentum_top5.yaml` | equal-risk 10 % | rank 1 manager on merged tickers |
| spy_sma200 | `spy_sma200.yaml` | same | exempt from ≥10-trade floor (structural, ~2–4 trades/yr) |
| spy_rsi2 | `spy_rsi2.yaml` | same | ~2 trades/wk; carries trade count |
| btc_vol_target_sma100 | `btc_vol_target_sma100.yaml` | same | BTC/USD on Alpaca; immediate fills; weekends |
| us_lowvol_top30 | **port P4** | same | vault YAML exists (`us_lowvol_top30.yaml`) |
| us_pead_top5 | **port P4** | same | vault YAML exists (`us_pead_top5.yaml`); earnings dates via yfinance calendar (free) |
| breakout_burst h20_k10 | **port P4** | same | spec authored from Alpha-Diversity-2026-08-17 params |
| dual_momentum | exists | **inactive** | registry `status: inactive` (3/5 gates) |

- Sleeves: nominal equal-risk (60 %/7), vol-targeted to 10 % annualized
  (realized vol window per strategy spec); total ≤60 % of account; 40 %
  cash buffer.
- $100-feasible: sizing engine must hold at a $100 sleeve equivalent
  (fractional shares on, min-notional checks) — proven by a **$100
  simulation test in CI** (new test, P4).
- Merged positions: same-ticker targets merge, managed by the
  higher-ranked strategy; fills attributed **pro-rata** by each strategy's
  target weight into per-sleeve P&L.
- No shorting below $2k equity (hard rule, long-only build).

## 9. Paper validation + go-live (P6/P7)

- First evaluation at **≥50 aggregate paper trades**, floor **≥10 per
  strategy** (sma200 exempt), Sharpe reported **with CI** (SE ≈ 0.17 at
  n = 50); gates: maxDD ≤40 %, OOS Sharpe ≥1.0 on paper P&L, beats
  SPY/BTC risk-adjusted, fees netted (Alpaca $0, 5 bps slippage model,
  T+1), $100-feasible.
- **Do NOT tune to pass — report.** Honest numbers in
  `docs/build/PAPER-GATE.md`.
- One-time permutation confirmation study (P0, session-owned): runs on the
  T+1-fixed engines, White's RC + properly labeled SPA; **failure policy
  pre-registered: trade + report** (study is evidence, never a filter).
  Weekly permutation path continues in CI (E-1 rebind keeps it honest).
- Go-live gate: N-day heartbeat (2 green weeks, B1 gate, running from
  2026-08-17), all 5 gates, kill-switch tested (K1–K6), balances verified,
  env locked — real money = `LIVE_TRADING_ENABLED=True` only.

## 10. Phase plan (owners)

| Phase | Content | Owner | PR |
|---|---|---|---|
| P0 | E-1/E-2/E-6 fixes + regression tests + permutation study | **session** | P0-PR |
| P1 | PLAN/ARCHITECTURE docs; supersede LIVE_DESIGN.md | **session** | P1-PR |
| P2 | Broker layer harden (idempotency, polling, taxonomy) | Jules | per-phase |
| P3 | Execution engine (portfolio/risk/audit, daily loop, workflow) | Jules | per-phase |
| P4 | Strategy wiring (+3 YAML ports, registry, $100-sim test) | Jules | per-phase |
| P5 | Ops (heartbeat, alerts, kill-switch, watch workflow) | Jules | per-phase |
| P6 | Paper validation (after ≥50 trades; honest evaluation) | session | PAPER-GATE.md |
| P7 | Go-live gate + JULES-TASKS.md + final PR | session | — |

Deliverables: `docs/build/{PLAN,ARCHITECTURE,PAPER-GATE,JULES-TASKS}.md`
+ working code + tests + per-phase PRs.

## 11. Open cross-references

- `docs/LIVE_DESIGN.md` — reconciled: §1 (capability flags) adopted; §2
  (gate in broker) adopted as P2 requirement; §3 (circuit breaker wiring)
  adopted as P3; §4 (startup reconciliation) adopted as P3; §5 (approval
  gate) implemented by PAPER-GATE; §6 (hedges) and §7 deferred to ≥$2k.
- `AUDIT_REPORT.md` — E-1/E-2/E-6 fixes tracked in P0; E-3/E-4/E-5/E-7/E-9..11
  cosmetic/prompt-only, noted but out of paper-build scope.
- `Ops-Design-2026-08-16/report.md` — heartbeat, alerts ladder, kill-switch
  matrix, cron table, resume gate adopted verbatim where not amended here.
- `Flagship-Research-Roadmap.md` — B1 row updated at close of this prompt.

*Recorded 2026-08-17. Design frozen by /grilling — any change requires a
new grilling decision.*