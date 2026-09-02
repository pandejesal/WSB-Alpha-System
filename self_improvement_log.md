## WSB-Alpha-System Self-Improvement Log

**Purpose:** Tracks weekly parameter optimization proposals from the self-improvement agent (`src/research/self_improvement_agent.py`)

**Format:** Each entry documents one parameter change proposal, its validation result, and the final outcome.

| Date | Hypothesis | Change (old_code -> new_code) | IS p-value | OOS p-value | DSR | Status |
|---|---|---|---|---|---|---|
| 2026-08-31 | Example: RSI threshold optimization | `df['RSI_14']` -> `df['RSI_14']` with new threshold | N/A | N/A | N/A | Pending |

**Weekly Workflow:**
1. **Agent runs** every Saturday at 12:00 UTC via `self_improvement.yml` GitHub Action
2. **Proposes** exactly ONE parameter change to `src/backtest/run_historic_backtest.py`
3. **Validates** using in-sample (p < 0.01) and walk-forward (p < 0.05) tests
4. **Logs** result in this file
5. **Reverts** if validation fails; **commits** if passed

**Active Parameters Tracked:**
- RSI thresholds (rsi_low, rsi_high in run_historic_backtest.py)
- Volatility limits (gk_vol_limit)
- Minimum confluence scores (min_confluence_score)
- Stop loss percentages (stop_loss_pct)

**Recent Activity:** (auto-updated by agent)