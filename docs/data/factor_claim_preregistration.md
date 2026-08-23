# Cycle 2 — Factor Claim Pre-registration (2026-08-14)

Status: PRE-REGISTERED (rules fixed by /grilling session, session 5d). The
universe SNAPSHOT is appended to this document BEFORE any evaluation runs
(Phase 2 first step). Any change after seeing results = disqualification.

## The claim (as pre-registered)
On the S&P 500 snapshot universe (rules below), a market-neutral weekly
long-short portfolio formed on momentum (12-1) and short-term reversal (1m)
signals earns a positive median weekly factor return out-of-sample
(2024-2026), beats a time-shuffled null distribution, and reproduces the
documented signs of both anomalies on the train window (2019-2023).

## Factors (fixed)
- MOM12-1: cumulative total return over months t-12..t-2 (skips most recent
  month), per the standard 12-1 momentum definition.
- REV1: cumulative return over month t-1 (short-term reversal).
- Composite: rank-normalized sum of the two factor ranks (0..1 each);
  long = top-decile names, short = bottom-decile names on the composite.
- Rebalance: weekly, on Friday close (last trading bar of the week).
- Equal weight within each decile. Holding: held until next rebalance
  (~1 week). No stop, no vol shield — this is a factor portfolio, not a
  single-name confluence stack; the old sim parameters do NOT carry over.

## Universe snapshot rules (fixed BEFORE any data is fetched)
- Source: S&P 500 constituents via yfinance, fetched exactly once.
- Snapshot date: the first fetch in Phase 2; the full ticker list + date +
  ticker count are appended to this doc (Appendix A) BEFORE any backtest runs.
- Liquidity floor (fixed): exclude names with average daily dollar volume
  < $10M over the last 60 trading days of the fetch date, or with > 5% of
  trading bars missing over 2019-01-01..2026-08-07, or priced < $2.
- Survivorship: backfill is as-of the snapshot only; delisted names are NOT
  included. This is a DOCUMENTED bias, mitigated by the sign gate + null
  (the null permutation destroys signal but not survivorship, so a pure
  survivorship artifact fails the null test only if it is not time-aligned
  with real anomalies; the sign gate additionally requires documented signs).

## Train / OOS split (fixed, unchanged from prior regime)
- Train (selection/observation): 2019-01-01 .. 2023-12-31.
- OOS (judgment): 2024-01-01 .. 2026-08-07 (3 complete years when 2026 ends;
  bar judgment requires 4 complete years -> earliest pass end-2027, same
  structural constraint as before — the claim is judged on 2024/2025/2026
  medians + full-OOS stats, with the 4th-year rule unchanged).

## Controls (fixed)
1. Time-shuffled null: permute signal->return alignment 1000x (block-shuffle
   on weekly rebalance dates); the observed OOS mean weekly factor return
   must exceed the 95th percentile of the null distribution.
2. Publication sign gate: on TRAIN only, MOM12-1 long-short must have
   positive mean weekly return and REV1 long-short must have negative mean
   weekly return (documented anomaly signs: momentum positive, reversal
   negative on monthly horizons). If either sign is wrong on train, the
   framework is dead on arrival — no tuning, no reversal of signs.

## Bar (fixed, adapted)
PASS requires ALL of:
- Median weekly factor return > 0 in 3 of the 4 complete OOS years
  (2024, 2025, 2026, 2027; earliest pass end-2027 by design).
- Full-OOS Sharpe >= 1.0 (annualized, weekly returns).
- Full-OOS PF >= 1.5.
- Full-OOS max drawdown <= 35%.
- OOS mean weekly factor return > 95th percentile of the shuffled null.

## Kill rules (unchanged in spirit)
- No post-hoc parameter changes, no factor redefinition, no universe
  changes after the snapshot appendix is written.
- Any theme/variant that is a measured NO-OP or DUPLICATE is declared, not
  re-scored.
- Per-name or per-sector tuning disqualifies immediately.
- The old single-name framework's variants are NOT rescuable here; this is a
  different claim with its own falsification.

## Execution layer (pre-registered)
- Paper (sandbox, verified to support shorts): A-config baseline track starts
  immediately; new-claim passers enter paper only after the bar above passes.
