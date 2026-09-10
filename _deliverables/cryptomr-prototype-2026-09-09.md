# Short-Horizon Crypto Mean-Reversion Prototype — 15-min Cross-Sectional Reversal (Kitron/Wengrowicz grounding)

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint.
Workdir: repo root (`C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-build`).
External claim under test (per task brief, not re-verified here): Kitron/Wengrowicz-style 15-min-bar crypto mean-reversion — OOS AUC +0.0313 over equities baseline on 183 Binance USDT pairs, +0.011 residual after flat-bar/latency adjustment.

## 1. What was actually verified in-repo (read, not assumed)

### 1a. Factors/signals are daily-bar, T+1, one-bar-gap enforced

- `src/signals/qlib_alpha158.py:228-231` — all 47+ features `shift(1)` at frame boundary ("shifted by 1 to enforce T+1 execution"). `compute_alpha158` expects daily OHLCV (`date, open, high, low, close, volume`).
- `src/signals/gplearn_factors.py:36-58` — `build_terminals()` past-only, terminal `out.shift(1)`; `evolve():233` adds a *second* `shift(1)` on position (`pos = sign > 0 ... .shift(1)`) → T+1 fill discipline doubled.
- `src/signals/engine.py` — 7 sleeves, all daily: `us_momentum_top5`, `spy_sma200`, `spy_rsi2` (`rsi2 < 10` LONG, `src/signals/engine.py:86-116`), `btc_vol_target_sma100`, `us_lowvol_top30`, `us_pead_top5`, `breakout_burst`. No intraday sleeve, no timestamp-bucket logic, no cross-sectional z-score helper.
- `src/ops/signals.py:17-83` — `get_ta_rules_signal` sorts by `Date`, requires `len(df) < 60` skip, uses `iloc[-1]/iloc[-2]` decision/execution split. `src/backtest/run_historic_backtest.py:58-69` — `exec_date = business_day_offset(post_date,1)`, decision indicators computed on `entry_iloc - 1` (last closed bar). `src/backtest/validation.py:29-33` — tearsheet engine pinned to `run_historic_backtest` (fills at Open[t+1]); loud-fail if rebound to legacy same-bar engine.
- `src/alpha/leakage_guard.py:68-79,199-234` — `detect_future_data` + `guard_signals` fail-closed on any row after `as_of`. Any 15-min prototype must keep this contract at bar granularity, not day granularity.

Implication: the repo has a *correct* one-bar feature/label gap habit for **daily** bars. A 15-min factor must replicate it as **feature(bar t-1) → signal(bar t close) → fill(bar t+1 open or t+2 under latency model)**. Nothing in `src/signals/` does this today.

### 1b. Data path cannot serve 15-min bars today

- `src/data/providers/binance_public_provider.py:42` — `interval` hardcoded `"1d"`. `_normalize_symbol` maps `BTC-USD → BTCUSDT`, `_is_crypto` requires `-` + `USD/USDT`. Pagination is single-shot `limit: 1000` with no cursor loop — fine for ~4y daily (1460 bars needs 2 pages already), broken for 15-min (96 bars/day; 1 year ≈ 35k bars ≈ 35 pages/pair; 183 pairs ≈ 6.4M bars).
- `src/data/providers/chain.py:14-29` — `Alpaca → Tiingo → BinancePublic → YFinance`. `fetch_ohlcv(tickers, start, end)` takes **no timeframe/interval argument**; every provider is called in daily mode. `MarketDataManager.fetch_data(..., timeframe='1d')` accepts a timeframe but `chain.fetch_ohlcv` drops it (`src/data/market_data.py:19-41`).
- `src/data/cache_engine.py` (via `chain.determine_missing_ranges`) — daily-range cache keyed by ticker/date; no bar-interval dimension. Storing 15-min panels in the same cache without an interval key would poison daily reads.
- Live crypto path (`src/execution/live_crypto_executor.py:13-14`) is a **daily 00:01 UTC cron** for 3 tickers (`BTC/ETH/SOL-USD` → Bybit perps via ccxt). No intraday scheduler, no 15-min poll loop, no bar-close alignment.

Implication: 15-min work needs (a) interval-parameterized Binance fetch + pagination, (b) interval-aware cache key, (c) explicit statement that live intraday execution is out of scope for the prototype (research/backtest only).

### 1c. Execution/latency gaps the paper's +0.011 adjustment maps onto

