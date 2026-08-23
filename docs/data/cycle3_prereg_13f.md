# Cycle 3 — Claim 1/4: Institutional 13F Accumulation Factor (Pre-registration)

Status: PRE-REGISTERED (rules fixed by /grilling session, 2026-08-16, rounds
1-4). Frozen 2026-08-18 before ANY evaluation runs. Any change after seeing
results = disqualification. Priority: 1 of 4 (13F > multi-asset > low-vol > ML,
per Q9a).

## The claim (as pre-registered)
On the S&P 500 snapshot universe (481 names, frozen 2026-08-14, same as Cycle
2), a market-neutral LONG-SHORT portfolio formed on institutional
accumulation earns a positive median quarterly factor return out-of-sample
(2024-2026), beats a time-shuffled null distribution, and reproduces the
documented sign of the 13F-flow anomaly on the train window (2019-2023).

## Signal (fixed)
- Institution = one of the 50 funds tracked in
  market_data_2019_2026/institutions/13f_funds.csv (renaissance, bridgewater,
  point72, citadel, millennium, tiger_global, soros, aqr, de_shaw, two_sigma,
  viking, lone_pine, pershing_square, appaloosa, coatue, third_point, tci,
  berkshire, greenlight, baupost, elliott, valueact, canyon, farallon,
  magnetar, king_street, davidson_kempner, goldentree, jane_street,
  susquehanna, balyasny, anchorage, oaktree, silver_lake, sequoia, artisan,
  fisher, jennison, wellington, geode, blackrock, vanguard, state_street, fmr,
  morgan_stanley, goldman_sachs, t_rowe, capital_world, northern_trust,
  jp_morgan).
- Source per fund-quarter: cache/13f/<fund>_<YYYYQn>.xml (1241 filings,
  ~29-30 quarters each). Each infoTable row = one holding (CUSIP,
  shrsOrPrnAmt, investmentDiscretion).
- Accumulation per quarter: for each snapshot ticker, sum of delta-shares
  (shares this quarter minus shares prior quarter, per fund) across all 50
  funds. Only holdings with investmentDiscretion = SOLE count; SHARED/OTHER
  are ignored (pre-registered; avoids double counting).
- CUSIP -> ticker map: built from the 481 snapshot names via yfinance
  ticker.info (cusip field). ANY holding whose CUSIP cannot be mapped to a
  snapshot ticker is IGNORED (pre-registered; unmapped holdings contribute
  nothing). Map + coverage stats appended to Appendix A BEFORE any backtest.
- Ranking: rank tickers by accumulation each quarter; long = top-decile
  names, short = bottom-decile names. Equal weight within each decile.
- Rebalance: QUARTERLY, at T+1 after filing availability (quarter-end + 45
  days filing lag, e.g. 2024Q1 filings usable from 2024-05-16). No lookahead:
  a quarter's filings are usable only after the lag.
- Missing filings: a fund with no XML for a quarter contributes ZERO change
  (not excluded). Funds flagged in 13f_issues.csv (e.g. soros 2026Q2
  no_filing, millennium cik_mismatch): their affected quarter is logged and
  treated as zero-change; the log is appended to Appendix B.
- Holding period: until next quarterly rebalance. No stops, no vol shield.

## Universe (fixed, reused from Cycle 2)
- Same frozen 481-name S&P 500 snapshot (2026-08-14; 503 constituents, 22
  excluded by >5% missing-bars rule). Snapshot appendix in
  factor_claim_preregistration.md (immutable) — reused as-is, no refresh.
- Survivorship bias documented as in Cycle 2; mitigated by sign gate + null.

## Train / OOS split (fixed)
- Train: 2019Q1 .. 2023Q4 (quarterly bars).
- OOS: 2024Q1 .. 2026Q2 (10 quarters; 2026Q3 filings available 2026-11-15,
  outside window). Claim judged on OOS median + full-OOS stats; complete-year
  rule: 3 of 4 complete OOS years positive -> earliest pass end-2027 (same
  structural constraint as Cycle 2).

