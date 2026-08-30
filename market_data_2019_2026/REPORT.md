# 2019-2026 Market Data Harvest - Report
- Generated: 2026-08-10 02:00 UTC, range 2019-01-01..2026-08-09
- Worker statuses: A done (news degraded), B partial, C done (degraded), D done

## 1. OHLCV
- 34 symbols covered (13 INDEX + 19 EQUITY + 2 CRYPTO); missing.csv empty (0 missing)

## 2. News index (GDELT)
- DEGRADED: news_index.csv 449 rows; quarters present 2019Q1..2020Q1 (5 of 30); all doc_count=0 -> 0 articles indexed (local news harvest failed this run)
- Schema updated to 9 cols (adds avg_tone, tone_disp, event_impact from GDELT Doc 2.0 TimelineTone); rebuild via news_redo.py deferred while GDELT API is unreachable (network/TLS)

## 3. Institutions (13F)
- 13f_universe_index.csv: 30 quarters (2019Q1..2026Q2), ~10000 HR + ~1500-2000 NT filings per quarter
- 13f_funds.csv: MISSING (13f dir empty); flagship funds table: MISSING

## 4. Events & causation
- total hits_raw 9339 across 34 symbols; kept 120 events (events_all.json, z>=3.67 or z<=-3.67, one event per symbol per day)
- causation_index.json: 120 rows - verdicts: ~104 NO_CLEAR_SOURCE, 16 LIKELY_DRIVER, 0 MIXED
- 120 report files in causation\reports\ (<symbol>_<date>.md with z, r%, sigma20, +-5 bar table, <=8 candidates, verdict, confidence)
- degraded=true (GDELT artlist fallback used; local news raw empty)

## 5. VC notes
- MISSING (vc dir empty)

## 6. Failures & warnings
- failures.md / warnings.md not accessible from worker workspace (controller runlog denied)
- C degraded: local news empty -> GDELT fallback; B partial: 13F funds + VC notes not harvested; stale A/B state files (finalize interrupted)

## 7. Data dictionary
- ohlcv/instruments.csv: symbol,kind,note
- ohlcv/missing.csv: symbol,reason
- news/news_index.csv: quarter,symbol,doc_count,top1_url,top1_title,top1_domain,avg_tone,tone_disp,event_impact
- institutions/13f_universe_index.csv: quarter,filing_13f_hr_count,filing_13f_nt_count,top_new_filers_json
- events/events_all.json: symbol,date,r,sigma20,z,threshold_hit,kind
- events/scan_summary.csv: symbol,bars,hits_raw,kept
- causation/causation_index.json: symbol,date,z,verdict,confidence,top1_title,top1_domain
- causation/reports/<symbol>_<date>.md: markdown report per event

## 8. Reproduction notes
- venv python: C:\Users\DELL\AppData\Local\Temp\opencode\wsb-verify-venv\Scripts\python.exe
- tools: news_harvest.py (GDELT quarterly harvest), news_redo.py (resumable rebuild: schema + raw g_*.jsonl + gdelt daily indices), C_scan_events.py (z-score scan, |z|>=3.67), C_causation.py (GDELT artlist per event, 2.5s pacing)
- degradation: local news raw empty -> causation used GDELT fallback; news rebuild deferred while GDELT API is unreachable (network/TLS)