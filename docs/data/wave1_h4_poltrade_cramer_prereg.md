# Wave 1 / H4 — Politician-Trade Replication + Cramer Follow-vs-Fade Pair
# (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-24. Status: LOCKED before any in-sample run of ANY arm.
Data acquisition may proceed in parallel; testing is deferred until the dataset is
frozen and its provenance hash recorded in the eval JSON. LIVE TRADING DISABLED —
paper only, fail-closed. FREE TIER ONLY (STOCK Act public filings, public Cramer
pick records; no paid APIs).

## 1. Hypotheses (two arms, ONE preregistration, both directions tested)

- ARM P (Congressional follow): US equities purchased by members of Congress,
  traded at the first available bar AFTER public disclosure availability, beat
  SPY buy-and-hold net-of-cost over a fixed 90-trading-day horizon on BOTH mean
  net excess return significance and the six gates.
- ARM C (Cramer pair): stocks on Jim Cramer's public picks exhibit (C1-follow)
  positive and (C2-fade) negative risk-adjusted drift vs SPY over 90 trading days
  after pick publication; AT MOST ONE direction can pass its full gate chain.
  Gates decide the direction; no post-hoc selection.

## 2. Prior art + changed conditions

| Prior attempt | Outcome | Source |
|---|---|---|
| 13F institutional accumulation factor | tested cycle3/cycle4 (quarterly, 45d lag); not congressional PTRs | cycle4_prereg_mega.md A.3 |
| New-data lane | explicitly left OPEN by 2026-08-14 closure | improvement_regime_conclusion.md |

Changed conditions: NEW DATA source class (legislator disclosure flow + media-pick
records), never tested in this repo. Academic prior: Ziobrowski et al. 2012
(Politicians Inside Trades study) for Arm P.

## 3. Frozen specification (both arms)

- Entry timing: Arm P = close of first trading bar ≥ filing_date + 45 calendar
  days (statutory PTR window; conservative). Arm C = close of first bar ≥ pick
  publication timestamp + 1 bar.
- Horizon/exit: fixed 90-trading-day hold, no stops, no re-entry within window;
  concurrent signals equal-weighted, max 10 open positions, excess cash 0%.
- Costs: 5bps/side entry+exit; SPY same-engine benchmark over identical windows
  (signal-date-aligned SPY legs).
- Window: signals 2019-01-02..2026-08-07 mapped onto the local panel; names
  without panel coverage are dropped BEFORE evaluation (droplist committed with
  dataset).
- Arm C2-fade feasibility note: paper account cannot short (no margin). The fade
  arm is evaluated as a synthetic inverse-excess series, −(r_stock − r_SPY), net
  of costs, for SIGNAL VALIDATION ONLY; it is marked non-deployable-as-cash-account
  in any export. This limitation is declared now, not discovered later.

## 4. Six gates per arm (verbatim thresholds)

Machinery identical to wave1_h1 §4, applied PER ARM: block bootstrap IS p≤0.05
(net excess vs aligned SPY leg); CPCV K=6 embargo 10d all-positive; WF folds =
5 calendar half-year expanding windows all-positive; circular-block permutation
(block=10, 1000 draws, seed 7) p95 survival on OOS excess Sharpe; positive DSR
entry in docs/data/eval_wave1_h4.json via scripts/preregister.py record.

POWER GATE (pre-declared, binds before statistics): if an arm has <40 independent
signal events in-window ⇒ verdict INSUFFICIENT_POWER honest no-op for that arm —
no p-values reported as encouragement. Trials charged to DSR ledger: Arm P = 1,
Arm C = 2 (both directions counted regardless of outcome).

Family decision rule (declared): each arm stands or fails alone on its own gate
chain; a mixed outcome is recorded as-is. No pooling, no rescues.

## 5. Kill criteria

Any gate FAIL ⇒ honest FAIL entry for that arm. Filing-lag lookahead, survivorship
(dropping delisted pre-window names from the SIGNAL set), or post-hoc horizon
changes are kills, not fixes. Dataset changes after first run ⇒ whole-prereg
disqualification unless declared as a delta BEFORE the affected run.
