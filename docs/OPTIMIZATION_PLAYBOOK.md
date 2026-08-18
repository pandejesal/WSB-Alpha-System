# WSB-Alpha-System Optimization Playbook

## 1. OpenCode Session Optimization
* **Model Routing & Context Discipline:** Route specific tasks to specialized agents to keep context windows focused. Do not overload a single session with unrelated context.
* **Delegation Rule:** Standard coding routes through Jules. Discovery of new strategy families should be launched as parallel OpenCode sessions.
* **TODO:** Define precise context-loading scripts for different task types.

## 2. Testing Optimization
* **Targeted Runs:** Use targeted `pytest` commands to test specific modules during active development to avoid brittle dependency issues.
* **Hermetic Tests & CI Gate:** Run the full suite (`pytest tests/ -q --continue-on-collection-errors`) before major merges. Maintain known baseline failures if necessary, but never merge with new regressions.
* **TODO:** Implement caching for heavy test fixtures.

## 3. Backtesting Optimization
* **Data Caching:** Utilize the embedded DuckDB cache (`src/data/cache_engine.py`) to speed up historical OHLCV and sentiment data retrieval.
* **Anti-Overfit Gates:** All strategies must survive Monte Carlo permutation tests, Combinatorial Purged Cross-Validation (CPCV), and Walk-Forward Optimization (WFO).
* **Param-Sweep Discipline:** Avoid naive grid searches over excessive parameter spaces. Pre-register hypotheses and use Bayesian Optimization to constrain sweeps.
* **TODO:** Standardize parameter bound constraints for all core indicators.

## 4. Hunt Protocol Pointer
* **Hunt Protocol:** For instructions on discovering new alpha and proposing entirely new strategy families, refer to the Hunt Protocol.
* See [HUNT_PROTOCOL.md](HUNT_PROTOCOL.md) (Placeholder)
* **TODO:** Formalize the end-to-end pipeline from Reddit idea extraction to backtest candidate generation.