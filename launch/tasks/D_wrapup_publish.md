# WORKER D — WRAP-UP: REPORT + GIT COMMIT + PUSH

You run LAST. You aggregate worker outputs into REPORT.md and own ALL git
publication. Read the worker state files (launch\runlog\*.state.json) before
starting. If a stage is failed/absent: report "MISSING" truthfully, publish
everything valid, and push.

- Repo: `C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest`
  (origin = github.com/pandejesal/WSB-Alpha-System, branch main)
- Output: `market_data_2019_2026\REPORT.md`

## 1. READ ALL OUTPUTS (read-only)

- `market_data_2019_2026\ohlcv\instruments.csv`, `ohlcv\missing.csv` (A)
- `market_data_2019_2026\news\news_index.csv` (A)
- `market_data_2019_2026\institutions\13f_universe_index.csv`, `institutions\13f_funds.csv` (B)
- `market_data_2019_2026\institutions\vc\portfolio_notes.md` (B)
- `market_data_2019_2026\events\events_all.json`, `events\scan_summary.csv` (C)
- `market_data_2019_2026\causation\causation_index.json`, `causation\reports\*.md` (C)
- `C:\Users\DELL\Documents\Default Project\launch\runlog\failures.md` + `warnings.md`

## 2. REPORT.md structure (exact headings)

```
# 2019–2026 Market Data Harvest — Report
- Generated: <UTC timestamp>, range 2019-01-01..2026-08-09
- Worker statuses: A done|failed , B ..., C ..., D ...
## 1. OHLCV
- symbols covered n/34, missing list (from missing.csv)
## 2. News index (GDELT)
- quarter coverage n/30, articles indexed (sum doc_count), quarterly counts table
## 3. Institutions (13F)
- universe index: 30 quarters, stats; flagship funds covered n/40
  (table: fund, quarters_covered, most_valued_issuer, top_value_usd_m)
## 4. Events & causation
- total hits detected, kept <=120, verdict distribution (LIKELY/MIXED/NO_CLEAR_SOURCE),
  report count, degraded flag if set
## 5. VC notes
## 6. Failures & warnings (copy lists)
## 7. Data dictionary (file -> columns)
## 8. Reproduction notes
```
- Every number in REPORT.md must equal the REAL disk counts — recount from
  files, do not trust state JSON blindly.

## 3. GIT (ONLY market_data_2019_2026/ is committed)

Do NOT touch .gitignore, .env, or any other path.
1. `git add market_data_2019_2026` in the repo.
2. `git diff --cached --name-only` MUST list ONLY `market_data_2019_2026/...`
   entries. Anything else → `git reset` and re-add exactly. Abort commit on mismatch.
3. Commit message (exact):
   `feat(data): 2019-2026 market harvest — OHLCV 34 syms, GDELT news index, 13F universe+flagships, event causation`
4. `git push origin main` (NEVER --force). On non-fast-forward → `git pull --rebase origin main` then push again.
5. Verify: `git rev-parse origin/main` before vs after, and
   `git log origin/main -1 --format="%H %s"` shows the new commit.

## 4. STATE + FINAL

- `C:\Users\DELL\Documents\Default Project\launch\runlog\D.state.json`:
  `{"status":"done","attempts":1,"lastError":null,"commit":"<sha>","pushed":true}`
- Write `...\D.done` (empty).
- Final output (<= 20 lines): REPORT path, push sha + OK, worker statuses matrix,
  counts table (rows per module), failures list (or "none"), next-steps (1 line).