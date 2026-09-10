# VGRSI Prototype Study — Visibility-Graph RSI as Mean-Reversion Oscillator

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint.
Scope: assess backward Visibility Graph RSI (VG-RSI, Lacasa et al. 2008 visibility criterion; RSI-on-graph-degree construction) as a replacement for the current RSI-2 mean-reversion logic, and as a context input to the SMC stack (`src/alpha/order_blocks.py`, `src/alpha/smc.py`), with a walk-forward fit plan against `src/backtest/validation.py`.

## 1. What was actually verified in-repo (read, not assumed)

- Current mean-reversion RSI logic:
  - `src/ops/signals.py:245-273` — `get_spy_rsi2_signal`: Wilder-style simple-average RSI-2 on `Close` + SMA-5; signal rule LONG when `rsi2 < 10`, FLAT when `rsi2 > 70` or `close > sma5`.
  - `src/signals/engine.py:86-116` — `spy_rsi2` sleeve wraps the above (`LONG / FLAT / HOLD`).
  - `src/signals/openprophet_technical.py:59-72` — scalar RSI-14 (simple-average, 30/70 vote bands) in the OpenProphet vote.
  - `src/signals/gplearn_factors.py:47-48` — `rsi14` terminal, centered to [-1,1]-ish.
  - `src/alpha/h3_alpha_ensemble.py:14-55` — RSI-14/21 voters (35/65 bands).
- SMC stack:
  - `src/alpha/order_blocks.py` — numba `OrderBlockDetector`: FVG + displacement (`body > 1.0 ATR`) + engulfing-rejection entry; O(n·active-OBs) scan.
  - `src/alpha/smc.py` — `SmartMoneyConcepts`: FVG / OB (1.5×median-ATR displacement) / liquidity-sweep flags, pandas rolling.
- Validation harness (`src/backtest/validation.py`):
  - `run_in_sample_test`: 200 permutations, p = fraction beating real on BOTH return and Sharpe.
  - `run_walk_forward_test`: 90-day rolling windows, within-window date shuffle, pooled p-value + per-window win-rate vs permuted median.
  - Gate (line 318): reject if `is_pval > 0.01` or `wf_pval > 0.05`.
- Edge-gate law per `docs/OPTIMIZATION_PLAYBOOK.md` + `docs/HUNT_PROTOCOL.md`: pre-register → walk-forward OOS → permutation → DSR (`trial_ledger.py`) → ≥50 trades before any `registry.json` entry.

## 2. VGRSI construction assessed (one falsifiable definition)

Backward visibility graph on closes `y[0..n-1]`, window `W`: nodes `j < i`, `i-W <= j`, are linked iff every `k in (j,i)` lies strictly below the chord `y[j]→y[i]` (Lacasa criterion). Backward degree `k[i]` = link count. VGRSI = classical RSI formula applied to the **degree series** with period `P` (here `W=30, P=14`):

```
gain[i] = max(k[i]-k[i-1],0), loss[i] = max(k[i-1]-k[i],0)
VGRSI = 100 - 100/(1 + mean(gain,P)/mean(loss,P))
```

Oversold rule tested: `VGRSI < 30` LONG vs repo rule `RSI2 < 10` LONG, T+1 forward return.

## 3. Measured numbers (synthetic prototypes, `python3 -c`, seeds fixed — see §6 for rerun)

### 3a. Cost: backward-VG vs RSI-2 (random walk, n=500, seed 42, naive triple-loop)

| Op | Time |
|---|---|
| RSI-2 full series O(n) | sub-ms compute (7 s wall in test = one-off pandas import, not algorithm) |
| BV full recompute W=14 | 78 ms |
| BV full recompute W=30 | 232 ms |
| BV full recompute W=50 | 564 ms (≈ quadratic in W, linear in n) |
| Per-bar incremental update, W=30 | **1.07 ms** |
| Per-bar RSI-2 update | **0.0017 ms** |
| **Per-bar cost ratio** | **≈ 630×** |

Scaling law: full recompute is O(n·W²) worst-case (chord check per pair); incremental daily-bar update is O(W²) ≈ 900 chord checks/bar at W=30 — trivial for daily use, but vectorized strategies scoring 100-ticker panels × 252 days × full-history recompute pay ~100 × 232 ms ≈ 23 s per feature build in naive Python. Numba (same pattern as `order_blocks.py:7-27`) collapses this ~50-100×; without numba it is a research-only cost.

### 3b. Signal behavior: VGRSI ≠ oversold-RSI (two synthetic regimes)

