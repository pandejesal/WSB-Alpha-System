# quantstats Adoption Study — Tearsheet / Metric Additions for Paper-Gate Evidence

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint.
Scope: `ranaroussi/quantstats` (50+ stats, Monte Carlo drawdown simulation, HTML tearsheets vs SPY/QQQ) vs ACTUAL repo reporting: `scripts/comprehensive_backtest_report.py` + `src/backtest/metrics.py` + `src/backtest/validation.py` quantstats block (+ `src/alpha/reporting.py`).
Workdir: repo root only.

## 1. Upstream assumed vs actual (verified by read + live API probe)

Upstream `ranaroussi/quantstats==0.0.81` (pinned in `requirements.txt:119`, installed — probed live):

- `qs.stats` exposes ~70 callables (probed `dir(qs.stats)`): `sharpe, sortino, adjusted_sortino, probabilistic_sharpe_ratio, probabilistic_sortino_ratio, probabilistic_ratio, smart_sharpe/smart_sortino, omega, tail_ratio, gain_to_pain_ratio, cpc_index, common_sense_ratio, calmar, recovery_factor, serenity_index, ulcer_index, ulcer_performance_index, risk_of_ruin, kelly_criterion, value_at_risk, conditional_value_at_risk/expected_shortfall, volatility, downside_risk?, skew, kurtosis, cagr, expected_return, geometric_mean, exposure, best/worst, consecutive_wins/losses, win_rate, avg_win/avg_loss, payoff_ratio/profit_factor/profit_ratio/win_loss_ratio, outlier_win_ratio/outlier_loss_ratio, payoffs?, information_ratio, r_squared/r2, greeks/rolling_greeks/treynor_ratio, rolling_sharpe/rolling_sortino/rolling_volatility, to_drawdown_series/drawdown_details/max_drawdown, monthly_returns/distribution, montecarlo/montecarlo_sharpe/montecarlo_cagr/montecarlo_drawdown, autocorr_penalty, compare`.
- `qs.reports.html(returns, benchmark=None, rf=0.0, title, output, compounded=True, periods_per_year=252, match_dates=True)` — full tearsheet (cumulative, drawdown, monthly heatmap, rolling Sharpe/vol, distribution, drawdown details, vs-benchmark excess). Passing `benchmark=<Series>` avoids all network; passing a ticker string triggers download — MUST NOT do that (offline/CI-safe rule).
- Monte Carlo: `qs.stats.montecarlo_drawdown(returns, sims=1000, seed=None)` (probed signature) + `montecarlo_sharpe/cagr` — simulates resampled paths, returns distribution of max-DD / Sharpe / CAGR. Direct paper-gate value: answers "is this Sharpe/DD luck?" without a new validator.

Actual repo (read):

- `src/backtest/metrics.py:1-43` — ONLY `safe_sharpe` + `safe_sortino` (fillna(0), `std<1e-12→0.0`). Consumed by `comprehensive_backtest_report.py:536-545,629`, `run_full_backtest.py`, `validation.py:78,88`. No omega/tail/PSR/ulcer/kelly/IR wrappers.
- `scripts/comprehensive_backtest_report.py:498-602` `calculate_metrics(portfolio, spy_df)` — deposit-adjusted daily `return` (`deposit_diff` mask, lines 509-512), then point metrics only: `total_return_pct, cagr, max_drawdown_pct+date, volatility, sharpe, sortino, calmar, var_95/99, cvar_95, win_rate, profit_factor, avg_holding, streaks, trades_per_year`. Gaps: (a) `spy_df` param ACCEPTED BUT UNUSED — no beta/alpha/IR/tracking-error/treynor/R²/up-down capture; (b) drawdown single scalar, no `drawdown_details`/duration/underwater series; (c) no skew/kurtosis, omega, tail ratio, gain-to-pain, ulcer/serenity, PSR, Kelly, risk-of-ruin, exposure, outlier ratios, recovery factor; (d) no rolling Sharpe/vol; (e) no Monte Carlo; (f) manual VaR/CVaR via `np.percentile` instead of `qs.stats.var/cvar`.
- `scripts/comprehensive_backtest_report.py:691-727,918-928` — SPY buy-and-hold `benchmark_history` + `benchmark_comparison` (return/CAGR/Sharpe/maxDD only). No SPY *returns Series* passed to any tearsheet; QQQ absent entirely.
- `src/backtest/validation.py:323-378` — ONLY existing quantstats call: `qs.reports.html(returns_series, output=...)` with THREE defects: (1) `returns_series = groupby('post_date')['return'].sum()` — sparse trade-day series, zeros on flat days missing → rolling/drawdown/duration wrong; (2) NO `benchmark=`, NO `rf=` (defaults `rf=0.0` while repo mandate is fixed 2.9% — `comprehensive_backtest_report.py:533,621`); (3) persists only `var_95/99, cvar_95, max_dd_duration` back into `backtest_report.json:portfolio_summary`, discards the other 50+ stats the HTML already computed. Guarded correctly by `TEARSHEET_ENGINE=rb` loud-fail (lines 28-33) — keep.
- `src/alpha/reporting.py:15-21` `PerformanceReporter.generate_tearsheet(strategy_returns, benchmark_returns=None, ...)` — correct signature (`benchmark=` passthrough, try/except→None) but: default `benchmark_returns=None` (no SPY/QQQ wired by any caller — grep: zero callers), no `rf=`, no `match_dates` note, default output dir `experiments/reports` while validation writes `docs/reports/strategy-<ts>.html`.

