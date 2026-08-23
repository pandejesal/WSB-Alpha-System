# WORKER C — ANOMALY EVENTS + CAUSATION JOIN

You are WORKER C in the unattended market-data harvest. You run AFTER worker A
(its outputs must exist). You run inside
`C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest`; ALL writes
under `market_data_2019_2026\`. No git ops (worker D owns git).

- Python: `C:\Users\DELL\AppData\Local\Temp\opencode\wsb-verify-venv\Scripts\python.exe`
- Range covered: 2019-01-01 .. 2026-08-09. KEYLESS sources only.

## 1. INPUTS (read-only)

- `market_data_2019_2026\ohlcv\{symbol}.csv` (from A; 34 symbols)
- `market_data_2019_2026\news\news_index.csv` + `news\raw\g_<quarter>.jsonl` (from A)

If A is marked FAILED in `launch\runlog\A.state.json`, run DEGRADED MODE:
scan whatever CSVs exist; causation → "unknown" where news missing; set
`"degraded":true` in your state. NEVER fabricate article URLs/titles.

## 2. ANOMALY EVENTS

Per symbol with >= 1400 rows:
- r_t = close_t / close_{t-1} - 1
- sigma20 = rolling 20-day std of r (min 20 obs; else skip early rows)
- z_t = r_t / sigma20
- EVENT iff z>=3 or z<=-3, OR |r| >= amp threshold (INDEX/ETF 2%, EQUITY 3%, CRYPTO 5%).

OUTPUTS:
- `market_data_2019_2026\events\events_all.json` — array of
  `{"symbol","date","r","sigma20","z","threshold_hit":"z|amp","kind":...}`
  sort by |z| desc, CAP at 120 events total.
- `market_data_2019_2026\events\scan_summary.csv` — per symbol: symbol, bars, hits_raw, kept.

## 3. CAUSATION JOIN (bounded)

For each KEPT event:
- window = [date-3d, date+3d]
- search `news\raw\g_<quarter>.jsonl` for the window's quarter: rows whose
  symbol matches; if none → GDELT artlist for the event window
  `https://api.gdeltproject.org/api/v2/doc/doc?query=<sym OR name>&mode=artlist&maxrecords=8&format=json&startdatetime=<start>&enddatetime=<end>&sourcelang=eng`
  (pacing 2.5s).
- Write ONE md per event: `market_data_2019_2026\causation\reports\<symbol>_<date>.md`:
  - header: symbol, date, z, r%, sigma20
  - price context: +/-5 bar table (date open high low close volume)
  - candidates: top <=8 news rows (title / domain / url / datetime — copy exactly)
  - verdict: `LIKELY_DRIVER | MIXED | NO_CLEAR_SOURCE`
  - confidence: `HIGH | MED | LOW`
  - rationale: one line.
- No candidates → verdict NO_CLEAR_SOURCE, confidence LOW, report still written.
- Emit `market_data_2019_2026\causation\causation_index.json`:
  `[{"symbol","date","z","verdict","confidence","top1_title","top1_domain"}]`

## 4. STATE + ACCEPTANCE

1. events_all.json (<=120), scan_summary.csv, reports/ count == kept events,
   causation_index.json row count == kept events.
2. `C:\Users\DELL\Documents\Default Project\launch\runlog\C.state.json`:
   `{"status":"running|failed|done","attempts":1,"lastError":null,"keptEvents":N,"reports":M,"degraded":false}`
3. Write `...\C.done` (empty) when complete; state done; print 5-line summary.