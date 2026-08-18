# Session report — Short-strategy research & empirical verification

**Date:** 2026-08-09
**Scope:** WSB-Alpha-System-latest — next SHORT strategy candidate selection (research only; no `src/` code, no validators, no brokers touched)

---

## 1. Goal

Pick the next single-name SHORT strategy for the small ($100) book. Constraints honored throughout: reuse existing infra (yfinance + `compute_indicators()` + `PositionSizer` + `MacroRegimeFilter`), free-tier data only, 1% risk per trade, 4-position cap, fractional shares.

## 2. What was inspected (repo)

- **Live/backtest strategies:** `src/alpha/fade_strategy.py` (live SHORT), `strategy_wsb_alpha.py` (live LONG), `wsb_alpha_legacy.py` (backtest + legacy sentiment pipeline → `wsb_factual_research_data.csv`, **not yet generated**), `man_ahl_legacy.py` (backtest).
- **Indicators:** `src/alpha/indicators.py` (`compute_indicators()` — RSI_14, BB, EMA_20, ATR_14, GK_Vol, CVaR_95, MACD).
- **Risk/sizing:** `position_sizing.py` (1% risk, 4-position cap, DD guardrails 5%/10%/15%), `macro_regime.py` (SPY-driven regime gate).
- **Verification:** `src.backtest.engines.vectorbt_engine.py`, `main_live.py`, `permutation_tester.py`, data providers (yfinance/reddit/ccxt), plus `web-research/strategies.md`, `web-research/indicators.md`, `web-research/quant-validation-best-practices.md`, `web-research/small-account-risk.md`.

## 3. Deliverable 1 — `docs/research/STRATEGY-CANDIDATES.md` (new)

Inventory (which strategy is live vs backtest-only), three candidate specs, feasibility matrix, VERIFY list, validation wiring:

| Candidate | Idea | Fit w/ infra | Composite (OPINION) |
|---|---|---|---|
| C1 OBB-Fade | Fade Close ≥ BB_upper(20,2) + RSI14 ≥ 70 | 9/10 (drop-in) | ~7.6 |
| C2 WeeklyTopFade | Cross-sectional short of prior-week winners | 6/10 | ~6.4 |
| C3 Residual-Short | Avellaneda–Lee s-score vs SPY | 6.5/10 | ~7.4 |

Initial recommendation (pre-verification): C3 primary, C1 fallback.

## 4. Deliverable 2 — Empirical verification (performed 2026-08-09)

Standalone scripts in `docs/research/` (anaconda python, yfinance daily 2015-01-01→2026-08-09, auto_adjust). **Proxy universe** (20 names: GME AMC NVDA TSLA AAPL MSFT META AMD NFLX SHOP ROKU SNAP PINS CRM MU U F KO JNJ BA) because the sentiment DB (`wsb_factual_research_data.csv`) is a pipeline artifact that does not exist yet — representativeness caveat, not the final universe.

Scripts: `verify_c3_scatter.py` (C3), `verify_c1_c2.py` (C1 + C2). Both went through at least one bug-fix round (P&L unit bug in C3 P&L; sign + SL-unit bug in C1/C2) — final numbers below are from the corrected runs.

### C3 — s-score short: **FAIL**
- Entry s ≥ 1.25, exit s ≤ 0.75, SL 1.5×resid-std, 10d time stop; T+1 open fill.
- 3,465 trades; mean **−0.14%/t trade (t≈−1.7 gross)**; win 48–51%; every subperiod ≤ 0 (2015–19 −0.15%, 2020–21 −0.38%, 2022–26 −0.03%).
- 20bp round-trip: −0.34%/t; 60bp: −0.74%/t. Grid (1.0/1.25/1.5) identically non-positive.
- OU half-life ≈ 0.2d → residual autocorr ≈ 0; residual series is noise, not tradeable mean reversion.
- **VERDICT: REJECTED as specced** (matches corpus warning of post-2011 edge decay).

### C2 — weekly reversal short: **FAILED**
- Cross-sectional top-quintile of 20 by last-week return, SHORT, 1w and 2w holds.
- Short P&L **negative**: −0.80%/wk (t≈−2.7) @1w; −1.59%/wk (t≈−3.2) @2w; worse after costs.
- Prior-week winners keep trending (momentum continuation) on this universe; the LONG mirror is positive (side-finding for a future long-side candidate).
- **VERDICT: REJECTED as specced.**