Conclusion: do NOT add a new engine or dep. Add a thin fail-closed `quantstats` adapter (pure wrapper, offline-safe), wire it into the two report paths that already own daily returns + SPY curve, and align benchmarks (SPY always, QQQ where cheap). Reporting-only; no gate-threshold or registry change.

## 2. Proposal — which stats, where wired, benchmark alignment

New module `src/backtest/qs_adapter.py` (single choke point; everything else is additive wiring):

| # | Stat(s) | qs call | Wired into | Paper-gate value |
|---|---|---|---|---|
| S1 | Full HTML tearsheet vs benchmark | `qs.reports.html(daily_rets, benchmark=spy_rets, rf=0.029, match_dates=True)` | `validation.py` (fix sparse→daily + add benchmark/rf); `reporting.py` (pass SPY) | One artifact reviewers open: cumulative/excess, monthly heatmap, rolling Sharpe, underwater, distribution — replaces "trust the JSON" |
| S2 | Benchmark-relative: IR, R², beta/alpha, Treynor, TE, up/down capture | `qs.stats.information_ratio/greeks/treynor_ratio/r_squared`, TE=`active.std()*sqrt(252)` | `comprehensive_backtest_report.calculate_metrics` (uses currently-unused `spy_df`) → `risk_tearsheet.tracking` | Proves excess vs SPY is skill not beta; QQQ second benchmark in `main()` |
| S3 | Significance: PSR + adjusted Sortino | `qs.stats.probabilistic_sharpe_ratio(rf=0.029)`, `adjusted_sortino`, `smart_sharpe` | `calculate_metrics` + validation `metrics` dict | Kills "Sharpe 1.2 on 40 trades" promotions; complements DSR/permutation gate |
| S4 | Tail: Omega, tail ratio, gain-to-pain, CPC, outlier win/loss | `qs.stats.omega/tail_ratio/gain_to_pain_ratio/cpc_index/outlier_win_ratio/outlier_loss_ratio` | `calculate_metrics` → `risk_tearsheet.tail` | Catches lottery-ticket strategies high Sharpe hides |
| S5 | Pain: Ulcer, Serenity, recovery factor, drawdown_details | `qs.stats.ulcer_index/serenity_index/recovery_factor/drawdown_details/to_drawdown_series` | `calculate_metrics` (replaces scalar-only DD) + validation (replaces bare `days.max()`) | Duration-aware DD; `current_underwater` blocks "recovered on paper" claims |
| S6 | Survival: Kelly, risk-of-ruin, exposure, VaR/CVaR via qs | `qs.stats.kelly_criterion/risk_of_ruin/exposure/value_at_risk/conditional_value_at_risk` | `calculate_metrics` (replaces hand-rolled `np.percentile` lines 549-552) | Position-sizing sanity + ruin probability on tiny ($100+50/q) accounts |
| S7 | Stability: rolling Sharpe/Sortino/vol + skew/kurt + monthly | `qs.stats.rolling_sharpe/rolling_sortino/rolling_volatility/skew/kurtosis/monthly_returns` | `calculate_metrics` summaries (min/median/current/frac<0) + report JSON | Exposes regime-decay the single full-sample Sharpe hides |
| S8 | Monte Carlo drawdown/ShT/CAGR | `qs.stats.montecarlo_drawdown/montecarlo_sharpe/montecarlo_cagr(sims=1000, seed=42)` | validation `metrics` + report `risk_tearsheet.montecarlo` (seeded, bounded sims) | "P(mDD>20%) under resampling = X" — cheapest anti-luck evidence before paper |

