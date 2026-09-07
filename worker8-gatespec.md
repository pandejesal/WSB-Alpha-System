# Worker brief: design 7-10 promotion-gate variations for SPY-beating strategies (worker 8, finance model)

## Objective
Our evolve loop evaluates parameter-search candidates on 2019-2026 daily
OHLCV (1,910 bars, 10-stock US universe + SPY + BTC) with T+1 execution and
5bps costs. The current promotion gate is a single conjunction: Sharpe>=0.8,
maxDD<=35%, OOS Sharpe>=0.5, trips>=10, absolute excess-vs-SPY>0, DSR>=0.95
(N=all trials), circular-shift perm_p<=0.05, stationary-bootstrap p<=0.05.
After 10,000+ scored iterations ZERO candidates pass. Either no edge exists
in these 10 families, or the gate is miscalibrated (statistically near
impossible, or admits only shapes our families cannot take).

Your job: design 7-10 ALTERNATIVE gate variations (promotion tracks — a
candidate promotes by clearing ANY ONE track fully). Each track must define
a genuinely good, relatively safe SPY-beater, not a loophole.

## Workdir
C:/Users/DELL/Documents/Default Project/WSB-Alpha-System-build
Read AGENTS.md first (pytest/ruff/bandit, paper-only, never live).
Write ALL deliverables inside this workdir (sandbox blocks outside writes).

## Mandatory inputs (read before designing)
- C:/Users/DELL/Documents/Default Project/_deliverables/impl_gates/GATES.md
  + purged_split + null_band_test + deflated_sharpe (existing gate modules,
  self-tests green — REUSE, do not reinvent).
- C:/Users/DELL/Documents/Default Project/_deliverables/impl_paper/ gate
  report + SPY yardstick: SPY total +137.1%, CAGR 13.85%, maxDD -34.1%
  (note: a different window/coverage than the loop's +245.5% — reconcile
  which window your calibration uses and state it).
- evolve_real.py REAL_GATE + stat_screens + stationary_bootstrap_p
  (current implementation to interoperate with — propose spec, do not edit it).
- docs/TOP5_TRIPLE_CHECK.md (why Sharpe ~0.9 candidates trail SPY by 70-137pp:
  low time-in-market inflates Sharpe while trailing absolute).

## Hard constraints on every proposed track
- All metrics computed T+1, costs deducted, identical-window SPY twin.
- Must include BOTH an absolute-excess-vs-SPY term AND a multiple-testing
  discount (DSR or equivalent) — raw Sharpe bars alone are banned.
- Must include a risk term (maxDD and/or downside deviation) and a
  minimum-activity term (trips or time-in-market floor).
- At least 3 tracks must be plausibly satisfiable by a low-exposure timing
  overlay (the only shape currently near passing); at least 2 tracks must
  REQUIRE high time-in-market or buy-hold-like exposure.
- Every track gets: full conjunction with numeric thresholds, 3-line
  rationale citing which failure mode each term blocks, the archetype it
  admits, and one plain-English sentence ("this track means: ...") for a
  non-finance reader.
- Calibrate against SPY itself: state for each track whether SPY buy-hold
  passes it (a track SPY itself fails is either elite-only — label it — or
  miscalibrated).

## Deliverables (prefix `gatespec38_`, inside workdir only — these names are
reserved to avoid overwriting the existing verified `gatespec_*` files)
- src/backtest/gatespec38_tracks.py — machine-readable track specs
  (list of dicts: name, terms, thresholds, rationale, archetype,
  plain_english, spy_passes) + a `check_track(metrics_dict)` evaluator.
- tests/test_gatespec38_tracks.py — ≥6 tests: SPY-baseline fixture passes
  at least one track; fabricated low-exposure high-Sharpe fixture fails
  all tracks; threshold boundary checks; evaluator determinism.
- docs/GATESPEC38_TRACKS.md — the 7-10 tracks in table form + calibration
  notes + which current near-miss each track would admit or still reject.

## Acceptance criteria
- PYTHONPATH=. pytest tests/test_gatespec_tracks.py → all pass.
- ruff check + bandit on your files → clean.
- ≥7 tracks, all constraints above met, real numbers where calibration is
  claimed (recompute, don't assert).
- Final message: track names + one-line each + test count.
