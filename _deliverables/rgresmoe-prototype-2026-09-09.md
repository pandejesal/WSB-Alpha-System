# RG-ResMoE Prototype Study — Regime-Gated Residual Mixture-of-Experts for Volatility Forecasting

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint.
Scope: prototype study for RG-ResMoE (soft regime routing over macro/market state variables; claimed 18.4% VaR coverage gain treated as **hypothesis to test, not verified fact**). Grounded in actual code: `src/risk/volatility_forecast.py` + `src/risk/crash_risk.py` + `src/risk/fred_macro_provider.py`. Proposes a soft-gating **adapter over the existing forecast (no rip-and-replace)**, regime features from FRED macro already present, and a VaR calibration test plan. Exact diffs + test plan below; nothing applied.

## 1. What was actually verified in-repo (read, not assumed)

- `src/risk/volatility_forecast.py:1-243` — graph-based vol forecast, numpy-only:
  - `forecast_volatility(returns)` contract (`:202-243`): `base_vol = std(returns,ddof=1)*sqrt(252)` → `build_correlation_graph` → `propagate_volatility(steps=3, decay=0.5)` → `classify_regime`. Returns `{forecasted_volatility, base_volatility, regime, adjacency}`.
  - `build_correlation_graph(:65-100)`: `abs(corrcoef)`, zero diagonal, threshold `DEFAULT_CORR_THRESHOLD = 0.30`; fail-closed on NaN (constant column), empty, `< MIN_OBS = 5` obs.
  - `propagate_volatility(:103-164)`: `vol_{t+1}[i] = (1-decay)*vol[i] + decay*neighbor_avg[i]`; isolated nodes keep own vol; validates `steps >= 0 int`, `decay in [0,1]`, non-negative finite `base_vol`.
  - `classify_regime(:167-199)`: mean-forecast-vol ladder `REGIME_THRESHOLDS = {calm: 0.10, normal: 0.20, elevated: 0.35, crisis: inf}`; neutral-`"normal"` fallback on empty/NaN/negative (never raises).
  - Tests: `tests/test_volatility_forecast.py` (233 lines) pins shape/diagonal/symmetry/sparsity, propagation convergence (`[0.5,0.1] → [0.3,0.3]`), regime bands, annualized-std identity.
- `src/risk/crash_risk.py:1-396` — compute-only option-implied crash score, numpy-only, no broker/network:
  - Inputs are caller-sourced IVs: `compute_iv_skew = OTMput − ATM (:179-189)`, `compute_put_call_skew = put/call (:192-204)`, `compute_term_structure_slope = back − front (:207-217)`.
  - Sub-scores 0–100 via `_score_from_range` with defaults `IVskew [2,8]pp`, `PCratio [1.0,1.5]`, `termSlope [−2,2]pp inverted`; composite `crash_risk_score = 0.4/0.3/0.3 weighted (:262-281)`; levels `LOW<40 <MODERATE<60 <ELEVATED<80 <HIGH`.
  - Contracts: `evaluate_crash_risk` raises on invalid/empty (`:326-362`); `crash_risk_gate` never raises — invalid → `NO_SIGNAL, trade_allowed=False (:365-396)`. Gate blocks trading at `score >= 60`.
- `src/risk/fred_macro_provider.py:1-180` (`src/risk/`, not `src/research/` — task path corrected):
  - `FredMacroProvider.get_regime(:72-120)`: fetches `T10Y2Y` (term spread) + `T10YIE` (breakeven inflation) via FRED observations API (`FRED_API_KEY`, 5 s timeout, 3 retries on 429/5xx); fail-closed to `{regime: NEUTRAL, confidence: 0.0, ...: None}` when key/data missing.
  - Heuristic labels already present: `spread<0 & infl>2.5 → STAGFLATION (0.8)`; `spread<0 → RISK_OFF (0.7)`; `spread≥0 & infl<2.5 → RISK_ON (0.6)`; else `NEUTRAL (0.4)`. `regime_multiplier(:122-138)`: RISK_ON 1.0 / NEUTRAL 0.8 / RISK_OFF 0.5 / STAGFLATION 0.4.
  - `get_historical_regimes(:140-180)`: keyless `fredgraph.csv?id=T10Y2Y|T10YIE` merge → `YYYY-MM-DD → regime` dict; empty dict on failure.