Benchmark alignment rule (all three sites):

1. `daily_rets` = deposit-adjusted equity pct (existing mask) reindexed to full SPY trading calendar, flat days = 0.0 (fixes validation sparse-series bug).
2. `spy_rets` = `spy_df["Close"].pct_change()` reindexed to same calendar (already built in `comprehensive_backtest_report.main:691-727`; build once in `validation.main` from preloaded `spy_close`).
3. `qqq_rets` = same for QQQ ONLY in `comprehensive_backtest_report.main` (download one extra symbol next to SPY line 40; fallback CSV `market_data_2019_2026/ohlcv/QQQ.csv` mirroring SPY fallback). Validation stays SPY-only (keep runtime bounded).
4. Always call `qs.reports.html(..., benchmark=spy_rets, rf=0.029, match_dates=True)` — never a ticker string (no download), never default `rf=0.0`.
5. Every qs call wrapped try/except → typed zero/empty fallback; tearsheet never raises into ranking/gates (fail-closed).

## 3. Exact diffs proposed (additive; no engine/signal/sizing/registry change)

### Diff 0 — NEW `src/backtest/qs_adapter.py` (~150 lines, full file)

Offline-safe choke point. Deposit-calendar helper fixes the sparse-series bug in one place. All fns fail-closed.

