# alphalens-reloaded Factor-Profiling Adoption Proposal — Pre-Registry Factor Tear Sheets

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint. Workdir-contained.
Scope: compare upstream `stefan-jansen/alphalens-reloaded` factor tear sheets (IC, forward quantile returns, turnover, sector-neutral demeaned alpha, 1/5/10-day horizons, quintile spread validation) vs actual repo validation `src/backtest/validation.py` + `src/backtest/metrics.py`. Propose factor-profiling additions that run BEFORE any strategy enters the registry: what metrics, what thresholds, where wired. Exact diffs + test plan.

Upstream sources (read via web):
- `https://github.com/stefan-jansen/alphalens-reloaded` — two-step API: `alphalens.utils.get_clean_factor_and_forward_returns(factor, pricing, quantiles=5, groupby, groupby_labels)` → `alphalens.tears.create_full_tear_sheet(factor_data)`; sections Returns / IC / Turnover / Grouped.
- `quantopian/alphalens tears.py` — `create_full_tear_sheet` = `create_returns_tear_sheet` + `create_information_tear_sheet` + `create_turnover_tear_sheet` (+ event/grouped variants); `create_summary_tear_sheet(factor_data, long_short, group_neutral)`.
- `quantopian/alphalens performance.py` — `factor_information_coefficient(factor_data, group_adjust, by_group)` = per-period Spearman rank IC of factor vs N-period forward returns; `mean_information_coefficient(..., by_time)`; quantile turnover + factor rank autocorrelation helpers.
- `alphalens.ml4trading.io` overview notebook — confirms horizons pattern (1D/5D/10D columns), `Quantile N Mean Turnover` tables, `IC Skew/Kurtosis` rows, long-short demeaned option, `by_group` sector views.

## 1. Study findings — assumed paths vs actual repo

Assumed paths that DO NOT EXIST (verified by directory read):

- `src/backtest/factor*.py`, `src/backtest/tearsheet.py`, `src/factors/*` — NOT FOUND. `src/backtest/` contains: `base_engine.py`, `engine_base.py`, `metrics.py`, `run_historic_backtest.py`, `validation.py`, `walk_forward_engine.py`, `permutation_tester.py`, `engines/`, `validators/`, `optimization/`, `defend/`, `legacy_backtest.py`, etc. No factor module.
- `src/reports/` — NOT FOUND. Reporting lives in `scripts/comprehensive_backtest_report.py`, `scripts/run_full_backtest.py`, `src/backtest/validation.py:main()`.
- Any `alphalens` / `spearman` / `rank_ic` / `quantile` helper — NOT FOUND. Grep for `spearman|rank_ic|information_coefficient|quantile|turnover` in `src/backtest/` hits only trade-quantile noise (zero factor harness). Confirmed gap.
- `requirements.txt:1-169` — `pandas==2.2.3, numpy==2.2.0, scipy==1.18.0, scikit-learn, quantstats==0.0.81, matplotlib, seaborn` present; NO `alphalens-reloaded` entry. Upstream pins are legacy (zipline-era, pre-pandas-2); proposal vendors formulas in-repo, no new hard dep.

Verified actual locations (read, with line refs):

- `src/backtest/metrics.py:1-43` — ONLY `safe_sharpe(returns, periods=252)` and `safe_sortino(...)`. Both `fillna(0)`, guard `std < 1e-12 → 0.0`. Sole metrics unit, consumed by `scripts/run_full_backtest.py:23,28-29,65-67`, `scripts/comprehensive_backtest_report.py:536-545`, `src/backtest/validation.py:78,88`. No IC, quantile, turnover, rank-autocorr, demeaned, or horizon helpers exist.
- `src/backtest/validation.py:1-382` — strategy-TRADE-level validation only:
  - `run_in_sample_test` (lines 91-156): real `rb.run_backtest` return+Sharpe vs 200 within-ticker date-shuffled permutations; joint p = fraction beating real on BOTH return AND Sharpe.
  - `run_walk_forward_test` (159-261): 90-day rolling windows, pooled return+Sharpe p + `windows_won vs permuted median` win-rate.
  - `main` (264-378): SPA via `StatisticalValidator.spa_test` (arch, lines 270-287), two permutation histograms, thresholds `is_pval > 0.01 or wf_pval > 0.05 → "has not demonstrated it beats random noise"` (line 318).
  - Tearsheet block (331-378): `qs.reports.html(returns_series)` where `returns_series = groupby('post_date')['return'].sum()` — sparse trade-day series, NOT a daily equity curve; plus `var_95/99, cvar_95, max_dd_duration`. `TEARSHEET_ENGINE = rb` loud-fail guard (lines 28-33).
  - What it never does: no raw-factor test. It tests post-rule trade outcomes (after RSI/GK-vol/confluence/ATR-slippage/T+1 in `run_historic_backtest.py:11-231`), never whether the underlying factor (e.g. `sentiment_score`, confluence rank, any `src/signals/*` or `src/alpha/indicators.py` column) predicts cross-sectional forward returns.
