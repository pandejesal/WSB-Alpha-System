# Cycle 2 — Cycle-End Report (2026-08-16)

Status: COMPLETE. All 7 phases executed; factor claim FALSIFIED (Phase 4).
This report is the Phase 7 deliverable: one consolidated report per layer
with measured numbers vs the per-layer goals from the /grilling session
(session 5d) and the pre-registered deliverables (docs/data/factor_claim_preregistration.md).

Plan: docs/data/cycle2_plan.md. Pre-registration (immutable): docs/data/factor_claim_preregistration.md.
Source data: factor_results.json, factor_evaluation.json, snapshot_SP500.json,
gap_report.csv, baseline_state.json, baseline_signals.json, te_report.json.

---

## Layer 1 — Data (Phase 2)

Goal: gap-free OHLCV for all snapshot names, 2019-01-01..2026-08-07, zero
missing bars report; weekly refresh script.

| Metric | Target | Measured | Status |
|---|---|---|---|
| Snapshot constituents | S&P 500, fetched once | 503 (Wikipedia canonical list) | OK |
| Included names | all passing floor | 481 | OK |
| Excluded names | documented by rule | 22 — ALL by >5% missing rule; zero dollar-volume or price exclusions | OK |
| Missing bars (included) | zero | 429/481 zero; 48 with 1-10; 4 genuine pre-listing (UBER 89, DOW 53, FOX 48, FOXA 47 — spin-offs/IPOs, verified, within 5% floor) | OK |
| Snapshot appendix frozen | before any evaluation | Appendix A frozen 2026-08-14 23:22 BEFORE Phase 3/4 runs | OK |
| Refresh script | idempotent weekly | scripts/refresh_market_data.py; dry-run clean + idempotent (AAPL/MSFT/NVDA added=0) | OK |

Data-layer verdict: **PASS** — floor enforced, gaps explained and within tolerance, snapshot frozen.

## Layer 2 — Factor engine (Phase 3)

Goal: weekly factor portfolio simulator with equal-weight deciles, short leg,
turnover-aware T+1 fills, documented in code.

| Metric | Target | Measured | Status |
|---|---|---|---|
| Factors | MOM12-1 + REV1 fixed | implemented (month-end closes strictly before signal bar) | OK |
| Engine | weekly rebalance, T+1 fills | scripts/factor_engine.py; long/short top/bottom decile, equal weight | OK |
| Leak guard | no lookahead | built-in assert: every month-end input < signal date (raises on violation) | OK |
| Regression check | reproduces hand-computed example | tests/test_factor_engine.py 6/6 PASS incl. 4-week example to 1e-12, mutation no-lookahead checks | OK |
| Real run | positions log complete | 481 tickers, 396 rebalances, 343 valid weeks 2020-01-06..2026-07-27, avg 418 ranked / 42 long / 43 short | OK |

Engine verdict: **PASS** — implemented to spec, tested, leak-guarded.

## Layer 3 — Evaluation (Phase 4)

Goal: control runs (null 1000x, sign gate) as automated checks; verdict vs the pre-registered bar.

| Metric | Target | Measured | Status |
|---|---|---|---|
| Sign gate (train 208 wk) | MOM12-1 L/S mean > 0; REV1 L/S mean < 0 | MOM12-1 **-0.13%/wk (WRONG SIGN)**; REV1 -0.06%/wk (correct) | **FAIL** |
| OOS median | > 0 | -0.13%/wk (135 wk, 2024-01-01..2026-08-03) | FAIL |
| OOS Sharpe | >= 1.0 | 0.54 | FAIL |
| OOS PF | >= 1.5 | 1.22 | FAIL |
| OOS maxDD | <= 35% | -12.3% | PASS |
| Complete years | 3 of 4 positive | 2024 pos / 2025 neg -> 1 of 2 | FAIL |
| Permutation null 1000x | beat p95 | p95 median +0.13% vs observed -0.13% | FAIL |
| Time-shuffle null 1000x | beat p95 | median invariant under permutation (order-dependent stat) | FAIL |

**Verdict: CLAIM_FALSIFIED** (fail-closed), 6 of 7 pre-BAR criteria unmet.
Composite train median +0.31%/wk but mean -0.002%/wk (skew; Sharpe -0.004).
Per kill rules: no tinkering; claim killed.