## Controls (fixed)
1. Time-shuffled null: permute signal->return alignment 1000x (block-shuffle
   on quarterly rebalance dates); observed OOS mean quarterly factor return
   must exceed the 95th percentile of the null distribution.
2. Sign gate on TRAIN only: 13F-flow anomaly documented sign = institutional
   accumulation positively predicts future returns. Accumulation long-short
   must have POSITIVE mean quarterly return on train. Wrong sign on train =
   dead on arrival, no tuning.

## Bar (fixed, Q2a hedge-fund-grade + Q25 gate-breaker)
PASS requires ALL of:
- OOS median quarterly factor return > 0 in 3 of the 4 complete OOS years
  (2024, 2025, 2026, 2027; earliest pass end-2027 by design).
- Full-OOS Sharpe >= 1.0 (annualized, quarterly returns).
- Full-OOS max drawdown <= 25%.
- Full-OOS CAGR >= 15%, NET of costs (10 bps per side).
- OOS mean quarterly factor return > 95th percentile of the shuffled null.
- Sign gate passed on train.

## Kill rules (fixed)
- No post-hoc parameter changes, no signal redefinition, no universe changes.
- 13f_issues.csv entries are LOGGED and handled by the pre-registered
  zero-change rule — never by excluding funds post-hoc to improve results.
- Any measured NO-OP or DUPLICATE is declared, not re-scored.
- Per-name or per-sector tuning disqualifies immediately.
- Reopen rule (Q28): a FAILED claim may be revised and re-run within the
  same cycle ONLY with a pre-registered delta appended to this doc (the
  change, written BEFORE re-running, no silent re-scoring).

## Execution layer (pre-registered)
- Paper (sandbox): winner of Cycle 3 enters paper only after the bar passes.
- Tracking-error SLA: |monthly TE| <= 2% vs backtest equal-weights; breach =
  stop-and-audit.
- Floor (anchored ratchet, Q23): floor = 75% of original capital while equity
  < 150% of original; floor = 100% of original once equity >= 150% of
  original; floor = 70% of peak once equity >= 500% of original. Applies to
  paper track AND live micro-account from day 1.
- Micro-live: $100 real seed -> Alpaca LIVE API after the 3-month live gate
  (Q8a); reinvest 100% of profits; no new outside capital (Q12b).

## Deliverables of this claim
- 13F parser (XML -> fund-quarter holdings frame), CUSIP->ticker map with
  coverage stats, accumulation factor, quarterly long-short engine, sign gate
  + 1000x null as automated checks, full numbers in
  docs/data/cycle3_13f_evaluation.json + cycle3_13f_results.json.
- Engine script: scripts/cycle3_13f_engine.py (local, in-session per Q27).

## Appendix A — CUSIP map + coverage (filled BEFORE any backtest)
### A.1 Delta (pre-registered change, written 2026-08-16 BEFORE any backtest)
- The pre-registered signal specified mapping CUSIP -> ticker via the yfinance
  `ticker.info` cusip field. Verification (2026-08-16): yfinance has NO cusip
  field — `Ticker.info` and `Ticker.get_info()` return cusip = None/absent for
  all 9 sampled tickers (AAPL, MSFT, NVDA, JPM, XOM, BRK-B, GOOGL, FOXA, WAB);
  ISIN lookup is unreliable (only 2/9 valid). The CUSIP field therefore does
  not exist as a data source; per the reopen rule (Q28, kill rules), this map
  method change is pre-registered HERE, before any evaluation run.