- `src/backtest/run_historic_backtest.py:11-231` — honest T+1 engine (`business_day_offset(post_date,1)`, fill at `Open[t+1]`, exit at `Close[t+H]`, ATR slippage, FRED regime label `NEUTRAL/...`, per-trade `spy_return/excess_return`). Returns one row per executed trade. This is the correct *trade* input to factor profiling only after mapping factor values → forward returns; it is NOT itself a factor frame.
- `src/backtest/permutation_tester.py:1-136` (`PermutationValidator`) — synthetic-OHLC null (`circular` roll vs shuffle, `p < 0.01` gate). Tests strategy profit-factor robustness to price-path noise, not factor rank predictive power.
- `src/backtest/walk_forward_engine.py:1-123` (`WalkForwardValidator`) — strict conjunction `avg >= OOS_MIN 0.40 AND consistency < 1.5 AND windows >= 3 AND >= 2/3 windows positive`, else FAILED. Tests OOS stability of strategy metric, not per-horizon factor decay.
- `src/backtest/validators/statistical.py:13-135` (`StatisticalValidator`) — White's Reality Check + Hansen SPA + `combinatorial_purged_cv(n_splits=5, n_test=2, purge=5, embargo=5)`. Multiple-testing + leakage machinery at *strategy* level; no IC t-stat / ICIR analogue at *factor* level.
- `src/backtest/defend/trial_ledger.py:388-422` — Bailey–Lopez de Prado DSR (`deflated_sharpe_ratio(T, SR, N)`, `deflated_sharpe_threshold`). Corrects best-of-N Sharpe; orthogonal to factor IC (a high-DSR trade rule can still sit on a zero-IC factor via overfit filters).
- `scripts/run_full_backtest.py:18-82` (`_compute_trade_metrics`) — trade-sum Sharpe/Sortino/Calmar/win-rate/PF + 80/20 train/OOS Sharpe split. No horizon structure, no quantiles, no turnover.
- `scripts/comprehensive_backtest_report.py:498-602` (`calculate_metrics`) — deposit-adjusted daily equity-curve metrics (total_return, CAGR, maxDD scalar, vol, Sharpe/Sortino/Calmar, VaR/CVaR, win-rate/PF/holding/streaks). No rolling, no benchmark-relative TE/IR, no round-trips, no factor split (see pyfolio-adopt companion for that gap — different layer).
- `scripts/hunt_runner.py:151-207` (`do_collect`) — validates `candidates/*.yaml` via `strategy_registry.validate_spec` + checks `pre_registration_ref` + `eval_records` presence. Refuses to write registry itself. Currently has NO factor-profile artifact check — this is the wiring point (see §3).
- `scripts/preregister.py:18-24` + `src/ops/preregistration.py:22,59` (`freeze_preregistration`, `record_evaluation`) — honest-claims gate. Currently records PASS/FAIL/HONEST_ABANDON with no factor-profile payload — second wiring point.
- `src/ops/strategy_registry.py:15` (`validate_spec`) — YAML shape gate. Factor gate must NOT live here (spec-shape only); it lives in `collect` checklist + `record_evaluation` evidence, so a factor FAIL can never silently become a registry entry.

## 2. Upstream tear-sheet semantics adopted (mapped to this repo)

Alphalens canonical input is a MultiIndex `(date, asset)` frame with columns `factor | forward_returns_1D/5D/10D | factor_quantile | (group)`. Two-step: `get_clean_factor_and_forward_returns` builds it (point-in-time join, no lookahead), tears consume it. Adopted section-by-section:

### 2a. Information Coefficient (IC) analysis — `performance.factor_information_coefficient`

- Upstream: per-date Spearman rank correlation `IC_d,h = spearman(factor_d, fwdret_d,h)` for each horizon h; summary table `mean(IC)/std(IC)/IR=mean/std/t=mean/(std/sqrt(T))/p/skew/kurtosis`, plus `% positive IC days`, cumulative-IC and IC-distribution plots; `group_adjust=True` demeans forward returns within group before correlating; `by_group=True` repeats per group.
- Repo gap: nothing computes rank correlation of any signal vs forward returns. `safe_sharpe` on trade sums is not IC; SPA/DSR/permutation test trade outcomes, not predictive rank.
- Adopt as: `rank_ic_series()` + `ic_summary()` in new `src/backtest/factor_profiling.py` (§3, Diff 1). Horizons fixed `(1, 5, 10)` — 1D catches microstructure/implementation, 5D matches repo `holding_days=5` default (`run_historic_backtest.run_backtest:244`), 10D catches decay. Both Pearson (diagnostic) and Spearman RankIC (gating) reported; gate uses RankIC (robust to outliers, matches upstream default).

### 2b. Returns analysis — mean period-wise returns by quantile + long-short spread

- Upstream: `mean_period_wise_return by quantile` (per-date mean forward return of each quintile, then time-mean/std/Sharpe), cumulative-returns-by-quantile, `Mean Period Wise Spread (Q5−Q1, bps)` long-short series with its Sharpe and `% periods spread > 0`, quantile-statistics table, monotonicity expectation Q1 < … < Q5.
- Repo gap: `calculate_metrics`/`_compute_trade_metrics` report single-strategy aggregates; no quintile framing, no spread series, no monotonicity test. A strategy can show positive total return while Q5−Q1 spread is zero/negative (rules cherry-pick rather than factor sorts).
- Adopt as: `quantile_returns()` + `quintile_spread()` (Diff 1). Spread computed long-short demeaned when `long_short=True` (mirror `create_summary_tear_sheet(long_short)` semantics: cross-sectional demean before averaging), reported in bps. Monotonicity = Spearman rho between quantile ordinal [1..5] and per-quantile mean forward return (must be strongly positive). Spread Sharpe reuses `safe_sharpe` (single primitive, no duplicate guards).

### 2c. Turnover analysis — quantile turnover + factor rank autocorrelation

- Upstream: per-quantile `quantile_turnover` = fraction of names entering a quantile each period (high turnover = unstable membership = implementation cost), plus factor-rank autocorrelation `spearman(rank_t, rank_{t+1})` stability diagnostic; turnover table by horizon (1D/5D/10D columns in overview notebook).
- Repo gap: no turnover metric anywhere in the factor sense. (`tests/test_qlib_port.py` has a rotation-turnover gate for portfolio rotation, not factor membership stability. `Portfolio.trades` has `holding_days` but no quantile-membership series.)
- Adopt as: `turnover_stats()` (Diff 1). Two numbers per horizon: mean top/bottom-quantile turnover (cost proxy) and mean rank autocorrelation (stability proxy). Thresholds (§3 table) encode "predictive AND implementable": a high-IC factor with ~0.9 daily turnover is rejected at the factor gate before any backtest spend, instead of dying later in capacity/slippage.

### 2d. Group-neutral / sector-demeaned + grouped analysis

- Upstream: `groupby=ticker_sector` path — `group_adjust` demeans forward returns within sector before IC; `by_group` repeats returns/IC per sector; sector tear sheet exposes sector-concentration masquerading as alpha.
- Repo gap: regimes exist (`NEUTRAL/low_volatility/normal/high_volatility` in `run_historic_backtest.py:49`, `Portfolio.open_position` line ~471) but are TIME regimes, not CROSS-SECTIONAL groups. No universe/sector mapping is loaded in the backtest path (`load_base_data` builds `unique_tickers` from posts CSV + SPY only). A single-sector bet (e.g. all signals in 2 tickers) can pass trade-level gates.
- Adopt as: `group_neutral=True` option on IC + spread (demean forward returns within group, then correlate/average — exactly upstream `group_adjust` semantics), plus `by_group` breakdown dict (Diff 1). Group labels come from caller-supplied `group_map: dict[asset, group]`; when absent, functions run pooled and report `"group_neutral": "n/a (no group_map)"` — never fail-closed on missing mapping, but the GATE requires group-neutral pass whenever a mapping is available (see thresholds table: pooled pass is necessary, group-neutral pass is required when groups exist).

### 2e. Horizons 1/5/10 + quintile-spread validation rule

