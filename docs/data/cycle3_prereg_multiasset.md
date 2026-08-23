# Cycle 3 — Claim 2/4: Multi-Asset Trend Following (Pre-registration)

Status: PRE-REGISTERED (rules fixed by /grilling session, 2026-08-16, rounds
1-4). Frozen 2026-08-18 before ANY evaluation runs. Any change after seeing
results = disqualification. Priority: 2 of 4 (13F > multi-asset > low-vol >
ML, per Q9a). Unique among the 4 claims: LONG/CASH only, own universe, own
data window (Q16a, Q20c).

## The claim (as pre-registered)
On 12 liquid instruments across equities, bonds, gold, silver, FX and crypto,
a weekly long/cash time-series trend portfolio (long when the instrument is
in an uptrend, cash otherwise, equal weight) earns a positive median weekly
return out-of-sample (2024-2026), beats a time-shuffled null distribution,
and reproduces the documented positive trend-following sign on train
(2019-2023). Trend following is the one strategy family with decades of
documented positive expectancy (the CTA anomaly).

## Instruments (fixed, 12)
SPY, QQQ, IWM, EFA, EEM, TLT, GLD, SLV, HYG, UUP, BTC-USD, ETH-USD.
- Source: yfinance daily OHLCV (adjusted close). Crypto via yfinance
  BTC-USD/ETH-USD (CCXT fallback only if yfinance crypto is unavailable —
  same symbols, verified price continuity).
- Data window: 2019-01-01 .. 2026-08-07 (own window, Q20c). Fetch date and
  any instrument gaps appended to Appendix A BEFORE any backtest.
- No snapshot concept: 12 fixed instruments, no survivorship.

## Signal (fixed)
- Trend = sign of 200-day simple moving average of adjusted close
  (price > SMA200 -> LONG, price <= SMA200 -> CASH), evaluated at weekly
  rebalance.
- Rebalance: weekly, on Friday close (last trading bar of the week).
- Portfolio: equal weight across instruments that are LONG at rebalance;
  instruments in CASH hold nothing (no short leg, no leverage).
- Holding: held until next weekly rebalance (~1 week). No stops, no vol
  targeting, no carry overlay — pure time-series trend, pre-registered.

## Train / OOS split (fixed, own window)
- Train: 2019-01-01 .. 2023-12-31.
- OOS: 2024-01-01 .. 2026-08-07 (2.6 years; 3 complete years when 2026 ends).

## Controls (fixed)
1. Time-shuffled null: permute signal->return alignment 1000x (block-shuffle
   on weekly rebalance dates); observed OOS mean weekly portfolio return must
   exceed the 95th percentile of the null distribution.
2. Sign gate on TRAIN only: documented trend-following sign = positive.
   Strategy mean weekly return on train must be POSITIVE. Wrong sign on
   train = dead on arrival, no tuning.

## Bar (fixed, Q2a hedge-fund-grade + Q25 gate-breaker)
PASS requires ALL of:
- OOS median weekly return > 0 in 3 of the 4 complete OOS years (2024, 2025,
  2026, 2027; earliest pass end-2027 by design).
- Full-OOS Sharpe >= 1.0 (annualized, weekly returns).
- Full-OOS max drawdown <= 25%.
- Full-OOS CAGR >= 15%, NET of costs (5 bps per side for ETFs/indexes, 10 bps
  per side for crypto).
- OOS mean weekly return > 95th percentile of the shuffled null.
- Sign gate passed on train.

## Kill rules (fixed)
- No post-hoc instrument additions/removals, no SMA window changes, no
  long/short flip, no vol targeting added later.
- Any measured NO-OP or DUPLICATE is declared, not re-scored.
- Per-instrument tuning disqualifies immediately.
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
- Micro-live: $100 real seed. If THIS claim wins, the equity legs trade via
  Alpaca LIVE; the BTC/ETH legs via CCXT with real USDT (Q26); reinvest 100%
  of profits; no new outside capital (Q12b).

## Deliverables of this claim
- yfinance fetch script for the 12 instruments (local, in-session per Q19a +
  Q27), weekly trend engine (long/cash), sign gate + 1000x null as automated
  checks, full numbers in docs/data/cycle3_multiasset_evaluation.json +
  cycle3_multiasset_results.json.
- Engine script: scripts/cycle3_multiasset_engine.py (local, in-session).

## Appendix A — Data fetch (FILLED 2026-08-16, before any backtest)

- Fetch date: 2026-08-16, via yfinance (anaconda python 3.11, yfinance 1.5.1),
  auto_adjust=True (dividend-adjusted close, matching local SPY convention
  verified 2026-08-16: local SPY 2019-01-02 close 223.805954 == yfinance
  auto_adjust=True value; auto_adjust=False differs -> corrected the 4 new
  fetches to adjusted). 8 of 12 instruments already local (fetched in prior
  cycles); EFA, UUP, BTC-USD, ETH-USD fetched today (adjusted).
- Window: 2019-01-01 .. 2026-08-07 for ALL 12. Zero gaps.
- Rows per instrument: SPY 1910, QQQ 1910, IWM 1910, EFA 1910, EEM 1910,
  TLT 1910, GLD 1910, SLV 1910, HYG 1910, UUP 1910 (trading calendar;
  2019-01-02 -> 2026-08-07) | BTC-USD 2776, ETH-USD 2776 (daily incl.
  weekends; 2019-01-01 -> 2026-08-07).
- Files: market_data_2019_2026/ohlcv/<SYM>.csv (format: date,open,high,low,
  close,volume,source; dividend-adjusted closes, consistent across all 12).
- No CCXT fallback needed (yfinance crypto succeeded).

## Appendix B — CCXT fallback (if used)
- (filled only if yfinance crypto fails)