### C1 — OBB-Fade short: **PASSES initial screen (with caveats)**
- signal Close ≥ BB_upper(20,2) AND RSI14≥70 → entry T+1 open; TP = signal-day BB_mid; SL = 1.5×ATR14; time stop ≤5 sessions.
- **780 trades; gross +1.30%/t (t≈+3.0); 60% win.** Episode lengths median 1d, p90 4d, max 8d.
- Subperiods all positive: 2015–19 +0.96%/t (t=3.6); 2020–21 +1.78%/t (t=1.3, squeeze headwinds); 2022–26 +1.33%/t (t=2.3).
- Costs: 20bp → +1.10%/t; 60bp → +0.70%/t.
- Geometry findings: TP fires first only ~3%, SL ~33%, TIME exits ~64% — expectancy comes from the fade/time tail, not the TP; median +1.09%.
- **Squeeze tail** (must-fix): worst single trade ≈ −223% (2020–21 GME/AMC-style gap), p5 ≈ −7.9%. At $100 / ~0.7 shares, one such name is a >50% path shock.
- **VERDICT: PASS as candidate — build REQUIRE: squeeze/extension guard (skip names with extreme recent extension, e.g. 5d move > +40%) + keep the repo's 4-position cap.**

## 5. Deliverable 3 — `STRATEGY-CANDIDATES.md` updated

§7 "Verification log" appended with the empirical numbers above and the reversal of the earlier recommendation:

> **Updated recommendation (OPINION):** C1 (OBB-Fade short) is now the primary next SHORT strategy — the only one of three with a positive measured edge (+1.3%/t, t≈3), survives 60bp costs, reuses existing indicators/infra, fits the $100 fractional book. Ship with (a) squeeze guard, (b) the §6 honest-gate chain (DSR ledger, WFE walk-forward, cost-stress).
> C3 and C2 remain **REJECTED as specced** (no edge / negative edge); the long-momentum continuation from C2's data is the next LONG-side candidate if desired.

## 6. Validation wiring (recorded, not executed)

- DSR + honest trial ledger — count every grid config.
- Walk-forward IS 3y / OOS ≥ 8 windows, WFE ≥ 0.5, never retune on OOS.
- Cost multiplier ×2–3 (fees+slippage); $100 make-or-break at 20–60bp round-trip.
- Mean-reversion-specific null: circular/block-shift permutation — **not** the repo's plain-shuffle null (`permutation_tester.py` is invalid for MR; no edit made — requirement recorded only).
- Monte-Carlo 10k-path drawdown envelope → repo DD guardrails (5/10/25%).

## 7. Files touched (complete list)

- **Changed:** `docs/research/STRATEGY-CANDIDATES.md` (created; later §7 appended)
- **Created:** `docs/research/verify_c3_scatter.py`, `docs/research/verify_c1_c2.py`
- **Deleted:** `docs/research/_probe_env.py` (scaffolding)
- **Not touched:** any file under `src/`, `strategies/`, `tests/`, config, `.env*`, git (no commits)

## 8. Environment note

`python` on PATH is a hermes-agent venv with no numpy/pandas; verification ran with `C:\Users\DELL\anaconda3\python.exe` (numpy, pandas, yfinance 1.5.1 available).

## 9. Caveats / known limitations

1. Proxy universe ≠ sentiment DB; count/edge may shift when the real universe is generated.
2. Verification uses daily closes 2015–2026; borrow costs, locates, PDT friction, and short-tilt venue rules are NOT modeled (PDT re-check was explicitly deferred to venue rule text — strategies.md F22).
3. C1 geometry relies on time exits; tail-risk from squeeze names is material (C1-CA).
4. Bug-hunting cost ~3 iterations before numbers stabilized — that history is preserved in §4 so the verdicts are not hindsight.

## 10. Suggested next steps (out of scope here)

1. Stand up the sentiment DB (legacy pipeline) → re-benchmark C1 recruit universe.
2. Spec + implement C1 build (fade_strategy.py pattern, squeeze guard, existing gates) WITHOUT touching this research set.
3. Run the §6 honest-gate chain (DSR, WFE walk-forward, cost stress, block-shift null, DD envelope) on C1.
4. Optionally bank the C2 long-momentum side-finding as a long-side research ticket.