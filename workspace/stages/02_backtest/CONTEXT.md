# Stage 02 — Backtest (Layer 2)

## Inputs
- Layer 4 (working): `../01_hypothesis/output/hypothesis_brief.yaml` (user-edited version wins)
- Layer 3 (reference): `references/harness-notes.md` — how the wrapper and gates work

## Process
1. Run: `python workspace/scripts/run_backtest.py <path-to-brief-spec> --out <this stage's output dir>`
   from repo root (`WSB-Alpha-System-build`). The wrapper delegates to
   `scripts/evaluate_candidate.py` — do NOT reimplement evaluation logic.
2. If the run fails on data or spec errors, report the exact error. Do not patch
   the harness; propose a brief fix to the user instead.
3. Summarize results into `results_summary.md`: IS p-value, walk-forward outcome,
   permutation survival, DSR entry, equity curve path, and PASS/FAIL per gate in
   `_config/edge-gates.md`.

## Outputs
- `results.json` -> `output/` (raw evaluator output)
- `results_summary.md` -> `output/`

## Write-back (on stage completion)
- Append session-log line (commands run, headline numbers) to vault session log.
- No memory_store unless an infra lesson emerged (e.g. harness quirk).

STOP. Report PASS/FAIL table. Never proceed to review yourself.
