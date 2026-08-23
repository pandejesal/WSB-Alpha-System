# Risk Policy (Layer 3 — configure the factory, not the product)

Source of truth: `src/risk/position_sizing.py` + operator decisions 2026-08-21/23.

## Hard caps
- Max risk per trade: 1% of equity
- Max position size: 25% of equity
- Max concurrent positions: 4
- Daily loss circuit breaker: 5%
- Max drawdown circuit breaker: 15%

## Operator constraints (non-negotiable)
- LIVE TRADING IS DISABLED. Paper only. This is an explicit standing decision
  (2026-08-21, reaffirmed 2026-08-23). Every artifact must fail closed: absent,
  malformed, or ambiguous live-trade flags resolve to disabled.
- Live-flip requires BOTH: repo variable LIVE_TRADING_ENABLED=true AND the
  human-gated workflow (live_gate_flip.yml). Neither may be triggered by an agent.
- Go/no-go for any future transition comes ONLY from the paper dashboard verdict
  ladder (scripts/baseline_paper_track.py): >=2 green months, no drawdown breach,
  no execution faults. Current verdict: NEED_MORE_PAPER_TIME.

## Naming conventions
- Candidate ids: `<family>_<concept>_v<n>` lowercase snake_case.
- Run slug: `YYYYMMDD-<short-hypothesis-name>`.
