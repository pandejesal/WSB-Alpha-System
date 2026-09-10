# pybroker Adoption Study — WFA / Bootstrap / Cost / Optuna / Alpaca

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint.
Scope: compare `edtechre/pybroker` patterns (Numba vectorized backtest, walk-forward + bootstrapping, Optuna tuning, Alpaca adapter) against ACTUAL `src/backtest/` + `src/execution/` and propose additive diffs only.
Upstream: `https://github.com/edtechre/pybroker` (master @ 1,259 commits; Apache-2.0 WITH Commons Clause — see Reject §5).
Workdir constraint: stayed inside workdir; no edits outside `_deliverables/`.

## 1. Actual repo surveyed (read, with line refs)

Backtest core:

- `src/backtest/base_engine.py:1-10` — 10-line ABC `BacktestEngine.run_backtest(data, strategy) -> dict`. No fees/slippage/bootstrap/WFA in interface.
- `src/backtest/engine_base.py:1-36` — `BaseBacktestEngine.run_sim()` + `apply_t1_execution_rule()`: signal(T) → execution_date = T+1 BDay (strict no-lookahead primitive).
- `src/backtest/run_historic_backtest.py:11-251` — HONEST T+1 sentiment engine. `business_day_offset(post_date,1)` + `np.searchsorted` (58-64), decision indicators on `entry_iloc-1` (67-72), GK vol shield (76), RSI filter (81), confluence score (94-99), entry fill at `Open[entry]` + ATR slippage `clamp(0.05*ATR, 0.1%, 2.5%)` (122-126), exit at `Close[exit]` minus slippage (139-141), intraday stop-loss via High/Low breach (143-158), SPY bench + excess (162-168, 188-195). Returns per-trade frame (`post_date,ticker,...,return,spy_return,excess_return`). `run_backtest()` wrapper pins defaults (holding 5, RSI 30/70, GK 1.20, confluence 3).
- `src/backtest/custom_engine.py:10-62` — vectorized signal-shift engine: `signal.shift(1)*Returns`, cost on `signal.diff()!=0` of `commission(0.0004 default) + slippage_pct` where slippage = `clamp(0.05*avgATR/avgPrice, 0.001, 0.025)` (30-36). Point metrics only (total_return, win_rate, maxDD, trades).
- `src/backtest/metrics.py:1-43` — ONLY `safe_sharpe` / `safe_sortino` (fillna(0), `std<1e-12→0`, sqrt(252)). No CIs, no PF/DD CIs.
- `src/backtest/walk_forward_engine.py:10-123` — `WalkForwardValidator(train 252/test 63, OOS_MIN 0.40, CONSISTENCY_MAX 1.5, MIN_WINDOWS 3)`. Strict conjunction: `avg>=thr AND consistency<1.5 AND windows>=3 AND ≥2/3 positive` (96-101). Fail-closed on short data / eval error / non-numeric (56-58, 72-73). Non-anchored step = test_window; no train/test ratio param, no shuffle, no per-window param retune, no bootstrap.
- `src/backtest/optimization/walk_forward.py:1-51` — `WalkForwardOptimizer(train 90/test 30/step 30)`: `generate_windows()` calendar split + `optimize()` picks best train Sharpe per grid, scores OOS. No purge/embargo, no bootstrap, no seed.
- `src/backtest/optimization/optimizer.py:1-53` — `GridSearchOptimizer` (exhaustive, sort by sharpe) + `BayesianOptimizer` (scipy L-BFGS-B on negative sharpe, midpoint x0). No Optuna, no TPE, no trial ledger hook.
- `src/backtest/permutation_tester.py:1-136` — `PermutationValidator(N=1000, p<0.01, seed 42, null_mode circular|shuffle)`. Vectorized OHLC synth: log-space intra-candle geometry preserved + inter-bar gaps shuffled/rolled (20-88), PF p-value (126-127). Requires real PF>1.0 else FAIL (97-103).
- `src/backtest/validation.py:1-382` — orchestration: `load_base_data` (yfinance SPY + indicators), `compute_metrics` (trade-sum return + `safe_sharpe` daily, 75-89), `run_in_sample_test` (200 perms, ticker-stratified date shuffle, joint return+sharpe p-value, 91-156), `run_walk_forward_test` (90-day rolling, pooled p-value + win-rate vs permuted median, 159-261), SPA via `StatisticalValidator.spa_test` (270-284), quantstats tearsheet on sparse trade-day series (331-378) guarded by `TEARSHEET_ENGINE=rb` loud-fail (28-33).
- `src/backtest/validators/statistical.py:1-135` — `whites_reality_check` (StationaryBootstrap block 10, 1000 reps, needs `arch`, 19-67), `spa_test` (arch `SPA`, consistent p, 70-93), `combinatorial_purged_cv` (n_splits/n_test/purge 5/embargo 5, 96-135).
- `src/backtest/whites_reality_check.py:1-32` — thin wrapper delegating to `StatisticalValidator` (StationaryBootstrap path).
- `src/backtest/defend/trial_ledger.py:1-630` — hashed JSONL trial ledger (`sha256(strategy,params,range)`, dedup skip, corrupt-line tolerant) + Bailey–Lopez de Prado DSR normal variant + break-even threshold (388-422). CLI ingest rankings → deflate best.
- `src/backtest/defend/minerva_score.py:1-173` — 5-gate rollup (DSR≥0.95, PBO≤0.5, SPA p<0.05, MTR pass, |regime z|<1.5) → 0-100 + SEAL≥80 iff all pass. Reporting layer over binding DSR gate.

