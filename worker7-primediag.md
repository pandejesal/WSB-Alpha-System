# Worker brief: diagnose prime-agent file-write failures in WSL (worker 7)

## Objective
prime-agent 0.9.1 runs in WSL Ubuntu (node 24, opencode provider, Zen key
forwarded via WSLENV=OPENCODE_API_KEY) and answers short prompts, but a
task like "append one line to /tmp/prime-write-test.txt then reply DONE"
exits 0 with reply DONE and NO file created. Find the true root cause and
produce a WORKING invocation. Do not guess — test each hypothesis.

## Workdir
C:/Users/DELL/Documents/Default Project/WSB-Alpha-System-build (read-only
for this task; write test files only to /tmp inside WSL or the brief dir
below). Shell is git-bash (POSIX syntax). Prefix `primediag_` for any file.

## Evidence so far (all verified)
- Daemon log (/root/.prime/agent/logs/): every worker gets "shutdown
  command received over socket" ~30s after listen (hardcoded create
  timeout). Short tasks (ECHO/PING) return; long ones die. One 8-min run
  returned DONE with no file written.
- Free-tier 429s observed on other models (mimo-v2.5-free) — quota/exhaustion
  is a live factor; avoid burning quota with retries (space attempts, small prompts).
- Key forwarding was broken, now fixed via WSLENV=OPENCODE_API_KEY.
- prime-agent runs as ROOT in WSL. Flags exist: `--cwd <dir>`,
  `-t, --tools <list>` (allowlist). Check --help for approval/permission flags.
- VPN rotator is broken (IP never changes) — do not rely on rotation.

## Test matrix (in order, stop at first full PASS: reply correct AND file exists)
1. Baseline: `--no-session "Append exactly one line PRIME_WRITE_OK to /tmp/pw1.txt then reply DONE"` with explicit `--cwd /tmp`. Verify file.
2. Tools: same with `-t` allowlisting file/write tools (see --help for names).
3. Approval: look for approval/permission flags (--approve, --yolo, --allow);
   test whether writes need an approval the print mode auto-denies.
4. User: test whether running as non-root changes anything (only if 1-3 fail).
5. Quota: if 429s appear, wait 15 min once and retry once (do not hammer).

## Deliverables
- docs/PRIMEDIAG_REPORT.md: per-hypothesis PASS/FAIL with verbatim outputs,
  root cause, and the exact WORKING invocation command.
- tests/test_primediag.py: ≥3 tests asserting the working invocation pattern
  (e.g. flag presence, command construction — no live Prime calls in tests).

## Acceptance criteria
- A repeatable invocation where Prime writes a file AND it exists on disk
  afterward (verified by your own shell, not Prime's word).
- ruff clean on your files. No registry writes, no live anything, paper context.
- Final message: root cause in one sentence + working command + test count.