- `src/execution/execution_bridge.py:16-41` — `execute_signal` places `market` orders with zero latency/slippage modeling; sizing via `PositionSizer`, breaker check only. No queue, no partial-fill, no flat-bar filter.
- `src/execution/paper_executor.py` — idempotent daily `plan.json → orders.json → fills.json` executor; assumes one decision per day.
- Cost model (verified per `docs/OPTIMIZATION_PLAYBOOK.md §3` + `config/risk_config.py:18-32`): equities 5–7 bps slippage + 1 bp commission, BTC 15–25 bps + 1 bp, vol-scaled `cost = base + commission + (vol_scalar-1).clip(0)*scale`, fallback 5 bps never 0, +10 bps borrow guard if short. Calibrated on **daily** closes. At 15-min horizons a 15–25 bp one-way cost dominates a few-bps-per-trade reversal edge — the prototype must carry costs explicitly and report net-of-cost as primary.
- Current validation (`src/backtest/validation.py:35+`, `walk_forward_engine.py:20-58`, `permutation_tester.py`) uses **iid within-window date shuffle** (200 perms, beat-on-both return+Sharpe, gates `is_pval ≤ 0.01`, `wf_pval ≤ 0.05`). Shuffling 15-min bars iid destroys the very autocorrelation a reversal factor monetizes → p-values would be fake-pass. Must be replaced by **moving-block bootstrap** for this family (see §3).

## 2. Proposed factor: 15-min cross-sectional reversal with hour-of-day vol normalization

Falsifiable hypothesis (pre-registration ready): *"On a liquid Binance-USDT 15-min panel, pairs with the lowest hour-normalized trailing return over lookback L rank lower cross-sectionally and outperform the highest-ranked pairs over the next 15-min bar, net of tiered costs, after skipping one bar for latency and excluding flat bars."*

### 2a. Exact construction (one definition, no variants in prototype)

Inputs per pair `i`, bar timestamp `t` (UTC, 15-min close-aligned, 96 bars/day, crypto 24/7 → hour-of-day bucket `h(t) ∈ {0..95}` = `hour*4 + minute//15`):

