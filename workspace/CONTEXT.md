# CONTEXT.md — Task Routing (Layer 1)

Workspace purpose: take one falsifiable trading-edge hypothesis from idea to a
registry-ready strategy export, with human review at every boundary.

## Routing

| User wants to... | Run | Notes |
|---|---|---|
| Research a new edge / hypothesis | `stages/01_hypothesis` | includes mandatory prior-art check |
| Execute backtest on an approved hypothesis | `stages/02_backtest` | mechanical: uses scripts/run_backtest.py |
| Judge results against the edge gate | `stages/03_review` | human edit surface before export |
| Produce registry artifacts | `stages/04_export` | strategy.yaml + metadata.json |
| Set up / reconfigure the factory | `_config/shared/setup/questionnaire.md` | once, or when policy changes |

## Shared resources

- Risk constraints: `_config/risk-policy.md`
- Edge-gate thresholds: `_config/edge-gates.md`
- Backtest wrapper: `scripts/run_backtest.py` (delegates to repo's evaluate_candidate.py)

Stages run strictly in order 01→02→03→04 for a given run. Never skip 03.
