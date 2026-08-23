# Cycle 2 Plan — Factor Claim + Whole-System Improvement (2026-08-14)

Source: /grilling session (session 5d). Shared understanding confirmed by user.
Horizon: 1 month. Capital: research + paper only. Discipline: pre-registered
falsification-first (docs/data/factor_claim_preregistration.md).

## Phase 1 — Pre-registration (DONE)
- [x] docs/data/factor_claim_preregistration.md written (factors MOM12-1 +
      REV1, composite rank, weekly Friday rebalance, long/short deciles,
      S&P 500 snapshot rules, train/OOS split, shuffled-null + sign-gate
      controls, adapted bar, kill rules, execution SLA).
- Acceptance: doc exists and is immutable from this point; any change is a
  disqualification.

## Phase 2 — Universe snapshot + data layer
- Tasks:
  1. Fetch S&P 500 constituents once via yfinance; append snapshot (date,
     full ticker list, count, liquidity-floor exclusions) to the
     pre-registration doc BEFORE any backtest. (docs/data/snapshot_SP500.json)
  2. Fetch daily OHLCV 2019-01-01..2026-08-07 for all snapshot names into
     market_data_2019_2026/ohlcv/ (same lowercase layout as prior data).
  3. Gap report: per-ticker missing-bar count; target = zero for all names
     that passed the floor; any name failing > 5% missing is documented and
     excluded per the pre-registered rule.
  4. Weekly refresh script (scripts/refresh_market_data.py): idempotent,
     extends local CSVs to current date.
- Acceptance (data layer goal): zero missing bars for included names;
  refresh script runs clean; snapshot appendix frozen.

## Phase 3 — Factor backtest engine
- Tasks:
  1. scripts/factor_engine.py: weekly factor portfolio simulator —
     factor ranks from MOM12-1 + REV1 composite, decile assignment,
     equal weight, short leg, T+1 fills, weekly turnover, no leakage
     (factor computed from bars strictly BEFORE the rebalance bar).
  2. Output: weekly long-short return series + per-decile series +
     positions log (for paper mapping and TE tracking).
  3. Regression check: engine reproduces a hand-computed 4-week example.
- Acceptance: no lookahead (test_session4_lookahead-style check on the
  engine), regression example matches, positions log complete.

## Phase 4 — Evaluation (train + controls + OOS)
- Tasks:
  1. Train-window sign gate (automated): MOM12-1 long-short mean weekly
     return > 0; REV1 long-short mean weekly return < 0 on 2019-2023.
  2. OOS statistics: median weekly factor return per complete year,
     full-OOS Sharpe / PF / maxDD.
  3. Shuffled null: 1000 block-permutations, 95th percentile of null mean
     weekly return; observed must beat it.
  4. Verdict vs the pre-registered bar; record docs/data/factor_results.json.
- Acceptance: verdict recorded PASS/FAIL with all numbers; control outputs
  stored; no post-hoc edits to the pre-registration doc.

## Phase 5 — Execution layer (paper)
- Tasks:
  1. A-config baseline paper track starts NOW (deprecated confluence config
     on the 16-name mega-cap list, existing sandbox path) — independent of
     the factor claim.
  2. If the factor claim PASSES its bar: map positions log -> paper sandbox
     (weekly rebalance, equal-weight, shorts supported — verified).
  3. TE tracking: monthly |TE| vs backtest equal-weights; >= 2% breach =
     stop-and-audit.
- Acceptance: baseline track running with state file; TE report monthly.

## Phase 6 — Ops + test debt (parallel, all layers)
- Tasks:
  1. Fix test env: pip install quantstats vectorbt (conda env) so the 3
     dep-dependent tests pass; adapt the no-arg run_backtest test if it
     asserts something obsolete (documented); sandbox test fixed or
     quarantined with documented reason.
  2. All tests green (pytest suite); lookahead test stays green; no new
     regressions from Phases 2-4.
  3. Dashboard/run-logs: daily freshness verified.
- Acceptance (ops goal): `pytest` green; lookahead green; freshness check
  green.

## Phase 7 — Cycle-end report (DONE 2026-08-16)
- [x] docs/data/cycle2_report.md filed — per-layer measured numbers vs goals.
- [x] Vault log (05-Session-Logs/2026-08-16.md) + Mnemosyne store.
- Verdict: factor claim FALSIFIED (6/7 pre-BAR criteria unmet) — does NOT
  survive to the 4-complete-year bar.

## Risks
- S&P 500 snapshot fetch failure / rate limits (yfinance) -> retry, record.
- Survivorship bias documented and accepted (mitigated by sign gate + null).
- 1000x null runs = compute time; use vectorized permutation, budget ~1-2h.
- Sandbox short accounting for weekly turnover (position churn) — validate
  against the positions log in Phase 5.
- Bar is structurally unpassable before end-2027 — the cycle judges the
  PRE-BAR statistics; PASS means "claim survives to the final bar", not
  "edge proven".