```python
"""quantstats adapter (offline-safe, fail-closed).

Wraps ranaroussi/quantstats so call sites never touch qs directly:
- never passes ticker strings (no download), always Series + match_dates
- always rf=0.029 (repo blended mandate), seeded Monte Carlo
- every helper returns typed zero/empty on short/empty input, never raises
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RF = 0.029
PERIODS = 252
MC_SIMS = 1000
MC_SEED = 42


def to_daily_calendar(trade_rets: pd.Series, calendar: pd.DatetimeIndex) -> pd.Series:
    """Spread sparse trade-day sums onto full trading calendar (flat days 0.0)."""
    r = pd.Series(trade_rets, dtype=float)
    r.index = pd.to_datetime(r.index)
    cal = pd.DatetimeIndex(sorted(set(pd.DatetimeIndex(calendar)) | set(r.index)))
    return r.reindex(cal).fillna(0.0)


def _qs():
    import quantstats as qs  # local import: keeps module importable without dep
    return qs


def full_stats(daily: pd.Series, bench: pd.Series | None = None) -> dict:
    qs = _qs()
    r = pd.Series(daily, dtype=float).fillna(0.0)
    if len(r) < 20:
        return {}
    out: dict = {}
    try:
        b = pd.Series(bench, dtype=float).fillna(0.0) if bench is not None else None
        out["sharpe_qs"] = float(qs.stats.sharpe(r, rf=RF))
        out["sortino_qs"] = float(qs.stats.sortino(r, rf=RF))
        out["adjusted_sortino"] = float(qs.stats.adjusted_sortino(r, rf=RF))
        out["psr"] = float(qs.stats.probabilistic_sharpe_ratio(r, rf=RF))
        out["smart_sharpe"] = float(qs.stats.smart_sharpe(r, rf=RF))
        out["omega"] = float(qs.stats.omega(r, rf=RF))
        out["tail_ratio"] = float(qs.stats.tail_ratio(r))
        out["gain_to_pain"] = float(qs.stats.gain_to_pain_ratio(r))
        out["cpc"] = float(qs.stats.cpc_index(r))
        out["calmar_qs"] = float(qs.stats.calmar(r))
        out["recovery_factor"] = float(qs.stats.recovery_factor(r))
        out["ulcer"] = float(qs.stats.ulcer_index(r))
        out["serenity"] = float(qs.stats.serenity_index(r))
        out["kelly"] = float(qs.stats.kelly_criterion(r))
        out["risk_of_ruin"] = float(qs.stats.risk_of_ruin(r))
        out["exposure"] = float(qs.stats.exposure(r))
        out["var_95_qs"] = float(qs.stats.value_at_risk(r))
        out["cvar_95_qs"] = float(qs.stats.conditional_value_at_risk(r))
        out["skew"] = float(qs.stats.skew(r))
        out["kurtosis"] = float(qs.stats.kurtosis(r))
        out["best_day"] = float(qs.stats.best(r))
        out["worst_day"] = float(qs.stats.worst(r))
        out["win_rate_qs"] = float(qs.stats.win_rate(r))
        out["profit_factor_qs"] = float(qs.stats.profit_factor(r))
        out["payoff_ratio"] = float(qs.stats.payoff_ratio(r))
        out["outlier_win"] = float(qs.stats.outlier_win_ratio(r))
        out["outlier_loss"] = float(qs.stats.outlier_loss_ratio(r))
        out["max_dd_qs"] = float(qs.stats.max_drawdown(r))
        dd = qs.stats.drawdown_details(r)
        out["max_dd_days"] = int(dd["days"].max()) if dd is not None and not dd.empty else 0
        try:
            rs = qs.stats.rolling_sharpe(r, rf=RF)
            rs = pd.Series(rs).dropna()
            out["rolling_sharpe"] = {"min": float(rs.min()), "median": float(rs.median()),
                                     "current": float(rs.iloc[-1]), "frac_negative": float((rs < 0).mean())} if not rs.empty else {}
        except Exception:
            out["rolling_sharpe"] = {}
        if b is not None and len(b) >= 20:
            n = min(len(r), len(b))
            rr, bb = r.iloc[-n:], b.iloc[-n:]
            out["information_ratio"] = float(qs.stats.information_ratio(rr, bb))
            try:
                g = qs.stats.greeks(rr, bb)
                out["beta"] = float(g["beta"]); out["alpha"] = float(g["alpha"])
            except Exception:
                out["beta"] = 0.0; out["alpha"] = 0.0
            try:
                out["treynor"] = float(qs.stats.treynor_ratio(rr, bb))
            except Exception:
                out["treynor"] = 0.0
            try:
                out["r_squared"] = float(qs.stats.r_squared(rr, bb))
            except Exception:
                out["r_squared"] = 0.0
            active = rr.reset_index(drop=True) - bb.reset_index(drop=True)
            out["tracking_error_pct"] = float(active.std() * np.sqrt(PERIODS)) * 100.0
    except Exception:
        return out  # partial dict is fine; caller merges additively
    return out


def montecarlo(daily: pd.Series, sims: int = MC_SIMS, seed: int = MC_SEED) -> dict:
    try:
        qs = _qs()
        r = pd.Series(daily, dtype=float).fillna(0.0)
        if len(r) < 60:
            return {"note": "n<60, skipped", "sims": 0}
        dd = qs.stats.montecarlo_drawdown(r, sims=sims, seed=seed)
        sh = qs.stats.montecarlo_sharpe(r, sims=sims, seed=seed)
        cg = qs.stats.montecarlo_cagr(r, sims=sims, seed=seed)
        import numpy as _np
        return {"sims": int(sims), "seed": int(seed),
                "mc_maxdd_p50": float(_np.percentile(dd, 50)), "mc_maxdd_p95": float(_np.percentile(dd, 95)),
                "mc_sharpe_p5": float(_np.percentile(sh, 5)), "mc_sharpe_p50": float(_np.percentile(sh, 50)),
                "mc_cagr_p5": float(_np.percentile(cg, 5)), "mc_cagr_p50": float(_np.percentile(cg, 50))}
    except Exception:
        return {}


def html_tearsheet(daily: pd.Series, bench: pd.Series | None, path: str, title: str = "Strategy Tearsheet") -> str | None:
    try:
        qs = _qs()
        qs.reports.html(pd.Series(daily).fillna(0.0), benchmark=bench, rf=RF,
                        title=title, output=path, match_dates=True)
        return path
    except Exception:
        return None
```

### Diff 1 — `src/backtest/metrics.py` (append; existing 2 fns untouched)

