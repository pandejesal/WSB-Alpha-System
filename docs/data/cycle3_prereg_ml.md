# Cycle 3 — Claim 4/4: ML Hybrid (Strict Protocol, Price-Only) (Pre-registration)

Status: PRE-REGISTERED (rules fixed by /grilling session, 2026-08-16, rounds
1-4). Frozen 2026-08-18 before ANY evaluation runs. Any change after seeing
results = disqualification. Priority: 4 of 4 (13F > multi-asset > low-vol >
ML, per Q9a). The claim is DESIGNED to fail-closed against overfitting — the
exact protocol that killed 0/14 prior variants in your history.

## The claim (as pre-registered)
On the S&P 500 snapshot universe (481 names, frozen 2026-08-14, same as Cycle
2), a cross-sectional weekly long-short portfolio selected by a gradient
boosting model — trained on a FROZEN price-only feature set with FIXED
hyperparameters, refit on an expanding train window, never tuned on OOS —
earns a positive median weekly factor return out-of-sample (2024-2026), beats
a time-shuffled null distribution, and shows positive train-window
consistency.

## Features (FIXED, price-only — no sentiment: it covers 11/481 names)
All computed from adjusted OHLCV at each weekly rebalance, for each snapshot
name, on the trailing window:
1. Return lags: 1w, 2w, 4w, 12w, 26w, 52w cumulative returns (6 features).
2. Realized volatility: 20-day and 60-day annualized std of daily returns
   (2 features).
3. RSI(14) (weekly).
4. Distance to SMA: close/SMA20 - 1, close/SMA50 - 1, close/SMA200 - 1
   (3 features).
Total: 12 fixed features. NO feature selection, NO feature engineering
iteration, NO interaction features added later.

## Model (FIXED — sklearn only, per requirements.txt)
- Class: sklearn.ensemble.GradientBoostingRegressor (scikit-learn 1.9.0;
  xgboost/lightgbm NOT installed — not used).
- Hyperparameters (FIXED, no tuning):
  n_estimators=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20,
  subsample=0.8, random_state=7, loss='squared_error'.
- Target: forward 1-week return (weekly, Friday-to-Friday), cross-sectionally
  standardized (rank-normalized) within each rebalance date.
- Refit: annually (every 52 rebalance dates) on the EXPANDING train window.
  First refit at window start; NO refit on OOS data, ever.
- Prediction -> portfolio: at each weekly rebalance, rank names by model
  prediction; long = top decile, short = bottom decile. Equal weight within
  each decile.

## Universe (fixed, reused from Cycle 2)
- Same frozen 481-name S&P 500 snapshot (2026-08-14; 503 constituents, 22
  excluded by >5% missing-bars rule). Snapshot appendix in
  factor_claim_preregistration.md (immutable) — reused as-is, no refresh.
- Survivorship bias documented as in Cycle 2; mitigated by null + the
  train-consistency gate.

## Train / OOS split (fixed)
- Train: 2019-01-01 .. 2023-12-31 (weekly bars; expanding refits inside).
- OOS: 2024-01-01 .. 2026-08-07 (2.6 years; 3 complete years when 2026 ends).

## Controls (fixed)
1. Time-shuffled null: permute signal->return alignment 1000x (block-shuffle
   on weekly rebalance dates); observed OOS mean weekly factor return must
   exceed the 95th percentile of the null distribution.
2. Train-consistency gate (replaces the sign gate — ML has no documented
   anomaly sign): the SAME frozen pipeline must produce POSITIVE mean weekly
   factor return on train (in-window, walk-forward refits only). Negative or
   ~zero train mean = model has no signal even in-sample -> dead on arrival,
   no tuning, no feature changes.
3. Overfit guard: OOS result is generated exactly ONCE by the frozen
   pipeline; any pipeline change re-triggers the null + train gates from
   scratch and is declared as a delta (Q28 reopen rule).

