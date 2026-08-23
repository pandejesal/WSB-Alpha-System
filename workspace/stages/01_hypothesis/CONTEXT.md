# Stage 01 — Hypothesis (Layer 2)

## Inputs
- Layer 3 (reference): `references/hunt-lessons.md` — failed-candidate ledger, what NOT to retry
- Layer 3 (reference): `references/brief-template.yaml` — pre-registration format
- Layer 4 (working): user's raw idea / market observation (from the run prompt)
- Vault (reference): `C:\Users\DELL\Documents\Obsidian Vault\02-Research\` notes relevant to the idea
- Mnemosyne: `memory_recall` on the core edge concept (prior attempts, outcomes)

## Process
1. Prior-art check (MANDATORY, appears in output): recall Mnemosyne for past
   candidates targeting this edge; scan vault research notes; read hunt-lessons.md.
   List every prior attempt with its outcome and state why this hypothesis differs
   or is a deliberate retest with changed conditions.
2. Draft ONE falsifiable hypothesis following brief-template.yaml fields:
   family, universe, hypothesis, acceptance, lookback_constraints, edge_gate_params.
   Use thresholds from `_config/edge-gates.md` verbatim.
3. State the kill criteria explicitly.

## Outputs
- `hypothesis_brief.yaml` -> `output/` (complete, parseable YAML)
- `prior_art.md` -> `output/` (recalled attempts, outcomes, differentiation)

## Write-back (on stage completion)
- Append session-log line to vault `05-Session-Logs/<today>.md`
- `memory_store`: 1 atomic fact only if this is a NEW edge direction worth remembering

STOP. Report to user. Do not run stage 02 until they approve the brief.
