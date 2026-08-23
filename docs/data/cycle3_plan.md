# Cycle 3 Plan — 4 Pre-Registered Claims + Comprehensive Check (2026-08-16)

Source: /grilling session (2026-08-16, rounds 1-4). Shared understanding
confirmed by user. Horizon: Phase A 2026-08-17 .. verdict 2026-09-17 (~1
month). Capital: research + paper only until the live gate passes (Q1a/d).
Discipline: 4 pre-registered claims, fail-closed (docs/data/cycle3_prereg_*).

## Context from Cycle 2
- Factor claim FALSIFIED (6/7 criteria; MOM12-1 wrong sign on train). No
  parameter tinkering — dead claim stays dead.
- A-config baseline paper track keeps running (Q21a) — independent of claims.
- Cycle 3 = 4 new claims: 13F accumulation (Q15a), multi-asset trend (Q16a),
  low-vol (Q17a), ML hybrid strict (Q18a). Priority: 13F > multi-asset >
  low-vol > ML (Q9a). Options-vol deferred, value/quality dropped (Q10a).

## Phase A1 — Pre-registration (DONE 2026-08-16)
- [x] docs/data/cycle3_prereg_13f.md (50-fund accumulation, quarterly
      rebalance T+1 after 45-day lag, CUSIP map rule, sign gate + 1000x null,
      bar Sharpe>=1.0 / maxDD<=25% / CAGR>=15% net, kill + reopen rules).
- [x] docs/data/cycle3_prereg_multiasset.md (12 instruments, weekly long/cash
      SMA200, own window, fetch appendix FILLED 2026-08-16).
- [x] docs/data/cycle3_prereg_lowvol.md (60-day realized vol, weekly L/S
      deciles, 481 snapshot, sign gate + null).
- [x] docs/data/cycle3_prereg_ml.md (12 frozen price features, sklearn
      GradientBoostingRegressor fixed hyperparams, annual expanding refits,
      train-consistency gate + null, overfit guard).
- Freeze date: 2026-08-18 — docs frozen BEFORE any backtest. Already written
  earlier (2026-08-16); immutable from now. Any change after seeing results
  = disqualification; reopen only via pre-registered delta (Q28).
- Acceptance: 4 docs exist, immutable; floor rule (anchored ratchet Q23) in
  each execution layer.

## Phase A2 — Data layer
- Tasks:
  1. Multi-asset OHLCV for the 12 instruments (DONE 2026-08-16; EFA/UUP/
     BTC-USD/ETH-USD fetched adjusted; 8 already local; zero gaps; appendix
     filled).
  2. 13F build: CUSIP->ticker map for the 481 snapshot (yfinance ticker.info
     cusip field), coverage stats appended to cycle3_prereg_13f.md Appendix
     A BEFORE any backtest; 13f_issues handling log (Appendix B).
- Acceptance: map coverage documented; every claim's data facts appended
  before its first backtest run.

## Phase A3 — Claim engines (local, in-session per Q27)
- Tasks:
  1. scripts/cycle3_13f_engine.py: XML parser -> fund-quarter holdings frame,
     accumulation factor (delta shares, SOLE discretion only), quarterly
     long/short deciles, T+1 after lag, no lookahead.
  2. scripts/cycle3_multiasset_engine.py: weekly SMA200 long/cash, equal
     weight, Friday close, costs 5bps/side (10bps crypto).
  3. scripts/cycle3_lowvol_engine.py: 60-day realized vol deciles, weekly L/S.
  4. scripts/cycle3_ml_engine.py: 12 frozen features, frozen sklearn GBR
     (n_estimators=200, lr=0.05, depth=3, min_samples_leaf=20, subsample=0.8,
     random_state=7), annual expanding refits, decile L/S.
  5. Per engine: no-lookahead check + a hand-computed regression example.
- Acceptance: engines run clean, outputs to docs/data/cycle3_*_results.json.

## Phase A4 — Evaluation (controls + OOS)
- Tasks (per claim, automated):
  1. Sign gate / train-consistency gate on train window.
  2. OOS stats: median per complete year, Sharpe / maxDD / CAGR net of costs.
  3. Shuffled null 1000x, p95; observed OOS mean must beat it.
  4. Verdict vs pre-registered bar -> cycle3_<claim>_evaluation.json.
- Acceptance: verdicts recorded with all numbers; no post-hoc doc edits.

## Phase A5 — Comprehensive check (a-h, gate-breaker standard Q25)
- Tasks: docs/data/cycle3_check.md by 2026-09-17 — per layer (a data, b
  engine, c evaluation, d paper plumbing, e execution adapters, f ops/tests,
  g security, h costs) measured evidence, PASS/FAIL, severity-graded
  findings. ANY HIGH-severity finding BLOCKS the cycle verdict until fixed.
- Fix routing: repo fixes via Jules (Q27); analysis/checking local.
- Acceptance: check filed; HIGH findings resolved before verdict.

## Phase A6 — Cycle verdict (2026-09-17)
- Tasks:
  1. Highest-priority claim that passed its bar (Q9a) -> winner. None pass
     -> cycle fails closed (recorded; losers reopenable via deltas Q28).
  2. Losers recorded with numbers, frozen for the cycle.
  3. Phase B starts for the winner: paper track + TE accrual + live-gate
     clock (3 complete calendar months: median excess > 0 OR TE <= 2%/mo,
     zero floor breaches, backtest OOS > 0, >= 1 full rebalance cycle —
     Q8a).
- Acceptance: verdict doc + Phase B kickoff state.

## Phase B — Winner paper track + live gate (after verdict)
- Winner config -> Alpaca paper sandbox, equal weights from backtest, weekly
  rebalance; TE tracker active (|TE| <= 2% monthly else stop-and-audit).
- Floor (anchored ratchet Q23) applies from day 1: 75% of original while
  equity < 150% of original; 100% of original once >= 150%; 70% of peak once
  >= 500%.
- After 3 clean calendar months: $100 real seed -> Alpaca LIVE (Q26),
  reinvest 100% of profits, no new outside capital (Q12b).
- Weekly checkpoints logged in vault (Q22).

## Weekly checkpoints (Q22)
- 2026-08-17: Phase A kickoff (done: pre-reg + data)
- 2026-08-24 / 08-31 / 09-07 / 09-14: engine + evaluation progress in vault
- 2026-09-17: verdict + comprehensive check filed