- Upstream pattern: every table has 1D/5D/10D columns; factor validity = consistent sign and sensible decay across horizons, not a single-horizon spike.
- Adopt as: every metric dict keyed by horizon `{1, 5, 10}`; promotion rule is conjunctive across horizons (§3 table): PRIMARY gate on 5D (matches repo holding period), 1D/10D as consistency/decay guards (no sign flip on spread, monotonic decay tolerance, turnover bound per horizon). A factor that is only significant at one horizon with flips elsewhere FAILs.

## 3. Proposal — factor-profiling additions that run BEFORE any registry entry

### 3a. New module (pure, offline-testable, zero new deps)

NEW `src/backtest/factor_profiling.py` (~230 lines, pure pandas/numpy/scipy-only — `scipy.stats.spearmanr` with a rank-fallback when scipy missing; `scipy==1.18.0` already pinned so import is safe). All functions fail-closed on empty/short input (typed empties, never raise into callers). Point-in-time discipline: factor values at date `d` join to forward returns `P(d+h)/P(d)−1` computed from the SAME preloaded `stock_dfs` bars used by `run_historic_backtest` (no new data plumbing, no yfinance, no network).

Factor-frame builder input contract (mirrors `get_clean_factor_and_forward_returns` minimally):

```
factor_long: DataFrame[date, asset, factor]   # one row per (date, asset); date = signal date (post_date normalized)
prices: dict[asset, DataFrame with Date|DatetimeIndex + Close]  # reuse stock_dfs
horizons: (1, 5, 10)
quantiles: 5
group_map: dict[asset, group] | None
```

Note on single-name history: repo's canonical backtest path is per-ticker trade lists, but factor profiling NEEDS a panel. Minimum viable panel = the hunt universe already in scope (`config/universe.json` tickers + `stock_dfs` preloaded in `validation.load_base_data` / `run_full_backtest.main`). `factor_long` is built by the caller from whatever signal is under test (sentiment_score, confluence score, any `src/signals/*` or `src/alpha/indicators.py` column) — the module never invents a factor, it profiles the one it is given. Warmup NaN left as NaN (never 0-filled — matches qlib-adopt NaN-hygiene rule).

### 3b. Metrics + thresholds (the pre-registry factor gate)

Primary horizon is 5D (repo default holding). All thresholds below are for `quantiles=5`, `min_periods=20` overlapping dates, two-sided 5% unless stated. FAIL on any `MUST` row; WARN (non-blocking, recorded) on `SHOULD` rows.

| # | Metric (per horizon 1/5/10 unless noted) | Formula (upstream-matched) | Threshold (PROMOTE requires) | Level |
|---|---|---|---|---|
| F1 | Mean RankIC (Spearman), 5D primary | `mean_d spearman(factor_d, fwdret_d,5)` | `> 0.02` at 5D, and `> 0.0` at 1D and 10D (no sign flip) | MUST |
| F2 | ICIR (information ratio), 5D | `mean(IC)/std(IC)` on RankIC series | `>= 0.30` at 5D (approx t≈2 at ~45 periods; report t and p alongside) | MUST |
| F3 | IC t-stat / p (5D) | `t = mean/(std/sqrt(T))`, two-sided p | `t > 2.0` (p < 0.05) at 5D | MUST |
| F4 | Positive-IC-day fraction, 5D | `mean(IC_d > 0)` | `>= 0.55` | MUST |
| F5 | Quintile spread mean (Q5−Q1, bps/day-equivalent), 5D | per-date `mean(fwdret|Q5) − mean(fwdret|Q1)`, time-mean ×1e4 | `> 0` and economically meaningful: `>= 5 bps` at 5D per-period (document universe costs alongside; wires to capacity later) | MUST |
| F6 | Spread Sharpe (5D) | `safe_sharpe(spread_series, 252/h)` scaled per horizon | `>= 0.5` at 5D (annualized on spread series) | MUST |
| F7 | Spread consistency (5D) | `mean(spread_d > 0)` | `>= 0.55` | MUST |
| F8 | Monotonicity rho (5D) | Spearman(quantile ordinal 1..5, per-quantile mean fwdret) | `>= 0.7` (strongly ordered; upstream Q1<…<Q5 expectation) | MUST |
| F9 | Group-neutral RankIC (5D, when group_map present) | demean fwdret within group, then F1–F3 | same bars as F1–F3 (`> 0.015`, `ICIR >= 0.25`, `t > 1.8`); pooled-pass + group-neutral-pass both required | MUST when groups available, else recorded n/a |
| F10 | Group-neutral spread (5D, when groups present) | Q5−Q1 on group-demeaned fwdrets | `> 0` (sign must survive demeaning; magnitude reported) | MUST when groups available |
| F11 | Top/bottom quantile turnover (1D) | `mean_d |Qk_d △ Qk_{d+1}| / |Qk|` for k ∈ {1,5} | `<= 0.60` daily (else implementation churn; 5D/10D reported, gate on 1D) | MUST |
| F12 | Factor rank autocorrelation (1D) | `mean_d spearman(rank_d, rank_{d+1})` | `>= 0.30` (stable membership; pure-churn factors fail here) | MUST |
| F13 | Horizon decay sanity | F1/F5 sign across 1/5/10 | no sign flip on F1 or F5 across horizons; 10D magnitude may decay ≤ 75% vs 5D | MUST (sign), SHOULD (decay bound) |
| F14 | Min Periods / coverage | T = # dates with ≥2 quantiles populated | `T >= 20` per horizon else `INSUFFICIENT_DATA → FAIL` (fail-closed) | MUST |
| F15 | IC skew/kurtosis (diagnostic) | skew/kurt of RankIC series | recorded only (upstream overview rows); extreme skew flags regime-dependence note, never gates | SHOULD (record) |
| F16 | Cumulative-IC / cumulative-spread (diagnostic) | cumsum series | recorded + plotted offline; break/rollover note when last-third slope < 0 while full-sample passes → WARN | SHOULD (record) |

Why these levels: repo's existing gates are strict at trade level (permutation p<0.01, WFO OOS≥0.40 + consistency<1.5, DSR break-even). Factor gate is deliberately CHEAPER per-metric but CONJUNCTIVE (16 rows, all MUSTs required) so it screens junk before the 200-permutation spend. `RankIC > 0.02 + ICIR ≥ 0.30` is the standard weak-but-real cross-sectional bar for daily equity factors (upstream notebooks show IC means in low single-hundredths for real factors); spread `≥ 5 bps/5D-period + Sharpe ≥ 0.5` keeps it economically (not just statistically) meaningful; turnover/autocorr bounds keep it implementable under the repo's tiered cost model (equities 5–7 bps + 1 bp commission, vol-scaled — see playbook footnote).