```diff
--- a/src/backtest/metrics.py
+++ b/src/backtest/metrics.py
@@
     mean = returns_series.mean()
     return float((mean / downside_std) * np.sqrt(periods))
+
+
+def qs_full_stats(returns_series, benchmark_series=None):
+    """Thin re-export of qs_adapter.full_stats (keeps existing import sites)."""
+    from src.backtest.qs_adapter import full_stats as _fs
+    try:
+        return _fs(returns_series, benchmark_series)
+    except Exception:
+        return {}
+
+
+def qs_montecarlo(returns_series, sims=1000, seed=42):
+    """Thin re-export of qs_adapter.montecarlo."""
+    from src.backtest.qs_adapter import montecarlo as _mc
+    try:
+        return _mc(returns_series, sims=sims, seed=seed)
+    except Exception:
+        return {}
```

### Diff 2 — `scripts/comprehensive_backtest_report.py` (`calculate_metrics`, additive)

```diff
--- a/scripts/comprehensive_backtest_report.py
+++ b/scripts/comprehensive_backtest_report.py
@@ def calculate_metrics(portfolio, spy_df):
      hist_df['deposit_diff'] = hist_df['deposits'].diff().fillna(0)
      mask = hist_df['deposit_diff'] > 0
      if mask.any():
          hist_df.loc[mask, 'return'] = (hist_df.loc[mask, 'equity'] - hist_df.loc[mask, 'deposit_diff'] - hist_df['equity'].shift(1).loc[mask]) / hist_df['equity'].shift(1).loc[mask]
+
+    # --- quantstats supplement (additive; legacy keys below unchanged) ---
+    try:
+        from src.backtest import qs_adapter as _qs
+        _spy_rets = None
+        if spy_df is not None and not spy_df.empty and "Close" in spy_df.columns:
+            _spy_rets = spy_df["Close"].pct_change().reindex(hist_df.index).fillna(0.0)
+        _qs_stats = _qs.full_stats(hist_df['return'], _spy_rets)
+        _qs_mc = _qs.montecarlo(hist_df['return'])
+    except Exception:
+        _qs_stats, _qs_mc = {}, {}
 
      # Return metrics ... (existing block unchanged)
 @@
          "avg_win": avg_win,
-        "avg_loss": avg_loss
+        "avg_loss": avg_loss,
+        "qs_stats": _qs_stats,        # S2-S7 (IR/beta/PSR/omega/ulcer/Kelly/rolling/...)
+        "qs_montecarlo": _qs_mc,      # S8 (seeded resampling; n<60 skipped)
      }
```

`main()` additions (same file): after `spy_metrics = calculate_metrics(...)` add QQQ benchmark + surface in report JSON:

```diff
@@
     spy_metrics = calculate_metrics(spy_benchmark_portfolio, spy_df)
+    # QQQ second benchmark (mirrors SPY download line 40 + fallback; cheap, aligned)
+    try:
+        qqq_data = yf.download('QQQ', start='2018-01-01', end=end_date, auto_adjust=True)
+        qqq_close = qqq_data['Close'] if 'Close' in qqq_data.columns else None
+    except Exception:
+        qqq_close = None
 @@
         "benchmark_comparison": {
             ...
             "strategy_max_dd_pct": best_metrics["max_drawdown_pct"],
-            "spy_max_dd_pct": spy_metrics["max_drawdown_pct"]
+            "spy_max_dd_pct": spy_metrics["max_drawdown_pct"],
+            "qs_stats": best_metrics.get("qs_stats", {}),
+            "qs_montecarlo": best_metrics.get("qs_montecarlo", {}),
         },
```

Note: `spy_df` finally consumed (fixes "accepted but unused"); QQQ optional — `None` tolerated, SPY stays the binding benchmark.

### Diff 3 — `src/backtest/validation.py` (fix sparse series + benchmark + persist)