Execution:

- `src/execution/base_broker.py:1-44` — `BaseBroker` (equity/cash, place_order, positions, cancel_order, get_capabilities). Capability-gated order types.
- `src/execution/alpaca_broker.py:1-98` — `AlpacaBroker` (TradingClient, paper flag from config, fractional-short int cast, DAY TIF, stop_loss attach, capabilities market/stop-limit/paper).
- `src/execution/live_alpaca_executor.py:1-394` — daily cron template: paper/live URL allowlist (75-92), `_is_alpaca_url_allowed` exact match (95-99), dual-gate killswitch (174-180), daily/weekly circuit breakers (211-232), technical-confluence filter (290-345), fractional notional orders capped by `MAX_RISK_PER_TRADE_PCT` (360-379), paper log dump (382-387). Returns early in paper mode (192) — live path only when `LIVE_TRADING_ENABLED`.
- `src/execution/execution_adapter.py:1-104` — `PaperTradeBroker` ABC + `PaperbrokerClient` (localhost:5000 REST) + `ExecutionAdapter.execute_signals` (ticker/side/quantity/CVaR routing).

## 2. pybroker patterns studied (verified raw sources)

- **Numba vectorized core**: `src/pybroker/vect.py` — `@njit(cache=True)` kernels `highv/lowv/sumv` (O(n) deque/Neumaier), `returnv`, `cross`, `atr`, `adx/stochastic/macd/trend/deviation/price_intensity/reactivity`. `benchmarks/bench_backtest.py` pins 4-sym×2y×3-window walkforward; `EvalKernels`/`IndicatorKernels` benches track JIT steady-state vs cold (`WalkforwardCold`, `WalkforwardProperCold` clears `.nbi`). Portfolio bar loop isolated in `BacktestBarLoop` bench.
- **WFA protocol**: `Strategy.walkforward(windows, train_size=0.5?, lookahead, shuffle, calc_bootstrap, timeframe, exit_on_last_bar)` + `WalkforwardWindow` splits; `benchmarks` use `walkforward(windows=3, lookahead=1, calc_bootstrap=True)`. `_run_walkforward` preprocess builds `{symbol: max_date}` map for `exit_on_last_bar`; `_filter_dates`, per-window store slicing (`slice_symbol_array_store_by_dates`), indicator cache (`IndicatorCacheKey`, `_L1Cache` disk+L1). Model path: pooled/multi-symbol training, per-bar predictions, `train_fn(symbol,train_df,test_df)`.
- **Bootstrap guards**: `StrategyConfig(bootstrap_samples=10_000 default)` (verified `config.py`); `src/pybroker/eval.py` — `@njit` BCa bootstrap: `_fill_bootstrap_row` (row-at-a-time, no 8GB matrix), `_bca_boot_conf_{pf,sharpe,generic}`, `conf_profit_factor/conf_sharpe_ratio`, `drawdown_conf` (quantile upper bounds q_001/01/05/10), `bootstrap_eval_all` (single shared resampling pass for PF+Sharpe+DD), `EvaluateMixin.evaluate(..., calc_bootstrap, bootstrap_samples, bars_per_year, seed=42)` → `EvalResult(metrics, bootstrap: BootstrapResult{conf_intervals, drawdown_conf})`. NaN/inf hardening: `sortino` returns `inf` only on genuine gain, `nan` on non-computable (fails Optuna trial); `calmar/upi` same discipline.
- **Cost modeling**: `StrategyConfig`: `fee_mode ∈ {ORDER_PERCENT, PER_ORDER, PER_SHARE, Callable[[FeeInfo],Decimal], None}` + `fee_amount`; `enable_fractional_shares` (default False); `round_fill_price=True`; `buy_delay=1/sell_delay=1` (T+1 equiv); `leverage≥1.0`, `interest_rate` (requires `bars_per_year`), `exit_on_last_bar` (+ fill-price enums), `record_portfolio/position_bars=False` (compact buffer default). `src/pybroker/slippage.py`: `SlippageContext(side,symbol,shares,fill_price,col_scope,ind_scope,sym_end_index,...)` with causal `end_index` bound (full-window scope, must slice to fill bar); `FixedSlippageModel(bps)` (buy×(1+bps/1e4), sell×(1−bps/1e4), 0=noop); `VolatilitySlippageModel(atr_period=14, scale=0.1)` (fill left alone in warmup/NaN/missing, floor 1% anti-negative); `VolumeSlippageModel(price_impact=0.1, volume_limit=0.025)` (cap `shares≤limit×volume`, square-law impact `impact×(shares/vol)²`, zero-volume→zero fill when cap on, floor 1%, volume-col validation).
- **Optuna tuning**: `src/pybroker/optimize.py` — `hyperparam(name, default, low, high, step)` global registry; `collect_hyperparams/collect_search_space` (reachable-from-executions only, warns on orphan); `Strategy.optimize(score_fn, sampler ∈ {grid,tpe,random} | BaseSampler, n_trials, study, direction, windows)`; `_build_sampler` (deepcopy+reseed per window, distinct inner/outer streams; grid enumerates shuffled `_all_grids` order); `_run_study` (grid/Random parallel via joblib, adaptive samplers forced sequential + log); per-window `WindowOptimizeResult(params, study, train_score, train/test dates, execution_symbols)` + stitched OOS `OptimizeResult(best_params=last window, best_score, result, study, windows)`. Trainable-model guard: `optimize()` REJECTS trainable `train_fn` models (pretrained only; tune inside `train_fn` or use `walkforward`). NaN score → trial FAIL (never silent best).
- **Alpaca/data adapter**: `Strategy(DataSource, start, end)` where `DataSource ∈ {Alpaca(api_key,secret), YFinance/YQuery, AKShare, Custom}`; canonical cols `(date,symbol,open,high,low,close,volume)`; timeframe formatting with strict unsupported-timeframe raise (no silent empty); caching (downloaded data, indicators, models; `_L1Cache` + diskcache benches `CacheHit/CacheDiskHit/CacheL1Hit`); `parallel_indicators` + `set_parallel(n_jobs)` (symbol-batched joblib); multi-interval (`intervals=["weekly"]`, `ctx.interval()`); `Alpaca` used identically to backtest source then `walkforward(timeframe='1m', windows=5, train_size=0.5)` in README model example.