- REPLACED map method (fixed from here on, no further changes):
  1. Primary name source: SEC `company_tickers.json` (CIK -> ticker + canonical
     title, e.g. 'NVIDIA CORP'), restricted to the 481 snapshot tickers —
     480/481 have SEC titles.
  2. Secondary name source: yfinance longName for the same 481 tickers
     (handles renames like GE -> GE Aerospace).
  3. Normalization (fixed function, scripts/cycle3_13f_map.py::clean):
     uppercase; & -> AND; strip legal suffixes (INCORPORATED, CORPORATION,
     COMPANY, CORP, INC, CO, LTD, LLC, LP, PLC, AG, NV, SA, COM, NEW,
     HOLDINGS, HLDGS, GROUP, GRP, SYS, ADR, TR, FDS, FD, TRUST, CAP, STK);
     strip state markers (DE, MA, PA, GA, ...); expand 13F abbreviations
     (WHSL -> WHOLESALE, PETE -> PETROLEUM, INTL -> INTERNATIONAL, COS ->
     COMPANIES, SYS -> SYSTEMS, INDS -> INDUSTRIES, INVT -> INVESTMENT, RLTY
     -> REALTY, EQ -> EQUITIES, COMM -> COMMUNITIES, SYSTEM -> SYSTEMS, ...);
     drop connectives (THE, AND, OF) and single letters A/B/C (class markers).
  4. Match tiers, in order (first hit wins):
     t1 exact cleaned name; t2 spaceless (JPMORGAN vs JP MORGAN); t3
     token-sorted (GRAINGER W W vs W W GRAINGER); t4 token-subset containment
     (13F 28-char truncations, e.g. CHARLES RIVER LABORATORIES vs ...LABORATORIES
     INTERNATIONAL); t5 fixed rename alias list (pre-registered, currently:
     WABTEC -> WAB only).
  5. Class-twins (ALPHABET -> GOOGL/GOOG, FOX -> FOXA/FOX, NEWS -> NWSA/NWS)
     disambiguated by the 13F titleOfClass field (CL A / CL B / CL C); rows
     whose class cannot disambiguate are IGNORED.
  6. ANY holding whose issuer cannot be resolved to a snapshot ticker by the
     above tiers is IGNORED (same pre-registered rule as the original CUSIP
     rule: unmapped holdings contribute nothing).
- Rationale: SEC canonical titles match the 13F name_of_issuer format directly;
  name-based matching is deterministic, auditable (map cached in
  cache/cycle3_13f_ticker_map.json), and has no lookahead (names are static
  per ticker).
- Coverage (measured 2026-08-16 over all 1,540,366 parsed 13F rows):
  - Mapped snapshot tickers: 481 / 481 (100%).
  - Holdings rows matched: 227,778 / 1,540,366 (14.8% of rows; the rest are
    ETFs, funds, non-snapshot issuers — correctly out-of-universe).
  - Dollar value matched: $59.8T of $83.4T total (71.7% of value; unmatched
    value is ETF/fund/foreign exposure, not snapshot names).
  - Tier breakdown: t1 180,303 rows; t2 1,138; t3 2,432; t4 43,475; t5 430.
  - Class-resolved twin rows: 238.
- Per-quarter per-fund coverage stats and the unmapped-holding log are written
  to docs/data/cycle3_13f_map_coverage.json by the engine at build time (before
  any return computation).

### A.2 Map build facts
- Map build date: 2026-08-16 (scripts/cycle3_13f_map.py)
- Mapped snapshot tickers: 481 / 481
- Holdings matched per quarter (min/median/max): computed at engine build
  (written to cycle3_13f_map_coverage.json BEFORE any backtest)
- Unmapped holding share: see coverage JSON (row share ~85%, value share
  ~28% — dominated by ETFs and non-snapshot issuers)

