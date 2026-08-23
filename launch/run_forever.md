# OVERNIGHT MARKET-DATA HARVEST — CONTROLLER PROMPT (2019–2026)

Paste this entire file as your prompt in a NEW opencode session (run from
`C:\Users\DELL\Documents\Default Project`). Do NOT run it in the session that
wrote these files.

You are the autonomous controller for an unattended financial-data harvest.
You drive OpenClaw; OpenClaw drives parallel OpenCode worker sessions; every
worker writes evidence to disk; you verify gates, retry on errors, aggregate,
and publish. READ THIS ENTIRE FILE, then follow the Sequence below exactly.

---

## 1. ROLE AND BOUNDARIES

You coordinate, you do NOT redo the workers' work. No wall-clock timeouts on
sessions — instead: RETRY + CONTINUE on every error. Never stop silently.

- Inputs: task specs in `launch\tasks\*.md` (A = OHLCV+news, B = 13F+VC,
  C = events+causation, D = wrap-up+publish). Controller logic is IN THIS FILE.
- Outputs (ALL files land here): `C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest\market_data_2019_2026\`
- Workspace repo (git): `C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest` (origin = github.com/pandejesal/WSB-Alpha-System, main)
- Runtime Python venv (verified): `C:\Users\DELL\AppData\Local\Temp\opencode\wsb-verify-venv\Scripts\python.exe`
- OpenClaw gateway (verified running): `ws://127.0.0.1:18789`, agent id `main`, model google/gemini-3.5-flash-lite (RPM 15, TPM 250k, RPD 500) — keep OpenClaw `main` turns SHORT and few; heavy work goes to opencode worker sessions, not OpenClaw inference.
- Today (end of range): 2026-08-09. Range: 2019-01-01 → 2026-08-09.

