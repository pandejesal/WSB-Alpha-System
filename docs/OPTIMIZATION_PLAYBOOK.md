# WSB-Alpha-System Optimization Playbook — Muse Spark 1.2 XHigh Pipeline

> Pipeline goal: code like Claude Fable 5 but better via `Muse Spark 1.2 XHigh` + effective memory + 3 bridges. This playbook is repo-truth. All agents MUST read it + `HUNT_PROTOCOL.md` before any edit (per `AGENTS.md:1`).

## 1. OpenCode Session Optimization (Muse Spark 1.2 XHigh · Obsidian+Mnemosyne)

### Model routing
| Agent | Model | Reasoning | Fallback |
|-------|-------|-----------|----------|
| `architect` | `opencode/muse-spark-1.2-contributor-free:xhigh` | plan, synthesis, 1M ctx | `nemotron-3-ultra-free`, `ox-alpha-free` |
| `coder` | `opencode/muse-spark-1.2-contributor-free:xhigh` | implementation | `ox-alpha-free`, `nemotron-3-ultra-free` |
| `reviewer` | `opencode/muse-spark-1.2-contributor-free:xhigh` | critique | `nemotron-3-ultra-free` |
| `critic` | `opencode/muse-spark-1.2-contributor-free:xhigh` | approval gate | `nemotron-3-ultra-free` |
| `explorer` | `opencode/muse-spark-1.2-contributor-free:low` | grep/read fanout, <30s p95 | `hy3-free`, `mimo-v2.5-free` |

Global `opencode.jsonc:4` = `muse-spark-1.2-contributor-free` (base), `small_model = :low`. Swarm override in `~/.config/opencode/opencode-swarm.json:1` is authoritative; project `.opencode/opencode-swarm.json` inherits.

### Context discipline
- **Heavy reads (>300 lines or 3+ files) → Antigravity Gemini 3.7 Flash `high` (1M)**. Hotspots `src/alpha/wsb_sentiment_alpha.py:864` + `src/ops/signals.py:662` + `src/backtest/defend/trial_ledger.py:545` must never be loaded in Muse Spark write session — delegate to Antigravity read lane, then inject summary.
- **Writes → Muse Spark XHigh only**. No dual-writer drift.
- **One session = one concern**. Do not mix hunt discovery + bug fix + doc write. Use `declare_scope` before coder dispatch.
- **Session start**: `read 99-Meta/Vault Guide.md + 01-Context/Workflow.md` + `memory_recall <task>` + `memory_recall_global <task>` (Obsidian vault `C:\Users\DELL\Documents\Obsidian Vault`). End: log `05-Session-Logs/YYYY-MM-DD.md` + `memory_store` one fact per non-obvious decision.

### Memory layer — actually help (Q4=C)
Vault = human-readable repo-truth, Mnemosyne = vector recall. Both required.

- **Mnemosyne health**: `34 working / 1 episodic` after `2026-08-21 sleep --force` (was 0). Crons scheduled: `Mnemosyne Sleep 02:00 DAILY`, `Mnemosyne Backup 03:00 SUN`. Fix applied `mnemosyne/cli.py:203` `→` charmap crash → `utf-8 errors=replace`. If recall crashes, set `PYTHONIOENCODING=utf-8`.
- **Swarm knowledge**: `.swarm/knowledge.jsonl:89` currently `shown 18-21 / applied 0` — dead. Policy: `curator_consolidation` → 5-10 hive, then archive `shown>10 && applied==0`. Track `applied/shown >0.3` weekly; goal `episodic >10` in 7 days.
- **Vault hygiene**: Inbox → processed weekly, decisions `03-Decisions/` ADR, prompt queues `04-Prompt-Queues/` self-contained (question + files to read + deliverable path + acceptance criteria).

## 2. Testing Optimization (deterministic-green CI)

### Commands (verified, per `AGENTS.md`)
- `PYTHONPATH=. pytest` (not `pytest tests/ -q --continue-on-collection-errors` blind)
- `ruff check .` (no `ruff` config file, latest defaults)
- `bandit -r src/`
- Targeted: `pytest tests/test_daily_check.py -k test_eval -q` during dev, full suite only before merge.

### Hermetic discipline
- Missing deps caused 6 COLLECT failures (`vectorbt`, `nautilus-trader`, `alpaca-py`, `pandera`, `duckdb`, `arch`, `riskfolio-lib`, `quantstats`, `langgraph`, `ccxt`, `cvxpy`). Fix: add to `requirements.txt` or mock — never `skip` collection.
- No API keys in tests. Tiingo 3 tests already mocked — keep. `test_providers.py` must run offline.
- Cache heavy fixtures (`duckdb` cache `src/data/cache_engine.py`) across pytest, not per-test download.