Verdict encoding: `factor_verdict ∈ {PASS, FAIL, INSUFFICIENT_DATA}` + per-metric rows. FAIL or INSUFFICIENT_DATA blocks `record_evaluation(PASS)` (Diff 3) and fails the `collect` checklist (Diff 4). No WARN-only path to promotion when any MUST fails.

### 3c. Where wired (before registry, NOT in evolve/registry/strategies)

1. `src/backtest/factor_profiling.py` — NEW pure module (Diff 1). No imports from `evolve_real`, `strategies/`, registry, yfinance, or network.
2. `src/backtest/metrics.py` — thin re-exports only (Diff 2, additive). Existing `safe_sharpe/safe_sortino` untouched; callers keep importing from `metrics`.
3. `src/ops/preregistration.py::record_evaluation` — additive factor-gate check (Diff 3): when `eval_payload` (or `eval-path` JSON) carries `factor_profile`, verdict `PASS` requires `factor_verdict == PASS`; a `PASS` without a factor profile is rejected with an explicit error telling the caller how to generate one. No change to `freeze_preregistration`.
4. `scripts/hunt_runner.py::do_collect` — additive checklist lines (Diff 4): for each valid spec, look for `results/factor_profile_<family>.json` (or `spec['factor_profile_ref']`); missing/FAIL profile → printed as blocking missing item ("not ready for registry merging"). Still refuses to write the registry itself.
5. `scripts/run_full_backtest.py` — additive optional flag (Diff 5): `--factor-profile <factor_csv> --prices <dir>` (or reuse preloaded frames) emits `factor_profile.json` alongside existing ranking output; ranking order unchanged when flag absent.
6. Explicitly NOT touched: `evolve_real.py`, `strategies/registry.json`, `strategies/*`, `WalkForwardValidator`/`PermutationValidator`/DSR thresholds, `TEARSHEET_ENGINE` guard. Factor gate is a NEW pre-gate; existing gates unchanged.

## 4. Exact diffs proposed

### Diff 0 — `requirements.txt` (no new dep; document why)

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@
 quantstats==0.0.81