## 3. Overlap (do NOT re-add)

| pybroker | Already in repo (equal or stronger) | Verdict |
|---|---|---|
| `buy_delay=1/sell_delay=1` T+1 | `engine_base.apply_t1_execution_rule` + `run_historic_backtest:58-72` (searchsorted T+1 + t−1 decisions) | OVERLAP — keep ours (sentiment-aware, FRED regimes) |
| ATR slippage | `run_historic_backtest:122-126` + `custom_engine:30-36` (0.05×ATR clamped 0.1–2.5%) | OVERLAP on direction; gap is only bps/volume/floor formalism (§4) |
| Commission/fee | `custom_engine commission=0.0004` on trade mask | OVERLAP (point); adopt FeeMode enum, not new math |
| Walkforward windows + OOS pick-best | `walk_forward_engine` (strict conjunction) + `optimization/walk_forward` (best-train→OOS) | OVERLAP on shape; ours STRICTER (0.40/1.5/3-window/2-3 rule). Adopt only train_size/shuffle/seed/replay (§4) |
| Permutation null | `permutation_tester` (OHLC-geometry synth, stronger than date-shuffle) + `validation` date-shuffle + WRC/SPA via `arch` | OVERLAP — pybroker bootstrap is COMPLEMENT (CIs), not replacement |
| DSR/multiple-testing | `trial_ledger` DSR + `minerva_score` 5-gate | STRONGER than pybroker (pybroker has no DSR). Never gate through Optuna best-value alone |
| Alpaca paper/live split + capability gates | `alpaca_broker` + `live_alpaca_executor` allowlist + dual-gate + circuit breakers | STRONGER (fail-closed). pybroker `Alpaca` source adds nothing for execution safety |
| Fractional shares caution | `alpaca_broker:63-66` (short int-cast, qty-0 raise) | OVERLAP — keep; do not enable fractional shorts |

## 4. Adopt (additive, fail-closed)

Ranked by edge-gate value / risk:

**A1 — BCa bootstrap CIs for Sharpe/PF/drawdown (highest value, low risk).**
Repo reports point Sharpe/PF/DD only (`metrics.py`, `custom_engine`, `run_full_backtest._compute_trade_metrics`, `validation.compute_metrics`). pybroker `eval.py` proves the pattern: BCa intervals + drawdown quantile bounds + `bootstrap_eval_all` single-pass + seed 42 + NaN discipline.
Propose NEW `src/backtest/bootstrap_cis.py` (pure numpy/pandas, stdlib+existing `arch` optional; NO numba dependency — copy the statistics, not the JIT):
- `bca_ci(x, fn, n_boot=2000, seed=42, cl=0.95)` for Sharpe (per-bar) and log-PF, jackknife acceleration, clamp indices (mirrors `_bca_intervals_from_boot`).
- `drawdown_quantiles(changes, returns, n_boot)` → `{q_001,q_01,q_05,q_10}` upper bounds (mirrors `drawdown_conf`).
- `evaluate_with_bootstrap(bar_returns, bar_changes, n_boot, seed)` → `{sharpe_ci, pf_ci, dd_bounds}` typed empties on len<20.
- Wire ADDITIVELY: `run_full_backtest._compute_trade_metrics` + `validation.compute_metrics` gain `sharpe_ci_95, pf_ci_95, dd_q05` informational fields; promotion thresholds UNCHANGED (CIs reported, never gate-loosening). Permutation p-value remains binding.

**A2 — Cost-model formalism: fixed-bps + volume cap + fee enum + floors.**
Repo has ATR slippage + flat commission but no (a) explicit bps leg, (b) volume participation cap / square-law impact, (c) fee-mode enum, (d) anti-negative floor, (e) causal fill-bar bound documented.
Propose NEW `src/backtest/cost_model.py`:
- `FeeSchedule(mode ∈ {order_percent, per_order, per_share, none}, amount)` → per-fill fee; mirrors `FeeMode` without importing pybroker.
- `apply_fixed_bps(side, price, bps)` (buy×(1+bps/1e4), sell×(1−bps/1e4); `bps=0` noop; raise if ≥10000).
- `apply_volume_cap(shares, bar_volume, limit=0.025, price_impact=0.0)` → `(capped_shares, impact_mult)` with zero-volume→0 fill when cap on (pybroker `VolumeSlippageModel` semantics).
- `apply_atr_slippage(...)` THIN WRAPPER over existing `run_historic_backtest:122-126` formula (no behavior change) + add 1%-of-fill floor + warmup-noop (pybroker guards).
- Causal rule docstring: slippage reads ONLY fill-bar slice (`end_index` bound) — codifies existing t−1/entry-bar discipline.
- Wire: `custom_engine` and `run_historic_backtest` accept optional `cost_model=` (default preserves current numbers byte-identical); `comprehensive_backtest_report.capacity_sweep` reuses it instead of 2% proxy when cost cols missing.

**A3 — WFA protocol hardening: train_size + anchored/shuffle + seed + replay.**
`WalkForwardValidator` steps by `test_window` with fixed 252/63, no `train_size` ratio, no shuffle/lock, no seed, no per-window param replay. pybroker `walkforward(windows, train_size, lookahead=1, shuffle, calc_bootstrap, exit_on_last_bar)` + `walkforward_split` + per-window store slicing is the template — WITHOUT adopting its engine.
Propose additive kwargs on `WalkForwardValidator.validate()` + `WalkForwardOptimizer.generate_windows()`:
- `train_size: float|None` (ratio; None = current day-count behavior; preserved default).
- `anchored: bool=False` (expand train start-fixed when True; else rolling).
- `shuffle: bool=False` (shuffles window ORDER only for sensitivity; default False, logged when True).
- `seed: int=42`, `purge: int=0, embargo: int=0` (delegate to existing `StatisticalValidator.combinatorial_purged_cv` when >0).
- Return `window_splits: [(train_start,train_end,test_start,test_end)]` + `params_per_window` passthrough so Optuna/WFO replay is auditable. Thresholds (0.40/1.5/3/2-3) UNTOUCHED.

**A4 — Optuna TPE as bounded tuner behind trial ledger (medium value, gated risk).**
Repo tuners: exhaustive grid + L-BFGS-B (both Sharpe-max, no trial counting). pybroker `optimize.py` contributes: hyperparam registry with (low,high,step) lattice validation, TPE/grid/random samplers with per-window reseed, NaN→FAIL, trainable-model refusal, `study`/`WindowOptimizeResult` audit trail.
Propose NEW `src/backtest/optimization/optuna_tuner.py` (optional `optuna` import; fail-closed skip if missing):
- `declare_space({name: (default,low,high,step)})` with span%step==0 validation (pybroker `Hyperparam.__post_init__`).
- `tpe_search(objective, space, n_trials≤200, seed=42, direction="maximize")` — TPE only (no GridSampler passthrough that hides best-trial); every evaluated config calls `TrialLedger.append_experiment` FIRST so N counts losers (DSR stays binding).
- Refuse trainable-model objectives (pybroker `_MODEL_OPTIMIZE_ERROR` mirrored): tuner tunes EXEC params (holding_days, rsi bounds, vol limit, confluence) on fixed features only.
- `replay_best_per_window()` helper consuming A3 `window_splits` for stitched OOS audit.
- NO change to promotion: tuned candidate still faces permutation + CPCV + WFO + DSR + Minerva before registry.

