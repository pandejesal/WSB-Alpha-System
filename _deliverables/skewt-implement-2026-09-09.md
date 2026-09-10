# Skew-Elliptical-t Option Portfolio Optimization (Sung/Pirvu) — VRP Sleeve Implementation Study — 2026-09-09

Date: 2026-09-09
Status: STUDY ONLY — zero tracked files edited. New deliverable file only.
Scope: workdir-only. Read-only survey of actual VRP/options code, `position_sizer` tail-risk hooks, optimizer higher-moment blending.
Paper: Sung & Pirvu — skew-elliptical-t (`GHST`) closed-form Sharpe-ratio and return-to-VaR maximization for option portfolios.
Claimed paper effects (to re-verify in validation, NOT asserted as repo fact): tail VaR −27.3% vs Gaussian plug-in, OOS Sharpe +0.42 on option-sleeve backtest.

## 0. Repo truth (read-only, verified paths)

### 0.1 No VRP sleeve exists today

- `strategies/registry.json` (8781 lines surveyed): families present are `spy_rsi2`, `spy_sma` (+ `FAMILIES` list in `evolve_real.py` per `_deliverables/papers-implement-2026-09-09.md:42-55`: `spy_sma, spy_rsi2, btc_vol, btc_donchian, us_momentum, us_lowvol, spy_ltrend, us_ltrend, gap_mr, btc_regime`). No `vrp`, `options`, `vol_premium`, or `short_vol` family, spec YAML, or registry entry.
- `src/signals/engine.py` + `src/ops/signals.py` (per papers study §0): 7-sleeve `SignalEngine` delegating to `src/ops/signals.py`; no VRP/options-sleeve signal function (`get_sentiment_overlay_signal`, `get_ta_rules_signal`, debate overlay only).
- `src/ops/portfolio.py` (`PortfolioManager`, per papers study §0): 7 sleeves, 60% exposure cap / 40% cash buffer, equal-risk nominal per sleeve. Adding a VRP sleeve changes sleeve count, per-sleeve nominal, and exposure-cap math — must be explicit in Diff 3.
- Implication: skew-t work is **new-sleeve + new-formula-module** work, not a knob tune. It cannot be expressed as a `src=bred` line (`family IN FAMILIES AND set(params)==set(SPACES[family])`, `evolve_real.py:617-622`). Any bred proxy is timing-envelope only; real edge needs a pre-registered new family per `docs/HUNT_PROTOCOL.md` §1–§4 + `docs/OPTIMIZATION_PLAYBOOK.md` §3 gates 1–5.

### 0.2 Actual options/vol code (all compute-only, no chain feed)

| File | What it actually does | Relevance / gap for skew-t |
|---|---|---|
| `src/risk/crash_risk.py:1-396` | Pure numpy IV-skew signals: `compute_iv_skew` (OTM-put IV − ATM IV), `compute_put_call_skew` (put IV / call IV), term-slope, `crash_risk_score` (default weights `(0.4,0.3,0.3)`), `evaluate_crash_risk` (raises on bad input), `crash_risk_gate` (never raises; `NO_SIGNAL` + `trade_allowed=False` on bad input). Calibs: `DEFAULT_IV_SKEW_LOW/HIGH 2.0/8.0`, `PUT_CALL 1.0/1.5`, `TERM −2/2`, gate `60.0`. | Closest existing options-surface consumer. Takes IV **inputs** from caller — never touches broker/chain/network (docstring lines 9–11). Skew-t module should follow this exact hermetic pattern: caller supplies surface/returns, module returns weights + VaR. `crash_risk_gate` is the template for a fail-closed `skewt_gate`. |
| `src/risk/volatility_forecast.py:1-243` | Graph-based vol forecast: cross-asset correlation graph (`DEFAULT_CORR_THRESHOLD 0.30`, `MIN_OBS 5`, `ANNUALIZATION 252`), numpy-only propagation, regime label from cross-asset vol level (`calm 0.10 / normal 0.20 / elevated 0.35 / crisis inf`). Fail-closed on empty/NaN/non-2D. | Provides `regime` input the sizer already consumes. Gives the `nu` (df) / vol-level conditioning hook: crisis regime → heavier tails (smaller `nu`). Does NOT estimate skew (`gamma`) or df — gap Diff 1 fills. |
| `src/backtest/validation.py:343-364` | Extra metrics: `VaR(95)`, `VaR(99)`, `CVaR(95)`, max-DD duration (empirical quantile, Gaussian-free). | Empirical VaR/CVaR is the validation comparator for closed-form skew-t VaR. Do NOT replace; use as ground-truth check in Diff 4. |
| `src/backtest/gatespec38_tracks.py:126-137` | `tail_risk_sentinel` track: `max_dd<=0.25` institutional tail protection. | The track a VRP sleeve must clear; skew-t VaR-ratio sizing directly targets this. |
| `src/backtest/defend/trial_ledger.py:21` | DSR normal-returns variant (skew 0, kurt 3). | DSR gate assumes normality — conservative for skew-t sleeve; record as known bias in Diff 4 (do not edit ledger in this plan). |

