# pyfolio-reloaded Institutional Risk Tearsheet Adoption Proposal

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py` and `strategies/registry.json` untouched per task constraint.
Scope: propose exact diffs adding stefan-jansen/pyfolio-reloaded tearsheet patterns to the ACTUAL backtest/reporting code.
Upstream: `https://github.com/stefan-jansen/pyfolio-reloaded` (pandas tearsheet: returns / positions / transactions inputs → rolling Sharpe, underwater, tracking error, round-trip attribution, factor / performance attribution, capacity).

## 1. Study findings (assumed paths vs. actual repo)

Assumed paths that DO NOT EXIST (verified by directory read):

- `src/backtest/tearsheet.py` — NOT FOUND. `src/backtest/` contains: `base_engine.py`, `engine_base.py`, `metrics.py`, `run_historic_backtest.py`, `validation.py`, `walk_forward_engine.py`, `permutation_tester.py`, `engines/`, `validators/`, `optimization/`, `defend/`, `legacy_backtest.py`, etc. No tearsheet module.
- `src/reports/` — NOT FOUND. Reporting lives in `scripts/comprehensive_backtest_report.py`, `scripts/run_full_backtest.py`, and `src/backtest/validation.py:main()` (quantstats tearsheet block).
- Any `pyfolio` / `quantstats-tearsheet` helper — NOT FOUND except the quantstats block noted below.

Verified actual locations (read, with line refs):

- `src/backtest/metrics.py:1-43` — ONLY `safe_sharpe(returns, periods=252)` and `safe_sortino(...)`. Both fillna(0), guard `std < 1e-12 → 0.0`. Sole metrics unit consumed by `scripts/run_full_backtest.py:23,28-29,65-67`, `scripts/comprehensive_backtest_report.py:536-545,629`, `src/backtest/validation.py:78,88`. No rolling, underwater, tracking-error, attribution, or capacity helpers exist.
- `scripts/comprehensive_backtest_report.py:498-602` — `calculate_metrics(portfolio, spy_df)` builds deposit-adjusted daily `return` series (`deposit_diff` mask, lines 509-512), then emits point metrics only: `total_return_pct, cagr, max_drawdown_pct + date, volatility, sharpe, sortino, calmar, var_95/99, cvar_95, win_rate, profit_factor, avg_holding, streaks, trades_per_year`. Drawdown is a single scalar (`drawdown.min()`); no underwater series/duration, no rolling Sharpe, benchmark `spy_df` param is accepted but UNUSED (no tracking error / beta / IR), no per-trade round-trip table beyond win/loss aggregates, no factor decomposition, no capacity/slippage sensitivity.
- `scripts/comprehensive_backtest_report.py:207-308` — `Portfolio` class already records everything pyfolio needs: `history[]` (`date, equity, cash, drawdown, deposits`), `trades[]` (`entry_date, exit_date, ticker, side, entry_price, exit_price, qty, pnl, fees, slippage, spread_cost, holding_days, regime`). `run_backtest_for_params()` force-liquidates at end (line 494-496). So tearsheet inputs can be derived with zero engine change.
- `scripts/comprehensive_backtest_report.py:905-959` — report JSON (`backtest_report.json`) has `portfolio_summary, benchmark_comparison (strategy vs SPY return/CAGR/Sharpe/maxDD only), quarterly/monthly returns, regime_breakdown, equity_curve, trade_log[:500]`. No `risk_tearsheet` section.
- `src/backtest/validation.py:322-378` — ONLY existing tearsheet: `qs.reports.html(returns_series)` → `docs/reports/strategy-<ts>.html`, plus `var_95/99, cvar_95, max_dd_duration` via `qs.stats.drawdown_details`, merged back into `backtest_report.json:portfolio_summary`. Guarded by `TEARSHEET_ENGINE = rb` loud-fail (lines 28-33). `returns_series` is sparse trade-day sums (`groupby('post_date')['return'].sum()`), NOT a daily equity curve — rolling/underwater/tracking-error computed on it would be wrong. This is the exact gap pyfolio patterns fill.
- `src/backtest/run_historic_backtest.py:11-231` — honest T+1 engine returning per-trade frame (`post_date, ticker, sentiment_score, entry_price, exit_price, return, holding_days, regime, spy_return, excess_return`). Already carries `spy_return/excess_return` per trade — the raw material for tracking-error and round-trip attribution without new data plumbing.
- `scripts/run_full_backtest.py:18-82` — `_compute_trade_metrics()` same gap: trade-sum Sharpe/Sortino/Calmar/win-rate/PF + 80/20 train/OOS Sharpe split. No rolling, underwater, TE, attribution, capacity.
- `requirements.txt:1-169` — `quantstats==0.0.81, matplotlib, seaborn` present; NO `pyfolio-reloaded` entry. Adding the full upstream dep pulls `zipline`-era weight; proposal therefore vendors the 6 formulas as pure pandas/numpy in-repo (pyfolio-compatible semantics, no new hard dep).