RED LINES (non-negotiable):
1. Never read/print `.env`, `.coverage`, keys, or secrets. Never send keys in prompts.
2. Never `git push --force`; never commit outside `market_data_2019_2026/`.
3. No destructive shell commands; no `rm -rf`; no trading/bridge/wallet actions.
4. Everything write lands under `market_data_2019_2026/` inside the repo, and under `launch\runlog\` (local, not committed).
5. Ambiguity → write WARN to `launch\runlog\warnings.md`, pick the non-destructive branch, continue.

---

## 2. SEQUENCE (single file order; A and B run in PARALLEL)

| Step | Action | Gate to pass |
|---|---|---|
| S0 | Preflight | openclaw health OK, repo exists, venv exists |
| S1 | Spawn WORKER A (OHLCV + GDELT news) — opencode session `research:A` | `runlog\A.done` |
| S1 | Spawn WORKER B (13F universe + flagship funds + VC notes) — opencode session `research:B` | `runlog\B.done` |
| S2 | Wait; poll BOTH; retry any failure; only after BOTH done → S3 | both done |
| S3 | Spawn WORKER C (events + causation join over A outputs) | `runlog\C.done` |
| S4 | Wait C with retries | C done |
| S5 | Spawn WORKER D (aggregate REPORT.md + git commit + push) | `runlog\D.done`, push verified |
| S6 | Final summary | reply to user with REPORT path + push sha |

A and B start concurrently (two separate sessions). C depends on A only; D depends on everything.

---

## 3. S0 — PREFLIGHT (10 checks, all must pass)

1. `openclaw health` → contains "Gateway event loop: ok". If not, start gateway: `openclaw gateway run --force` in background, wait for health, retry health up to 3 times.
2. `Test-Path "C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest\.git"` must be True.
3. `Test-Path "C:\Users\DELL\AppData\Local\Temp\opencode\wsb-verify-venv\Scripts\python.exe"` must be True.
4. `Test-Path "C:\Users\DELL\Documents\Default Project\launch\tasks\A_ohlcv_news.md"` (+ B, C, D) all True.
5. `git -C ...WSB-Alpha-System-latest status --short` must NOT contain `.env`; working tree dirty STATE is OK (do not touch pre-existing changes except: do nothing).
6. `git -C ... remote -v` shows origin.
7. Create structure: repo\market_data_2019_2026\{ohlcv, news, institutions, events, causation, runlog, tools} and local `launch\runlog\`.
8. Write `launch\runlog\status.json` = {"stage":"S0","workers":{},"ok":true,"startedUtc": "<now>"}.
9. Verify rate-limit budget for OpenClaw main turns today < 400 (keep turns under ~25/day total used by your orchestration; workers do not count).
10. Record `S0 PASS` in `launch\runlog\progress.md`.

## 3. RETRY — CONTINUE LOGIC (APPLIES TO EVERY SPAWN)

- Every worker writes its own state file: `runlog\<A|B|C|D>.state.json` `{status: running|failed|done, attempts: n, lastError, artifacts: [...]}`; on done ALSO writes `<A|B|C|D>.done` empty marker.
- Polling loop: every 120 seconds, read the state files. Do not spin faster.
- On `failed` (or on missing files after a generous runtime), do NOT reimplement the work. Build a "CONTINUE" message: `launch\continue-N.md` containing:
  - stage id, raw `lastError`,
  - instruction: "RE-RUN your task. Continue from your existing partial files in runlog/artifacts/. Fix the error above. Write runlog\<stage>.state.json again."
  - Send it as a fresh spawn (same session id if the session still replays, else new session id) with the SAME task file attached.
- MAX attempts per stage: 4. After that: mark stage FAILED in `launch\runlog\status.json`, append to `launch\runlog\failures.md`, and CONTINUE TO THE NEXT STAGE that does not depend on it (B can finish even if A fell 4 tries; C is skipped only if A is truly failed AND retried — then C runs in "unknown-only" mode per its spec).
- NEVER silently drop a failure: D's REPORT.md must list it.

## 3.2 SPAWN MECHANICS (verified on this machine)

OpenCode session CLI (verified `opencode run --help`): supports
`--session <id>` / `-c/--continue`, `-f/--file <path>` (attach),
`--dir <dir>`, `--title <title>`, `--format json`.

Worker spawn (parallel A and B from this controller) — TWO separate shell calls
in one message (two distinct opencode processes = two sessions):

- A: `opencode run --dir "C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest" --title "research:A" -f "C:\Users\DELL\Documents\Default Project\launch\tasks\A_ohlcv_news.md" -- "You are WORKER A. Read the attached task spec and follow it end-to-end. Write your state to launch\runlog\A.state.json and the A.done marker when complete."`
- B: same with `--title "research:B"` and `tasks\B_13f_vc.md`, message "You are WORKER B ...".

OpenClaw-driven alternative (owner requirement: "opencode → openclaw → more
opencode"): route the spawn through the gateway —
`openclaw agent --agent main --session-key research:workerA --message-file "C:\Users\DELL\Documents\Default Project\launch\tasks\A_ohlcv_news.md" --json --timeout 600`
(verified flags: `--agent`, `--message-file`, `--session-key`, `--json`, `--timeout`).
OpenClaw `main` (default agent, verified up) then drives the OpenCode session via
its ACP default agent. USE THIS FIRST; if it errors or returns no evidence of
work starting, FALL BACK to direct `opencode run` (documented, verifiable).
Retries: fresh spawn with the SAME task file (workers resume from their own
partial artifacts on disk — idempotent by design).

## 3.3 FEEDBACK TO THIS SESSION

Every worker, when done, also writes `launch_abs\runlog\status.json` merge:
`{"workers":{"A":{"status":"done","artifacts":[...],"rows":N}, "B":{...}, "C":{...}, "D":{...}}}`.
At S6 you MUST embed the full REPORT.md content + git push sha in YOUR final reply, so the owner sees results in this session's transcript.

---

## 4. STAGE DETAILS (read the task files at spawn-time; do not inline them here)

- A_ohlcv_news.md → OHLCV daily bar history 2019-2026 for 34 instruments (12 INDEX/ETF incl. ^VIX, 20 EQUITY, 2 CRYPTO with keyless Binance; equity via yfinance → STOOQ fallback) + GDELT news index per symbol per quarter (keyless, TimelineVol + artlist top-10, 2.5s pacing, resume checkpoint).
- B_13f_vc.md — SEC EDGAR full-text index (keyless) for 13F-HR 2019-2026: full-universe LEAN (all filers counts per quarter) + DEEP quarterly holdings for ~40 flagship hedge funds (Renaissance, Bridgewater, Point72, Citadel, Millennium, Tiger, Soros, AQR, DE Shaw, Two Sigma ... ) + VC public-notes (public corpus; no private DBs; e.g., a16z/Sequoia/YC public portfolio pages — bounded: max 3 pages fetched per VC, keyword-notes).
- C_events_causation.md — anomaly scan over A CSVs (daily returns, 20d rolling sigma, z>3 or |r| threshold: 2% indices/ETF, 3% equity, 5% crypto), events_all.json capped at 120 worst, causation join to GDELT ±3 days → per-event md reports + causation_index.json; "unknown" allowed when no source found; degraded mode if A failed.
- D_wrapup_publish.md — REPORT.md (structure per spec; counts must match real disk), `git add` ONLY `market_data_2019_2026/`, commit `feat(data): 2019-2026 market harvest — OHLCV 34 syms, GDELT news index, 13F universe+flagships, event causation` and `git push origin main` (no force; rebase on non-FF). Verify push: `git log origin/main -1`.

## 5. PUBLISH AND WRAP (S5-S6)

- After D passes (push sha captured), merge results: write `market_data_2019_2026\REPORT.md` by D (per spec).
- Update `launch\runlog\status.json` stage `S6 done`.
- Final reply structure (IMPORTANT — owner sees this):
  ```
  == OVERNIGHT HARVEST COMPLETE ==
  - REPORT.md: <full path>
  - Push: <sha> on main (origin pandejesal/WSB-Alpha-System)
  - Worker statuses: A=done|failed, B=..., C=..., D=...
  - Artifacts: counts from REPORT
  - Failures/warnings: list or "none"
  - Next steps suggestion (1 line)
  ```

## 6. WHAT NEVER HAPPENS

- No trading/swap/bridge/wallet operations.
- No .env reads: no secret material anywhere.
- No commits outside market_data_2019_2026.
- No blind infinite loops — retries capped per stage (4), FAILED then continue; a stage that depends on failed input gets its spec-defined degraded mode, not doom.

Begin with S0 now. Report progress in-session (brief line per stage pass/fail).