No file fetches an option chain, computes realized-vs-implied (VRP), or prices options. There is no `src/signals/*vrp*`, `src/alpha/*option*`, or `strategies/*vrp*`. Grep for `vrp|volatility risk premium|implied_vol|realized_vol` returns only crash-risk IV-skew hits — confirming the gap.

### 0.3 Position-sizer tail-risk hooks (actual code)

1. `src/risk/position_sizer.py` (319 lines, primary Kelly path):
   - `KellyCalculator.kelly_fraction` (`f*=(p*b−q)/b`), `semi_variance_adjustment` (`1 − downside_var/(avg_win²+downside_var)`, floor 0.1), `raw_kelly`, `adjusted_kelly`.
   - `RegimeAdjuster.REGIME_MULTIPLIERS` (`strong_bull 1.0 … crisis 0.1`), `MacroAdjuster` (`expansion 1.0 … contraction 0.6`), `ConfidenceAdjuster` (<20 trades ×0.5, <50 ×0.75), `KellyBoostAggregator.aggregate` (weighted mean + variance diversification bonus capped +5%, gated via `config/risk_config`).
   - `PositionSizer.size_position` → `_kelly_size` (9 steps: raw → semi-var → confidence → regime → macro → KellyBoost blend → half-Kelly `KELLY_FRACTION=0.5` → `MAX_NOTIONAL_LEV=1.0` cap → shares) vs `_atr_fallback_size`. `TradeStats.downside_var` is the existing tail hook — skew-t VaR ratio plugs in here or as a parallel multiplier (Diff 2).
2. `src/risk/portfolio_manager.py:27-203` (`KellySizer` quarter-Kelly `0.25`, `max_position_pct 0.20`, `min_edge 0.01`, dual-constraint `MIN(confidence, Kelly)`).
3. `src/risk/position_sizing.py:35-113` (micro-account `PositionSizer`: fractional Kelly `0.15`, `MAX_RISK_PER_TRADE_PCT 0.01`, `MAX_POSITION_SIZE_PCT 0.25`, `MAX_CONCURRENT_POSITIONS 4`; breakers disabled default `1.0`).
4. `config/risk_config.py:1-32` (single source: `MAX_NOTIONAL_LEV 1.0`, `HALF_KELLY 0.5`, `BASE_RISK_PCT 0.02`, `MAX_POSITION_PCT 0.20` + cost tiers).

Hook conclusion: the cleanest insertion is a **VaR-ratio multiplier** (`skewt_var / gaussian_var` at same α, capped, fail-closed to 1.0) applied at `PositionSizer._kelly_size` step 5.5 (after macro, before KellyBoost) OR threaded through `TradeStats.downside_var`. No signature break: add optional `tail_multiplier: float = 1.0` param + `SkewtTailAdjuster` class. Cap mandatory (see Diff 2).

### 0.4 Optimizer higher-moment blending (actual code)

