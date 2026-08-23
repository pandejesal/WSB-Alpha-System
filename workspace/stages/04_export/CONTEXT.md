# Stage 04 — Export (Layer 2)

## Inputs
- Layer 4 (working): `../03_review/output/review_verdict.md` (must contain an
  operator-approved PASS — verify before anything else; abort if absent)
- Layer 4 (working): `../01_hypothesis/output/hypothesis_brief.yaml`
- Layer 3 (reference): `references/registry-schema.md`
- Layer 3 (reference): `_config/risk-policy.md` (root `_config/`)

## Process
1. Confirm verdict contains "Operator decision: APPROVED" (or equivalent explicit
   approval). If not: abort, report.
2. Produce registry-ready artifacts per `references/registry-schema.md`:
   - `strategy.yaml` — spec in repo format (compatible with src/ops/strategy_registry.py)
   - `metadata.json` — id, name, family, venue=alpaca, spec_file, gates_passed,
     rank (assign next), status="evaluated", evaluated_at
3. State paper-only constraint in both files' header comments. Live trading is
   DISABLED by operator policy.

## Outputs
- `strategy.yaml` -> `output/`
- `metadata.json` -> `output/`

Integration into the live registry (`strategies/registry.json`) is a separate,
user-initiated step OUTSIDE this workspace.

## Write-back (run complete)
- Vault: full run narrative -> `02-Research/wsb-icm/<date>-<slug>.md`; session-log line.
- Mnemosyne: durable outcome fact(s), max 3.
- Git commit (repo root): `icm: run <date-slug>` including all four stage outputs.