- Tracking-error SLA: |monthly TE| <= 2% vs backtest equal-weights;
  breach = stop-and-audit.

## Deliverables of the cycle (per-layer goals)
- Data: gap-free OHLCV for all snapshot names, 2019-01-01..2026-08-07,
  zero missing bars report; weekly refresh script.
- Backtest engine: weekly factor portfolio simulator with equal-weight
  deciles, short leg, turnover-aware fills (T+1), documented in code.
- Evaluation: control runs (null 1000x, sign gate) as automated checks.
- Paper: A-config baseline + any passers, TE <= 2% monthly.
- Ops: all tests green (incl. fixing quantstats/vectorbt deps), no lookahead
  regressions; one cycle-end report per layer.

## Appendix A — Universe snapshot (to be filled BEFORE any evaluation)
- Snapshot date: TBD (Phase 2 first fetch)
- Ticker count: TBD
- Ticker list: TBD (full list pasted here, no abbreviation)
- Names excluded by liquidity floor: TBD (list + rule values applied)

## Appendix A — Universe snapshot (FROZEN 2026-08-14, before any evaluation)

- Snapshot date: 2026-08-14 23:22
- Source: Wikipedia 'List of S&P 500 companies' (canonical list; yfinance has no constituents endpoint)
- Constituents total: 503
- Included: 481 | Excluded: 22
- Reference calendar: ^GSPC (1910 trading days)
- Data window: 2019-01-01 -> 2026-08-07

Included tickers (481):
A AAPL ABBV ABT ACGL ACN ADBE ADI ADM ADP
ADSK AEE AEP AES AFL AIG AIZ AJG AKAM ALB
ALGN ALL ALLE AMAT AMCR AMD AME AMGN AMP AMT
AMZN ANET AON AOS APA APD APH APO APTV ARE
ARES ATO AVB AVGO AVY AWK AXON AXP AZO BA
BAC BALL BAX BBY BDX BEN BF-B BG BIIB BKNG
BKR BLDR BLK BMY BNY BR BRK-B BRO BSX BX
BXP C CAH CASY CAT CB CBOE CBRE CCI CCL
CDNS CDW CF CFG CHD CHRW CHTR CI CIEN CINF
CL CLX CMCSA CME CMG CMI CMS CNC CNP COF
COHR COO COP COR COST CPAY CPRT CPT CRH CRL
CRM CSCO CSGP CSX CTAS CTSH CVNA CVS CVX D
DAL DD DE DECK DELL DG DGX DHI DHR DIS
DLR DLTR DOC DOV DOW DPZ DRI DTE DUK DVA
DVN DXCM EBAY ECHO ECL ED EFX EG EIX EL
ELV EME EMR EOG EQIX EQR EQT ERIE ES ESS
ETN ETR EVRG EW EXC EXPD EXPE EXR F FANG
FAST FCX FDS FDX FE FERG FFIV FICO FIS FISV
FITB FIX FLEX FOX FOXA FRT FSLR FTNT FTV GD
GDDY GE GEN GILD GIS GL GLW GM GNRC GOOG
GOOGL GPC GPN GRMN GS GWW HAL HAS HBAN HCA
HD HIG HII HLT HON HPE HPQ HRL HSIC HST
HSY HUBB HUM HWM IBKR IBM ICE IDXX IEX IFF
INCY INTC INTU INVH IP IQV IR IRM ISRG IT
ITW IVZ J JBHT JBL JCI JKHY JNJ JPM KDP
KEY KEYS KHC KIM KKR KLAC KMB KMI KO KR
L LDOS LEN LH LHX LII LIN LITE LLY LMT
LNT LOW LRCX LULU LUV LVS LYB LYV MA MAA
MAR MAS MCD MCHP MCK MCO MDLZ MDT MET META
MGM MKC MLM MMM MNST MO MOS MPC MPWR MRK
MRNA MRSH MRVL MS MSCI MSFT MSI MTB MTD MU
NCLH NDAQ NDSN NEE NEM NFLX NI NKE NOC NOW
NRG NSC NTAP NTRS NUE NVDA NVR NWS NWSA NXPI
O ODFL OKE OMC ON ORCL ORLY OXY PANW PAYX
PCAR PCG PEG PEP PFE PFG PG PGR PH PHM
PKG PLD PM PNC PNR PNW PODD PPG PPL PRU
PSA PSKY PSX PTC PWR PYPL QCOM RCL REG REGN
RF RJF RL RMD ROK ROL ROP ROST RSG RTX
RVTY SBAC SBUX SCHW SHW SJM SLB SMCI SNA SNPS
SO SPG SPGI SRE STE STLD STT STX STZ SW
SWK SWKS SYF SYK SYY T TAP TDG TDY TECH
TEL TER TFC TGT TJX TKO TMO TMUS TPL TPR
TRGP TRMB TROW TRV TSCO TSLA TSN TT TTD TTWO
TXN TXT TYL UAL UBER UDR UHS ULTA UNH UNP
UPS URI USB V VEEV VICI VLO VMC VRSK VRSN
VRT VRTX VST VTR VTRS VZ WAB WAT WBD WDAY
WDC WEC WELL WFC WM WMB WMT WRB WSM WST
WTW WY WYNN XEL XOM XYL XYZ YUM ZBH ZBRA
ZTS