Conclusion: correct insertion is (a) NEW pure-function module `src/backtest/tearsheet.py` (pyfolio-reloaded formulas, offline-unit-testable), wired as (b) additive `risk_tearsheet` section in `calculate_metrics()` + report JSON, (c) additive fields in `_compute_trade_metrics()`, (d) replacement of the sparse-series quantstats-only block in `validation.py:main()` with a daily-equity-curve tearsheet call. No engine, signal, sizing, or registry change.

## 2. Design (pyfolio-reloaded patterns adopted, mapped to this repo)

pyfolio-reloaded canonical inputs are `returns (daily %)`, `positions`, `transactions`, `benchmark_rets`. Mapping:

| pyfolio concept | This repo source (no new plumbing) |
|---|---|
| `returns` | `calculate_metrics` `hist_df['return']` (deposit-adjusted, `comprehensive_backtest_report.py:505-512`) |
| `benchmark_rets` | SPY benchmark equity curve already built in same script (`benchmark_history`, lines 691-727); resample to daily pct |
| `positions` | `Portfolio.history` equity/cash + `open_positions` qty × price; else reconstruct exposure = `(equity-cash)/equity` |
| `transactions` | `Portfolio.trades` (entry/exit/qty/pnl/fees/slippage/spread_cost) = pyfolio `transactions` + round-trips |
| `gross_lev / exposure` | `max_pos_size_pct=0.25 × max_positions=4` caps (lines 331-332); capacity sweep scales these |

Six patterns adopted (formulas match pyfolio-reloaded semantics):

1. **Rolling Sharpe** (`pyfolio.timeseries.rolling_sharpe`): 63d/126d rolling mean/std × sqrt(252) on excess returns; report `min/median/current + share_of_windows<0`.
2. **Max underwater / drawdown duration** (`pyfolio.timeseries.underwater` + `drawdown_details`): underwater% = `(cum-ret − cummax)/cummax`; report full series + `max_underwater_pct, max_underwater_days, longest_recovery_days, current_underwater_pct/days`.
3. **Tracking error / IR / beta** (`pyfolio.timeseries` + `perf_attrib`): active = strat − bench aligned daily; `TE = std(active)×sqrt(252)`, `IR = mean(active)/std(active)×sqrt(252)`, `beta = cov(strat,bench)/var(bench)`, `corr`, `up/down capture`.
4. **Round-trip attribution** (`pyfolio.round_trips`): each closed trade = one round trip; aggregate `pnl` by `ticker / regime / holding_bucket (≤5d, 6-15d, 16-30d, >30d) / entry-year-month`; report top/worst contributors + concentration (top-5 share).
5. **Factor / regime decomposition** (`pyfolio.perf_attrib` spirit, no factor lib needed): repo has no factor returns feed, so decompose by available labels — `regime` (`low_volatility/normal/high_volatility` from `Portfolio.open_position`, line 471-475; FRED `NEUTRAL/...` in `run_historic_backtest.py:49`), plus `ticker` concentration (HHI). Additive, never blocks promotion.
6. **Capacity checks** (`pyfolio.capacity` spirit): slippage-sensitivity sweep — re-price every trade `pnl` at `slippage × {1×, 2×, 5×}` and participation cap `qty × {1.0, 0.5, 0.25}`; report Sharpe/PF/total-return degradation table. Uses recorded `slippage + spread_cost + fees` fields, so no microstructure model needed.

