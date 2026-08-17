# Paper Gate — Autonomous Paper-Trading System

Status: **PRE-GATE** — gate criteria not yet met. No live paper trading until this doc flips to GATE-OPEN by an explicit decision (repo edit + Telegram alert).

Source of truth: `docs/build/PLAN.md` (mission, runtime model, state machine) and `docs/build/ARCHITECTURE.md` (audit trail, kill-switch, reconciliation). This file is the operational gate contract.

## Gate criteria (all must hold)

| # | Criterion | Evidence artifact |
|---|---|---|
| G1 | >= 50 paper trades executed by the live system (Alpaca paper) | `docs/data/ops/` fill ledger (reconciled), `docs/data/paper/` trade log |
| G2 | >= 10 trades per active sleeve (sma200 exempt — structural strategy) | per-sleeve trade counts in `docs/data/ops/plan.json` + fills |
| G3 | Sharpe ratio of the paper P&L series with confidence interval; lower bound of 90% CI must be > 0 | `docs/data/paper/sharpe.json` (point estimate + CI computed per ARCHITECTURE.md) |
| G4 | Full 200-permutation protocol run on the honest T+1 engine (`run_historic_backtest`): White's RC p-value and Hansen SPA recorded in `docs/data/permutation_study.json` (full run, not the bounded 40-perm confirmation below) | `docs/data/permutation_study.json` |
| G5 | Alerting verified: Telegram heartbeat seen for >= 7 consecutive trading days (`docs/data/ops/heartbeat.json` timestamps) | heartbeat log + ops watch log |
| G6 | Kill-switch rehearsal documented once (tier-2 repo edit + tier-3 manual dispatch both exercised, then restored) | `docs/data/ops/kill_switch_rehearsal.json` |
| G7 | Reconciliation check: zero unresolved fill/order mismatches over the last 10 trading days | `docs/data/ops/reconciliation.json` |

## Permutation study — bounded confirmation (P0, 2026-08-18)

Ran on the audit-fixed honest engine (fills at `Open[t+1]`, gates on bar `t`). Data mode: technical-only synthetic signals (the `wsb_factual_research_data.csv` sentiment file is not in the build worktree; the full protocol re-runs post-merge with whatever data the daily workflow has).

Results (`docs/data/permutation_study.json`, 40 permutations):

- In-sample permutation p-value: **0.525** (real return −9.5%, permuted mean +17.4%)
- Walk-forward pooled p-value: **0.725**, windows won 14/27 (51.9%)
- Hansen SPA p-value: **0.699**

Interpretation: on the synthetic technical-only universe the honest engine shows **no detectable edge** — the correct honest outcome. The run confirms the permutation/SPA machinery is functional and produces well-behaved (non-degenerate) p-values on the T+1 engine. This is expected pre-deployment: the live paper phase produces the real signal flow that the gate then tests (G1–G3). Do NOT read this as license to trade; the gate is not open.

## Failure policy (pre-registered)

- If G1/G2 fail after 120 calendar days of operation: stop the system, review sleeve roster in PLAN.md, record decision in `03-Decisions/` of the vault, and either revise the roster (new paper cycle) or demote the system to research-only.
- If G3 fails (Sharpe CI lower bound <= 0): stop the system. Options, in order: (1) parameter revision with full re-validation, (2) sleeve removal, (3) decommission to research-only. Never "disable the gate".
- If G4 fails (permutation p < 0.05 on the full run): the strategy as-built beats random shuffles — treat as strong evidence of data leakage or overfit. Re-run audit checks (docs/AUDIT_FINDINGS.md E-1/E-2/E-6 regression tests must stay green) before any interpretation.
- The gate flips to GATE-OPEN only via an explicit decision (repo edit of this file + Telegram alert). No automated self-gating.

## Pre-gate checklist (ops)

- [ ] E-1/E-2/E-6 regression tests green in CI (`tests/test_p0_fixes.py`)
- [ ] Full 200-permutation protocol recorded (G4)
- [ ] Heartbeat streak (G5)
- [ ] Kill-switch rehearsal (G6)
- [ ] Reconciliation clean (G7)
- [ ] This doc flipped to GATE-OPEN with date + decision reference