- `src/risk/portfolio_optimization.py:15-108` (`PortfolioOptimizer`: `optimize_cvar`, `optimize_erc` via `riskfolio-lib`, `method_mu='hist'`, `method_cov='hist'`, `max_weight 0.25`, `min_cash 0.10`, cap-and-redistribute loop). Mean + covariance only — **no skew, kurtosis, df, or GHST parameters**. Hist-cov is Gaussian-equivalent for weighting; CVaR objective helps tails but weights still come from second moments.
- `src/backtest/optimization/optimizer.py:1-53` (`GridSearchOptimizer` by `sharpe`, `BayesianOptimizer` L-BFGS-B minimizing −sharpe). Sharpe-only objective — blind to higher moments; skew-t sleeve needs VaR-aware objective or post-hoc VaR-ratio gate (Diff 3/4).
- Blending conclusion: do NOT fork `PortfolioOptimizer`. Add a **sleeve-level blender**: `w_final = (1−λ)·w_cvar + λ·w_skewt` with `λ` from crash-risk/IV-skew regime (calm → small λ, elevated → larger λ), capped, logged. Keeps riskfolio path intact; skew-t weights come from hermetic formula module (Diff 1).

## 1. Paper mapping (Sung/Pirvu → repo)

Paper result (per task brief): option returns modeled as generalized hyperbolic skew-t (`GHST(μ, Σ, γ, ν)`); **closed-form** max-Sharpe weights and max–return-to-VaR weights; backtest −27.3% tail VaR vs Gaussian plug-in at same return, +0.42 OOS Sharpe on equity-index options.

| Paper object | Repo counterpart (new or hook) | Notes |
|---|---|---|
| GHST params `(μ, Σ, γ, ν)` from option-strategy returns | New `src/risk/skewt_formulas.py` estimators (MOM + optional MLE-lite, numpy/scipy-only) | Inputs: sleeve return panel (synthetic surfaces in tests; realized option-strategy returns in prod — NOT live IV fetch). No network. |
| Closed-form max-Sharpe `w*(μ,Σ,γ,ν)` | `skewt_sharpe_weights()` pure function | Falls back to `Σ⁻¹μ` Gaussian plug-in when `γ≈0` or `ν→∞`; unit test asserts convergence. |
| Closed-form max–return-to-VaR `w*(VaR_α)` | `skewt_var_weights(alpha)` + `skewt_var(weights, alpha)` | α=0.05 default (matches `PortfolioOptimizer(alpha=0.05)`). VaR ratio `skewt_var/gaussian_var` is the sizer signal. |
| −27.3% VaR claim | Diff 4 empirical check: closed-form VaR vs `validation.py` empirical quantile + Gaussian VaR on same synthetic panel | Pass bar: direction + materiality (e.g. ≥15% VaR cut at matched return), not exact −27.3% (sample-dependent). |
| +0.42 OOS Sharpe | Walk-forward sleeve backtest, T+1, tiered costs (`OPTIMIZATION_PLAYBOOK.md` footnote: equities 5–7bps+1bp, BTC 15–25bps+1bp, floor 5bps) | Must pass `tail_risk_sentinel` + overlays (`perm_p≤0.05`, `boot_p≤0.05`, DSR per `FAM_TRIALS`) before any registry write. |

Assumptions (explicit): (a) VRP sleeve = short-volatility / put-write proxy on SPY (liquid, matches existing `spy_*` universe); (b) α=0.05 throughout; (c) `ν∈(4,20]`, `γ` bounded (fail-closed clamps); (d) no new broker/chain integration — surfaces are caller-supplied arrays, mirroring `crash_risk.py` contract.

## 2. Staged plan — Diff 1–4 (each diff independently revertible, hermetic first)

### Diff 1 — Formula module, hermetic (`src/risk/skewt_formulas.py` NEW; `tests/test_skewt_formulas.py` NEW)

