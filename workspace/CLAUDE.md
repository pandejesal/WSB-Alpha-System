# CLAUDE.md — WSB-Alpha Research Loop Workspace (Layer 0)

You are the single orchestrating agent for this ICM workspace. This folder IS the
pipeline. Read only the layers your current stage contract declares.

## Structure map

- `CONTEXT.md` — Layer 1: task routing. Which stage handles what.
- `stages/NN_name/CONTEXT.md` — Layer 2: stage contracts (Inputs / Process / Outputs).
- `stages/NN_name/references/` + `_config/` — Layer 3: reference material. Stable
  across runs. Internalize as constraints.
- `stages/NN_name/output/` — Layer 4: working artifacts. Change every run.
  Process as input. The previous stage's output/ is your input.
- `scripts/` — mechanical work that needs no AI. Run them; do not reimplement them.

## Rules

1. One stage per invocation. The user names the stage ("run stage 02").
2. Load ONLY the files in the stage's Inputs table. Nothing else.
3. Write outputs ONLY to that stage's `output/`.
4. HARD GATE between stages: after writing output/, stop and report. Never start
   the next stage without explicit user go-ahead. The user edits output/ files
   between stages; their edit wins over your draft.
5. Live trading is DISABLED by operator decision. Paper only. Any artifact that
   would enable live execution must state paper-only and fail closed.
6. After a completed run: write-back to both memory layers (see stage contracts'
   Write-back sections) and commit with message `icm: run <date-slug>`.