**A5 — Execution/data-source parity checklist (no new live path).**
pybroker `Alpaca/YQuery/AKShare` strictness worth copying as CHECKS, not code: unsupported-timeframe raise (never silent empty), canonical-column assert `(date,symbol,open,high,low,close,volume)`, indicator/model cache keyed by (symbol, tf, date-range, ind-name) with L1+disk, `parallel_indicators` symbol-batched. Repo already caches market data (`market_data_2019_2026/`, `cache/`); propose documenting the parity checklist in `PAPER_BROKER_SETUP.md` appendix + adding the asserts to `load_base_data`/report loaders. No live-trading behavior change; `live_alpaca_executor` dual-gate/allowlist/circuit-breakers remain authoritative.

**A6 — Diagnostics to borrow verbatim (informational):**
`EvalMetrics` breadth (`sortino` w/ inf-only-on-gain, `calmar`, `ulcer_index/upi`, `equity_r2`, `annual_volatility_pct`) as extra keys in `calculate_metrics`; `record_portfolio_bars=False` default + `return_signals/return_stops` opt-in flags for per-window replay (memory-safe). Numba kernels (`highv/lowv/sumv/atr`) ONLY if a profile proves the indicator loop hot — default is NOT to add numba (repo has no numba dep; Numba JIT cold-start cost + `cache=True` `.nbi` hygiene per pybroker benches outweighs gains on daily sentiment bars).

## 5. Reject (with reason)