- New pure module, numpy (+ scipy if already required, else numpy-only MOM) — **no imports from `src.ops`, `src.signals`, `src.execution`, `src.data`; no network, no disk, no broker**. Mirror `crash_risk.py` header contract.
- API (proposed, frozen at implementation):
  - `estimate_ghst_params(returns: np.ndarray) -> GHSTParams(mu, Sigma, gamma, nu)` — MOM closed-form; `nu` clamped `[4.01, 20]`; `gamma` shrunk toward 0 when `n_obs < 60`; raises `ValueError` on empty/NaN/short panel (`MIN_OBS=20`).
  - `skewt_sharpe_weights(params) -> np.ndarray` — closed-form Sung/Pirvu; long-only + sum-to-1 projection helper `project_long_only()`; falls back to Gaussian `Σ⁻¹μ` when `‖γ‖<1e-6` or `ν>19.9`.
  - `skewt_var(weights, params, alpha=0.05) -> float`, `gaussian_var(weights, mu, Sigma, alpha) -> float`, `var_ratio(...) -> float` (skewt/gaussian; `NaN→1.0` never propagates).
  - `skewt_var_weights(params, alpha=0.05) -> np.ndarray` — closed-form return-to-VaR max.
  - `skewt_gate(var_ratio, iv_skew_score) -> (allowed: bool, tail_multiplier: float)` — never raises; invalid → `(False, 1.0)` mirroring `crash_risk_gate`.
- Constants single-sourced where possible (`ALPHA=0.05` matches `PortfolioOptimizer`; `NU_MIN/MAX`, `GAMMA_SHRINK_N` local with rationale comments).
- Acceptance: §3 test plan rows T1–T6 green; `ruff check` clean (no new config); zero imports outside `numpy`/`scipy`/`dataclasses`.

### Diff 2 — VaR-ratio sizer (`src/risk/position_sizer.py` hook ONLY; `config/risk_config.py` 2 consts; tests NEW)

- New `SkewtTailAdjuster` class in `position_sizer.py` (adjacent to `ConfidenceAdjuster`, same style):
  - `multiplier(var_ratio: float, iv_skew_score: float|None) -> float`: `clip(1/var_ratio, 0.5, 1.0)` when `var_ratio>1` (fatter tails → cut size); `1.0` when `var_ratio<=1`; invalid/NaN → `1.0`; optional IV-skew overlay: `iv_skew_score>=60 → ×0.75`, `>=80 → ×0.5` (matches `DEFAULT_GATE_THRESHOLD 60.0`).
  - Never increases size above Kelly path (`≤1.0` hard cap) — tail-risk hook is **down-only** (fail-closed direction).
- `PositionSizer.size_position(..., tail_multiplier: float = 1.0)` optional kwarg; applied at step 5.5 (`final_kelly = macro_adj × clip(tail_multiplier,0.1,1.0)` before KellyBoost blend). Default `1.0` ⇒ byte-identical behavior when unused (regression test asserts).
- `config/risk_config.py` adds `SKEWT_VAR_ALPHA=0.05`, `SKEWT_TAIL_CAP=(0.5,1.0)` (single-source per CS-04; sizer imports, no literals).
- `KellyBoostAggregator` +5% bonus untouched; tail multiplier applies before aggregation so diversification bonus cannot override tail cut.
- Acceptance: rows T7–T9 green; existing `tests/test_risk.py` + sizer tests green with default path unchanged.

### Diff 3 — Sleeve blend (`src/ops/portfolio.py` hook + `src/signals/engine.py` VRP sleeve stub behind flag; all default-off)

- Blender (in `src/ops/portfolio.py` or new `src/risk/skewt_blend.py` if file >300 lines — prefer new module, thin hook):
  - `blend_weights(w_cvar, w_skewt, lam) = (1−λ)w_cvar + λw_skewt`, `λ = lam_from_regime(vol_regime, iv_skew_score)` ∈ `[0, 0.5]` (cap: skew-t never majority without OOS proof; raise cap only after Diff 4 passes + pre-register).
  - `w_cvar` from existing `PortfolioOptimizer.optimize_cvar/optimize_erc` (unchanged); `w_skewt` from Diff 1 `skewt_var_weights`; both projected long-only, `max_weight 0.25`, `min_cash 0.10` preserved.