- Adjacent verified context:
  - `src/risk/position_sizer.py:84-140`: `RegimeDetector` (GK-vol bands), `RegimeAdjuster` (strong_bull…crisis multipliers), `MacroAdjuster` (expansion/slowdown/contraction/recovery/unknown) — the downstream consumers a vol-forecast adapter must not break.
  - `src/alpha/macro_regime.py`: SPY-vs-SMA200 `BULL/BEAR` filter (yfinance) — market-state source independent of FRED.
  - **Gap found**: no VaR module exists in-repo (search over `src/risk/*.py` finds only CVaR optimizer + semi-variance; no `VaR`, Kupiec, coverage, or quantile-calibration code). Any "18.4% VaR coverage gain" therefore has **no baseline to compare against yet** — §4 defines the baseline + metric from scratch so the claim becomes falsifiable.
  - `docs/OPTIMIZATION_PLAYBOOK.md` + `docs/HUNT_PROTOCOL.md` law (per AGENTS.md session discipline): pre-register → walk-forward OOS → permutation → DSR → ≥50 trades before any `registry.json` entry. This study proposes no registry entry.

## 2. RG-ResMoE design (soft-gating adapter, residual — no rip-and-replace)

Core idea: keep `forecast_volatility()` as the frozen base `f0` (tested contract, fail-closed graph), and learn a **small residual correction** routed softly by regime state `z`. Final forecast per asset `i`:

```
f[i] = f0[i] * (1 + clip(sum_k w_k(z) * r_k[i], -CAP, +CAP)),   CAP = 0.50 default
w(z) = softmax((W z + b) / tau),                                  tau = 1.0 default, K = 3 experts
```

- Why multiplicative residual + cap: vol is strictly positive; additive residuals risk sign flips on low-vol assets. Cap keeps the adapter a bounded overlay (max ±50%) so a broken gate cannot 10× position sizing downstream. `steps=0` equivalent = all `r_k = 0` → `f = f0` exactly (safe default + rollback switch).
- Why soft gating, not hard regime-switch: hard switches (`if STAGFLATION: use expert 2`) create discontinuity jumps at threshold boundaries (spread = 0, infl = 2.5) and starve experts of data. Softmax with temperature `tau` shares gradient across experts, degrades gracefully when FRED returns `None` (uniform weights), and is auditable (log `w(z)` per bar).
- Experts `r_k` (K=3, deliberately tiny — this is a risk overlay, not a forecaster):
  - E0 "calm-mean-reversion": shrinks `f0` toward cross-asset median (counters graph over-smoothing in calm; mirrors `propagate_volatility` neighbor-averaging direction).
  - E1 "stress-amplifier": expands `f0` proportional to recent realized-vol / forecast-vol ratio (under-forecast correction in elevated/crisis).
  - E2 "macro-tilt": affine tilt from standardized `(spread, inflation)` (inversion + high breakeven → wider vol).
  - Each expert is **linear/closed-form with ≤4 params** (total ≤ 12 + gate `W(3×d)+b`). Anything larger on a vol panel is overfit by construction.
- Regime features `z` (all already present in-repo — no new feeds):
  - From `FredMacroProvider.get_regime()`: `term_spread` (float|None), `inflation` (float|None), one-hot regime `{RISK_ON, NEUTRAL, RISK_OFF, STAGFLATION}` + `confidence`. Standardize spread/inflation with **train-fold-only** mean/std; `None` → 0.0 + missingness flag bit (fail-closed, never impute a fake macro number).
  - From `forecast_volatility()` output itself: `level = mean(f0)` (same scalar `classify_regime` uses), `dispersion = std(f0)/mean(f0)`, graph density `nnz(adj)/n²` — market-state variables with zero new dependencies.
  - Optional (caller-sourced only): `crash_risk_gate(...).score/100` when option IVs exist; absent → 0.0 + missing flag (module stays compute-only; adapter must not add network calls).
  - Target `d ≈ 8–10`: `[spread_z, infl_z, spread_missing, infl_missing, level_z, dispersion, density, crash_score, conf]`. All `z` clipped to `[-3, +3]` post-standardization.

## 3. Exact diffs proposed (NOT applied — study only)

### Diff 0 — NEW `src/risk/rgresmoe_adapter.py` (frozen-base adapter, numpy-only, fail-closed)

