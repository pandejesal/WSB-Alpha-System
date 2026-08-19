# WSB-Alpha-System: Hunt Protocol

This document defines the operating protocol for parallel OpenCode/Jules hunt sessions. These autonomous sessions are strictly designed to discover and evaluate **NEW** strategy families.

Any agent executing a hunt session MUST adhere to the discipline and contracts defined below.

## 1. SESSION BRIEF TEMPLATE

Every hunt session must be initialized with a self-contained brief. This brief serves as the charter for the discovery process.

```markdown
### Hunt Session Brief: <Strategy Family Name>

**Family Hypothesis (Falsifiable):**
[State the core market inefficiency or edge being targeted. Must be testable. e.g., "Assets exhibiting a daily close > 20-day high with 1.5x average volume will outperform the baseline over a 20-day holding period."]

**Target Universe & Timeframe:**
[e.g., 100-stock liquid large-cap panel (excluding SPY/QQQ/AGG/BND), 2019-2026 Daily OHLCV]

**Data Sources:**
[e.g., YFinance daily OHLCV, FRED Macro endpoints, Reddit sentiment data]

**Expected Deliverable:**
1. `strategies/<family_name>.yaml` (Specifying entry, exit, sizing, max_k, and params).
2. A new entry in `strategies/registry.json` configured for autonomous consumption.

**Acceptance Criteria (DONE):**
- Edge claim is pre-registered in `docs/data/`.
- YAML spec is fully complete and parses without errors.
- `registry.json` is updated and wired correctly.
- Strategy passes Walk-Forward validation, Permutation tests, and achieves a positive Deflated Sharpe Ratio (DSR) ledger entry.

**Kill Criteria (Honest Abandonment):**
- Hypothesis is falsified during in-sample validation (p-value > 0.05).
- Strategy fails walk-forward out-of-sample testing.
- Over-parameterization is detected, or no parameter set survives the permutation gate.
```

## 2. TARGET FAMILIES

- **Selection and Scoping:** Target families are derived from macroeconomic shifts, market microstructure observations, or external research (e.g., WSB sentiment, fundamental anomalies). A family represents a distinct conceptual edge, not just a variation of moving average lengths.
- **Concurrency & Isolation:** Hunt sessions operate in parallel. However, **never** run two sessions concurrently on the exact same strategy family to prevent merge conflicts and duplicate parameter sweeping. One session owns one family end-to-end.

## 3. OUTPUT CONTRACT

Every successfully completed hunt session MUST produce exactly the following artifacts:

1. **Strategy Specification (`strategies/<family_name>.yaml`):** A strictly formatted YAML document outlining the universe, entry/exit logic, sizing rules, concurrency caps, and exact parameters. It must match the structure of existing strategies (e.g., `breakout_burst.yaml`).
2. **Registry Integration (`strategies/registry.json`):** A new dictionary entry appended to the `strategies` list. It must be wired so that `src/ops/signals.py` and the daily operational pipeline can consume the strategy **WITHOUT** any manual Python code changes.
3. **Evaluation Record (`docs/data/`):** A formalized record proving the strategy passed the Edge Gate (see Section 4). This includes a pre-registration markdown doc, an evaluation JSON output, and the final recorded verdict.

## 4. ACCEPTANCE PATH THROUGH THE EDGE GATE

We enforce an absolute "honest-claims discipline." No post-hoc cherry-picking is allowed.

1. **Pre-Registration:** Before running exhaustive historical backtests, the agent must generate a frozen specification document using `python scripts/preregister.py freeze` (`docs/data/cycle*_prereg_<family>.md`) declaring the hypothesis and parameter search space. The automated tool will prevent overwriting and handle formatting.
2. **Validation Pipeline:** The candidate must be evaluated using the canonical validation scripts:
   - `scripts/run_full_backtest.py`
   - `scripts/comprehensive_backtest_report.py`
   - `scripts/generate_strategy_data.py`
3. **The Gate:** The strategy must survive in-sample testing, combinatorial cross-validation, walk-forward out-of-sample validation, and parameter permutation checks.
4. **Ledger Entry:** The final result must be recorded as a Deflated Sharpe Ratio (DSR) entry in the evaluation JSON using `python scripts/preregister.py record`. No claim is recorded without prior pre-registration. The automated tooling strictly enforces this honest-claims gate.

## 5. CADENCE RULES

- **Concurrency:** A maximum of 3-5 parallel hunt sessions may run at any given time to manage compute resources and review bandwidth.
- **New Cycles:** A new hunt cycle begins when the active queue of target families drops below the concurrency limit, or a major regime shift invalidates existing active strategies.
- **Handling Failures:** If a candidate fails the Edge Gate (kill criteria met):
  - An honest failed verdict is recorded in the evaluation record.
  - The family is either permanently retired, OR it is heavily revised requiring a completely new, distinct pre-registration document before any further testing. Failed hypotheses are never silently overwritten.

## 6. RUNNING A HUNT SESSION

The `scripts/hunt_runner.py` tool orchestrates the lifecycle of a hunt session, enforcing pre-registration discipline and validating outputs before registry entry. It uses three subcommands:

- **`run`**: Initializes a new session workspace.
  ```bash
  python scripts/hunt_runner.py run --brief <brief.yaml> --out hunts/<family>/...
  ```
  This creates the session directory (`hunts/<family>/<run_id>`), copies the brief, freezes the claims ledger via `preregistration.freeze_preregistration`, and prints a compact markdown block ready for injection into a hunt session.

- **`collect`**: Validates the candidate artifacts produced by the session.
  ```bash
  python scripts/hunt_runner.py collect --dir hunts/<family>/<run_id> --registry strategies/registry.json
  ```
  Scans the `candidates/` folder for spec YAMLs, validates them strictly against `strategy_registry.validate_spec`, and prints a checklist of missing requirements (e.g., pre-registration record, gate artifacts in `results/`). Invalid specs are separated into a rejected list. It strictly refuses to write to the registry itself.

- **`status`**: Summarizes all hunt sessions.
  ```bash
  python scripts/hunt_runner.py status
  ```
  Prints a per-cycle summary of hunt runs, tracking frozen claims, candidate validation status, and edge-gate artifacts.

**Candidate Output Contract**: Every valid candidate placed in `candidates/` must be paired with its edge-gate artifacts (the evaluation JSON) generated by the canonical test scripts and placed in the `results/` folder, verifying the claim frozen during the `run` stage.

## 7. COEXISTENCE WITH THE WEEKLY SELF-IMPROVEMENT AGENT (FR-012)

Strict division of labor exists between parallel hunt sessions and the weekly self-improvement agent (`src/research/self_improvement_agent.py`):

- **Hunt Sessions OWN Discovery:** Hunt agents are exclusively responsible for hypothesizing, testing, and introducing entirely **NEW** strategy families. They create new YAML specs and add new entries to `registry.json`. Hunt sessions **never** tune the parameters of an already active strategy.
- **Self-Improvement Agent OWNS Tuning:** The self-improvement agent strictly optimizes and iterates on the parameters of **ACTIVE** strategies already present in the `registry.json`. It **never** introduces a new strategy family or creates new YAML specifications.

**Coordination Point:** Both systems observe `strategies/registry.json` and `docs/data/` records as the source of truth. The self-improvement agent queries the registry to find active strategies to tune, while hunt sessions append to the registry once a new family survives the Edge Gate. They operate orthogonally and do not step on each other's domain.