- VRP sleeve stub in `src/signals/engine.py`: `get_vrp_sleeve_signal(returns_panel, iv_inputs, enabled=False)` returning `NO_SIGNAL`/zero-weight unless `VRP_SLEEVE_ENABLED=1` env AND pre-registration file exists (fail-closed default-off; mirrors `LIVE_TRADING_ENABLED` pattern in `position_sizing.py:16`).
- Exposure math: 7→8 sleeves changes per-sleeve nominal — document as `1/8` equal-risk nominal with 60% cap / 40% cash buffer unchanged; no live-weight change while flag off.
- No `strategies/registry.json` write in this diff (registry write only after Diff 4 gates pass + `preregister.py freeze/record`).
- Acceptance: rows T10–T12 green; sleeve-off path byte-identical (portfolio weights snapshot test).

### Diff 4 — Validation (`scripts/validate_skewt_sleeve.py` NEW; `docs/data/cycle*_prereg_vrp_skewt.md` NEW via `preregister.py freeze`)

- Pre-register hypothesis first (`docs/HUNT_PROTOCOL.md` §1 brief: falsifiable VRP + skew-t edge, universe SPY puts 2019–2026 daily, kill criteria `p>0.05`/OOS fail/over-param).
- Validation script (offline, synthetic + cached history only):
  1. Synthetic-surface checks (§3 fixtures F1–F3): VaR-cut direction/materiality, Gaussian-convergence, weight sanity.
  2. Cached-history walk-forward (same loop window `T=1910` bars 2019-01-02→2026-08-07 per papers study §0; T+1, tiered costs, SPY twin excess): report Sharpe/OOS/maxDD/excess/DSR(`FAM_TRIALS`-scoped)/`perm_p`/`boot_p`/trips.
  3. Target track: `tail_risk_sentinel` (sharpe≥0.55, maxDD≤0.25, oos≥0.35, excess≥0.03, dsr≥0.75, trips≥6); paper-effect bars: VaR cut ≥15% at matched return, OOS Sharpe lift reported (informational until `perm_p≤0.05` + DSR pass).
  4. Honest `ABANDON` path (`preregister.py record`) if gates fail — no registry write.
- Acceptance: rows T13–T15 green; either (a) gate-pass record + registry-ready proposal, or (b) abandonment record. Both are valid Diff 4 outcomes.

## 3. Test plan — synthetic surfaces, zero network

Global constraints: **no network** (no yfinance/Alpaca/FRED/chain fetch; `cache_engine` fixtures or `numpy` RNG only, `rng=default_rng(7)` matching `perm K=200 rng 7` convention); **no API keys**; hermetic `PYTHONPATH=. pytest <single-file> -q` per-file serial (per session test discipline — never full suite from this plan).

Fixtures (all in-test, seeded):
- F1 `ghst_panel(n=2000, k=3, nu=6, gamma=[−0.8,−0.4,−0.2])`: heavy-tail, left-skewed option-proxy returns (put-write-like). Expected: `var_ratio > 1.15`, skew-t VaR < Gaussian VaR at matched mean.
- F2 `gaussian_panel(n=2000, k=3)`: `gamma=0`, large `nu` path. Expected: `var_ratio ≈ 1.0 ± 0.05`, `‖w_skewt − w_gauss‖ < 0.05`.
- F3 `crisis_panel`: F1 with 5% injected −5σ jumps. Expected: gate blocks or `tail_multiplier ≤ 0.5`.
- F4 `empty/nan/short panels`: fail-closed contract checks.