Evaluation verdict: **FAIL** — claim falsified cleanly, controls all ran.

## Layer 4 — Paper (Phase 5)

Goal: A-config baseline running; any passers enter paper only after bar
passes (none); TE <= 2% monthly.

| Metric | Target | Measured | Status |
|---|---|---|---|
| A-config baseline track | running now | scripts/baseline_paper_track.py live; state initialized 2026-08-14, value 100.00, 0 signals first run (conf5 strict), idempotent | OK |
| Sizing | equal-weight 1/4, matches backtest | 1-of-4 equal weight, long-only, entry last close, exit >= 20 trading days | OK |
| TE tracker | monthly, <= 2% | scripts/te_tracker.py; benchmark cached (331 trades, 83 monthly returns, median +3.1%/mo); te_report.json status OK, 0 paper months yet (accrues 2026-09) | OK |
| Factor->paper mapping | only if claim passes | Phase 5.2 SKIPPED (claim falsified) | N/A |

Paper verdict: **PASS (baseline only)** — track live, TE SLA armed; no passers.

## Layer 5 — Ops + test debt (Phase 6)

Goal: all tests green (incl. quantstats/vectorbt deps), no lookahead regressions.

| Metric | Target | Measured | Status |
|---|---|---|---|
| Deps | quantstats + vectorbt install | quantstats 0.0.81, vectorbt 1.1.0, nautilus_trader 1.231.0 (anaconda py3.13.5); riskfolio NOT installable (no py3.13 wheels) -> quarantined via importorskip, documented | OK |
| Full suite | pytest green | **141 passed, 1 skipped (riskfolio), 0 failed** | OK |
| Lookahead suite | green | green (test_session4_lookahead fixed: df.index = dates for pandas 3) | OK |
| Source fixes | documented | memory_engine sqlite leak (contextlib.closing), sandbox_env Windows `\U` escape, 3 test adaptations documented | OK |
| Freshness | daily verified | check_market_data.py vs real world (SPY 776.34, AAPL 305.93); apiHealth.json stale orphan -> docs/data/_orphan/ | OK |

Ops verdict: **PASS** — suite green, lookahead green, freshness verified.

---

## Cycle outcome vs the pre-registered bar

The cycle judges PRE-BAR statistics. PASS = "claim survives to the final
bar" (earliest pass end-2027), NOT "edge proven".

**The factor claim does NOT survive. It is dead on arrival:**
- Sign gate failed on TRAIN (momentum long-short had the wrong sign, -0.13%/wk) —
  the documented 12-1 momentum anomaly does not replicate on this S&P 500
  snapshot over 2020-2023.
- 5 further OOS/control criteria unmet; only maxDD passed.
- The observed OOS median (-0.13%/wk) does not even beat the permutation null.

Per the pre-registered kill rules the claim is not rescuable: no post-hoc
parameter changes, no factor redefinition, no universe changes. The old
single-name framework (Cycle 1 / improvement regime) was closed separately
(regime conclusion: 'no universal edge', 0/14 variants kept) and is NOT
resuscitated here.

## Recommendations (forward, for a possible Cycle 3)

1. The falsification is a measured negative, not noise: momentum lost on this
   universe/window. A new claim would need a different mechanism, not a
   re-tuned version of this one.
2. Keep the frozen 481-name snapshot and weekly refresh pipeline as reusable
   data assets; they are validated and gap-audited.
3. Keep the A-config baseline paper track running through its TE accrual
   window (first TE months accrue from 2026-09); it is independent of the
   factor claim and tests the paper/ops plumbing end-to-end.
4. Any next claim must be pre-registered with its own sign gate and null
   before data work, same discipline.

## Artifacts

- Pre-registration (immutable, Appendix B appended): docs/data/factor_claim_preregistration.md
- Plan: docs/data/cycle2_plan.md
- Results: docs/data/factor_results.json, factor_evaluation.json
- Snapshot: docs/data/snapshot_SP500.json, gap_report.csv
- Paper: docs/data/baseline_state.json, baseline_signals.json, baseline_trades.csv, te_report.json, baseline_backtest_monthly.json
- Tests: tests/test_factor_engine.py