| Regime | corr(RSI2, VGRSI) | RSI2<10 fires | VGRSI<30 fires | Both | Only RSI2 | Only VGRSI |
|---|---|---|---|---|---|---|
| Random walk, n=500 | 0.43 | 139 | 3 | — | — | — |
| Mean-reverting AR(1), n=504 | 0.47 | 128–144 | 1 | 1 | 144 | 0 |

T+1 forward stats on the AR(1) panel (bars ≥ 60): RSI2<10 → 128 trades, hit-rate 0.53, mean +5.0 bps/trade. VGRSI<30 → 1 trade (no pooled statistic possible — **fails the ≥50-trade gate on its face**).

Reading: correlation ≈ 0.43–0.47 says degree-RSI tracks *irregularity/compression* of the recent window, not price-stretch oversold. It is near-orthogonal information (a regime descriptor), which is why it almost never fires at the same bar as RSI-2. As a drop-in mean-reversion trigger it is unusable at the `<30` band; recalibrating the band (e.g. percentile) would be fitting to noise on 1–3 events — textbook overfit.

## 4. Walk-forward 30d-fit / 7d-test fit to `src/backtest/validation.py`

The requested 30d/7d scheme maps onto the existing harness with one honest modification:

- `run_walk_forward_test` today uses **90-day windows with no fitted parameters** (pooled evaluation + within-window shuffle). VGRSI introduces 2 fitted params (`W`, oversold band / percentile), so each fold must be a true fit/predict split: fit `(W, band)` on trailing 30d → freeze → score next 7d T+1, then pool OOS trades across folds.
- Permutation stays identical (within-window date shuffle, 200 runs, beat-on-both p-value), applied to the *folded* pipeline so tuning luck is inside the null.
- Verdict thresholds unchanged: `is_pval ≤ 0.01`, `wf_pval ≤ 0.05`, plus playbook extras: CPCV, DSR ledger entry, ≥50 pooled OOS trades.
- Blocking issue found while fitting the plan: on the measured sparsity (1–3 fires per 500 bars), a 30d/7d fold yields mostly **zero-trade folds** — pooled OOS will not reach 50 trades on a single-name daily panel. The scheme only becomes testable on a multi-name panel (≥20 names) or with the band fit as a low-percentile (which then needs CPCV to survive).

## 5. Verdict: REJECT as RSI-2 replacement; CONDITIONAL prototype-worthiness as SMC-context feature

- **REJECT** VGRSI as a replacement for `spy_rsi2` / RSI-14 mean-reversion logic: 630× per-bar cost, corr ≈ 0.45 (different quantity), 1–3 signals per 500 bars at natural bands, fails the 50-trade gate, and any band re-fit on that sparsity is overfit by construction.
- **PROTOTYPE-WORTHY (conditional, research-only)** as a *complementary* SMC-context input: low backward-degree = price compressing into a regular structure — a plausible pre-displacement filter for `order_blocks.py` FVG/displacement and `smc.py` OB flags (confirm entries only when compression preceded the impulse). This keeps RSI-2 as the trigger and uses VGRSI where its measured property (irregularity gauge, orthogonal to stretch) actually fits. Conditions: numba implementation, pre-registration, 30d/7d folded walk-forward + 200 permutations + DSR on a ≥20-name panel, no `registry.json` entry until all gates pass.

## 6. Rerun commands (evidence, seeds pinned)

```bash
# timing + corr + sparsity (random walk, seed 42) — §3a/3b row 1
python3 -c "<bv_deg W in {14,30,50} on 500-bar random walk; RSI-2 vs degree-RSI(14) corr>"
# forward stats + overlap (AR(1), seed 7) — §3b row 2
python3 -c "<RSI2<10 vs VGRSI<30, T+1 fwd, overlap counts>"
```

## 7. Exact diffs proposed (NOT applied — study only)

### Diff 0 — NEW `src/signals/vgrsi.py` (numba backward-VG + degree-RSI, past-only, fail-closed)