| ID | Test file (NEW) | Case | Asserts |
|---|---|---|---|
| T1 | `tests/test_skewt_formulas.py` | MOM recovers `nu≈6±1`, `gamma<0` on F1 | param recovery within tolerance; `ValueError` on F4 |
| T2 | same | Gaussian convergence on F2 | `var_ratio ∈ [0.95,1.05]`; weight distance `<0.05` |
| T3 | same | Closed-form VaR < Gaussian VaR on F1 at matched return | `skewt_var < gaussian_var`; cut ≥10% on synthetic (paper −27.3% is history-specific; direction + materiality gate here) |
| T4 | same | Return-to-VaR weights beat plug-in on F1 | `mean(w_var)/VaR(w_var) > mean(w_gauss)/VaR(w_gauss)`; long-only, sums to 1 |
| T5 | same | Max-Sharpe closed form sane | Sharpe(w_skewt) ≥ Sharpe(equal-weight) on F1; no NaN/inf/leverage (weights ∈ [0,1]) |
| T6 | same | Fail-closed | F4 → `ValueError` (estimators) / `(False,1.0)` (`skewt_gate`); no NaN propagates |
| T7 | `tests/test_skewt_sizer.py` | Down-only tail cut | `var_ratio=1.3 → mult≈0.77`; `var_ratio=2.0 → 0.5` (floor); `var_ratio=0.9 → 1.0`; NaN → 1.0 |
| T8 | same | IV-skew overlay | score 65 → ×0.75 stack; 85 → ×0.5 stack; `None` → no overlay |
| T9 | same | Default-path regression | `size_position(...)` without `tail_multiplier` == pre-Diff-2 snapshot; `KellyBoost` +5% cap intact; `config/risk_config` single-source import |
| T10 | `tests/test_skewt_blend.py` | Blend caps | `λ∈[0,0.5]`; `λ=0 → w_cvar`; invalid regime → `λ=0`; `max_weight`/`min_cash` preserved post-blend |
| T11 | same | Sleeve-off regression | flag off → 7-sleeve weights byte-identical snapshot |
| T12 | same | Sleeve-on smoke (synthetic) | F1 weights long-only, sum `0.9` (1−min_cash), no sleeve >0.25 |
| T13 | `scripts/validate_skewt_sleeve.py --synthetic-only` | Synthetic gate | VaR-cut + weight-sanity JSON report, exit 0 on F1/F2/F3 expectations |
| T14 | same `--walk-forward` (cached data) | History gate | `tail_risk_sentinel` checklist JSON + overlays (`perm_p`, `boot_p`, DSR `FAM_TRIALS`-scoped); T+1 + tiered costs applied |
| T15 | `pytest tests/test_skewt_*.py -q` serial | Lint/security | `ruff check` on new files clean; `bandit -r` new-module clean; no network calls (assert via `socket` block fixture or grep `requests|urllib|yfinance|alpaca` = 0 hits in new files) |

Commands (per-file, serial):
`PYTHONPATH=. pytest tests/test_skewt_formulas.py -q`
`PYTHONPATH=. pytest tests/test_skewt_sizer.py -q`
`PYTHONPATH=. pytest tests/test_skewt_blend.py -q`
`python scripts/validate_skewt_sleeve.py --synthetic-only`
`ruff check src/risk/skewt_formulas.py tests/test_skewt_formulas.py` (repo has no ruff config — latest defaults per AGENTS.md)

## 4. Risks / non-goals

- Overfit: GHST adds `γ(k) + ν` params — DSR must be `FAM_TRIALS`-scoped, plus `perm_p`/`boot_p` overlays; Sharpe-only tuning (`optimizer.py`) is insufficient — VaR-aware gate mandatory.
- Estimation risk: `ν` unstable in small samples → clamp + shrink + crisis-regime prior from `volatility_forecast.py`; short panels raise, never silently extrapolate.
- No live options trading in Diffs 1–4: no chain feed, no broker hook, no `LIVE_TRADING_ENABLED` flip, no registry write until Diff 4 passes.
- VRP definition risk: realized-minus-implied needs an IV history the repo does not store — Diff 1–3 use return-panel GHST only; true VRP-signal (term-structure carry) is follow-up work with its own pre-registration.

## 5. Deliverable contract

- This file only. No edits to `src/`, `config/`, `strategies/`, `tests/`, `scripts/`, `docs/` made or proposed as done.
- Next action (not taken here): implement Diff 1 behind `declare_scope[src/risk/skewt_formulas.py, tests/test_skewt_formulas.py]` after plan approval.