```python
"""Regime-gated residual MoE adapter over forecast_volatility (research-only).

f = f0 * (1 + clip(W_gate-routing over z applied to K linear residual experts)).
Fail-closed: any invalid input returns base f0 with uniform weights + reason.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from .volatility_forecast import forecast_volatility  # frozen base, never modified

K_EXPERTS = 3
RESIDUAL_CAP = 0.50
TAU = 1.0

@dataclass(frozen=True)
class RGResMoEParams:
    W_gate: np.ndarray      # (K, d)
    b_gate: np.ndarray      # (K,)
    A_exp: np.ndarray       # (K, d) expert loadings on z -> scalar residual per expert
    c_exp: np.ndarray       # (K,) expert biases
    tau: float = TAU
    cap: float = RESIDUAL_CAP
    z_mean: np.ndarray = field(default_factory=lambda: np.zeros(9))
    z_std: np.ndarray = field(default_factory=lambda: np.ones(9))

def softmax(logits: np.ndarray) -> np.ndarray:
    m = np.max(logits)
    e = np.exp((logits - m) / max(TAU, 1e-6))
    return e / max(np.sum(e), 1e-12)

def build_regime_features(*, term_spread, inflation, confidence,
                          level, dispersion, density, crash_score=0.0) -> np.ndarray:
    """Assemble raw z (length 9). None -> 0.0 + missing bit. No network here."""
    sm = 0.0 if term_spread is None else float(term_spread)
    im = 0.0 if inflation is None else float(inflation)
    return np.array([sm, im,
                     1.0 if term_spread is None else 0.0,
                     1.0 if inflation is None else 0.0,
                     float(level), float(dispersion), float(density),
                     float(crash_score), float(confidence)], dtype=float)

def adapt_forecast(returns: np.ndarray, z_raw: np.ndarray,
                   params: RGResMoEParams | None = None) -> dict:
    """Frozen base + optional residual. params=None -> pure base (rollback path)."""
    base = forecast_volatility(returns)  # raises on invalid returns (fail-closed, preserved)
    f0 = np.asarray(base["forecasted_volatility"], dtype=float)
    if params is None:
        return {**base, "adapted_volatility": f0.copy(),
                "gate_weights": np.full(K_EXPERTS, 1.0 / K_EXPERTS),
                "residual": np.zeros_like(f0), "adapter_active": False, "reason": "params-none"}
    z = np.clip((z_raw - params.z_mean) / np.maximum(params.z_std, 1e-12), -3.0, 3.0)
    if not np.all(np.isfinite(z)):
        return {**base, "adapted_volatility": f0.copy(),
                "gate_weights": np.full(K_EXPERTS, 1.0 / K_EXPERTS),
                "residual": np.zeros_like(f0), "adapter_active": False, "reason": "nonfinite-z"}
    w = softmax(params.W_gate @ z + params.b_gate)          # (K,)
    r = params.A_exp @ z + params.c_exp                      # (K,) scalar residual per expert
    mix = float(w @ r)
    mix = float(np.clip(mix, -params.cap, params.cap))
    f = f0 * (1.0 + mix)
    if not np.all(np.isfinite(f)) or np.any(f <= 0):
        return {**base, "adapted_volatility": f0.copy(),
                "gate_weights": w, "residual": np.zeros_like(f0),
                "adapter_active": False, "reason": "nonfinite-or-nonpositive"}
    return {**base, "adapted_volatility": f, "gate_weights": w,
            "residual": np.full_like(f0, mix), "adapter_active": True, "reason": "ok"}
```

- Design notes: `params=None` path **is** the current production behavior bit-for-bit (`adapted == forecasted`, uniform weights) — deploy adapter behind this flag; `adapter_active/reason/gate_weights` logged per bar for audit. No changes to `volatility_forecast.py`, `crash_risk.py`, `fred_macro_provider.py` signatures.
- Param init for walk-forward fit: all zeros (`W=0,b=0 → uniform w`; `A=0,c=0 → zero residual`) so optimization starts exactly at base forecast and must earn every deviation.

### Diff 1 — NEW `src/risk/var_calibration.py` (VaR from adapted vol + coverage tests; no baseline exists today)

```python
"""One-day parametric VaR from vol forecast + Kupiec/Christoffersen coverage tests."""
from __future__ import annotations
import numpy as np
from scipy.stats import norm, chi2  # only new dep; else hand-roll norm.ppf

def var_from_vol(vol_ann: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """1d 95% VaR (loss, positive) = z_{1-alpha} * vol_ann / sqrt(252)."""
    return norm.ppf(1.0 - alpha) * np.asarray(vol_ann, float) / np.sqrt(252.0)

def kupiec_pof(hits: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    """Likelihood-ratio POF test. Returns (LR, p-value). hits: 1 = exceedance."""
    n, x = len(hits), int(np.sum(hits))
    if n == 0 or x in (0, n): return float("nan"), float("nan")
    phat = x / n
    lr = -2*( (n-x)*np.log((1-alpha)/(1-phat)) + x*np.log(alpha/phat) )
    return lr, float(chi2.sf(lr, 1))
```

- Metric definition for the "18.4%" claim: **coverage-error reduction** `1 − |ê_adapt − α| / |ê_base − α|` at α = 5% pooled over walk-forward OOS bars, plus quantile (pinball) loss ratio. Report both; a gain on coverage with worse pinball loss = recalibration artifact, not skill (kill criterion §5.6).