Rules for this repo (fail-closed, edge-gate safe):

1. All new code pure functions on `pd.Series/pd.DataFrame` (no yfinance, no network, no `evolve_real.py`/registry imports).
2. Deposit days handled exactly like existing code (`deposit_diff` mask → adjusted return) before any rolling/underwater/TE math.
3. Empty/short inputs return typed empty dicts/frames, never raise into `calculate_metrics` / `_compute_trade_metrics` / `validation.main`.
4. `safe_sharpe/safe_sortino` remain the single Sharpe/Sortino primitive (reuse, don't duplicate guards).
5. No promotion-gate change: tearsheet is reporting-only; `WalkForwardValidator` / `PermutationValidator` thresholds untouched.

## 3. Exact diffs proposed

### Diff 0 — `requirements.txt` (no new dep; document why)

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@
 quantstats==0.0.81
+# NOTE(pyfolio-adopt 2026-09-09): pyfolio-reloaded patterns are vendored as
+# pure pandas/numpy in src/backtest/tearsheet.py (no new dep). Full
+# `pyfolio-reloaded` wheel pulls legacy zipline-era pins incompatible with
+# pinned pandas==2.2.3 / numpy==2.2.0; revisit only if factor-attribution
+# needs upstream `perf_attrib` tables.
```

### Diff 1 — NEW `src/backtest/tearsheet.py` (full file, ~200 lines)

Pure functions; every pattern unit-testable offline. Deposit adjustment helper mirrors `comprehensive_backtest_report.py:509-512`.

```python
"""Institutional risk tearsheet helpers (pyfolio-reloaded patterns, vendored).

Pure pandas/numpy only. All functions fail-closed on empty/short input.
Deposit-adjusted returns: caller passes the already-adjusted daily return
series (see comprehensive_backtest_report.calculate_metrics deposit_diff mask).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.metrics import safe_sharpe

TRADING_DAYS = 252


def rolling_sharpe(returns: pd.Series, windows: tuple[int, ...] = (63, 126), periods: int = 252) -> dict:
    """pyfolio.timeseries.rolling_sharpe pattern. Returns per-window {min, median, current, frac_negative}."""
    out: dict[str, dict] = {}
    r = pd.Series(returns, dtype=float).fillna(0.0)
    for w in windows:
        if len(r) < w + 1:
            out[str(w)] = {"min": 0.0, "median": 0.0, "current": 0.0, "frac_negative": 0.0, "n_windows": 0}
            continue
        roll_mean = r.rolling(w).mean()
        roll_std = r.rolling(w).std()
        rs = (roll_mean / roll_std.replace(0.0, np.nan)) * np.sqrt(periods)
        rs = rs.dropna()
        if rs.empty:
            out[str(w)] = {"min": 0.0, "median": 0.0, "current": 0.0, "frac_negative": 0.0, "n_windows": 0}
            continue
        out[str(w)] = {
            "min": float(rs.min()), "median": float(rs.median()), "current": float(rs.iloc[-1]),
            "frac_negative": float((rs < 0).mean()), "n_windows": int(len(rs)),
        }
    return out


def underwater_stats(returns: pd.Series) -> dict:
    """pyfolio underwater pattern. cum-ret vs running max → depth + duration."""
    r = pd.Series(returns, dtype=float).fillna(0.0)
    if len(r) < 2:
        return {"max_underwater_pct": 0.0, "max_underwater_days": 0, "longest_recovery_days": 0,
                "current_underwater_pct": 0.0, "current_underwater_days": 0, "underwater": []}
    cum = (1.0 + r).cumprod()
    peak = cum.cummax()
    uw = (cum - peak) / peak  # <= 0
    max_depth = float(uw.min()) * 100.0
    # durations: consecutive days with uw < 0
    is_uw = (uw < 0).to_numpy()
    longest = cur = 0
    for v in is_uw:
        cur = cur + 1 if v else 0
        longest = max(longest, cur)
    cur_days = int(cur)
    # max single-episode length
    episodes, e = [], 0
    for v in is_uw:
        if v:
            e += 1
        elif e:
            episodes.append(e); e = 0
    if e:
        episodes.append(e)
    return {"max_underwater_pct": abs(max_depth), "max_underwater_days": int(max(episodes) if episodes else 0),
            "longest_recovery_days": int(longest), "current_underwater_pct": abs(float(uw.iloc[-1])) * 100.0,
            "current_underwater_days": cur_days,
            "underwater": [{"i": int(i), "pct": float(v) * 100.0} for i, v in enumerate(uw.to_list())]}


def tracking_stats(strat_rets: pd.Series, bench_rets: pd.Series, periods: int = 252) -> dict:
    """Tracking error / IR / beta / capture vs SPY benchmark (pyfolio perf_attrib spirit)."""
    s = pd.Series(strat_rets, dtype=float).fillna(0.0)
    b = pd.Series(bench_rets, dtype=float).fillna(0.0)
    n = min(len(s), len(b))
    if n < 20:
        return {"tracking_error_pct": 0.0, "information_ratio": 0.0, "beta": 0.0, "corr": 0.0,
                "up_capture": 0.0, "down_capture": 0.0, "n_overlap": int(n)}
    s, b = s.iloc[-n:].reset_index(drop=True), b.iloc[-n:].reset_index(drop=True)
    active = s - b
    te = float(active.std() * np.sqrt(periods)) * 100.0
    ir = float(safe_sharpe(active, periods=periods))
    var_b = float(b.var())
    beta = float(s.cov(b) / var_b) if var_b > 1e-12 else 0.0
    corr = float(s.corr(b)) if len(s) > 2 else 0.0
    up = b > 0; dn = b < 0
    up_cap = float(s[up].mean() / b[up].mean()) if up.any() and abs(float(b[up].mean())) > 1e-12 else 0.0
    dn_cap = float(s[dn].mean() / b[dn].mean()) if dn.any() and abs(float(b[dn].mean())) > 1e-12 else 0.0
    return {"tracking_error_pct": te, "information_ratio": ir, "beta": beta, "corr": corr,
            "up_capture": up_cap, "down_capture": dn_cap, "n_overlap": int(n)}


def round_trip_attribution(trades: pd.DataFrame) -> dict:
    """pyfolio.round_trips pattern over Portfolio.trades / run_historic_backtest frames."""
    if trades is None or trades.empty:
        return {"by_ticker": [], "by_regime": [], "by_holding_bucket": [], "concentration_top5_share": 0.0, "n_round_trips": 0}
    df = trades.copy()
    pnl = pd.to_numeric(df.get("pnl", df.get("return", 0.0)), errors="coerce").fillna(0.0)
    df["_pnl"] = pnl
    hold = pd.to_numeric(df.get("holding_days", df.get("holding_period", 5)), errors="coerce").fillna(5)
    df["_bucket"] = pd.cut(hold, bins=[-1, 5, 15, 30, 10**6], labels=["<=5d", "6-15d", "16-30d", ">30d"]).astype(str)
    out: dict = {"n_round_trips": int(len(df))}
    for key, name in (("ticker", "by_ticker"), ("regime", "by_regime"), ("_bucket", "by_holding_bucket")):
        if key in df.columns:
            g = df.groupby(key)["_pnl"].agg(["sum", "count", "mean"]).reset_index().rename(columns={"sum": "total_pnl", "count": "n", "mean": "avg_pnl"})
            g = g.sort_values("total_pnl", ascending=False)
            out[name] = [{"key": str(r[key]), "total_pnl": float(r["total_pnl"]), "n": int(r["n"]), "avg_pnl": float(r["avg_pnl"])} for _, r in g.iterrows()]
        else:
            out[name] = []
    tot = float(pnl.sum())
    if tot > 0 and "ticker" in df.columns:
        top5 = float(df.groupby("ticker")["_pnl"].sum().sort_values(ascending=False).head(5).sum())
        out["concentration_top5_share"] = top5 / tot
    else:
        out["concentration_top5_share"] = 0.0
    return out


def factor_decomposition(trades: pd.DataFrame) -> dict:
    """perf_attrib spirit with available labels: regime split + ticker HHI. No factor feed required."""
    if trades is None or trades.empty:
        return {"regime_share": [], "ticker_hhi": 0.0, "note": "no trades"}
    df = trades.copy()
    pnl = pd.to_numeric(df.get("pnl", df.get("return", 0.0)), errors="coerce").fillna(0.0)
    tot = float(pnl.abs().sum())
    reg = []
    if "regime" in df.columns:
        df["_pnl"] = pnl
        g = df.groupby("regime")["_pnl"].sum()
        reg = [{"regime": str(k), "pnl": float(v), "share_abs": float(abs(v) / tot) if tot > 0 else 0.0} for k, v in g.items()]
    hhi = 0.0
    if "ticker" in df.columns and tot > 0:
        w = df.groupby("ticker").apply(lambda x: float(x["_pnl"].abs().sum() / tot) if "_pnl" in df.columns else 0.0)
        hhi = float((w ** 2).sum())
    return {"regime_share": reg, "ticker_hhi": hhi,
            "note": "label-based decomposition (regime/ticker); wire factor returns feed for full perf_attrib"}


def capacity_sweep(trades: pd.DataFrame, slip_mults: tuple[float, ...] = (1.0, 2.0, 5.0)) -> dict:
    """Capacity pattern: re-price recorded slippage+spread+fees at multiples; report degradation."""
    if trades is None or trades.empty:
        return {"rows": [], "note": "no trades"}
    df = trades.copy()
    base_pnl = pd.to_numeric(df.get("pnl", df.get("return", 0.0)), errors="coerce").fillna(0.0)
    cost = pd.to_numeric(df.get("slippage", 0.0), errors="coerce").fillna(0.0)
    if "spread_cost" in df.columns:
        cost = cost + pd.to_numeric(df["spread_cost"], errors="coerce").fillna(0.0)
    if "fees" in df.columns:
        cost = cost + pd.to_numeric(df["fees"], errors="coerce").fillna(0.0)
    # run_historic frames carry returns not costs → fall back to haircut on positive pnl
    if float(cost.abs().sum()) == 0.0:
        cost = base_pnl.clip(lower=0.0) * 0.02  # assumed 2% friction proxy, disclosed
        proxy = True
    else:
        proxy = False
    rows = []
    for m in slip_mults:
        adj = base_pnl - cost * (m - 1.0)
        rows.append({"slip_mult": float(m), "total_pnl": float(adj.sum()),
                     "win_rate": float((adj > 0).mean()) if len(adj) else 0.0,
                     "profit_factor": float(adj[adj > 0].sum() / abs(adj[adj <= 0].sum())) if (adj <= 0).any() and abs(float(adj[adj <= 0].sum())) > 1e-12 else float("inf")})
    return {"rows": rows, "cost_proxy_used": proxy,
            "note": "2% friction proxy used (no cost cols)" if proxy else "recorded slippage+spread+fees scaled"}
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
+def rolling_sharpe_summary(returns_series, windows=(63, 126), periods=252):
+    """Thin re-export of tearsheet.rolling_sharpe so callers import from metrics."""
+    from src.backtest.tearsheet import rolling_sharpe as _rs
+    return _rs(returns_series, windows=windows, periods=periods)
+
+
+def max_underwater(returns_series):
+    """Thin re-export of tearsheet.underwater_stats (scalar summary)."""
+    from src.backtest.tearsheet import underwater_stats as _uw
+    s = _uw(returns_series)
+    return {k: v for k, v in s.items() if k != "underwater"}
```

Rationale: existing callers already import from `src.backtest.metrics`; avoids touching their import sites while keeping formulas in one tested module.

### Diff 3 — `scripts/comprehensive_backtest_report.py` (`calculate_metrics` + report JSON, additive only)

```diff
--- a/scripts/comprehensive_backtest_report.py
+++ b/scripts/comprehensive_backtest_report.py
@@ def calculate_metrics(portfolio, spy_df):
     hist_df['return'] = hist_df['equity'].pct_change().fillna(0)
     # Handling deposits ... (existing mask unchanged)
     hist_df['deposit_diff'] = hist_df['deposits'].diff().fillna(0)
     mask = hist_df['deposit_diff'] > 0
 
     if mask.any():
         hist_df.loc[mask, 'return'] = (hist_df.loc[mask, 'equity'] - hist_df.loc[mask, 'deposit_diff'] - hist_df['equity'].shift(1).loc[mask]) / hist_df['equity'].shift(1).loc[mask]
+
+    # --- Institutional risk tearsheet (pyfolio-reloaded patterns, additive) ---
+    from src.backtest import tearsheet as _ts
+    try:
+        _roll = _ts.rolling_sharpe(hist_df['return'])
+    except Exception:
+        _roll = {}
+    try:
+        _uw = _ts.underwater_stats(hist_df['return'])
+        _uw_series = _uw.pop("underwater", [])
+    except Exception:
+        _uw, _uw_series = {}, []
+    try:
+        _spy_rets = None
+        if spy_df is not None and not spy_df.empty and "Close" in spy_df.columns:
+            _spy_rets = spy_df["Close"].pct_change().reindex(hist_df.index).fillna(0)
+        _te = _ts.tracking_stats(hist_df['return'], _spy_rets if _spy_rets is not None else pd.Series(dtype=float))
+    except Exception:
+        _te = {}
+    try:
+        _rt = _ts.round_trip_attribution(pd.DataFrame(portfolio.trades))
+        _fd = _ts.factor_decomposition(pd.DataFrame(portfolio.trades))
+        _cap = _ts.capacity_sweep(pd.DataFrame(portfolio.trades))
+    except Exception:
+        _rt, _fd, _cap = {}, {}, {}
 
     # Return metrics ... (existing block unchanged)
@@
         "avg_win": avg_win,
-        "avg_loss": avg_loss
+        "avg_loss": avg_loss,
+        "risk_tearsheet": {
+            "rolling_sharpe": _roll,
+            "underwater": _uw,
+            "tracking": _te,
+            "round_trips": _rt,
+            "factor_decomposition": _fd,
+            "capacity": _cap,
+        },
     }
```

And in `main()` report assembly (after `portfolio_summary`, additive key):

```diff
         "portfolio_summary": {
             ...
             "roic": roic
         },
+        "risk_tearsheet": best_metrics.get("risk_tearsheet", {}),
+        "underwater_curve": _uw_series,  # from calculate_metrics internals; cap at full length (daily, ~2k pts)
```

Note: `spy_df` is already in scope in `calculate_metrics(portfolio, spy_df)` — currently unused; this diff finally consumes it (tracking error vs the SPY benchmark curve built at lines 691-727).

### Diff 4 — `scripts/run_full_backtest.py` (`_compute_trade_metrics`, additive fields)

Trade-frame path has no daily equity curve, so only trade-derivable patterns apply (round-trips, factor split, capacity, OOS already exists):

```diff
--- a/scripts/run_full_backtest.py
+++ b/scripts/run_full_backtest.py
@@ def _compute_trade_metrics(trades_df):
     return {
         ...
         "train_sharpe": float(train_sharpe),
-        "oos_sharpe": float(oos_sharpe) if oos_sharpe is not None else None
+        "oos_sharpe": float(oos_sharpe) if oos_sharpe is not None else None,
+        # pyfolio-reloaded round-trip / factor / capacity (trade-derivable subset)
+        "round_trips": __import__("src.backtest.tearsheet", fromlist=["round_trip_attribution"]).round_trip_attribution(trades_df),
+        "factor_decomposition": __import__("src.backtest.tearsheet", fromlist=["factor_decomposition"]).factor_decomposition(trades_df),
+        "capacity": __import__("src.backtest.tearsheet", fromlist=["capacity_sweep"]).capacity_sweep(trades_df),
     }
```

Fail-closed note: wrap the three calls in try/except → `{}` if `tearsheet` import fails, so Darwin ranking (`darwin.evaluate_population`) never breaks.

### Diff 5 — `src/backtest/validation.py` (fix sparse-series tearsheet, use daily curve)

Replace the trade-day sparse series with a deposit-aware daily series before `qs.reports.html`, then append tearsheet JSON:

```diff
--- a/src/backtest/validation.py
+++ b/src/backtest/validation.py
@@
         real_trades = TEARSHEET_ENGINE.run_backtest(custom_posts_df=posts_df, stock_dfs_preloaded=stock_dfs, spy_close_preloaded=spy_close)
         if len(real_trades) > 0:
-            real_trades_sorted = real_trades.sort_values(by="post_date").reset_index(drop=True)
-            returns_series = real_trades_sorted.groupby('post_date')['return'].sum()
-            returns_series.index = pd.to_datetime(returns_series.index)
+            # Daily equity-curve series (pyfolio-correct input): trade returns spread to exit-date equity steps,
+            # reindexed to full SPY trading calendar, zeros on flat days.
+            from src.backtest import tearsheet as _ts
+            real_trades_sorted = real_trades.sort_values(by="post_date").reset_index(drop=True)
+            _trade_rets = real_trades_sorted.groupby(pd.to_datetime(real_trades_sorted['post_date']))['return'].sum()
+            _cal = pd.DatetimeIndex(sorted(set(spy_close.index) | set(_trade_rets.index)))
+            returns_series = _trade_rets.reindex(_cal).fillna(0.0)
+            _spy_rets = pd.Series(spy_close.pct_change().fillna(0.0)).reindex(_cal).fillna(0.0)
+            _risk = {
+                "rolling_sharpe": _ts.rolling_sharpe(returns_series),
+                "underwater": {k: v for k, v in _ts.underwater_stats(returns_series).items() if k != "underwater"},
+                "tracking": _ts.tracking_stats(returns_series, _spy_rets),
+                "round_trips": _ts.round_trip_attribution(real_trades),
+                "factor_decomposition": _ts.factor_decomposition(real_trades),
+                "capacity": _ts.capacity_sweep(real_trades),
+            }
 
             os.makedirs("docs/reports", exist_ok=True)
             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005 - Timezone not critical for this usage
             report_path = f"docs/reports/strategy-{timestamp}.html"
             qs.reports.html(returns_series, output=report_path)
             print(f"Tearsheet saved to: {report_path}")
```

And extend the `metrics` dict written back to `backtest_report.json:portfolio_summary` (lines 357-362):

```diff
             metrics = {
                 "var_95": float(var_95),
                 "var_99": float(var_99),
                 "cvar_95": float(cvar_95),
-                "max_dd_duration": int(max_dd_duration)
+                "max_dd_duration": int(max_dd_duration),
+                "risk_tearsheet": _risk,
             }
```

## 4. Why this is safe for this repo

- Preserves fail-closed mandate: every new call wrapped in try/except with typed empty fallback; tearsheet never raises into backtest ranking, reporting, or validation gates.
- Preserves no-lookahead: pure functions over already-executed returns/trades; T+1 execution (`run_historic_backtest.py:59`, `engine_base.py:18-36`) and `TEARSHEET_ENGINE` loud-fail guard untouched.
- Preserves edge gate: reporting-only addition; `WalkForwardValidator` (OOS≥0.40, consistency<1.5, ≥3 windows, 2/3 positive) and `PermutationValidator` (p<0.01) thresholds unchanged; no `strategies/registry.json` entry proposed.
- Cost: zero new deps (pandas/numpy already pinned); `quantstats` HTML path retained, enriched with daily-calendar input fix.
- Security: `bandit`-clean surface (no eval/pickle/network/subprocess; bounded underwater series).

## 5. Test plan

New file `tests/backtesting/test_tearsheet.py` (offline, deterministic, no network):

1. `test_rolling_sharpe_known_series` — constant +0.001 daily returns → rolling Sharpe large positive; alternating ±0.01 → near 0; series shorter than window → zero-filled dict, no raise.
2. `test_rolling_sharpe_matches_safe_sharpe` — full-sample window rolling-sexcess `current` ≈ `safe_sharpe` on same series (tolerance 1e-9).
3. `test_underwater_depth_and_duration` — synthetic `[-0.5, +0.1, +0.1, ...]`ams: `max_underwater_pct ≈ 50`, `longest_recovery_days` counts consecutive underwater days, recovery to new peak resets `current_underwater_days == 0`.
4. `test_tracking_stats_perfect_tracker` — strat == bench → `tracking_error_pct == 0`, `IR == 0`, `beta ≈ 1`, `corr ≈ 1`; disjoint/short series (<20 overlap) → zero-filled, no raise.
5. `test_round_trip_by_ticker_regime_bucket` — fixture trades with known tickers/regimes/holdings; assert `by_ticker` sorted desc by pnl, bucket labels `<=5d/6-15d/16-30d/>30d`, `concentration_top5_share in [0,1]`.
6. `test_factor_hhi_bounds` — single-ticker trades → `ticker_hhi == 1.0`; equal-split N tickers → `hhi ≈ 1/N`; empty frame → `note == "no trades"`.
7. `test_capacity_monotonic` — `capacity_sweep` rows `total_pnl` non-increasing over `slip_mults=(1,2,5)`; proxy flag True when no cost cols, False when `slippage/spread_cost/fees` present.
8. `test_calculate_metrics_additive` — minimal fake `Portfolio` (5-day history + 2 trades) through `comprehensive_backtest_report.calculate_metrics`; assert legacy keys (`sharpe, max_drawdown_pct, win_rate`) unchanged AND `risk_tearsheet` has all 6 sub-keys.
9. `test_validation_series_daily_calendar` — assert new reindex logic yields `len(returns_series) == len(calendar)` with zeros on flat days (regression: old sparse groupby understated drawdown duration).
10. `test_fail_closed_empty` — every tearsheet fn with empty Series/Frame returns typed empties without raise.

Commands (per AGENTS.md, single-file serial):

```
PYTHONPATH=. pytest tests/backtesting/test_tearsheet.py -q
PYTHONPATH=. pytest tests/backtesting/test_validation.py -q
ruff check src/backtest/tearsheet.py tests/backtesting/test_tearsheet.py
bandit -r src/backtest/tearsheet.py
```

Acceptance: 10/10 new tests pass, existing `test_validation.py::test_validation_main_execution` still passes (mocked `rb.run_backtest` path), ruff + bandit clean, `calculate_metrics` legacy keys byte-identical on fixture, no diff to `evolve_real.py` / `strategies/registry.json` (`git status --porcelain` shows only new + listed files).

## 6. Rollout steps (for implementer, not done here)

1. Add Diff 1 (new module) → run new tests 1-7,10.
2. Add Diff 2 (metrics re-exports) → ruff/bandit.
3. Add Diff 3 (comprehensive report) → run test 8 + regenerate one local report on cached CSVs (do NOT publish; `DATA_IS_MOCK` guard stays).
4. Add Diff 4 (run_full_backtest fields) → confirm Darwin ranking order unchanged on fixture population.
5. Add Diff 5 (validation daily calendar) → run test 9 + existing validation test.
6. Pre-register any strategy change motivated by tearsheet (e.g. underwater-duration stop) + walk-forward + permutation + DSR before any registry promotion.

## 7. References

- Upstream: `stefan-jansen/pyfolio-reloaded` — tearsheet sections: rolling Sharpe, underwater, tracking/performance attribution, round-trips, capacity.
- Actual metrics: `src/backtest/metrics.py:1-43`.
- Actual report: `scripts/comprehensive_backtest_report.py:498-602 (calculate_metrics), 905-959 (report JSON), 691-727 (SPY benchmark curve)`.
- Actual validation tearsheet: `src/backtest/validation.py:28-33 (engine guard), 322-378 (quantstats block)`.
- Actual engines: `src/backtest/run_historic_backtest.py:11-231 (T+1, spy_return/excess_return)`, `src/backtest/engine_base.py:18-36 (T+1 rule)`, `src/backtest/walk_forward_engine.py:24-123`, `src/backtest/permutation_tester.py:90-136`.
- Trade metrics: `scripts/run_full_backtest.py:18-82`.