## Appendix B — 13f_issues handling log (filled during build)
### B.1 Data-handling facts (written 2026-08-16, engine build)
- **Engine source of truth**: harvested CSVs in market_data_2019_2026/institutions/13f/
  DROP the investmentDiscretion and titleOfClass columns; the engine therefore
  parses cache/13f/*.xml DIRECTLY (infoTable rows), so discretion filtering,
  class-twin disambiguation, and putCall tagging are exact. 1,241 XML files on
  disk across 49 of the 50 pre-registered funds.
- **Probe files excluded**: probe_2019Q1.xml and probe_aqr25q3.xml are NOT
  pre-registered funds (not in 13f_funds.csv); excluded at parse
  (excluded_non_fund:probe = 2). probe_aqr25q3 also has a malformed quarter
  label. No pre-registered fund is affected by this exclusion.
- **t_rowe**: 0 XMLs on disk for the pre-registered fund t_rowe (download gap).
  Per the pre-registered missing-filing rule it contributes ZERO change for all
  quarters (never excluded post-hoc; logged here).
- **Funds with partial XML coverage** (zero-change outside their quarters, per
  rule): blackrock 3 files (2023Q4..2024Q2), fmr 4 (2025Q2..2026Q1), goldman_sachs
  4 (2023Q4..2024Q1,2026Q1), jp_morgan 4 (2024Q3..2026Q1), morgan_stanley 4,
  state_street 8 (2023Q4..2025Q3), vanguard 5 (2025Q1..2026Q1), northern_trust 25,
  capital_world 26. All other funds have 29-30 files.
- **Fund slug fix**: fund is now matched by LONGEST-PREFIX slug (goldman_sachs,
  de_shaw, two_sigma, tiger_global, third_point, pershing_square, silver_lake,
  lone_pine, king_street, jane_street, davidson_kempner, state_street, jp_morgan,
  morgan_stanley, northern_trust, capital_world) — a first-pass naive
  split('_')[0] would have silently dropped these 16 funds; caught during build
  (coverage JSON "excluded_non_fund" counts were nonzero for each), fixed
  BEFORE the first evaluation run.
- **13f_issues.csv entries** (soros 2026Q2 no_filing, de_shaw/two_sigma/aqr/
  citadel/point72 2026Q2 no_filing, millennium/tiger_global cik_mismatch,
  viking 2019Q3 xml_parse_error): all handled by the zero-change rule. viking
  2019Q3's XML parses cleanly (ET.parse ok), so no special handling was needed;
  the issues log entry is recorded as informational.
- **putCall rows**: 375,936 rows carry <putCall> (Put 182,287 / Call 193,649),
  concentrated in anchorage filings. These are infoTable rows with
  shrsOrPrnAmt/sshPrnamt; per the pre-registered letter they are INCLUDED in
  accumulation (no option-specific filtering was pre-registered). Count logged
  here; no discretion/class exceptions.
- **Discretion filter**: 2,506,657 rows SHARED/OTHER ignored; 126,048 SOLE rows
  mapped. (SOLE-only is the pre-registered filter.)
- **Unmapped rows**: 546,740 SOLE rows not resolvable to a snapshot ticker
  (ETFs, funds, foreign, truncated-name tier misses) — ignored per the
  pre-registered unmapped rule.
- **Map coverage at engine level** (BEFORE any return computation, written to
  docs/data/cycle3_13f_map_coverage.json): 3,179,445 total infoTable rows;
  126,048 SOLE+mapped; tiers t1 108,144 / t2 666 / t3 1,630 / t4 15,424 /
  t5 184. This is the engine-scope coverage (XML-parsed, SOLE-filtered); the
  Appendix A coverage (227,778 rows / $59.8T / 71.7% of value) was measured on
  the full un-filtered CSV parse at map-build time. Both are logged, neither
  was changed after seeing results.
- **Pending quarters**: 2026Q1 and 2026Q2 declared PENDING (holding-period exit
  dates 2026-08-17 / 2026-11-16 beyond last price date 2026-08-07). The verdict
  on 2026-09-17 may refresh prices to complete 2026Q1 (pre-registered note in
  evaluation.json).
- **Factor quarters**: 27 of 28 computable quarters produced a factor (2019Q1
  is the first accumulation quarter and is all-zero by the first-filing
  zero-change rule; skipped by the engine's no-spread check, deterministic).
- **Runs**: first evaluation run completed 2026-08-16 after the slug fix;
  results in docs/data/cycle3_13f_evaluation.json + cycle3_13f_results.json.
- **Verdict: BAR PASS = False** (claim FAILS). Gates: sign gate on train
  PASSED (+0.87%/quarter mean on 2019Q2..2023Q4); OOS 2024-2025 median
  quarterly factor return -0.80% (2024 negative, 2025 positive -> 1 of 2
  computable years; 3-of-4-year bar not met, earliest possible pass end-2027);
  full-OOS Sharpe 0.24 (bar >= 1.0); maxDD -7.0% (bar ok <= 25%); CAGR 2.1%
  net (bar >= 15%); OOS mean +0.64% vs null p95 +6.09% (null FAILS). No
  re-scoring, no re-opening under Q28 without a pre-registered delta.