1. `ret[i,t] = close[i,t]/close[i,t-1] - 1`. Drop bars with `volume == 0` or `high == low == close` (flat-bar filter; mirrors the paper's flat-bar adjustment — report gross **and** filtered side by side).
2. Trailing signal return: `R[i,t] = close[i,t]/close[i,t-L] - 1`, default `L = 12` bars (3 h). Pre-register `L ∈ {4, 12, 24}` sweep max; winner chosen on train folds only.
3. Hour-of-day vol normalization: `sigma[i,h] = median over trailing D=30 days of |ret[i, τ]| for bars τ in bucket h` (robust, per-pair-per-bucket; minimum 30-day warmup, NaN before). Normalized move `Z[i,t] = R[i,t] / max(sigma[i,h(t)]*sqrt(L), eps)` with `eps = 1e-8` (fail-closed: NaN sigma → NaN signal → FLAT, never 0-filled).
4. Cross-sectional reversal score at each `t`: `S[i,t] = -zscore_i(Z[:,t])` where zscore is cross-sectional `(Z - median)/(MAD*1.4826)` (robust to outliers; fallback std if MAD=0). Higher `S` = more oversold-relative-to-panel = predicted outperformer.
5. Trading rule (long-short, dollar-neutral): each bar, rank `S[:,t]`, go long bottom-decile losers / short top-decile winners (decile of liquid panel, min 20 tradable names/bar else FLAT), hold 1 bar. **Latency enforcement**: signal computed on closes through `t-1` only (`shift(1)`), order staged at close `t`, filled at open `t+1`; latency-sensitivity variant fills at open `t+2` (one extra bar skip) — the paper's latency adjustment. Primary verdict uses the `t+2` fill; `t+1` reported as sensitivity only.
6. Costs applied per fill at repo tiers: BTC majors 15–25 bps + 1 bp, alts same BTC tier (conservative; no cheaper alt tier invented), vol-scaled per `risk_config`. Report gross, net-`t+1`, net-`t+2`.

Why hour-of-day normalization: crypto has a persistent intraday vol season (US/EU/Asia overlap, funding windows). Raw reversal confounds "large move" with "high-vol hour". Per-bucket sigma removes the seasonal so `S` compares *abnormal* moves. This is the prototype's only novelty over a naive past-return reversal and must be ablated (raw vs normalized) in validation.

### 2b. Universe & data spec (mirrors the 183-pair claim without inventing it)

- Universe: Binance USDT spot klines, 15-min, trailing 2 years minimum; liquidity filter pre-registered (median daily notional top-200 → intersect with ≥90% bar completeness → cap at 183 to match paper scale; exact N recorded, never tuned to maximize AUC).
- Source: `data-api.binance.vision/api/v3/klines` with `interval=15m` + paginated cursor (new code, §4 Diff 0). No Alpaca/Tiingo/YFinance for this family (they lack 15-min crypto depth). Cache under `database/cache/crypto_15m/` with interval in key (never the daily cache).

## 3. Validation: moving-block bootstrap (why, exactly how)

Why blocks, not the repo's iid shuffle: 15-min returns are autocorrelated (bid-ask bounce, vol clustering, funding effects). Iid permutation whitens the null → even noise looks "significant" against a whitened null → fake PASS. Moving-block bootstrap preserves local dependence inside blocks while breaking signal/label alignment across blocks.

Pre-registered procedure:

1. Fold structure: expanding-train / rolling-test on **time-ordered** bars — e.g. 6-month train (fit `L`, decile, sigma warmup) → 1-month test, step 1 month. Fit *only* on train; freeze; score test with `t+2` fills and costs. Pool OOS test bars.
2. Metric: primary = OOS long-short spread (bps/bar, net-`t+2`) + AUC of `S` vs next-bar return sign (matches paper's AUC language); secondary = Sharpe (annualized on 15-min grid), hit-rate, turnover, ≥50 pooled OOS trades gate retained (trivially cleared at 15-min — gate becomes ≥500 test bars with ≥20 names each instead; record both).
3. Null: circular moving-block bootstrap over the **panel jointly** (same block offsets for all pairs → preserves cross-sectional correlation): block length `B = 96 bars` (1 day; sensitivity `B ∈ {48, 480}` = 12 h / 5 d reported). `M = 500` resamples (heavier than repo's 200 because per-resample cost is a cheap vector op). For each resample: block-resample the return panel, recompute `S` through the identical pipeline (sigma, zscore, decile, `t+2` fill, costs), record spread/AUC. p-value = fraction of resamples ≥ realized on **both** spread and AUC (same beat-on-both conjunction as `validation.py`).
4. Thresholds unchanged: `is_pval ≤ 0.01`, block-bootstrap p ≤ 0.05, DSR ledger entry (`trial_ledger.py`), honest ABANDON otherwise. Ablation required: normalized vs raw `R` must win paired across folds, else the hour-normalization claim is rejected even if raw reversal passes.

## 4. Exact diffs proposed (NOT applied — study only)

### Diff 0 — NEW `src/signals/cryptomr_15m.py` (past-only, fail-closed, no sleeve wiring)

```python
"""15-min cross-sectional crypto reversal (research-only, past-only).

Pipeline: ret -> trailing R(L) -> per-pair-per-96-bucket sigma (30d median |ret|)
-> robust cross-sectional z -> S = -z. Every frame shifted by 1 bar at the
boundary (same discipline as qlib_alpha158.py:228 / gplearn_factors.py:58).
Flat bars (vol==0 or high==low) -> NaN, never 0-filled. Fills modeled by the
caller at t+1 (sensitivity) and t+2 (primary latency-adjusted).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

N_BUCKETS = 96
EPS = 1e-8

def trailing_R(close: pd.DataFrame, L: int) -> pd.DataFrame:
    return close / close.shift(L) - 1

def bucket_sigma(ret: pd.DataFrame, bucket: pd.Series, days: int = 30) -> pd.DataFrame:
    # median |ret| per (pair, bucket) over trailing days*96 bars; past-only rolling
    out = pd.DataFrame(np.nan, index=ret.index, columns=ret.columns)
    span = days * N_BUCKETS
    absret = ret.abs()
    for b in range(N_BUCKETS):
        m = (bucket == b).astype(float)
        masked = absret.where(m.astype(bool))
        out = out.combine_first(masked.rolling(span, min_periods=span // 2).median())
    # NOTE: prototype-grade loop; vectorize (groupby-transform) before any panel >50 pairs.
    return out

def reversal_score(close: pd.DataFrame, volume: pd.DataFrame,
                   L: int = 12, vol_days: int = 30) -> pd.DataFrame:
    ret = close.pct_change()
    flat = (volume == 0) | (close.diff().abs() == 0)  # caller ORs high==low where available
    R = trailing_R(close, L)
    bucket = pd.Series((close.index.hour * 4 + close.index.minute // 15) % 96, index=close.index)
    sig = bucket_sigma(ret, bucket, vol_days)
    Z = R / (sig * np.sqrt(L) + EPS)
    Z = Z.mask(flat)
    med = Z.median(axis=1)
    mad = (Z.sub(med, axis=0)).abs().median(axis=1) * 1.4826
    S = -(Z.sub(med, axis=0)).div(mad.replace(0, np.nan), axis=0)
    return S.shift(1)  # single terminal shift = one-bar feature/label gap
```

- Hour bucket uses UTC 15-min close timestamps; DST-irrelevant (crypto 24/7).
- Warmup NaNs propagate (never filled) → thin-history pairs naturally FLAT.

### Diff 1 — Binance 15-min fetch (sketch; touches `binance_public_provider.py` + cache key only, prototype task)

```python
# provider: add interval param + paginated cursor over startTime/endTime in 1000-klines pages
# def fetch_ohlcv(..., interval: str = "1d")  # default preserves daily callers
# cache: key = sha256(f"{ticker}_{start}_{end}_{interval}") + subdir crypto_15m/ for 15m
```

- `chain.fetch_ohlcv` gains optional `interval` passthrough (default `"1d"` → zero behavior change for daily sleeves). Prototype task only.

### Diff 2 — NEW `tests/test_cryptomr_15m.py` (gates)

```python
def test_one_bar_gap():      # score(t) == raw pipeline on closes[:t-1]
def test_flat_bars_nan():    # zero-volume bars -> NaN score, never a trade
def test_warmup_nan():       # first 30d of buckets NaN (sigma warmup, no fake signal)
def test_bucket_seasonality():  # synthetic 2x-vol bucket -> normalized |Z| equalized vs raw
def test_latency_fill_ordering():  # t+2 fill <= t+1 fill歓迎 (no lookahead profit)
```

### Diff 3 — NEW `scripts/validate_cryptomr_blocks.py` (research script, not wired to registry)

Expanding-train/rolling-test folds + circular joint-panel block bootstrap (`B=96`, `M=500`, beat-on-both p), gross vs net-`t+1` vs net-`t+2`, raw-vs-normalized ablation. Reads the 15-min cache, writes `docs/data/cryptomr_15m_eval.json`. Never touches `run_historic_backtest` daily path.

## 5. Test / edge-gate plan (ordered, fail-closed)

1. Pre-register: `python scripts/preregister.py freeze` — hypothesis §2 + frozen `(universe rule, L ∈ {4,12,24}, decile, B=96, M=500, t+2 primary, cost tier)`. No cherry-pick.
2. Unit gates: `PYTHONPATH=. pytest tests/test_cryptomr_15m.py -q` + `ruff check src/signals/cryptomr_15m.py` + `bandit -r src/signals/cryptomr_15m.py`.
3. Data audit: completeness per pair (≥90% of expected 96/day), flat-bar rate, corporate-action sanity (splits n/a crypto; stablecoin pairs USDT/USDC/BUSD excluded by rule — reversal on pegged pairs is artifact).
4. Folded OOS: 6-month train / 1-month test rolling, `t+2` net spread + AUC primary; report `t+1` and gross as sensitivities (expect decay gross → net-`t+1` → net-`t+2`, mirroring +0.0313 → +0.011).
5. Block bootstrap: 500 joint-panel resamples, beat-on-both p; thresholds `≤0.01 / ≤0.05`; DSR ledger entry; `preregister.py record` honest PASS/ABANDON.
6. Kill criteria (abandon on any): net-`t+2` spread ≤ 0; either p-value over threshold; DSR ≤ 0; normalized fails to beat raw paired across folds; flat-bar exclusion erases the edge (then the "edge" was stale-quote artifact).

## 6. Risks & non-goals

- Cost dominance: at 15-min frequency even BTC-tier 16–26 bps one-way can exceed per-trade edge; size turnover accordingly (decile + 1-bar hold = ~100% turnover/bar on traded names). Report bps/trade prominently.
- Survivorship/selection: 183-pair panels invite listing-bias (dead pairs drop out). Freeze the historical constituent rule at train-start dates; never use end-of-sample listings for early folds.
- Shorts on spot: prototype scores long-short spreads; live spot cannot short — any future live mapping needs perps (`live_crypto_executor.py` Bybit path) and funding-rate deduction, explicitly out of scope here.
- Non-goals for any prototype task: touching `evolve_real.py`, `strategies/registry.json`, `strategies/`, sleeve wiring, daily cache keys, or live-signal paths. No registry entry until all gates pass.

## 7. Rerun / grounding checklist (evidence)

- `src/signals/qlib_alpha158.py:228-231` shift(1); `src/signals/gplearn_factors.py:58` shift(1); `src/signals/engine.py:86-116` daily sleeves; `src/data/providers/binance_public_provider.py:42` hardcoded `1d`; `src/data/providers/chain.py:31` no-interval chain; `src/execution/execution_bridge.py:16-41` zero-latency market fill; `src/execution/live_crypto_executor.py:13-14` daily 00:01 UTC cron; `config/risk_config.py:18-32` tiered costs; `src/backtest/run_historic_backtest.py:58-69` Open[t+1] fill; `src/backtest/validation.py:29-33` tearsheet-engine pin; `src/alpha/leakage_guard.py:68-79` future-data block; `docs/OPTIMIZATION_PLAYBOOK.md §3` + `docs/HUNT_PROTOCOL.md §4` edge-gate law.