1. **Wholesale `Strategy`/`Portfolio`/`ExecContext` engine swap.** Breaks sentiment-confluence engine, FRED regimes, T+1/searchsorted path, trial ledger, DSR gate; Commons-Clause license encumbers commercial use; bar-loop/`ctx.buy_shares/hold_bars/stop_*` DSL would orphan `strategies/`. Reuse formulas, not the engine.
2. **Numba JIT as default.** No `numba` in `requirements.txt`; cold-compile regressions (pybroker's own `WalkforwardProperCold` bench exists because of this), Windows `.nbi` cache fragility, and daily-bar workloads are I/O/indicator-bound, not loop-bound. Accept kernels only behind a profile gate.
3. **Leverage>1 / interest-rate carry / margin trading.** `StrategyConfig(leverage, interest_rate)` violates fail-closed risk mandate (`MAX_RISK_PER_TRADE_PCT`, circuit breakers). Paper-only; never enable without pre-registered gate change.
4. **Fractional shorts / `enable_fractional_shares=True` default.** Repo explicitly int-casts shorts (`alpaca_broker:63-66`); pybroker defaults False for the same reason. Keep.
5. **`exit_on_last_bar=True` default.** Liquidates hanging positions to flatter DD; masks exposure bugs. Keep default False; force-liquidation stays explicit (`comprehensive_backtest_report:494-496`).
6. **Trainable ML inside `optimize()` loop.** pybroker itself refuses this; would break pre-registration + DSR N-counting. Tune exec params only; models train in `walkforward` w/ validation split or not at all.
7. **Live data fetch inside backtest (`YFinance/YQuery/AKShare` network).** Repo gates run offline on cached CSVs (`DATA_IS_MOCK` guard, `load_base_data` local-first). Network in gates = flaky CI + lookahead risk. Keep data-source classes as loader CHECKS only.
8. **Ranking by raw Optuna `best_value` (Sharpe/PF/sortino `inf` handling).** pybroker `inf`-on-flawless-curve is correct for ranking but lethal as promotion gate (single-trade miracles). Binding gates stay: permutation p + WRC/SPA + CPCV + WFO conjunction + DSR + Minerva SEAL.
9. **Full `record_portfolio_bars/record_position_bars=True` always-on.** Memory blowup on multi-year daily × universe; keep compact-buffer default, opt-in per replay (A6).

## 6. Exact diffs proposed (additive; no engine/registry edits)

### Diff 0 — `requirements.txt` (comment only; optional dep noted, not added)

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@
 quantstats==0.0.81
+# NOTE(pybroker-adopt 2026-09-09): pybroker patterns vendored as pure
+# numpy/pandas in src/backtest/bootstrap_cis.py + cost_model.py (no new hard
+# dep). `optuna` stays OPTIONAL (tuner skips fail-closed if missing); `numba`
+# NOT adopted (cold-JIT + Commons-Clause; see _deliverables/pybroker-adopt-2026-09-09.md §5).
+# `arch` already optional for WRC/SPA — bootstrap CIs reuse it when present.
```

### Diff 1 — NEW `src/backtest/bootstrap_cis.py` (~120 lines; BCa-lite, no numba)

```python
"""BCa bootstrap CIs for Sharpe / profit-factor / drawdown (pybroker eval.py pattern, vendored).

Pure numpy/pandas. Fail-closed: short/degenerate input -> typed empties, never raise into callers.
Mirrors pybroker bca_boot_conf + drawdown_conf semantics; resampling row-at-a-time; seed=42 default.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from math import erf, sqrt

def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))

def _ncdf_inv(p: float) -> float:  # Acklam, same contract as trial_ledger.inverse_normal_cdf
    from src.backtest.defend.trial_ledger import inverse_normal_cdf
    return inverse_normal_cdf(min(max(p, 1e-10), 1.0 - 1e-10))

def _sharpe(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) < 2 or float(np.std(x)) == 0.0:
        return 0.0
    return float(np.mean(x) / np.std(x))

def _log_pf(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.log((1e-10 + x[x > 0].sum()) / (1e-10 - x[x < 0].sum())))

def bca_ci(x, fn=_sharpe, n_boot: int = 2000, seed: int = 42, cl: float = 0.95) -> dict:
    """Bias-corrected accelerated CI for fn(x). Returns {low, high, cl, n_boot} or empty-typed on len<20."""
    x = np.ascontiguousarray(np.asarray(x, dtype=float))
    n = len(x)
    if n < 20 or n_boot <= 0:
        return {"low": 0.0, "high": 0.0, "cl": cl, "n_boot": 0, "note": "insufficient data"}
    rng = np.random.default_rng(seed)
    theta = fn(x)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        boot[i] = fn(x[rng.integers(0, n, n)])
    z0 = _ncdf_inv(np.mean(boot < theta))
    jack = np.empty(n)  # leave-one-out for acceleration
    for i in range(n):
        jack[i] = fn(np.concatenate([x[:i], x[i + 1:]]))
    m = jack.mean()
    a = ((m - jack) ** 3).sum() / (6.0 * (((m - jack) ** 2).sum() ** 1.5) + 1e-60)
    alpha = (1.0 - cl) / 2.0
    out = {}
    for q, k in ((alpha, "low"), (1.0 - alpha, "high")):
        from math import isnan
        z = _ncdf_inv(q)
        adj = _ncdf(z0 + (z0 + z) / (1.0 - a * (z0 + z)))
        idx = int(min(max(adj * (n_boot + 1) - 1, 0), n_boot - 1))
        out[k] = float(np.sort(boot)[idx])
    out.update({"cl": cl, "n_boot": n_boot, "theta": float(theta)})
    return out

def drawdown_quantiles(changes, returns, n_boot: int = 2000, seed: int = 42) -> dict:
    """Upper bounds {q_001,q_01,q_05,q_10} for max-DD cash and pct (pybroker drawdown_conf pattern)."""
    ch = np.asarray(changes, dtype=float); re = np.asarray(returns, dtype=float)
    if len(ch) < 20 or len(ch) != len(re):
        return {"cash": {}, "pct": {}, "note": "insufficient data"}
    rng = np.random.default_rng(seed)
    n = len(ch)
    bdd, bddp = np.empty(n_boot), np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        cs, rs = ch[idx], re[idx]
        cum = np.cumsum(cs); bdd[i] = float(-(np.maximum.accumulate(cum) - cum).max())
        eq = np.cumprod(1.0 + rs); bddp[i] = float(((eq / np.maximum.accumulate(eq)) - 1.0).min() * 100.0)
    bdd.sort(); bddp.sort()
    def q(a, p): return float(a[min(max(int(p * (n_boot + 1)) - 1, 0), n_boot - 1)])
    return {"cash": {"q_001": q(bdd,.001),"q_01": q(bdd,.01),"q_05": q(bdd,.05),"q_10": q(bdd,.10)},
            "pct": {"q_001": q(bddp,.001),"q_01": q(bddp,.01),"q_05": q(bddp,.05),"q_10": q(bddp,.10)},
            "n_boot": n_boot, "seed": seed}
```

Wiring (additive, informational): `validation.compute_metrics` and `run_full_backtest._compute_trade_metrics` append
`sharpe_ci_95=bca_ci(daily_rets)`, `dd_bounds=drawdown_quantiles(...)`; thresholds untouched.

### Diff 2 — NEW `src/backtest/cost_model.py` (~90 lines; FeeMode + bps + volume cap)

```python
"""Explicit cost model (pybroker FeeMode + Fixed/Volume slippage patterns, vendored).

Wraps existing ATR formula (run_historic_backtest:122-126) — default output byte-identical.
Causal rule: reads fill-bar slice only (pybroker end_index bound); warmup/NaN -> noop; 1% floor.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class FeeSchedule:
    mode: str = "none"  # order_percent | per_order | per_share | none
    amount: float = 0.0
    def fee(self, price: float, shares: float) -> float:
        if self.mode == "order_percent": return float(price) * float(shares) * self.amount
        if self.mode == "per_share": return float(shares) * self.amount
        if self.mode == "per_order": return float(self.amount)
        return 0.0

def apply_fixed_bps(side: str, price: float, bps: float = 0.0) -> float:
    if bps == 0: return float(price)
    if not 0 <= bps < 10000: raise ValueError("bps must be in [0, 10000)")
    m = 1.0 + bps / 1e4 if side == "buy" else 1.0 - bps / 1e4
    return max(float(price) * m, float(price) * 0.01)

def apply_volume_cap(shares: float, bar_volume: float | None, limit: float | None = 0.025,
                     price_impact: float = 0.0) -> tuple[float, float]:
    """Returns (fillable_shares, price_mult). Zero-volume + cap -> (0, 1.0). Square-law impact."""
    if (limit is None or limit <= 0) and price_impact <= 0: return float(shares), 1.0
    if bar_volume is None or not bar_volume > 0:
        return (0.0, 1.0) if limit else (float(shares), 1.0)
    sh = min(float(shares), limit * bar_volume) if limit else float(shares)
    mult = 1.0 + price_impact * (sh / bar_volume) ** 2 if price_impact > 0 else 1.0
    return sh, mult

def atr_slippage(existing_slippage: float, fill_price: float, warmup: bool = False) -> float:
    """Thin guard over the existing 0.05*ATR clamp: warmup/NaN -> 0; floor at 99% adverse."""
    if warmup or not fill_price or existing_slippage != existing_slippage:
        return 0.0
    return min(max(float(existing_slippage), 0.0), float(fill_price) * 0.99)
```

Wiring: `run_historic_backtest.run_backtest_with_params(..., cost_model: FeeSchedule|None=None, fixed_bps: float=0.0)` —
when both default, `actual_entry/exit` math unchanged (assert in tests); `custom_engine.__init__(..., fee_schedule=None, fixed_bps=0.0)` same contract.

### Diff 3 — `src/backtest/walk_forward_engine.py` (additive kwargs + splits in result)

```diff
--- a/src/backtest/walk_forward_engine.py
+++ b/src/backtest/walk_forward_engine.py
@@
-    def __init__(self, train_window_days=252, test_window_days=63, oos_min=0.40):
+    def __init__(self, train_window_days=252, test_window_days=63, oos_min=0.40, seed=42):
         self.train_window = train_window_days
         self.test_window = test_window_days
         self.oos_min = oos_min
+        self.seed = seed  # pybroker-adopt: reproducible window shuffle / bootstrap draws
         self.logger = logging.getLogger(__name__)
@@
     def validate(self, df, strategy_eval_func, oos_min=None, sharpe_floored=None,
+                 train_size=None, anchored=False, shuffle=False, purge=0, embargo=0):
+        """Additive WFA protocol (pybroker walkforward_split pattern).
+        Defaults preserve current behavior: train_size=None -> day-count windows;
+        anchored=False rolling; shuffle=False; purge/embargo=0 (delegates to
+        StatisticalValidator.combinatorial_purged_cv splits when >0). Thresholds unchanged.
+        """
+        # ... build splits honoring train_size/anchored/shuffle(seed) ...
+        # ... result gains "window_splits": [(train_start, train_end, test_start, test_end)] ...
```

Same additive treatment for `optimization/walk_forward.py:generate_windows(start, end, train_size=None, anchored=False)`.

### Diff 4 — NEW `src/backtest/optimization/optuna_tuner.py` (~80 lines; TPE bounded, ledger-first)

```python
"""Bounded Optuna TPE tuner (pybroker optimize.py pattern, vendored subset).

Rules: every evaluated config -> TrialLedger.append_experiment FIRST (N counts losers, DSR binding);
NaN/non-finite score -> trial FAIL (never best); trainable-model objectives refused; n_trials<=200; seed=42.
Skips fail-closed when `optuna` missing. Promotion still requires permutation+CPCV+WFO+DSR+Minerva.
"""
```

Wiring: `WalkForwardOptimizer.optimize(..., tuner="grid"|"tpe")` — `"grid"` preserves current path; `"tpe"` delegates per-train-window to `optuna_tuner.tpe_search` then replays best on test window; `params_per_window` returned for A3 audit.

### Diff 5 — docs/checklist only (no live change)

- `PAPER_BROKER_SETUP.md` appendix: pybroker parity checklist (canonical cols assert, unsupported-timeframe raise, cache key `(symbol,tf,range,ind)`, symbol-batched parallel) mapped to `validation.load_base_data`, `market_data_2019_2026/` loaders.
- `comprehensive_backtest_report.calculate_metrics`: extra informational keys (`sortino` already, + `calmar, ulcer_index, upi, equity_r2, annual_volatility_pct` via A6 formulas; `risk_tearsheet` untouched) + `return_signals/return_stops` opt-in flags for replay (default off).

## 7. Test plan (offline, deterministic, serial per SWARM config)

New `tests/backtesting/test_pybroker_adopt.py` (no network, no numba/optuna hard deps — skip-if-missing):

1. `test_bca_ci_known` — constant +0.001 series: `theta>0`, `low>0` at n=500/seed 42; alternating ±0.01: CI straddles 0; n=10 → `n_boot==0` note, no raise.
2. `test_bca_reproducible` — same seed twice → identical `low/high`; different seed may differ (assert not-equal OR document collision tolerance).
3. `test_drawdown_bounds_monotone` — `q_001<=q_01<=q_05<=q_10<=0` (cash) on synthetic drawdown series; empty → note, no raise.
4. `test_fixed_bps_math` — buy 100 @5bps → 100.05; sell → 99.95; 0 noop; ≥10000 raises.
5. `test_volume_cap` — shares 1000, vol 10000, limit 0.025 → 250; zero vol + cap → 0; no-vol-col (None) → passthrough with warning path.
6. `test_fee_schedule` — order_percent/per_order/per_share/none against hand-computed fills.
7. `test_cost_default_identical` — `run_backtest_with_params` on 30-day synthetic fixture with/without default `cost_model` → identical `return` col (byte parity); nonzero `fixed_bps=5` strictly worsens both legs.
8. `test_wfa_splits_additive` — `WalkForwardValidator.validate` on synthetic df returns `window_splits` matching legacy windows when defaults; `train_size=0.5/anchored/shuffle(seed)` deterministic and logged; thresholds (0.40/1.5/3/2-3) unchanged — one crafted failing case still FAILED.
9. `test_optuna_ledger_first` (skip if no optuna) — 10-trial TPE on fixture: `len(TrialLedger.load_trials())` grows by trials evaluated INCLUDING losers; NaN objective → FAIL not best; best replay OOS recorded.
10. `test_no_forbidden_edits` — `git status --porcelain` shows only `src/backtest/bootstrap_cis.py`, `cost_model.py`, `optimization/optuna_tuner.py`, modified WFA/report files + new test; `evolve_real.py`, `strategies/registry.json`, `strategies/` clean.

Commands (one file at a time, serial):

```
PYTHONPATH=. pytest tests/backtesting/test_pybroker_adopt.py -q
PYTHONPATH=. pytest tests/backtesting/test_walk_forward.py -q
ruff check src/backtest/bootstrap_cis.py src/backtest/cost_model.py src/backtest/optimization/optuna_tuner.py
bandit -r src/backtest/bootstrap_cis.py src/backtest/cost_model.py
```

Acceptance: 10/10 new pass (or skip-with-reason for optuna-missing), legacy WFA/validation/permutation suites green, ruff+bandit clean, cost-default parity test green, forbidden-files clean.

## 8. Rollout (for implementer, not done here)

1. Land Diff 1+tests 1-3 → report CIs informational one cycle (no gate change).
2. Land Diff 2+tests 4-7 → confirm parity, then capacity sweep consumes real costs.
3. Land Diff 3+test 8 → replay last promotion audit with splits attached.
4. Land Diff 4+test 9 (only if `optuna` approved as optional dep) → pre-register any TPE-motivated param change; full edge gate before registry.
5. Diff 5 docs/checks → no live change; `live_alpaca_executor` gates untouched.
6. Revisit Numba ONLY with `bench_backtest`-style profile proving hot loop + license review (Commons Clause).

## 9. References

- Upstream code (fetched raw 2026-09-09): `src/pybroker/config.py` (StrategyConfig: fees/leverage/interest/delays/bootstrap_samples), `slippage.py` (Fixed/Volatility/Volume + SlippageContext causal bound + floors), `eval.py` (BCa/njit/bootstrap_eval_all/EvaluateMixin), `optimize.py` (hyperparam lattice/TPE/grid/reseed/trainable-refusal/study audit), `vect.py` (njit kernels), `ext/data.py` (AKShare/YQuery strict timeframes), `benchmarks/bench_backtest.py` (pinned walkforward scenario + cold/JIT/cache benches), README (Alpaca/YFinance + walkforward + Optuna feature list).
- Actuals: `src/backtest/{base_engine,engine_base,run_historic_backtest,custom_engine,metrics,walk_forward_engine,permutation_tester,validation,whites_reality_check,validators/statistical,optimization/walk_forward,optimization/optimizer,defend/trial_ledger,defend/minerva_score}` + `src/execution/{base_broker,alpaca_broker,live_alpaca_executor,execution_adapter}` (line refs §1).
- Sibling study format: `_deliverables/pyfolio-adopt-2026-09-09.md` (additive diffs + test plan convention followed here).