## Bar (fixed, Q2a hedge-fund-grade + Q25 gate-breaker)
PASS requires ALL of:
- OOS median weekly factor return > 0 in 3 of the 4 complete OOS years (2024,
  2025, 2026, 2027; earliest pass end-2027 by design).
- Full-OOS Sharpe >= 1.0 (annualized, weekly returns).
- Full-OOS max drawdown <= 25%.
- Full-OOS CAGR >= 15%, NET of costs (10 bps per side).
- OOS mean weekly factor return > 95th percentile of the shuffled null.
- Train-consistency gate passed.

## Kill rules (fixed)
- No feature additions/changes, no hyperparameter tuning, no model class
  change, no refit-schedule change, no universe changes.
- Any measured NO-OP or DUPLICATE is declared, not re-scored.
- "The model needs more features / a different loss / more depth" is NOT a
  valid adjustment within this claim — it is a NEW claim (reopen delta).
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
- Feature builder (12 features, fixed), frozen GradientBoostingRegressor
  pipeline with annual expanding refits, decile long-short engine, train-
  consistency gate + 1000x null as automated checks, full numbers in
  docs/data/cycle3_ml_evaluation.json + cycle3_ml_results.json.
- Engine script: scripts/cycle3_ml_engine.py (local, in-session per Q27).

## Appendix A — Reproducibility (filled BEFORE any backtest)
- sklearn version: 1.9.0 (frozen)
- numpy 2.2.0 / pandas 2.2.3 (frozen)
- Random seeds: model random_state=7 (frozen); null shuffle seed logged in
  engine output (TBD).

## Appendix B — Pre-registered delta (written 2026-08-16 BEFORE any backtest)
### B.1 Installed-version discrepancy (declared, per Q28 reopen rule)
- The frozen versions in Appendix A (sklearn 1.9.0 / numpy 2.2.0 / pandas
  2.2.3) are NOT what the environment actually has. Measured at engine build
  time, BEFORE any evaluation run: sklearn 1.6.1, numpy 2.4.6, pandas 3.0.5
  (anaconda python 3.11, C:\Users\DELL\anaconda3\python.exe). Installing the
  frozen versions would be an environment change performed AFTER the claim
  started; per the fail-closed protocol the engine runs on the INSTALLED
  versions (sklearn 1.6.1). All fixed hyperparameters (n_estimators=200,
  learning_rate=0.05, max_depth=3, min_samples_leaf=20, subsample=0.8,
  random_state=7, loss='squared_error') exist and behave identically in
  sklearn 1.6.1. Declared here; no silent re-scoring.
### B.2 Interpretation notes (declared, fixed from here on)
- All 12 features are close-derived (the fixed feature list uses returns,
  realized vol, RSI, SMA distances — no O/H/L feature is in the list);
  features are computed from ADJUSTED close.
- SMA distances (close/SMA20-1, /SMA50-1, /SMA200-1): SMAs over 20/50/200
  DAILY trading bars, evaluated at the Friday rebalance close (same daily-SMA
  basis as the Claim 2 multi-asset SMA200).
- RSI(14): Wilder smoothing on WEEKLY Friday closes.
- Realized vol: 20-day and 60-day annualized std of DAILY returns (x sqrt
  252), evaluated at the Friday close.
- Feature warm-up: the 52-week return lag requires 52 weeks of prior weekly
  bars and SMA200 requires 200 prior daily bars; the earliest date with a
  complete 12-feature row is therefore ~2020-01-02 (data starts 2019-01-01).
  Train rows used from the first complete feature date (declared data
  availability fact, not a feature change).
- Target: forward 1-week Friday-to-Friday return, cross-sectionally
  rank-normalized within each rebalance date (rank -> uniform -> inverse
  normal CDF; standard quantile normalization).
- Refit: annually (every 52 rebalance dates) on the EXPANDING train window;
  the last refit anchor is the largest anchor <= 2023-12-31; OOS predictions
  use only the last train-fitted model, never refit on OOS.
- Null shuffle seed: 7 (np.random.default_rng(7)), logged here as Appendix A
  "TBD" is resolved.