### Diff 2 — NEW `tests/test_rgresmoe.py` (gates; run serially per swarm test policy)

```python
def test_params_none_is_bitwise_base(): ...
def test_nonfinite_z_falls_back_to_base(): ...
def test_residual_capped_at_50pct(): ...
def test_uniform_gate_when_W_zero(): ...
def test_var_exceedance_counts_match_manual(): ...
def test_kupiec_known_values(): ...  # x=5,n=100,alpha=.05 -> LR≈0, p≈1
def test_no_network_imports(): ...   # adapter imports forecast_volatility only
```

## 4. VaR calibration test plan (makes the claim falsifiable)

1. Baseline freeze: `f0` from `forecast_volatility` on trailing-60d returns window per asset, daily step; 1d 95% VaR via `var_from_vol`. No fitted params in baseline.
2. Folded walk-forward (respects `validation.py` 90d-window spirit, adapted to fitted params): **60d fit → 20d OOS**, step 20d, 2019–2026 daily panel (≥20 names to clear 50 exceedances: 5% × 20 × ~250 OOS bars ≈ 250 expected hits pooled). Fit `(W_gate, b, A, c)` on fit-window quantile loss only; freeze; score OOS. Standardization stats from fit window only.
3. Metrics per fold + pooled: empirical exceedance `ê`, coverage error `|ê−α|`, Kupiec POF p-value, Christoffersen independence LR (clustered violations = fail even with right unconditional rate), pinball loss at α=0.05, Diebold-Mariano vs base on pinball loss.
4. Permutation (inside `validation.py:318` thresholds): 200 within-window return shuffles of the **full fit→forecast→VaR pipeline**; beat-on-both (coverage error + pinball) p-values; pass requires `is_pval ≤ 0.01`, `wf_pval ≤ 0.05`.
5. DSR + record: `trial_ledger.py` DSR on OOS pinball-loss edge; `preregister.py` freeze/record honest PASS/ABANDON. Registry entry ONLY on pass (none proposed here).

## 5. Verdict: CONDITIONAL prototype-worthiness (adapter + VaR harness first, experts second)

- **Worth prototyping** as Diff 0 + Diff 1 + Diff 2 only: the adapter is ~80 lines, zero-dependency, rollback-trivial (`params=None`), reuses already-present FRED features, and fills a real gap (no VaR layer exists). Cost is one review cycle.
- **Not approved** (study cannot approve): fitting experts, claiming any "18.4% gain", or touching sizing/registry paths until §4 passes with kill criteria:
  1. Pooled OOS exceedances < 50 → abandon (underpowered).
  2. Kupiec rejects adapted VaR (p < 0.05) while base passes → abandon.
  3. Christoffersen rejects independence → abandon (right rate, wrong clustering = tail-risk failure).
  4. Pinball loss worse than base OR Diebold-Mariano p > 0.05 → abandon (coverage gain without loss gain = threshold gaming).
  5. Either permutation p-value over threshold, or DSR ≤ 0 → abandon.
  6. `|w − uniform|` mean < 0.02 across OOS (gate never routes) → simplify to single-residual, drop MoE.

## 6. Rerun / reproduce commands (evidence, study-only)

```bash
# grounding reads (no edits performed for this report)
PYTHONPATH=. python -c "from src.risk.volatility_forecast import forecast_volatility; help(forecast_volatility)"
PYTHONPATH=. pytest tests/test_volatility_forecast.py tests/test_crash_risk.py -q   # existing gates, serial
# future prototype gates (do NOT run now — files do not exist yet)
PYTHONPATH=. pytest tests/test_rgresmoe.py -q
ruff check src/risk/rgresmoe_adapter.py src/risk/var_calibration.py
bandit -r src/risk/rgresmoe_adapter.py src/risk/var_calibration.py
```

## 7. Risks & non-goals

- FRED `None` bars (no key / API fail) collapse `z` to missing-bits + uniform gate — correct fail-closed behavior, but OOS must include a no-key run to prove no silent outperformance from imputed macro.
- `get_historical_regimes` CSV fetch is a research convenience, not a pit-point-in-time feed (revision risk); walk-forward must lag macro by ≥1 day or use vintage data.
- Crash-score feature is optional and caller-sourced; adapter must never import a feed or broker (preserves `crash_risk.py` compute-only contract).
- Non-goals for any prototype task: editing `evolve_real.py`, `strategies/registry.json`, `strategies/`, `volatility_forecast.py`, `crash_risk.py`, `fred_macro_provider.py` logic; sleeve wiring; live-signal paths.
