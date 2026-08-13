# Handoff — OpenCode Parallel Audit (WSB-Alpha-System)

**For:** any future session picking up WSB-Alpha-System work.
**Read first:** `docs/OPENCODE_PARALLEL_AUDIT.md` (full report, dated 2026-08-09) — this file is only the summary + entry points.

## Context

A 6-lane read-only parallel audit (CI/CD, risk/execution, validation stack, research/data, docs/numbers, tests/secrets) was run against `WSB-Alpha-System` on branch `fix/self-improvement-fallback-paths` @ `8424589`. Every finding cited with `file:line`; all verified against committed main (working-tree edits are cosmetic only).

## Top findings (full tables in the report)

1. **CRITICAL** Real-money risk gaps today: `live_crypto_executor.py:292-293` position cap prints but proceeds to open new orders; `position_sizer.py:26,55` 2% default, no clamp (up to ~6% risk/trade vs declared 1% at `position_sizing.py:13`).
2. **Metrics are fabricated/degenerate:** `oos_sharpe` == `train_sharpe` (`generate_strategy_data.py:357-358`, `run_full_backtest.py:73-74`); Sharpe `-9.6e16` committed in `docs/data/backtest_report.json` / `strategy_rankings.json`; Monte Carlo does not exist in code though README claims it.
3. **CI burn:** `api_health_check.yml` cron `*/5 * * * *` ~8,755 runs/mo ≈ 13-26× the GitHub free tier; all 6 auto-commit steps use `git commit -am`.
4. **Docs contradict data:** README claims 108.16%/484 trades/+1,479.92% vs JSON −0.30%/1 trade; `update_readme.py:124` not idempotent; dashboard reads `data.population` while producers write `data.strategies` / `ticker`.
5. **Security:** plaintext dashboard password `WSB-Alpha-2026` in `update_auth.py:11` (committed) — scrub + rotate.

## Fixed constraints for this project

- `docs/` is where audit/research notes live (`docs/AUDIT_FINDINGS.md`, `docs/OPENCODE_PARALLEL_AUDIT.md`).
- Risk constants have **5 copies**; `config/risk_config.py` is dead duplicate (delete + consolidate, fix mis-import `src/research/agent_skills_registry.py:139`).
- Requirements.txt: `ccxt/aiohttp/feedparser/openbb/streamlit` imported but missing; `nautilus_trader` duplicated; `defusedxml` unpinned.
- Tests: 6/15 fail collection locally (missing heavyweight deps); CI installs all pinned.
- Permutation/Whites/walk-forward validators exist but are standalone — never run by `generate_strategies.yml`.

## Next session recommendations (mapped in report §4)

| Priority | Work to pick up |
|---|---|
| P0 risk gates | Fix `live_crypto_executor.py` cap → `return`; clamp `position_sizer`; wire `MAX_DRAWDOWN`; add `check_order_allowed()` at broker sinks (`alpaca_broker.py:82`, `ccxt_broker.py:88`) |
| P0 validation | Fix `oos_sharpe` aliasing; near-zero-std guard in `get_sharpe` (`comprehensive_backtest_report.py:~597`); wire permutation/Whites/WF into generators |
| P1 results integrity | Reconcile README/RLV numbers to JSON (reconciled values in report §3); make `update_readme.py` idempotent; fix dashboard schema mismatches |
| P1 hygiene | Delete patch_*/fix_indent*/root test_*/`update_auth.py`, gitignore `.acp-ping.txt` + `rejected_strategies.log`; scrub `WSB-Alpha-2026` |
| P2 CI | Drop `-am`, SHA-pin actions, slow `api_health` cron, stagger paper/sandbox crons |

## Quick verify commands

```bash
git -C "WSB-Alpha-System" diff --stat          # cosmetic local edits only
grep -n "cron" WSB-Alpha-System/.github/workflows/*.yml
grep -n "oos_sharpe" WSB-Alpha-System/scripts/generate_strategy_data.py
```