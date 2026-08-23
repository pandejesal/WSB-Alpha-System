# Cycle 3 — Claim 3/4: Price-Only Low-Volatility Factor (Pre-registration)

Status: PRE-REGISTERED (rules fixed by /grilling session, 2026-08-16, rounds
1-4). Frozen 2026-08-18 before ANY evaluation runs. Any change after seeing
results = disqualification. Priority: 3 of 4 (13F > multi-asset > low-vol >
ML, per Q9a).

## The claim (as pre-registered)
On the S&P 500 snapshot universe (481 names, frozen 2026-08-14, same as Cycle
2), a market-neutral weekly long-short portfolio formed on realized
volatility (long the lowest-vol decile, short the highest-vol decile) earns a
positive median weekly factor return out-of-sample (2024-2026), beats a
time-shuffled null distribution, and reproduces the documented low-volatility
anomaly sign (low-vol stocks earn higher risk-adjusted returns) on the train
window (2019-2023). Pure price data — no fundamentals, no sentiment.

## Signal (fixed)
- Volatility measure: annualized standard deviation of daily returns over the
  trailing 60 trading days (60-day realized vol), computed at each rebalance
  from adjusted closes.
- Ranking: cross-sectional, on the 481-name snapshot, at each weekly
  rebalance. Long = bottom decile (lowest vol), short = top decile (highest
  vol).
- Rebalance: weekly, on Friday close (last trading bar of the week).
- Equal weight within each decile. Holding: held until next rebalance
  (~1 week). No stops, no vol shield, no other filter — the factor alone.

## Universe (fixed, reused from Cycle 2)
- Same frozen 481-name S&P 500 snapshot (2026-08-14; 503 constituents, 22
  excluded by >5% missing-bars rule). Snapshot appendix in
  factor_claim_preregistration.md (immutable) — reused as-is, no refresh.
- Survivorship bias documented as in Cycle 2; mitigated by sign gate + null.

## Train / OOS split (fixed)
- Train: 2019-01-01 .. 2023-12-31 (weekly bars).
- OOS: 2024-01-01 .. 2026-08-07 (2.6 years; 3 complete years when 2026 ends).

## Controls (fixed)
1. Time-shuffled null: permute signal->return alignment 1000x (block-shuffle
   on weekly rebalance dates); observed OOS mean weekly factor return must
   exceed the 95th percentile of the null distribution.
2. Sign gate on TRAIN only: documented low-vol anomaly sign = positive
   (low-vol long-short has positive mean weekly return on train). Wrong sign
   on train = dead on arrival, no tuning.

## Bar (fixed, Q2a hedge-fund-grade + Q25 gate-breaker)
PASS requires ALL of:
- OOS median weekly factor return > 0 in 3 of the 4 complete OOS years (2024,
  2025, 2026, 2027; earliest pass end-2027 by design).
- Full-OOS Sharpe >= 1.0 (annualized, weekly returns).
- Full-OOS max drawdown <= 25%.
- Full-OOS CAGR >= 15%, NET of costs (10 bps per side).
- OOS mean weekly factor return > 95th percentile of the shuffled null.
- Sign gate passed on train.

## Kill rules (fixed)
- No post-hoc volatility-window changes, no factor redefinition, no universe
  changes after the snapshot appendix is written.
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
- Vol computation + decile long-short engine (reuses Cycle 2 weekly OHLCV
  infrastructure), sign gate + 1000x null as automated checks, full numbers
  in docs/data/cycle3_lowvol_evaluation.json + cycle3_lowvol_results.json.
- Engine script: scripts/cycle3_lowvol_engine.py (local, in-session per Q27).

## Appendix A — Universe snapshot (FROZEN 2026-08-14, reused from Cycle 2)
- Same 481-name snapshot as factor_claim_preregistration.md Appendix A
  (immutable; 503 constituents, 22 excluded). No re-fetch, no refresh.