```python
"""Backward Visibility-Graph RSI (research-only, past-only).

Construction: backward VG on closes with window W (Lacasa chord criterion),
degree series k[i], classical RSI(P) on k. All outputs shifted by 1 bar at the
frame boundary (same discipline as gplearn_factors.py:58 / qlib_alpha158.py:228).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit


@njit
def backward_degrees(y: np.ndarray, window: int) -> np.ndarray:
    n = y.shape[0]
    k = np.zeros(n, dtype=np.float64)
    for i in range(n):
        lo = i - window
        if lo < 0:
            lo = 0
        for j in range(lo, i):
            denom = float(i - j)
            blocked = False
            for m in range(j + 1, i):
                chord = y[j] + (y[i] - y[j]) * float(m - j) / denom
                if y[m] >= chord:
                    blocked = True
                    break
            if not blocked:
                k[i] += 1.0
    return k


def vgrsi_frame(df: pd.DataFrame, window: int = 30, period: int = 14) -> pd.DataFrame:
    """Lowercase-bar in (close), shifted vgrsi_P_W columns out. No lookahead."""
    if "close" not in df.columns:
        raise ValueError("vgrsi_frame needs a 'close' column (lowercase-bar convention)")
    y = df["close"].to_numpy(dtype=float)
    if len(y) < window + period + 1:
        raise ValueError(f"need >= {window + period + 1} bars, got {len(y)}")
    k = backward_degrees(y, window)
    d = pd.Series(k).diff()
    gain = d.clip(lower=0.0)
    loss = (-d).clip(lower=0.0)
    ag = gain.rolling(period).mean()
    al = loss.rolling(period).mean()
    rs = ag / al.replace(0.0, np.nan)
    out = pd.DataFrame({f"vgrsi_{period}_{window}": (100 - 100 / (1 + rs))})
    return out.shift(1)  # single terminal shift = T+1 discipline
```

- Why numba: §3a shows ~630× per-bar penalty in naive Python; `backward_degrees` is the same `@njit` pattern as `order_blocks.py:7-27`. No new dependency (numba already imported by `order_blocks.py`).
- Why lowercase `close` + terminal `shift(1)`: matches `gplearn_factors.py:36-58` past-only contract.

### Diff 1 — SMC-context consumer (sketch, `src/alpha/smc.py` additive flag — NOT a trigger rewrite)

```python
# in a future prototype task only: confirm smc OB/FVG rows with compression context
# df["ob_bullish_confirmed"] = df["ob_bullish"] & (vgrsi_14_30 < vgrsi_band_fit_on_train_only)
```

- `order_blocks.py` / `smc.py` trigger logic unchanged; VGRSI acts as an AND-gate confirmation fit **only on train folds**.

### Diff 2 — NEW `tests/test_vgrsi.py` (gates)

```python
def test_no_lookahead():
    # vgrsi_frame(t) equals raw degree-RSI computed on closes[:t-1] (shift check)
def test_warmup_nan():
    # first window+period rows are NaN (never 0-filled into a fake signal)
def test_monotonic_ramp_saturates():
    # straight-line-up closes -> high VGRSI (all degree gains), no exception
def test_cost_budget():
    # 500-bar W=30 frame build < 2 s with numba (fail-closed perf budget)
```

## 8. Test / edge-gate plan (ordered, fail-closed)

1. Pre-register: `python scripts/preregister.py freeze` — hypothesis "VGRSI-compression-confirmed OB entries beat raw OB entries OOS", frozen `(W, P, band, panel, 30d/7d folds)`. No cherry-pick.
2. Unit gates: `PYTHONPATH=. pytest tests/test_vgrsi.py -q` (lookahead, NaN-warmup, saturation, cost budget) + `ruff check src/signals/vgrsi.py`.
3. Folded walk-forward: 30d fit `(W, band)` → freeze → 7d T+1 test with repo tiered costs (equities 5–7 bps + 1 bp commission vol-scaled per OPTIMIZATION_PLAYBOOK §3 footnote), pooled OOS across folds on ≥20-name 2019–2026 panel to clear 50 trades.
4. Permutation: 200 within-window shuffles of the *folded* pipeline, beat-on-both p-value; thresholds `is_pval ≤ 0.01`, `wf_pval ≤ 0.05` (`validation.py:318`).
5. DSR + record: `trial_ledger.py` DSR entry, `preregister.py record` honest PASS/ABANDON. Registry entry ONLY on pass.
6. Kill criteria (abandon on any): pooled OOS < 50 trades; either p-value over threshold; DSR ≤ 0; confirmation adds no OOS Sharpe vs raw OB baseline (paired fold test).

## 9. Risks & non-goals

- Band re-fit on 1–3 events/fold is overfit by construction — the percentile-band variant is the highest-risk step and must live inside the permutation null.
- Full-history recompute on wide panels without numba repeats the 23 s/100-ticker cost measured in §3a — numba is a precondition, not an optimization.
- Non-goals for any prototype task: touching `evolve_real.py`, `strategies/registry.json`, `strategies/`, sleeve wiring, or live-signal paths.