### CI budget
- Public repo `FR-009` — GH Actions free. Pip cache `actions/cache` on all workflows. Heavy backtests (`run_full_backtest.py`) on `schedule/dispatch` only, push `ci.yml` = fast pytest only.

## 3. Backtesting Optimization (speed + anti-overfit)

### Pipeline
`DataProviderChain: Alpaca → Tiingo → BinancePublic → yfinance` + `cache_engine.py` (duckdb, `OUTPUT_CSV` + `CO_MENTION_JSON`). Never hit network twice.

### Gates (must all pass before `strategies/registry.json`)
1. `preregister.py freeze` → `docs/data/cycle*_prereg_<family>.md` (frozen hypothesis, no cherry-pick)
2. `run_full_backtest.py` (T+1 ATR slippage 0.1-2.5%, GK_vol shield)
3. `comprehensive_backtest_report.py` + `generate_strategy_data.py`
4. `validation.py:286` permutation, CPCV, walk-forward OOS, `trial_ledger.py:545` DSR, min 50 trades, Sharpe/DD thresholds
5. `preregister.py record` — honest ABANDON if `p>0.05` or OOS fail.

### Param discipline
- Pre-register search space, Bayesian opt, not naive grid. Current 0/16 PASS + `fb3b07f` honest-signal fix shows need for indicator normalization — re-run `test_evaluate_candidate.py:369` after any signal change.
- One family per session, `hunt_runner.py run/collect/status` enforces isolation.

## 4. Hunt Protocol
See `HUNT_PROTOCOL.md:103` — canonical. Summary: brief template (falsifiable hypothesis, universe 2019-2026, deliverables), concurrency 3-5, output contract `strategies/<family>.yaml` + `registry.json` + `docs/data/` record, coexistence hunt=discovery / `self_improvement_agent.py`=tuning.

## 5. Bridge Optimization (Q6-8)

### Jules ↔ Opencode (Q6=D, Q12=C)
- **Create**: every `jules_create` must include boilerplate: `Repo source: sources/github/pandejesal/<repo>, base branch, acceptance criteria, pinned versions, verify: pytest + ruff, one task per session, no unrelated files` (`Workflow.md:75`). Cap 3 concurrent, queue `04-Prompt-Queues/Coding/`.
- **Gate**: CI blocks merge unless `ruff` + `bandit` + hermetic green.
- **Close-loop**: Jules PR → Muse Spark reviewer lane → `03-Decisions/` + `memory_store` + move queue → `05-Session-Logs/`.

### Antigravity ↔ Opencode (Q7=A, Q13=A 3.7 Flash)
- Heavy reads via `opencode-antigravity-auth@1.6.0` `antigravity-gemini-3.7-flash:high` (1M). Threshold 300+ lines or 3+ files. Writes never via Antigravity.
- Provider `google` entry: `antigravity-gemini-3.7-flash` limit 1048576, variants minimal/low/medium/high. Rate-limit check before bulk read.

### OpenClaw ↔ Opencode (Q8=C, Q14=A+C)
- Hybrid: `Research-Auto/` night auto-spawn + `Research-Awake/` day copy-paste, both self-contained briefs.
- Crons (re-created, were missing per `Workflow.md:50` audit): `Research Workers :30` + `Hourly Check-in :00`, Lite primary, Lite fallback, `quota.ps1 check/log/fail` before every Google call, `WARN@80% STOP@95%`, stagger ≥60s, ≤3 concurrent, backoff 1s/2s/4s/8s, fallback chain, ledger `00-System/quota-ledger.json` → `06-Mnemosyne/`.

## 6. Pipeline Victory Gate (Q15=A, Q17=C)
30-day window, rendered to `PIPELINE_GATE.md` + `docs/data/ops/` + GH Pages:

| Metric | Gate | Source |
|--------|------|--------|
| `knowledge applied/shown` | >0.3 | `.swarm/knowledge.jsonl` |
| `episodic` | >10 | `mnemosyne stats` |
| Jules PR first-time green | >90% | `ci.yml` |
| Hunt PASS | ≥1 /4 families (now 0/16) | `docs/data/eval_*.json` |
| Explorer p95 latency | <30s on `wsb_sentiment_alpha.py:864` | `ops/metrics.json` |

Order per Q16=A: (1) Mnemosyne fix+crons ✓ (2) this playbook (3) shard hotspots <400 lines (4) `trial_ledger.py:545` DSR gate. Do not act past frontier without gate evidence.

---
*Last updated: 2026-08-21 — grilling rounds Q1-Q17 CONFIRMED, frontier empty.*
