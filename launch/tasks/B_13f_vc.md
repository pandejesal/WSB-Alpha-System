# WORKER B — 13F HOLDINGS UNIVERSE (2019–2026) + FLAGSHIP FUNDS + VC NOTES

You are WORKER B in an unattended market-data harvest. You run inside
`C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest`; ALL writes
under `market_data_2019_2026\`. Work autonomously, retry on errors, write state
files. Do NOT commit/push (worker D owns git).

- Python: `C:\Users\DELL\AppData\Local\Temp\opencode\wsb-verify-venv\Scripts\python.exe`
- KEYLESS only. SEC EDGAR is keyless but REQUIRES a descriptive User-Agent header
  ("Sample Company Name AdminContact@<sample>.com"); always send it.
- Politeness: SEC rate limit 10 req/s HARD; use 1 req/s with random jitter; EDGAR
  full-text search (`efts.sec.gov`) and `data.sec.gov` are heavier — 3s between
  requests.

## 1. 13F UNIVERSE — FULL-FILER INDEX (LEAN)

Goal: for every quarter 2019Q1..2026Q2 (30 quarters): how many 13F-HR filings and
13F-NT (initial) filings were made (all managers), and the top-30 new 13F-NT filers
per quarter.

Endpoint (keyless JSON): full-text search on 13F-HR
`https://efts.sec.gov/LATEST/search-index?q=%22<13F-HR>%22&forms=13F-HR&dateRange=custom&startdt=2019-01-01&enddt=2026-08-09&output=json` — returns `{"hits":{"total":N,"hits":[...]}}` chunks. For QUARTER COUNTS run one query per quarter:
`https://efts.sec.gov/LATEST/search-index?q=%22<13F-HR>%22&forms=13F-HR&dateRange=custom&startdt=<qstart>&enddt=<qend>&output=json` — capture `hits.total` per quarter; then top filers page for NT:
`...&forms=13F-NT&startdt=...` → take first 30 `hits.hits[]._source` CIK/name/period.

For the flagship DEEP pass (below), never scrape the whole universe per quarter —
only flagship funds, bounded.

Write `market_data_2019_2026\institutions\13f_universe_index.csv`:
`quarter,filing_13f_hr_count,filing_13f_nt_count,top_new_filers_json` (top 25: cik|name|date).

## 2. FLAGSHIP FUNDS — DEEP QUARTERLY HOLDINGS (bounded set)

Funds (40): Renaissance Technologies, Bridgewater Associates, Point72 Asset
Management, Citadel Advisors, Millennium Management, Tiger Global Management,
Soros Fund Management, AQR Capital Management, D.E. Shaw Group, Two Sigma,
Viking Global, Lone Pine Capital, Pershing Square, Appaloosa Management,…
Fill remaining slots from the same league; the FINAL list (FUNDS.md) must expand
to 40 with real, currently registered 13F filers (verify existence via EDGAR).

PROCEDURE per fund (automated, keyless):
1. Resolve CIK: load `https://www.sec.gov/files/company_tickers.json` (keyless,
   maps ticker→cik_str,title), find by fund name/ticker search; if not found,
   use EDGAR full-text `q="<fund>"` first hit. Do NOT hardcode CIKs — always
   resolve from the files (they change).
2. Submissions JSON: `https://data.sec.gov/submissions/CIK<10digits>.json` —
   find 13F-HR/13F-NT accession numbers with primaryDocument, per quarter
   2019Q1..2026Q2 (missing quarter = record `no filing` politely).
3. For each quarter filing: `https://www.sec.gov/Archives/edgar/data/<CIK>/<accn no dash>/<info table primaryDocument>` — parse the XML `<infoTable>`: rows:
   nameOfIssuer, titleOfClass, cusip, value (x$1000), sshPrnamt, putCall, investmentDiscretion. Store raw.
4. Ticker mapping: nameOfIssuer→ticker best-effort via the SAME company_tickers.json (exact string match; else leave ticker empty — NEVER guess).
5. Output per fund-quart quarter:
   `market_data_2019_2026\institutions\13f\<fundslug>_<quarter>.csv` cols:
   `name_of_issuer,cusip,value_usd_thousands,shares,put_call,ticker(optional)` —
   remove zero `value` rows, dedupe by (cusip,name), sort by value desc.
6. Sandbox semantics: missing filings or filing formats → record in
   `market_data_2019_2026\institutions\13f_issues.csv` (fund,quarter,reason) — do not fail the fund.

Also emit per fund a one-line summary CSV: `market_data_2019_2026\institutions\13f_funds.csv`
`fund_slug,fund_name,cik,quarters_covered,most_valued_issuer,top_value_usd_m`.

## 3. VC PUBLIC SIGNALS (boundable)

Public, keyless sources only. For listed VCs (a16z, Sequoia, Y Combinator, Lightspeed,
 Index Ventures, Benchmark, Bessemer, GGV?... choose, max 10), fetch:
- their official PUBLIC portfolio pages (max 3 pages per VC, respect robots and
  rate limits; prefer static lists)
- extract: name, category(consumer/enterprise/AI/...), round (debt app, seed, series x)
  if visible, country.
Save `market_data_2019_2026\institutions\vc\portfolio_notes.md` — organized table +
one-line summary per VC. No private databases; if a page blocks parsing, note BLOCKED
and move on (still pass).

## 4. STATE HANDOFF

Write `C:\Users\DELL\Documents\Default Project\launch\runlog\B.state.json`:
`{"status":"running|failed|done","attempts":1,"lastError":null,"fundsDeep":n,
"universeQuarters":n,"artifacts":[...],"notes":[]}`; then `...\B.done` empty file when complete.

## 5. ACCEPTANCE

1. 13f_universe_index.csv has 30 quarter rows. 2. ≥36 of 40 funds with ≥20 quarters
  each of deep tables (aggregate ≥ 700 files — object with per-fund coverage).
3. 13f_issues.csv even if empty. 4. VC file exists with ≥5 VCs. 5. State counts
  spot-checked vs disk (2 funds). Then B.done + summary (last 5 lines).