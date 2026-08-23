# WORKER A — OHLCV (2019–2026) + GDELT NEWS INDEX

You are WORKER A in an unattended market-data harvest. You run INSIDE the repo
`C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest` (or a `--dir`
you were given). ALL your writes go under `market_data_2019_2026\`. Work
autonomously, retry on errors, keep state files. Do NOT commit or push (worker D owns git).

- Python: `C:\Users\DELL\AppData\Local\Temp\opencode\wsb-verify-venv\Scripts\python.exe`
- KEYLESS ONLY data sources (no API keys anywhere).
- Range: 2019-01-01 .. 2026-08-09 inclusive.

## 1. instruments.csv — WRITE FIRST (34 symbols, 3 kinds)

`market_data_2019_2026\ohlcv\instruments.csv`, columns:
`symbol,kind,note` where kind in INDEX|EQUITY|CRYPTO.

- INDEX/ETF (12): SPY, QQQ, DIA, IWM, EEM, GLD, SLV, TLT, HYG, XLE, XLF, ^VIX
- EQUITY (20): AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AVGO, JPM, BAC, WMT, XOM, UNH, JNJ, V, MA, NFLX, DIS, AMD, ADBE
- CRYPTO (2): BTC, ETH

## 2. OHLCV DAILY BARS

Per symbol, one CSV: `market_data_2019_2026\ohlcv\{symbol}.csv`,
columns `date,open,high,low,close,volume,source` (date = YYYY-MM-DD; crypto has
every calendar day; equity/ETF trading days only; volume 0 = missing).

Fetch chain per symbol (first success wins):
1. CRYPTO (BTC, ETH): Binance keyless klines,
   `https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime=<ms>&endTime=<ms>&limit=1000`,
   paginate in 1000-day chunks from 2019-01-01 to 2026-08-09; close=col4, volume=col7.
2. EQUITY/ETF/INDEX: yfinance `yf.download(sym, start="2019-01-01", end="2026-08-10", interval="1d", auto_adjust=True)`.
   If empty/failed → retry 3x (sleep 5s) → fallback STOOQ keyless CSV:
   `https://stooq.com/q/d/l/?s=<lower>.<us>&d1=20190101&d2=20260809&i=d`
   (columns Date,Open,High,Low,Close,Volume). ^VIX has no cheap keyless EOD — try yfinance
   only; if both fail, write header-only file and log MISSING.
3. If a symbol fails ALL sources: write header-only CSV and append row
   `symbol,reason` to `market_data_2019_2026\ohlcv\missing.csv`. Continue — one
   bad symbol must NOT kill the batch.

Validate per symbol: rows>=1400 (equity/ETF) or >=2600 (crypto) else WARN
(append to `launch\runlog\warnings.md`, do not fail); dates strictly increasing
and unique; H>=L>=0.

## 3. NEWS INDEX (GDELT, keyless) — per symbol × per quarter

For EACH of the 34 symbols × 30 quarters (2019Q1..2026Q2), 2 requests →
~2040 requests, 2.5s apart ≈ 85 min. Chunk the loop; if interrupted,
resume from a progress checkpoint file `market_data_2019_2026\news\run\news_progress.json`
`{"done":["SPY:2019Q1", ...],"next":"..."}` and SKIP completed ones.

Query: `"<SYMBOL> OR <common name>"` e.g. `SPY OR "S&P 500"`, `AAPL OR Apple`,
`BTC OR Bitcoin OR BTCUSD`. URLencode. `sourcelang=eng`.

1. Index (counts) — `mode=TimelineVol`:
   `https://api.gdeltproject.org/api/v2/doc/doc?query=<q>&mode=TimelineVol&format=json&startdatetime=<YYYYMMDD000000>&enddatetime=<YYYYMMDD235959>&sourcelang=eng`
   → total articles in quarter = sum of `timeline`/`timelineVol` values.
2. Top docs — `mode=artlist&maxrecords=10&format=json` same query → capture
   url, title, domain from `articles[{url,title,domain}]` (take what exists).

OUTPUT:
- `market_data_2019_2026\news\news_index.csv`, columns:
  `quarter,symbol,doc_count,top1_url,top1_title,top1_domain`
- `market_data_2019_2026\news\raw\g_<quarter>.jsonl` (30 files): per quarter one
  JSONL with every fetched top-doc row: `{"quarter","symbol","url","title","domain"}`.

Errors: 4xx/5xx → sleep 30/60/120 backoff (3 tries) then mark that cell `null`
in `market_data_2019_2026\news\errors.csv` (`quarter,symbol,error`) and continue.

## 3. STATE HANDOFF (every worker writes these)

- Overwrite `launch\runlog\A.state.json`:
  `{"status":"running|failed|done","attempts":n,"lastError":null,"ohlcvRows":NNNN,"newsRows":NNNN,"missing":[...],"newsMissingCells":NN,"artifacts":["ohlcv/SPY.csv", ...]}`
- On COMPLETE: `launch\runlog\A.done` (empty file) + status done. "Complete"
  means every one of the 34 symbols has a CSV (header-only allowed if recorded
  MISSING) — partial still counts as done, truthfully labelled.

## 4. ACCEPTANCE (self-check BEFORE A.done)

1. instruments.csv exists (34 rows). 2. one CSV per symbol exists (spot check 5).
3. news_index.csv has ~1020 rows (34×30 minus recorded misses). 4. raw JSONL
   every quarter. 5. missing.csv + news backoff cells logged truthfully.
Then write A.done + state (done). Print a 5-line summary (counts + 3 sample
dates per currency of data).