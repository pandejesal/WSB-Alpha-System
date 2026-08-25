# Wave 3 / H4 — Overnight-Session Capture on the Incumbent Basket
# (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-25. Status: LOCKED before any in-sample run. LIVE TRADING
DISABLED — paper only, fail-closed. FREE TIER ONLY (local OHLCV panel).

## 1. Hypothesis

Holding the incumbent's monthly top-5 basket ONLY across overnight sessions in a
fixed weekly pattern — enter at the close of the FIRST trading day of each ISO
week, exit at the open of the LAST trading day of the same week, flat otherwise
(captures the Mon/Tue/Wed/Thu overnight legs) — beats SPY buy-and-hold
net-of-cost on BOTH OOS net CAGR and Sharpe and passes all six gates.

Mechanism family: overnight-vs-intraday return decomposition (Lou-Polk-Skouras
2019; Cliff-Cooper-Gulen 2008). Execution-timing claim on an untested
return-capture dimension.

## 2. Prior art + changed conditions

| Prior attempt | Outcome | Source |
|---|---|---|
| All closed families | see §4 ledger v6 rows | HUNT_MEGA_PROMPT.md |

Changed conditions: no prior hypothesis in this repo conditioned the HOLDING
SESSION (overnight vs intraday). Signal/universe/sizing unchanged from incumbent;
only WHEN returns are captured changes. Weekly (not daily) round-trips declared
ex ante to bound turnover costs (~104 sides/yr).

## 3. Frozen specification

- Basket: incumbent monthly top-5 (same scores/rebalance dates as baseline).
- Entry: close of FIRST trading day of each ISO week, exec_delay 1 bar (order at
  that close fills NEXT bar close if next bar exists inside the same week;
  single-day weeks are skipped and counted).
- Exit: open of LAST trading day of the SAME ISO week (executes that open
  directly); flat from that open until next week's entry close.
- Whole-basket entries/exits, no drift trades, cash yield 0%, 5bps/side every
  entry and exit.
- Benchmark SPY same-engine B&H net over identical calendar; IS/OOS split and
  G4 endpoints inherited verbatim.

## 4. Six gates

Verbatim wave1_h1 §4 machinery imports. Positive DSR entry in
docs/data/eval_wave3_h4.json. Trials charged: 1.

## 5. Kill criteria

Standard five. Declared structural risks (disclosed, not kills): turnover drag
(~10bp/week all-in) vs overnight premium magnitude; part-time exposure CAGR
handicap as in H3.
