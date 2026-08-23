# Stage 03 — Review (Layer 2)

## Inputs
- Layer 4 (working): `../02_backtest/output/results_summary.md` and `results.json`
- Layer 3 (reference): `references/review-checklist.md`
- Layer 3 (reference): `_config/edge-gates.md` (root `_config/`)

## Process
1. Score the candidate against every checklist item. Cite exact numbers from
   results.json — never from memory of the summary.
2. Write an honest verdict: PASS / FAIL / REVISE with reasons. A FAIL is a
   successful run of this pipeline; do not soften it.
3. Flag any overfitting smell: parameter count vs sample size, cherry-picked
   windows, universe tweaks made after seeing results.

## Outputs
- `review_verdict.md` -> `output/`

## Human gate (this stage IS the gate)
The user edits or annotates `review_verdict.md`. Their annotation overrides.
Only a user-approved PASS unlocks stage 04. Record their decision verbatim
in the verdict file under "Operator decision".

## Write-back (on stage completion)
- Vault: verdict summary line in session log; if the decision sets precedent,
  add a note to vault `03-Decisions/`.
- Mnemosyne: outcome fact (`memory_store`): "<candidate-id>: <PASS/FAIL>, key numbers".

STOP after write-back.