Excluded (22, all by the pre-registered >5% missing-bars rule; no dollar-volume or price exclusions):
- ABNB: missing 25.7% > 5%
- APP: missing 30.1% > 5%
- CARR: missing 16.0% > 5%
- CEG: missing 40.2% > 5%
- COIN: missing 30.1% > 5%
- CRWD: missing 5.8% > 5%
- CTVA: missing 5.3% > 5%
- DASH: missing 25.6% > 5%
- DDOG: missing 9.4% > 5%
- EXE: missing 27.8% > 5%
- FDXF: missing 97.3% > 5%
- GEHC: missing 52.2% > 5%
- GEV: missing 69.0% > 5%
- HONA: missing 98.0% > 5%
- HOOD: missing 33.9% > 5%
- KVUE: missing 57.2% > 5%
- OTIS: missing 16.0% > 5%
- PLTR: missing 23.0% > 5%
- Q: missing 89.7% > 5%
- SNDK: missing 80.5% > 5%
- SOLV: missing 68.9% > 5%
- VLTO: missing 62.7% > 5%

Gap notes among included: 429/481 have zero missing bars; 48 have 1-10; 4 have genuine pre-listing gaps (UBER 89 bars IPO 2019-05, DOW 53 spin-off 2019-04, FOX 48 / FOXA 47 spin-off 2019-03) — all within the 5% floor, verified genuine, not fetch defects.

## Appendix B — Evaluation results (appended 2026-08-14, immutable)

**Verdict: CLAIM FALSIFIED** (fail-closed; 6 of 7 pre-BAR criteria unmet).

- Sign gate (train 2020-01-06..2023-12-31, 208 weeks): MOM12-1 long-short mean **-0.13%/wk (WRONG SIGN** — momentum L/S loses on train; documented anomaly does not replicate on this universe) | REV1 mean -0.06%/wk (correct reversal sign). Gate FAIL.
- OOS 2024-01-01..2026-08-03 (135 weeks): median **-0.13%/wk** (needs > 0) | Sharpe 0.54 (needs >= 1.0) | PF 1.22 (needs >= 1.5) | maxDD -12.3% (passes <= 35%).
- Complete OOS years: 2024 positive, 2025 negative -> 1 of 2 (needs 3 of 4).
- Nulls (1000x each): permutation-null p95 median +0.13% — observed -0.13% does NOT beat it. Time-shuffle median invariant under permutation (p95 = observed, by construction).
- Composite train: median +0.31%/wk but mean -0.002%/wk (skewed; Sharpe -0.004).
- Full numbers: docs/data/factor_evaluation.json + factor_results.json.

Per plan: claim killed; NO parameter tinkering allowed. Phase 5.2 (factor->paper mapping) skipped; Phase 5.1 baseline paper track + Phase 6 ops debt remain. Earliest final-bar pass was end-2027; now moot.