+# NOTE(alphalens-adopt 2026-09-09): alphalens-reloaded patterns are vendored as
+# pure pandas/numpy/scipy in src/backtest/factor_profiling.py (no new dep).
+# Full `alphalens-reloaded` wheel carries legacy zipline-era pins incompatible
+# with pinned pandas==2.2.3 / numpy==2.2.0; revisit only if upstream
+# event-study / plotting tears are needed (plots stay offline/matplotlib here).
```

### Diff 1 — NEW `src/backtest/factor_profiling.py` (full file, ~230 lines)

Pure functions; every pattern unit-testable offline. Forward returns are point-in-time (`Close[d+h]/Close[d]-1` on preloaded bars; NaN when `d+h` out of range — never forward-filled).

```python
"""Factor-profiling harness (alphalens-reloaded patterns, vendored).

Pure pandas/numpy/scipy only. No yfinance, no network, no evolve/registry imports.
All functions fail-closed on empty/short input (typed empties, never raise).

Upstream mapping (stefan-jansen/alphalens-reloaded = quantopian/alphalens API):
  rank_ic_series      <-> performance.factor_information_coefficient (Spearman per date)
  ic_summary          <-> mean_information_coefficient + IC stats table (mean/std/IR/t/p/skew/kurt)
  quantile_returns    <-> mean period-wise return by quantile + cumulative
  quintile_spread     <-> Q5-Q1 spread series (bps), Sharpe via safe_sharpe, consistency
  turnover_stats      <-> quantile turnover + factor rank autocorrelation
  group-neutral opts  <-> group_adjust=True (demean fwdrets within group) + by_group breakdown
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.metrics import safe_sharpe

HORIZONS = (1, 5, 10)
N_QUANTILES = 5
MIN_PERIODS = 20


def _spearman(a: pd.Series, b: pd.Series) -> float:
    try:
        from scipy.stats import spearmanr
        r = spearmanr(a, b).statistic
        return float(r) if r == r else 0.0
    except Exception:
        ra, rb = pd.Series(a).rank(), pd.Series(b).rank()
        c = ra.corr(rb)
        return float(c) if c == c else 0.0


def build_forward_returns(prices: dict, horizons=HORIZONS) -> dict:
    """Per-asset forward-return frames: fwd_h[d] = Close[d+h]/Close[d]-1 (point-in-time)."""
    out: dict[str, pd.DataFrame] = {}
    for asset, df in (prices or {}).items():
        d = df.copy()
        if "Date" not in d.columns:
            d = d.reset_index()
            if "Date" not in d.columns and "Datetime" in d.columns:
                d = d.rename(columns={"Datetime": "Date"})
            if "Date" not in d.columns and "index" in d.columns:
                d = d.rename(columns={"index": "Date"})
        if "Date" not in d.columns or "Close" not in d.columns:
            continue
        d["Date"] = pd.to_datetime(d["Date"])
        d = d.sort_values("Date").reset_index(drop=True)
        close = pd.to_numeric(d["Close"], errors="coerce")
        f = pd.DataFrame({"Date": d["Date"]})
        for h in horizons:
            f[f"fwd_{int(h)}"] = close.shift(-int(h)) / close - 1.0
        out[str(asset)] = f
    return out


def build_factor_frame(factor_long, prices, horizons=HORIZONS,
                       quantiles=N_QUANTILES, group_map=None) -> pd.DataFrame:
    """Long factor frame indexed (date, asset): factor | fwd_1/5/10 | quantile | group.

    Mirrors get_clean_factor_and_forward_returns minimally: point-in-time join of
    factor_long(date, asset, factor) to forward returns; quantile cut per date.
    """
    if factor_long is None or len(factor_long) == 0 or not prices:
        return pd.DataFrame(columns=["date", "asset", "factor", "quantile", "group"]
                            + [f"fwd_{int(h)}" for h in horizons])
    fl = factor_long.copy()
    fl["date"] = pd.to_datetime(fl["date"])
    fl["asset"] = fl["asset"].astype(str)
    fl["factor"] = pd.to_numeric(fl["factor"], errors="coerce")
    fl = fl.dropna(subset=["factor"])
    fwds = build_forward_returns(prices, horizons)
    parts = []
    for asset, f in fwds.items():
        sub = fl[fl["asset"] == asset]
        if sub.empty:
            continue
        m = sub.merge(f, left_on="date", right_on="Date", how="inner").drop(columns=["Date"])
        parts.append(m)
    if not parts:
        return pd.DataFrame(columns=["date", "asset", "factor", "quantile", "group"]
                            + [f"fwd_{int(h)}" for h in horizons])
    frame = pd.concat(parts, ignore_index=True)
    frame["quantile"] = np.nan
    for d, g in frame.groupby("date"):
        if len(g) >= quantiles and g["factor"].nunique() >= quantiles:
            try:
                frame.loc[g.index, "quantile"] = pd.qcut(
                    g["factor"], quantiles, labels=list(range(1, quantiles + 1))).astype(int)
            except ValueError:
                frame.loc[g.index, "quantile"] = pd.qcut(
                    g["factor"].rank(method="first"), quantiles,
                    labels=list(range(1, quantiles + 1))).astype(int)
    frame["group"] = frame["asset"].map(group_map or {})
    return frame


def _demeaned(frame: pd.DataFrame, col: str) -> pd.Series:
    if "group" in frame.columns and frame["group"].notna().any():
        return frame.groupby(["date", "group"])[col].transform(lambda s: s - s.mean())
    return frame[col]


def rank_ic_series(frame: pd.DataFrame, horizons=HORIZONS, group_neutral=False) -> dict:
    """Per-date Spearman RankIC series per horizon (upstream factor_information_coefficient)."""
    out: dict[str, list] = {}
    if frame is None or frame.empty:
        return {str(int(h)): [] for h in horizons}
    for h in horizons:
        col = f"fwd_{int(h)}"
        rows = []
        for d, g in frame.groupby("date"):
            g = g.dropna(subset=["factor", col])
            if len(g) < 3:
                continue
            y = _demeaned(g, col) if group_neutral else g[col]
            rows.append({"date": d, "ic": _spearman(g["factor"], y)})
        out[str(int(h))] = rows
    return out


def ic_summary(ic_series: dict) -> dict:
    """Mean/std/IR/t/p/frac-positive/skew/kurt per horizon (upstream IC table)."""
    from scipy.stats import t as _t
    out: dict[str, dict] = {}
    for h, rows in (ic_series or {}).items():
        vals = np.array([r["ic"] for r in rows], dtype=float)
        vals = vals[np.isfinite(vals)]
        n = len(vals)
        if n < MIN_PERIODS:
            out[str(h)] = {"n": int(n), "mean": 0.0, "std": 0.0, "icir": 0.0,
                           "t": 0.0, "p": 1.0, "frac_positive": 0.0,
                           "skew": 0.0, "kurt": 0.0, "insufficient": True}
            continue
        mean, std = float(vals.mean()), float(vals.std(ddof=1)) if n > 1 else 0.0
        icir = float(mean / std) if std > 1e-12 else 0.0
        tstat = float(mean / (std / np.sqrt(n))) if std > 1e-12 else 0.0
        p = float(2.0 * _t.sf(abs(tstat), n - 1)) if n > 1 else 1.0
        s = pd.Series(vals)
        out[str(h)] = {"n": int(n), "mean": mean, "std": std, "icir": icir,
                       "t": tstat, "p": p, "frac_positive": float((vals > 0).mean()),
                       "skew": float(s.skew()), "kurt": float(s.kurt()),
                       "insufficient": False}
    return out


def quantile_returns(frame: pd.DataFrame, horizons=HORIZONS) -> dict:
    """Per-horizon: per-quantile mean/std/sharpe + cumulative + monotonicity rho."""
    out: dict[str, dict] = {}
    if frame is None or frame.empty:
        return {str(int(h)): {"by_quantile": [], "monotonicity_rho": 0.0,
                              "cumulative": {}} for h in horizons}
    for h in horizons:
        col = f"fwd_{int(h)}"
        df = frame.dropna(subset=["quantile", col])
        by_q = []
        means = []
        for q in sorted(df["quantile"].dropna().unique()):
            s = pd.to_numeric(df[df["quantile"] == q][col], errors="coerce").dropna()
            means.append((int(q), float(s.mean()) if len(s) else 0.0))
            by_q.append({"quantile": int(q), "mean": float(s.mean()) if len(s) else 0.0,
                         "std": float(s.std()) if len(s) > 1 else 0.0,
                         "sharpe": float(safe_sharpe(s, periods=252)),
                         "n": int(len(s))})
        rho = _spearman(pd.Series([m[0] for m in means]), pd.Series([m[1] for m in means])) if len(means) >= 3 else 0.0
        cum = {}
        for q in sorted(df["quantile"].dropna().unique()):
            s = df[df["quantile"] == q].groupby("date")[col].mean().sort_index()
            cum[str(int(q))] = [{"date": str(i), "cum": float(v)} for i, v in enumerate((1.0 + s.fillna(0.0)).cumprod().tolist())]
        out[str(int(h))] = {"by_quantile": by_q, "monotonicity_rho": float(rho), "cumulative": cum}
    return out


def quintile_spread(frame: pd.DataFrame, horizons=HORIZONS,
                    group_neutral=False, long_short=True) -> dict:
    """Per-date Q5-Q1 spread series + mean_bps/sharpe/consistency (upstream spread table)."""
    out: dict[str, dict] = {}
    if frame is None or frame.empty:
        return {str(int(h)): {"mean_bps": 0.0, "sharpe": 0.0, "consistency": 0.0,
                              "n": 0, "series": []} for h in horizons}
    for h in horizons:
        col = f"fwd_{int(h)}"
        df = frame.dropna(subset=["quantile", col]).copy()
        if long_short or group_neutral:
            df["_y"] = _demeaned(df, col) if group_neutral else df[col] - df.groupby("date")[col].transform("mean")
        else:
            df["_y"] = df[col]
        spreads = df.groupby("date").apply(
            lambda g: float(g[g["quantile"] == 5]["_y"].mean() - g[g["quantile"] == 1]["_y"].mean())
            if (g["quantile"] == 5).any() and (g["quantile"] == 1).any() else np.nan,
            include_groups=False).dropna()
        vals = spreads.to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]
        n = len(vals)
        if n < MIN_PERIODS:
            out[str(int(h))] = {"mean_bps": 0.0, "sharpe": 0.0, "consistency": 0.0,
                                "n": int(n), "series": [], "insufficient": True}
            continue
        out[str(int(h))] = {"mean_bps": float(np.mean(vals)) * 1e4,
                            "sharpe": float(safe_sharpe(pd.Series(vals), periods=252)),
                            "consistency": float(np.mean(vals > 0)), "n": int(n),
                            "series": [{"date": str(d), "spread": float(v)} for d, v in spreads.items()],
                            "insufficient": False}
    return out


def turnover_stats(frame: pd.DataFrame, horizons=HORIZONS) -> dict:
    """Top/bottom quantile turnover + rank autocorrelation (upstream turnover tear sheet)."""
    out: dict[str, dict] = {}
    if frame is None or frame.empty:
        return {str(int(h)): {"q1_turnover": 0.0, "q5_turnover": 0.0,
                              "rank_autocorr": 0.0, "n_transitions": 0} for h in horizons}
    piv_q = frame.pivot_table(index="date", columns="asset", values="quantile", aggfunc="first").sort_index()
    piv_f = frame.pivot_table(index="date", columns="asset", values="factor", aggfunc="first").sort_index()
    dates = list(piv_q.index)
    trans = max(len(dates) - 1, 0)
    q1, q5, ac = [], [], []
    for i in range(trans):
        a, b = piv_q.iloc[i], piv_q.iloc[i + 1]
        both = a.notna() & b.notna()
        for q, acc in ((1, q1), (5, q5)):
            mem_a = set(a[both][a[both] == q].index)
            if mem_a:
                acc.append(len([x for x in mem_a if b.get(x) != q]) / len(mem_a))
        ra, rb = piv_f.iloc[i], piv_f.iloc[i + 1]
        bothf = ra.notna() & rb.notna()
        if bothf.sum() >= 3:
            ac.append(_spearman(ra[bothf], rb[bothf]))
    row = {"q1_turnover": float(np.mean(q1)) if q1 else 0.0,
           "q5_turnover": float(np.mean(q5)) if q5 else 0.0,
           "rank_autocorr": float(np.mean(ac)) if ac else 0.0,
           "n_transitions": int(trans)}
    return {str(int(h)): dict(row) for h in horizons}


def evaluate_factor(frame: pd.DataFrame, horizons=HORIZONS, group_map=None) -> dict:
    """Full pre-registry verdict: pooled + group-neutral IC/spread, quantiles, turnover.

    Returns {"metrics": {...}, "verdict": PASS|FAIL|INSUFFICIENT_DATA, "failures": [...]}.
    Thresholds live in FACTOR_GATE (§3b table); group-neutral rows required iff group_map given.
    """
    ic = ic_summary(rank_ic_series(frame, horizons))
    ic_gn = ic_summary(rank_ic_series(frame, horizons, group_neutral=True)) if group_map else {}
    qr = quantile_returns(frame, horizons)
    sp = quintile_spread(frame, horizons)
    sp_gn = quintile_spread(frame, horizons, group_neutral=True) if group_map else {}
    to = turnover_stats(frame, horizons)
    failures: list[str] = []
    insuff = False
    h5 = "5"
    if ic.get(h5, {}).get("insufficient", True):
        insuff = True
    else:
        if not ic[h5]["mean"] > 0.02:
            failures.append(f"F1 RankIC 5D {ic[h5]['mean']:.4f} <= 0.02")
        if not ic[h5]["icir"] >= 0.30:
            failures.append(f"F2 ICIR 5D {ic[h5]['icir']:.3f} < 0.30")
        if not ic[h5]["t"] > 2.0:
            failures.append(f"F3 t 5D {ic[h5]['t']:.2f} <= 2.0")
        if not ic[h5]["frac_positive"] >= 0.55:
            failures.append(f"F4 frac-pos 5D {ic[h5]['frac_positive']:.3f} < 0.55")
        for h in ("1", "10"):
            if h in ic and not ic[h].get("insufficient", True) and not ic[h]["mean"] > 0.0:
                failures.append(f"F1 sign-flip RankIC {h}D {ic[h]['mean']:.4f} <= 0")
    s5 = sp.get(h5, {})
    if s5.get("insufficient", True):
        insuff = True
    else:
        if not s5["mean_bps"] >= 5.0:
            failures.append(f"F5 spread 5D {s5['mean_bps']:.2f}bps < 5bps")
        if not s5["sharpe"] >= 0.5:
            failures.append(f"F6 spread-Sharpe 5D {s5['sharpe']:.3f} < 0.5")
        if not s5["consistency"] >= 0.55:
            failures.append(f"F7 consistency 5D {s5['consistency']:.3f} < 0.55")
    rho5 = qr.get(h5, {}).get("monotonicity_rho", 0.0)
    if not rho5 >= 0.7:
        failures.append(f"F8 monotonicity 5D {rho5:.3f} < 0.7")
    if group_map:
        g5 = ic_gn.get(h5, {})
        if g5.get("insufficient", True):
            insuff = True
        else:
            if not g5["mean"] > 0.015:
                failures.append(f"F9 group-neutral RankIC 5D {g5['mean']:.4f} <= 0.015")
            if not g5["icir"] >= 0.25:
                failures.append(f"F9b group-neutral ICIR 5D {g5['icir']:.3f} < 0.25")
        n5 = sp_gn.get(h5, {})
        if not n5.get("insufficient", True) and not n5["mean_bps"] > 0.0:
            failures.append(f"F10 group-neutral spread 5D {n5['mean_bps']:.2f}bps <= 0")
    t1 = to.get("1", {})
    if t1.get("n_transitions", 0) >= MIN_PERIODS:
        if not t1["q1_turnover"] <= 0.60 or not t1["q5_turnover"] <= 0.60:
            failures.append(f"F11 turnover 1D Q1={t1['q1_turnover']:.3f} Q5={t1['q5_turnover']:.3f} > 0.60")
        if not t1["rank_autocorr"] >= 0.30:
            failures.append(f"F12 rank-autocorr 1D {t1['rank_autocorr']:.3f} < 0.30")
    else:
        insuff = True
    verdict = "INSUFFICIENT_DATA" if insuff else ("FAIL" if failures else "PASS")
    return {"metrics": {"ic": ic, "ic_group_neutral": ic_gn, "quantile_returns": qr,
                        "spread": sp, "spread_group_neutral": sp_gn, "turnover": to,
                        "horizons": [int(h) for h in horizons], "quantiles": N_QUANTILES,
                        "group_neutral_available": bool(group_map)},
            "verdict": verdict, "failures": failures}
```

### Diff 2 — `src/backtest/metrics.py` (append; keep existing functions untouched)

```diff
--- a/src/backtest/metrics.py
+++ b/src/backtest/metrics.py
@@
     mean = returns_series.mean()
     return float((mean / downside_std) * np.sqrt(periods))
+
+
+def factor_ic_summary(ic_values, horizon=5):
+    """Thin re-export of factor_profiling.ic_summary for callers importing from metrics."""
+    from src.backtest.factor_profiling import ic_summary as _ic
+    import pandas as pd
+    rows = [{"date": i, "ic": float(v)} for i, v in enumerate(ic_values or [])]
+    return _ic({str(int(horizon)): rows})
+
+
+def quintile_spread_sharpe(spread_series, periods=252):
+    """Spread Sharpe via the single safe_sharpe primitive (no duplicate guards)."""
+    from src.backtest.factor_profiling import HORIZONS as _H  # noqa: F401 (docs link)
+    return safe_sharpe(spread_series, periods=periods)
```

Rationale: existing callers already import from `src.backtest.metrics`; avoids touching their import sites while keeping formulas in one tested module.

### Diff 3 — `src/ops/preregistration.py::record_evaluation` (additive factor-gate check)

```diff
--- a/src/ops/preregistration.py
+++ b/src/ops/preregistration.py
@@ def record_evaluation(spec_path, verdict, cycle=None, eval_path=None, registry_path=..., docs_dir=...):
+    # --- Factor-profiling pre-gate (alphalens-adopt 2026-09-09, additive) ---
+    # A PASS verdict requires a PASS factor profile generated by
+    # src/backtest/factor_profiling.evaluate_factor (see scripts/run_full_backtest.py --factor-profile).
+    # FAIL / HONEST_ABANDON verdicts are recorded unchanged.
+    if verdict == "PASS":
+        _fp = _load_factor_profile(spec_path, eval_path, docs_dir)  # returns dict|None
+        if _fp is None:
+            raise ValueError(
+                "record_evaluation PASS blocked: no factor_profile found. "
+                "Generate one via `python scripts/run_full_backtest.py --factor-profile <csv>` "
+                "or place results/factor_profile_<family>.json and reference it as "
+                "`factor_profile_ref` in the spec.")
+        if _fp.get("verdict") != "PASS":
+            raise ValueError(
+                f"record_evaluation PASS blocked: factor_verdict={_fp.get('verdict')} "
+                f"failures={_fp.get('failures', [])}. Revise factor or record HONEST_ABANDON.")
```

Helper `_load_factor_profile` (new, ~15 lines in same file): checks `spec['factor_profile_ref']`, then `results/factor_profile_<family>.json`, then `eval_payload['factor_profile']`; returns parsed dict or None. No change to `freeze_preregistration`; no registry write here (that stays human-gated per hunt protocol §5).

### Diff 4 — `scripts/hunt_runner.py::do_collect` (additive checklist lines)

```diff
--- a/scripts/hunt_runner.py
+++ b/scripts/hunt_runner.py
@@ def do_collect(args):
             if 'eval_records' not in spec:
                 missing_items.append("Missing eval_records in spec")
             else:
                 eval_file = spec['eval_records']
                 if not os.path.exists(eval_file) and not os.path.exists(os.path.join(results_dir, os.path.basename(eval_file))):
                      missing_items.append(f"Eval records not found at {eval_file} or in results/")
+
+            # --- Factor-profiling pre-registry checklist (alphalens-adopt 2026-09-09) ---
+            import json as _json
+            _fp_path = spec.get('factor_profile_ref') or os.path.join(
+                results_dir, f"factor_profile_{spec.get('family', 'unknown')}.json")
+            _alt = os.path.join(results_dir, os.path.basename(_fp_path)) if _fp_path else None
+            _found = _fp_path if _fp_path and os.path.exists(_fp_path) else (
+                _alt if _alt and os.path.exists(_alt) else None)
+            if _found is None:
+                missing_items.append(
+                    f"Missing factor_profile (alphalens gate): expected {_fp_path}. "
+                    "Generate via run_full_backtest --factor-profile before registry merge.")
+            else:
+                try:
+                    with open(_found) as _fh:
+                        _fp = _json.load(_fh)
+                    if _fp.get("verdict") != "PASS":
+                        missing_items.append(
+                            f"Factor profile verdict={_fp.get('verdict')} "
+                            f"failures={_fp.get('failures', [])} — not ready for registry merging.")
+                except Exception as _e:  # noqa: BLE001 — checklist must never crash collect
+                    missing_items.append(f"Factor profile at {_found} unreadable ({_e}).")
```

Behavior preserved: still prints `✅ Valid Spec` + missing items / `Ready for registry merging (human-gated step)`; still refuses to write the registry itself; still moves malformed specs to `rejected/`.

### Diff 5 — `scripts/run_full_backtest.py` (additive optional flag; ranking order unchanged when absent)

```diff
--- a/scripts/run_full_backtest.py
+++ b/scripts/run_full_backtest.py
@@ def main():
+    # --- Factor-profile emitter (alphalens-adopt 2026-09-09, opt-in) ---
+    # python scripts/run_full_backtest.py --factor-profile factor_long.csv [--group-map groups.json]
+    # factor_long.csv columns: date, asset, factor[, group]. Prices reuse preloaded stock_dfs.
+    # Emits results/factor_profile_<family>.json via factor_profiling.evaluate_factor.
+    # Ranking path untouched when flag absent.
```

Implementation (~30 lines in `main`, argparse `--factor-profile`, `--group-map`, `--factor-family`): loads CSV, calls `build_factor_frame` with the already-preloaded `stock_dfs`, calls `evaluate_factor`, writes JSON with `{verdict, failures, metrics, factor_csv_sha, data_range, generated_at}`. Fail-closed: any error → non-zero exit with message, never a silent PASS.

## 5. Why this is safe for this repo

- Preserves fail-closed mandate: every new function returns typed empties on bad input; `evaluate_factor` returns `INSUFFICIENT_DATA → FAIL` path instead of raising; `collect`/`record_evaluation` additions are additive checks that block promotion, never auto-promote.
- Preserves no-lookahead: forward returns use `Close[d+h]/Close[d]−1` on closed bars only; factor frame joins factor at `d` to returns starting at `d` (no `d−h` leakage); warmup NaN never 0-filled; T+1 execution and `TEARSHEET_ENGINE` guard untouched.
- Preserves edge gate: new factor gate sits BEFORE the existing expensive gates (pre-reg → FACTOR → WF → permutation → DSR → registry). Existing `WalkForwardValidator` (OOS≥0.40, consistency<1.5, ≥3 windows, 2/3 positive) and `PermutationValidator` (p<0.01) thresholds unchanged; no `strategies/registry.json` entry proposed.
- Cost: zero new deps (pandas/numpy/scipy already pinned); no network; no `evolve_real.py` import; `bandit`-clean surface (no eval/pickle/subprocess; bounded series output).
- Non-duplication: spread Sharpe reuses `safe_sharpe`; IC t-stat uses `scipy.stats.t` (already-transitive via statsmodels/scipy); quantile cut uses `pd.qcut` with rank-fallback for low-unique dates.

## 6. Test plan

New file `tests/backtesting/test_factor_profiling.py` (offline, deterministic, no network; single-file serial per repo policy):

1. `test_forward_returns_point_in_time` — synthetic 10-bar Close series; assert `fwd_1[d] == C[d+1]/C[d]−1`, last-h rows NaN, no forward-fill.
2. `test_rank_ic_perfect_factor` — factor monotonically increasing in forward returns → RankIC ≈ 1.0 per date; `ic_summary` mean ≈ 1, `frac_positive == 1`.
3. `test_rank_ic_null_factor` — seeded random factor vs random returns (n=60 dates × 10 assets) → `|mean| < 0.1`, verdict FAIL via F1/F2 (guards against vacuous PASS).
4. `test_ic_summary_matches_hand_calc` — hand-computed mean/std/IR/t/p on fixed IC vector vs `ic_summary` (tolerance 1e-9); `insufficient=True` when n < 20.
5. `test_quantile_spread_and_monotonicity` — constructed frame with Q1..Q5 means −2,−1,0,+1,+2 bps → spread mean ≈ 4 bps, `monotonicity_rho ≈ 1.0`; inverted frame → rho ≈ −1 and F8 failure string present.
6. `test_group_neutral_kills_sector_mimic` — two groups where pooled IC > 0.02 but within-group IC ≈ 0 → pooled PASS-track but `ic_group_neutral` FAILs F9 and `evaluate_factor(..., group_map=...)` verdict FAIL with `F9` in failures.
7. `test_turnover_bounds` — frozen-quantile frame → turnover ≈ 0, autocorr ≈ 1; pure-churn frame (random reshuffle per date) → turnover > 0.6 / autocorr < 0.3 and F11/F12 failures present.
8. `test_horizon_sign_flip_blocks` — frame engineered with +IC at 5D but −IC at 1D/10D → verdict FAIL with `sign-flip` failure.
9. `test_insufficient_data_fail_closed` — 5-date frame → verdict `INSUFFICIENT_DATA`, never PASS; empty frame → typed empties, no raise.
10. `test_evaluate_factor_thresholds_end_to_end` — seeded passing frame (linear factor + noise, 60 dates × 12 assets, stable quantiles) → verdict PASS with all MUST rows satisfied; asserts every §3b MUST row programmatically.
11. `test_collect_checklist_blocks_without_profile` — `do_collect` on temp hunt dir with valid spec but no `factor_profile_*.json` → "Missing factor_profile" in missing items; with FAIL-profile JSON → verdict line in missing items; registry file untouched (assert bytes-identical before/after).
12. `test_record_blocks_pass_without_profile` — `record_evaluation(..., verdict="PASS")` with no profile raises `ValueError("no factor_profile")`; with FAIL profile raises `ValueError("factor_verdict=FAIL")`; `HONEST_ABANDON` records unchanged.

Commands (per AGENTS.md, single-file serial):

```
PYTHONPATH=. pytest tests/backtesting/test_factor_profiling.py -q
PYTHONPATH=. pytest tests/backtesting/test_validation.py -q
ruff check src/backtest/factor_profiling.py tests/backtesting/test_factor_profiling.py
bandit -r src/backtest/factor_profiling.py
git status --porcelain  # must show only new + listed files; evolve_real.py / registry.json / strategies/ untouched
```

Acceptance: 12/12 new tests pass, existing `test_validation.py::test_validation_main_execution` still passes, ruff + bandit clean, seeded PASS fixture verdict stable across runs (fixed seed, no wall-clock in profile JSON except `generated_at` display field excluded from verdict hash).

## 7. Rollout steps (for implementer, not done here)

1. Add Diff 1 (new module) → run new tests 1–10.
2. Add Diff 2 (metrics re-exports) → ruff/bandit.
3. Add Diff 5 (run_full_backtest flag) → generate one local `factor_profile_<family>.json` on cached CSVs (do NOT publish; `DATA_IS_MOCK` guard stays).
4. Add Diff 4 (collect checklist) → run test 11.
5. Add Diff 3 (record_evaluation gate) → run test 12.
6. Backfill profiles for any candidate currently awaiting registry merge; any promotion-motivated factor change (e.g. new sentiment normalization) requires fresh pre-reg + factor PASS + WF + permutation + DSR before registry entry.

## 8. References

- Upstream: `stefan-jansen/alphalens-reloaded` — `get_clean_factor_and_forward_returns` + `tears.create_full_tear_sheet` (returns/IC/turnover/grouped sections); `quantopian/alphalens tears.py` (`create_summary/returns/information/turnover/full_tear_sheet`); `performance.py` (`factor_information_coefficient`, `mean_information_coefficient`, turnover/autocorr); `alphalens.ml4trading.io` overview (1D/5D/10D tables, turnover rows, IC skew/kurtosis).
- Actual metrics: `src/backtest/metrics.py:1-43`.
- Actual validation: `src/backtest/validation.py:28-33 (engine guard), 91-156 (in-sample), 159-261 (walk-forward), 264-378 (SPA + quantstats block, p>0.01/0.05 fail line 318)`.
- Actual engines: `src/backtest/run_historic_backtest.py:11-231 (T+1, ATR slippage, FRED regime, spy/excess per trade)`, `walk_forward_engine.py:20-23,42-47 (OOS≥0.40/conjunction)`, `permutation_tester.py:18,127-129 (p<0.01)`, `validators/statistical.py:70-135 (SPA/CPCV)`, `defend/trial_ledger.py:388-422 (DSR)`.
- Actual gates/wiring: `scripts/hunt_runner.py:151-207 (collect)`, `scripts/preregister.py:18-24` + `src/ops/preregistration.py:22,59 (freeze/record)`, `src/ops/strategy_registry.py:15 (validate_spec)`, `scripts/run_full_backtest.py:18-82 (_compute_trade_metrics)`, `scripts/comprehensive_backtest_report.py:498-602 (calculate_metrics)`.
- Companion adopts (same `_deliverables/` series): `pyfolio-adopt-2026-09-09.md` (trade-level risk tearsheet — different layer from this factor-level screen), `qlib-adopt-2026-09-09.md` (§1c IC gap — this proposal implements the IC/IR harness it calls for).