```diff
--- a/src/backtest/validation.py
+++ b/src/backtest/validation.py
@@
         real_trades = TEARSHEET_ENGINE.run_backtest(custom_posts_df=posts_df, stock_dfs_preloaded=stock_dfs, spy_close_preloaded=spy_close)
         if len(real_trades) > 0:
+            from src.backtest import qs_adapter as _qs
             real_trades_sorted = real_trades.sort_values(by="post_date").reset_index(drop=True)
-            returns_series = real_trades_sorted.groupby('post_date')['return'].sum()
-            returns_series.index = pd.to_datetime(returns_series.index)
+            # Daily calendar (was: sparse trade-day sums — rolling/DD wrong)
+            _trade_rets = real_trades_sorted.groupby(pd.to_datetime(real_trades_sorted['post_date']))['return'].sum()
+            _cal = pd.DatetimeIndex(sorted(set(pd.DatetimeIndex(spy_close.index)) | set(_trade_rets.index)))
+            returns_series = _qs.to_daily_calendar(_trade_rets, _cal)
+            _spy_rets = pd.Series(spy_close.pct_change().fillna(0.0)).reindex(returns_series.index).fillna(0.0)
 
             os.makedirs("docs/reports", exist_ok=True)
             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005 - Timezone not critical for this usage
             report_path = f"docs/reports/strategy-{timestamp}.html"
-            qs.reports.html(returns_series, output=report_path)
+            _qs.html_tearsheet(returns_series, _spy_rets, report_path)
             print(f"Tearsheet saved to: {report_path}")
 
-            # Calculate extra metrics: VaR, CVaR, Max DD Duration
-            confidence_level = 0.95
-            var_95 = np.percentile(returns_series, (1 - confidence_level) * 100)
-            cvar_95 = returns_series[returns_series <= var_95].mean()
-
-            var_99 = np.percentile(returns_series, (1 - 0.99) * 100)
-
-            try:
-                dd_info = qs.stats.drawdown_details(returns_series)
-                max_dd_duration = dd_info['days'].max() if not dd_info.empty else 0
-            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
-                logger.warning(f"Error computing drawdown for WFO fold: {e}")
-                max_dd_duration = 0
+            # quantstats stats (keep legacy keys; append full set + Monte Carlo)
+            import quantstats as qs
+            _full = _qs.full_stats(returns_series, _spy_rets)
+            var_95 = float(_full.get("var_95_qs", float(np.percentile(returns_series, 5))))
+            var_99 = float(np.percentile(returns_series, 1))
+            cvar_95 = float(_full.get("cvar_95_qs", float(returns_series[returns_series <= np.percentile(returns_series, 5)].mean())))
+            max_dd_duration = int(_full.get("max_dd_days", 0))
 
             metrics = {
                 "var_95": float(var_95),
                 "var_99": float(var_99),
                 "cvar_95": float(cvar_95),
-                "max_dd_duration": int(max_dd_duration)
+                "max_dd_duration": int(max_dd_duration),
+                "qs_stats": _full,
+                "qs_montecarlo": _qs.montecarlo(returns_series),
             }
```

Legacy `var_95/99, cvar_95, max_dd_duration` keys preserved (same names/units for existing readers); `TEARSHEET_ENGINE` guard untouched.

### Diff 4 — `src/alpha/reporting.py` (wire benchmark + rf; 3 lines)

```diff
--- a/src/alpha/reporting.py
+++ b/src/alpha/reporting.py
@@
-    def generate_tearsheet(self, strategy_returns: pd.Series, benchmark_returns: pd.Series = None, title: str = "Strategy"):
+    def generate_tearsheet(self, strategy_returns: pd.Series, benchmark_returns: pd.Series | None = None, title: str = "Strategy"):
         output_file = os.path.join(self.output_dir, f"{title.replace(' ', '_').lower()}_tearsheet.html")
         try:
-            qs.reports.html(strategy_returns, benchmark=benchmark_returns, title=title, output=output_file)
+            qs.reports.html(pd.Series(strategy_returns).fillna(0.0), benchmark=benchmark_returns,
+                            rf=0.029, title=title, output=output_file, match_dates=True)
             return output_file
```

Caller rule (no diff needed now): pass SPY returns Series (never `None` in paper-gate path, never a ticker string).

### Diff 5 — `requirements.txt` (comment only, no version change)

```diff
  quantstats==0.0.81
+ # NOTE(quantstats-adopt 2026-09-09): pinned qs is the tearsheet engine; no new
+ # dep. All calls via src/backtest/qs_adapter.py (Series-only, rf=0.029,
+ # match_dates=True). matplotlib/seaborn already present for qs.reports.html.
```

## 4. Safety / gate notes

- Fail-closed: every qs call in try/except with typed fallback; adapter import inside fns so missing dep → `{}`/`None`, never breaks ranking, `calculate_metrics`, or `validation.main`.
- No-lookahead: pure functions over executed returns; T+1 (`run_historic_backtest.py:59`, `engine_base.py:18-36`) and `TEARSHEET_ENGINE` loud-fail untouched.
- Edge gate unchanged: reporting-only; `WalkForwardValidator` / `PermutationValidator` thresholds, DSR, registry promotion path untouched. MC `sims=1000/seed=42` bounded; `n<60→skip`.
- `bandit`-clean surface: no eval/pickle/network/subprocess; HTML written to `docs/reports/` only.
- `DATA_IS_MOCK` publish guard (`comprehensive_backtest_report.py:962-964`) stays authoritative.

