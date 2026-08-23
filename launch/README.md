# Overnight Market-Data Harvest — Launch Pack (2019–2026)

Unattended data-collection run driven by OpenClaw + parallel OpenCode workers.
All data lands in `WSB-Alpha-System-latest\market_data_2019_2026\` and is pushed
to github.com/pandejesal/WSB-Alpha-System (main). No API keys required.

## Files in this pack

| File | Role |
|---|---|
| `run_forever.md` | **THE controller prompt — paste into a NEW opencode session** |
| `tasks\A_ohlcv_news.md` | Worker A: OHLCV daily bars (34 syms) + GDELT news index |
| `tasks\B_13f_vc.md` | Worker B: 13F universe index + 40 flagship funds deep + VC notes |
| `tasks\C_events_causation.md` | Worker C: anomaly events + causation join (needs A) |
| `tasks\D_wrapup_publish.md` | Worker D: REPORT.md + git add/commit/push |
| `runlog\` | Local state/status files the controller reads (never committed) |

## How to use

1. Make sure the OpenClaw gateway is running (`openclaw health` → "ok").
2. Open a NEW opencode session in `C:\Users\DELL\Documents\Default Project`
   (not this one).
3. Paste the FULL content of `run_forever.md` as the session's first prompt.
   The controller then: preflight → spawns A and B in parallel (openclaw route,
   fallback direct `opencode run`) → waits with 120s polls → spawns C after A →
   spawns D → pushes to GitHub → prints the report in-session.
4. Keep the machine awake; check `launch\runlog\status.json` + `*.done`
   markers whenever curious.

## Resume / re-run

Everything is idempotent: workers resume from partial artifacts on disk
(A: `news\run\progress.json`; B: per-fund CSVs; C: per-event reports). Re-pasting
`run_forever.md` in a new session is safe — the controller reads existing
`runlog\*.done` markers and jumps past completed stages (S0 preflight only checks
the same facts again).

## Failure policy (built into the controller)

- No wall-clock timeouts. Errors → "CONTINUE" respawn with the same task file,
  workers fix `lastError` and resume partial work. Max 4 attempts per stage.
- After 4 fails a stage is marked FAILED and logged in `launch\runlog\failures.md`
  and the flow continues with degraded modes (C without A → "unknown" causation).
- Nothing is ever force-pushed; commits are restricted to `market_data_2019_2026/`.

## Verified environment (2026-08-09)

- OpenClaw 2026.7.1-2, gateway event loop OK, agent `main` (google/gemini-3.5-flash-lite:
  RPM 15 / TPM 250k / RPD 500 — orchestration keeps main-agent turns few and short;
  the heavy work runs in the opencode workers).
- `opencode run` flags verified: `-f/--file`, `--dir`, `--title`, `--format json`, `-c/--continue`.
- `openclaw agent` flags verified: `--agent`, `--message-file`, `--session-key`, `--json`, `--timeout`.
- Python venv: `C:\Users\DELL\AppData\Local\Temp\opencode\wsb-verify-venv\Scripts\python.exe`