# WSB-Alpha-System AI Agent Guidelines

This repository is a sentiment-driven quantitative trading system that automates Alpaca paper trading entirely via zero-cost GitHub Actions. It is built on a strict "fail-closed" risk mandate and utilizes a rigorous anti-overfit edge gate (involving combinatorial cross-validation, permutation tests, and walk-forward optimization) to ensure that only statistically robust strategies are deployed.

## Verified Development Commands

Agents should use the following verified commands for development, testing, and validation:

* **Testing:** `PYTHONPATH=. pytest` (Run the test suite)
* **Linting:** `ruff check .` (Run linting using latest defaults; do not add ruff configuration files)
* **Security:** `bandit -r src/` (Scan source code for security vulnerabilities)

**Preflight (INF-08, before any hunt/evolve session):** `ruff check .` must pass (0 errors except intentional `noqa: E402` in `src/config/risk_config.py`). Pin: `ruff==0.16.1` in `requirements.txt` (reconciled per W14; runner `ruff --version` must match pin; line ~121 in original file, now 126 after deps). No `ruff.toml`/`pyproject.toml` per repo rule (never create). JS lint (`biome`/`eslint`) is N/A — pure Python repo, missing binaries are acceptable. CI emits `ruff_errors.json` artifact on failure. **W14 SCOPED per `_deliverables/impl_B4d_ruff.md`:** full `ruff check .` green is infeasible without a config change the repo rule forbids — baseline `~1000+ repo-wide` (E402 384, BLE001 171, F401 145, RUF100 106, etc., pre-existing style) is **referenced not enforced**; CI gates only scoped surface `ruff check . --statistics || true` + `ruff check evolve_real.py` + `bandit -r src/` + `PYTHONPATH=. pytest tests/test_gatespec38_tracks.py tests/test_gatespec_tracks.py`. Acceptance = CI yml contains ruff+bandit+pytest steps + pin matches + baseline referenced (NOT full-green).

### Key Scripts

* `python scripts/run_full_backtest.py` - Runs historical backtests.
* `python scripts/comprehensive_backtest_report.py` - Generates the backtest report.
* `python scripts/paper_trading_sandbox.py` - Simulates paper trading.
* `python scripts/run_research.py` - Orchestrates the research pipeline (scraper, debate engine, FRED macro).

## Session Discipline

1. **Prerequisites:** Before beginning any work or proposing strategy modifications, agents MUST read `docs/OPTIMIZATION_PLAYBOOK.md` and `docs/HUNT_PROTOCOL.md`.
2. **Edge Gates:** All strategy candidates must pass the strict edge gate (pre-registration, walk-forward optimization, permutation tests, and Deflated Sharpe Ratio) before they can be entered into `strategies/registry.json`.
3. **Delegation Rule:** All standard coding and repository maintenance tasks must route exclusively through Jules. Broad research or creative "hunts" for new alpha should be spun up as parallel OpenCode sessions.

*Note: The system runs a weekly self-improvement agent (`src/research/self_improvement_agent.py`) which tunes the parameters of ACTIVE strategies. This operates concurrently with the hunt factory, which is responsible for discovering entirely NEW strategy families. They coexist.*