## 5. Test plan (offline, deterministic, no network)

New `tests/backtesting/test_qs_adapter.py`:

1. `test_calendar_spreads_sparse` — sparse `{d1:+1%, d3:-0.5%}` + 5-day cal → len 5, flat days 0.0, index == calendar.
2. `test_full_stats_known` — constant +0.001 daily (252d): `sharpe_qs` large positive, `max_dd_qs==0`, `win_rate_qs==1.0`; alternating ±0.01: `sharpe≈0`, `tail_ratio≈1`.
3. `test_full_stats_short_empty_fail_closed` — len 5 / empty → `{}` no raise; `montecarlo` n<60 → `sims==0` skip note.
4. `test_benchmark_perfect_tracker` — strat==bench → `tracking_error_pct==0`, `beta≈1`, `information_ratio==0`; short bench (<20) → tracking keys absent, no raise.
5. `test_psr_direction` — high-Sharpe long series `psr` > low-Sharpe series `psr` (monotonic sanity, not exact value).
6. `test_montecarlo_seeded_stable` — same series twice `seed=42` → identical `mc_maxdd_p50`; `mc_maxdd_p95 >= mc_maxdd_p50 >= 0`-as-drawdown convention checked.
7. `test_html_offline` (tmp_path) — `html_tearsheet(daily, spy, tmp.html)` returns path, file exists, size>0; `benchmark="SPY"` string never used (assert adapter source has no ticker-string branch).
8. `test_calculate_metrics_additive` — 5-day fake `Portfolio` + SPY frame through `calculate_metrics`: legacy keys (`sharpe, max_drawdown_pct, win_rate, var_95`) unchanged AND `qs_stats`/`qs_montecarlo` present.
9. `test_validation_regression_calendar` — sparse trade frame through `to_daily_calendar` yields `len == len(calendar)` (old groupby length < calendar — the bug).
10. `test_reporting_passthrough` — monkeypatch `qs.reports.html`, call `generate_tearsheet` with SPY Series, assert kwargs `rf==0.029`, `match_dates is True`, `benchmark is <Series>`.

Commands (per AGENTS.md):

```
PYTHONPATH=. pytest tests/backtesting/test_qs_adapter.py -q
PYTHONPATH=. pytest tests/backtesting/test_validation.py -q
ruff check src/backtest/qs_adapter.py tests/backtesting/test_qs_adapter.py
bandit -r src/backtest/qs_adapter.py
```

Acceptance: 10/10 new pass; existing validation test passes (mocked `rb.run_backtest`); ruff+bandit clean; legacy `calculate_metrics` keys byte-identical on fixture; `git status --porcelain` shows only `src/backtest/qs_adapter.py`, `tests/...`, listed edits — never `evolve_real.py` / `strategies/registry.json` / `strategies/`.

## 6. Rollout (implementer, not done here)

1. Add Diff 0 → tests 1-7.
2. Add Diff 1 → ruff/bandit.
3. Add Diff 2 → test 8 + local regen on cached CSVs (do NOT publish; `DATA_IS_MOCK` guard stays).
4. Add Diff 3 → test 9 + existing validation test; confirm HTML now shows SPY-excess section.
5. Add Diff 4-5 → test 10.
6. Any sizing/stop change motivated by tearsheet (e.g. ulcer/MC-DD rule) → pre-register + walk-forward + permutation + DSR before any registry entry.

## 7. References

- Upstream: `ranaroussi/quantstats` — `qs.stats.*` (~70 fns, probed live), `qs.reports.html(..., benchmark, rf, match_dates)`, `qs.stats.montecarlo_{drawdown,sharpe,cagr}`.
- Actuals: `src/backtest/metrics.py:1-43`; `scripts/comprehensive_backtest_report.py:498-602,691-727,905-959`; `src/backtest/validation.py:28-33,323-378`; `src/alpha/reporting.py:15-21`; `requirements.txt:119`.
- Sibling study pattern: `_deliverables/pyfolio-adopt-2026-09-09.md` (vendored pure-pandas alternative; this proposal instead wraps pinned qs — complementary, not conflicting).
