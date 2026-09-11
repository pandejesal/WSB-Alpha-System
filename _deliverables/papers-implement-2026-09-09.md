# Papers-to-Bred-Proposals Study — 2026-09-09

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint.
Scope: workdir-only. Convert 5 papers into `src=bred` proposals consumable by `evolve_real.py`.

## 0. Gate logic verified (read-only)

`evolve_real.py:9-15,60-66,350-428,600-625` + `src/backtest/gatespec38_tracks.py:1-402` + `scripts/evolve_generations.py:303-318`:

- **Promotion = clear ANY ONE of 10 gatespec38 tracks fully** (`check_track(metrics) -> list[str]`). Every track is a full conjunction: `sharpe + max_dd + oos + excess-vs-SPY + dsr + activity(trips|tmin)`.
- **Universal overlays** (can only block, never admit): `perm_p<=0.05` (circular-shift timing test, K=200, rng 7) + `boot_p<=0.05` (stationary bootstrap). Fail-closed on exception (`dsr=0/perm_p=1`).
- **Costs/execution:** T+1 (`signal.shift(1)`), tiered cost floor 5bps + 10bps short-borrow guard, SPY twin same-window absolute excess (`excess = prod(1+net)-prod(1+spy)` in pp, must be `>0` on every track except `benchmark_parity`).
- **DSR scoping (W1 fix):** per-family `FAM_TRIALS[family]` with `T=1910` bars (2019-01-02→2026-08-07 loop window), NOT global `TRIAL_COUNT(~10k)`. `recompute_dsr(T,sharpe,N)` wraps `deflated_sharpe_ratio`. At N_fam~500–1000, DSR 0.70–0.95 needs Sharpe ~1.38–1.79; at N=10k/0.95 needs ~2.01 (near-impossible — the documented flaw gatespec38 fixes by splitting tracks).
- **10 tracks (thresholds):**

| # | track | sharpe≥ | maxDD≤ | oos≥ | excess≥(pp) | dsr≥ | activity |
|---|---|---|---|---|---|---|---|
| 1 | `core_timing_overlay` | 0.60 | 0.30 | 0.40 | 0.05 | 0.80 | trips≥8 |
| 2 | `drawdown_warrior` | 0.55 | 0.35 | 0.35 | 0.10 | 0.75 | trips≥6 |
| 3 | `conservative_timing` | 0.50 | 0.35 | 0.35 | 0.15 | 0.70 | trips≥5 |
| 4 | `tail_risk_sentinel` (gatespec38 addition over ling-fin 9) | 0.55 | 0.25 | 0.35 | 0.03 | 0.75 | trips≥6 |
| 5 | `high_exposure_momentum` | 0.75 | 0.35 | 0.50 | 0.05 | 0.90 | tmin≥0.70 |
| 6 | `buy_hold_companion` | 0.85 | 0.35 | 0.55 | 0.02 | 0.95 | tmin≥0.80 |
| 7 | `statistical_rigor` | 0.70 | 0.35 | 0.45 | 0.02 | 0.92 | trips≥15 |
| 8 | `absolute_return_focus` | 0.65 | 0.35 | 0.40 | 0.20 | 0.75 | trips≥10 |
| 9 | `risk_adjusted_discipline` | 0.70 | 0.28 | 0.45 | 0.05 | 0.85 | trips≥12 |
| 10 | `benchmark_parity` (SPY calibration anchor, only `spy_passes=True`) | 0.90 | 0.35 | 0.85 | 0.00 | 0.95 | trips≥0 |

- **SPY baselines:** loop window (1910 bars): Sharpe 0.941, maxDD 0.337, CAGR 17.77%, total +245.5%. Paper-gate window (1678 bars): Sharpe 0.744, maxDD 0.341, CAGR 13.85%.

### `src=bred` proposal JSON format (strict — `evolve_real.py:breed_proposals()` lines 617-622)

Consumed from `docs/data/next_gen_proposals.jsonl` via pointer file `docs/data/next_gen_consumed.txt`. Verified live format (`head docs/data/next_gen_proposals.jsonl`):

```json
{"family": "spy_rsi2", "bred_from": "spy_rsi2_real_20260904-205625", "params": {"entry": 10, "exit_hi": 60, "max_hold": 7}, "parent_oos": 1.633}
```

Acceptance rule: `family IN FAMILIES` AND `set(params) == set(SPACES[family])` exactly, else skipped silently (`return None`). No new family names pass.

```python
FAMILIES = ["spy_sma","spy_rsi2","btc_vol","btc_donchian","us_momentum","us_lowvol","spy_ltrend","us_ltrend","gap_mr","btc_regime"]
SPACES = {
 "spy_sma": {"window": (50,300,int)},
 "spy_rsi2": {"entry": (5,20,int), "exit_hi": (60,80,int), "max_hold": (3,10,int)},
 "btc_vol": {"target": (0.20,0.50,float), "vol_window": (20,60,int), "gate": (50,200,int)},
 "btc_donchian": {"entry_ch": (10,30,int), "exit_ch": (5,20,int)},
 "us_momentum": {"lookback": (63,252,int), "skip": (5,42,int), "top_n": (3,10,int)},
 "us_lowvol": {"vol_window": (20,120,int), "top_n": (10,50,int)},
 "spy_ltrend": {"window": (150,400,int)},
 "us_ltrend": {"lookback": (252,504,int), "top_n": (3,10,int)},
 "gap_mr": {"gap_z_window": (10,60,int), "entry_z": (1.2,3.0,float), "exit_mid_frac": (0.3,0.8,float), "max_hold_days": (1,5,int), "vol_filter_pct": (0.6,1.4,float)},
 "btc_regime": {"target": (0.20,0.50,float), "btc_vol_window": (15,60,int), "spy_vol_window": (20,90,int), "corr_window": (20,60,int), "spy_vol_cap": (0.12,0.30,float), "corr_cap": (0.2,0.7,float)},
}
```

Breeder writes `{"family","bred_from","params","parent_oos"}` only (`scripts/evolve_generations.py:317-318`); children mutate ±30% (`rng.uniform(0.7,1.3)`). Implication for papers: **full paper logic (sentiment RL, skew-t, spectral shrinkage, eigenspace velocity, conformal Kelly) CANNOT be expressed in a bred line alone** — bred lines only tune existing family knobs. Each proposal below therefore gives (a) honest code insertion point under real paths, (b) a gate-valid proxy bred line that tests the closest existing dynamics, (c) the track it can plausibly clear, (d) the expected failure mode.

### Real paths verified (workdir-only reads)

- PEAD: `src/ops/signals.py` (875 lines; `get_sentiment_overlay_signal`, `get_ta_rules_signal`, debate-engine overlay; sleeve signals) + `src/signals/engine.py` (`SignalEngine`, 7 sleeves delegating to `src/ops/signals.py`).
- Factors: `src/signals/` (`engine.py`, `qlib_alpha158.py` 47 feats shift(1), `gplearn_factors.py` terminals+`shift(1)`, `fingpt_sentiment.py`, `agentquant_regime.py`).
- Sizing: `src/risk/` (`position_sizer.py`: Kelly `f*=(p*b-q)/b` + semi-variance adjust + `KELLY_FRACTION=0.5` half-Kelly + `RegimeAdjuster` multipliers + `MAX_NOTIONAL_LEV=1.0`; `position_sizing.py`, `alptrading_sizing.py`, `portfolio_manager.py`).
- Optimizer: `src/risk/portfolio_optimization.py` (`PortfolioOptimizer.optimize_cvar/optimize_erc` via riskfolio, `hist` cov) + `src/ops/portfolio.py` (`PortfolioManager`, 7 sleeves, 60% exposure cap / 40% cash buffer, equal-risk nominal per sleeve).
- Backtest: `src/backtest/` (`metrics.safe_sharpe`, `gatespec38_tracks.check_track`, `defend/trial_ledger.deflated_sharpe_ratio`, `walk_forward_engine.py`, `permutation_tester.py`, `validation.py`).

---

## 1. FinSMART — market-aligned RL sentiment (sentiment_decay / signal timing)

**Paper idea (proxy):** RL policy aligns sentiment signal to market regime; effective behavior = exponentially decayed sentiment score gates entries + faster exit when alignment breaks.

**Target family:** `gap_mr` — only short-hold timing family with explicit decay-like knobs (`max_hold_days 1–5` ≈ sentiment half-life; `entry_z` ≈ sentiment surprise threshold; `vol_filter_pct` ≈ calm-regime alignment gate; `exit_mid_frac` ≈ partial-fill exit when edge decays). Alternative `spy_rsi2` (`entry/exit_hi/max_hold`) is second choice but lacks vol-filter alignment.

**Honest insertion (future diff, NOT done here):** `src/ops/signals.py:get_sentiment_overlay_signal()` — add `sentiment_decay: exp(-age/half_life)` multiplier on `score_text()` + debate score before `threshold` compare; `src/signals/fingpt_sentiment.py` carries half-life param; pre-register per `docs/HUNT_PROTOCOL.md`. Bred line below only tunes the timing-envelope proxy.

**Param space (within SPACES[gap_mr]):** `gap_z_window 10–60 (int)`, `entry_z 1.2–3.0`, `exit_mid_frac 0.3–0.8`, `max_hold_days 1–5` (maps to decay half-life), `vol_filter_pct 0.6–1.4` (maps to market-alignment gate).

**Track cleared (plausible):** `conservative_timing` (sharpe≥0.50, oos≥0.35, excess≥0.15, dsr≥0.70, trips≥5) or `core_timing_overlay` (sharpe≥0.60/excess≥0.05/dsr≥0.80/trips≥8). Low-exposure timing is the only realistic lane: sentiment timing sits in cash most days (low tmin ⇒ tmin tracks 5/6 unreachable), needs few high-conviction trips.

**Failure mode:** phantom-Sharpe-without-excess (TOP5_TRIPLE_CHECK failure): decayed sentiment looks Sharpe-clean on few trades but trails SPY by 70–137pp absolute; `excess_min` blocks it. Second: `perm_p` circular-shift screen — sentiment timing with no real lead-lag skill fails `perm_p<=0.05`; third: over-short `max_hold_days=1` collapses `trips` composition under costs (5bps floor) → OOS Sharpe decay.

## 2. Skew-t option portfolio — closed-form weights (VRP / tail-risk sizer)

**Paper idea (proxy):** multivariate skew-t closed-form portfolio weights overweight variance-risk-premium (VRP) harvesting while penalizing left-tail (downside) exposure.

**Target family:** `btc_regime` — only family with explicit tail-risk gates: `spy_vol_cap (0.12–0.30)` ≈ tail-risk cutoff, `corr_cap (0.2–0.7)` ≈ contagion cutoff, `target (0.20–0.50)` ≈ VRP-harvest size, dual vol/corr windows ≈ skew-t scale estimation windows. `btc_vol` (`target/vol_window/gate`) is fallback but has no corr/left-tail knob.

**Honest insertion (future diff, NOT done here):** `src/risk/position_sizer.py` (Kelly×semi-variance already penalizes downside var — natural host for skew-t left-tail penalty) + `src/risk/portfolio_optimization.py` (add `optimize_skewt()` alongside `optimize_cvar/optimize_erc`; keep `MAX_NOTIONAL_LEV=1.0`, long/flat mandate — no paper leverage/shorts). Bred line tunes the regime-filter envelope that mimics skew-t tail avoidance.

**Param space (within SPACES[btc_regime]):** `target 0.20–0.50`, `btc_vol_window 15–60`, `spy_vol_window 20–90`, `corr_window 20–60`, `spy_vol_cap 0.12–0.30` (tight cap = strong tail penalty), `corr_cap 0.2–0.7`.

**Track cleared (plausible):** `tail_risk_sentinel` (sharpe≥0.55, maxDD≤0.25, excess≥0.03, dsr≥0.75, trips≥6) — the gatespec38-added 10th track designed exactly for crisis-alpha overlays that cut SPY 33.7% DD by >25%. Fallback: `drawdown_warrior`.

**Failure mode:** cash-parking → `excess_min` fail: too-tight `spy_vol_cap/corr_cap` keeps strategy flat through bull years, Sharpe looks safe but `excess>=0.03pp` fails net of 5bps costs. Loose caps invert the failure: `max_dd<=0.25` violated in 2020/2022 tails. DSR 0.75 on few crisis trips is also brittle — single-event timing looks like an artifact under per-family N.

## 3. Neural spectral shrinkage covariance (40% Sharpe claim vs gate realism)

**Paper idea (proxy):** learned spectral shrinkage of sample covariance → stabler minimum-variance / low-vol rotation weights; paper claims ~40% Sharpe uplift vs sample covariance.

**Target family:** `us_lowvol` — the only covariance-sensitive rotation family (`vol_window 20–120` ≈ shrinkage estimation window, `top_n 10–50` ≈ concentration/diversification knob that shrinkage controls). `monthly_rotation(..., lowvol=True)` in `evolve_real.py:464-467` is the exact call path; `_rotation_result()` fixes `trips=12` (monthly rebalance fiction) with tiered costs.

**Honest insertion (future diff, NOT done here):** `src/risk/portfolio_optimization.py` (`assets_stats(method_cov='hist')` → `'shrink'`/custom spectral-shrinkage estimator; `src/signals/qlib_alpha158.py` covariance features stay untouched); must pass walk-forward + DSR per `AGENTS.md` edge gate before `registry.json`. Claim audit: 40% uplift on a backtest Sharpe 0.9 → 1.26 still needs per-family DSR≥0.90–0.95 on tmin tracks (requires ~1.5–1.8 at N_fam 500–1000) AND `excess>0` vs SPY +0.941 loop baseline AND `perm_p/boot_p<=0.05` on shifted weight schedules — most published uplifts evaporate here.

**Param space (within SPACES[us_lowvol]):** `vol_window 20–120` (long window = strong-shrinkage proxy; short = sample-cov proxy), `top_n 10–50` (wide = shrinkage-diversified, narrow = concentrated).

**Track cleared (plausible):** `high_exposure_momentum` (sharpe≥0.75, oos≥0.50, excess≥0.05, dsr≥0.90, tmin≥0.70) — rotation is ~always invested (high tmin). `buy_hold_companion` (sharpe≥0.85/dsr≥0.95/tmin≥0.80) is the stretch goal and usually the failure point.

**Failure mode:** DSR + excess double-bind: shrinkage improves in-sample Sharpe but `dsr>=0.90` at N_fam plus `excess>=0.05pp` vs SPY +245.5% loop window kills factor tilts that match vol but bleed cost drag (index-hugger rationale in track 5). Rotation `perm_p` (shifted weight schedule test, `evolve_real.py:511-531`) also blocks covariance overfits that lack genuine cross-sectional timing.

## 4. Reconfiguration Premium — eigenspace turning velocity as VRP timing factor

**Paper idea (proxy):** rate of change (turning velocity) of the return-covariance eigenspace predicts VRP expansion → scale risk up when eigenspace stable, cut when turning fast (regime break).

**Target family:** `us_momentum` (`lookback 63–252`, `skip 5–42`, `top_n 3–10`) — cross-sectional rotation whose formation window naturally encodes eigenspace stability; short `lookback` + large `skip` ≈ high-velocity (fast-turning) regime, long `lookback` + small `skip` ≈ stable-eigenspace VRP harvest. `btc_regime` corr windows are second choice but lack cross-sectional breadth.

**Honest insertion (future diff, NOT done here):** new factor `src/signals/` (e.g. `eigenspace_velocity.py`: rolling PCA on `UNI` panel → eigenvector-turn angle / subspace distance → VRP-timing scalar), consumed as `skip`/weight-tilt in `monthly_rotation()`; pre-register, walk-forward, permutation test. Bred line tunes the lookback/skip envelope that mimics velocity gating.

**Param space (within SPACES[us_momentum]):** `lookback 63–252` (stability horizon), `skip 5–42` (turning-velocity lag / post-break avoidance), `top_n 3–10` (concentration when velocity low).

**Track cleared (plausible):** `high_exposure_momentum` (tmin≥0.70 lane for near-continuous rotation) with `absolute_return_focus` (excess≥0.20pp/trips≥10/dsr≥0.75) as upside case if velocity timing adds genuine absolute alpha.

**Failure mode:** `skip` too large → signal staleness → `excess` fail vs SPY momentum baseline; `lookback` too short → turnover/cost bleed under tiered 5–7bps+vol-scaled costs in `_rotation_result()` → OOS Sharpe collapse; eigenspace angle estimated on 10-ticker `UNIVERSE` is noisy → `boot_p` stationary-bootstrap screen blocks single-regime luck (2020 crash turn dominates fit).

## 5. Conformal Kelly intervals — replacing std with prediction intervals in fractional Kelly

**Paper idea (proxy):** replace Gaussian-std Kelly scaling with distribution-free conformal prediction intervals (wider intervals in uncertainty → smaller fraction; tight intervals → fuller Kelly), keeping fractional (half-Kelly) cap.

**Target family:** `btc_vol` (`target 0.20–0.50` ≈ Kelly fraction cap, `vol_window 20–60` ≈ conformal calibration window proxy, `gate 50–200` ≈ interval-confidence / entry-selectivity proxy). Maps 1:1 onto `src/risk/position_sizer.py` (`KELLY_FRACTION=0.5`, `raw_kelly×semi_variance×RegimeAdjuster`, `MAX_NOTIONAL_LEV=1.0`).

**Honest insertion (future diff, NOT done here):** `src/risk/position_sizer.py:KellyCalculator` — add `conformal_interval_scale(trade_stats, alpha)` replacing `semi_variance_adjustment` denominator with conformal interval width; `adjusted_kelly = raw × conformal_scale × regime_mult`, still capped at half-Kelly; needs coverage-calibration test (miscoverage ⇒ overbet). Bred line tunes the vol-target envelope that mimics interval-widening (low `target` = wide-interval caution).

**Param space (within SPACES[btc_vol]):** `target 0.20–0.50` (fractional cap), `vol_window 20–60` (calibration window), `gate 50–200` (selectivity).

**Track cleared (plausible):** `risk_adjusted_discipline` (sharpe≥0.70, maxDD≤0.28, excess≥0.05, dsr≥0.85, trips≥12) — the strict-drawdown risk-efficiency lane conformal Kelly is built for. Fallback: `drawdown_warrior`.

**Failure mode:** interval miscalibration → chronic underbet → `excess>=0.05pp` fail (too safe to beat SPY +245.5%) or regime-conditional overbet → `max_dd<=0.28` violated in volatility clusters. Narrow `vol_window` makes intervals jittery → `trips` churn × 5bps costs → Sharpe/OOS decay; `dsr>=0.85` + `trips>=12` jointly punish the few-trade caution case.

---

## Copy-paste bred lines (valid JSON, gate-consumable)

Each line satisfies `family IN FAMILIES` and exact `set(params)==set(SPACES[family])` with in-range types. Append to `docs/data/next_gen_proposals.jsonl` (do NOT touch pointer semantics — `breed_proposals()` resets `idx=0` on mtime change, so coordinate with a running loop). `bred_from` tags the paper source; `parent_oos` is a neutral placeholder (loop recomputes real OOS; breed step only uses it for logging).

```json
{"family": "gap_mr", "bred_from": "paper_finsmart_20260909", "params": {"gap_z_window": 30, "entry_z": 2.0, "exit_mid_frac": 0.5, "max_hold_days": 3, "vol_filter_pct": 1.0}, "parent_oos": 0.6}
{"family": "btc_regime", "bred_from": "paper_skewt_vrp_20260909", "params": {"target": 0.3, "btc_vol_window": 30, "spy_vol_window": 45, "corr_window": 30, "spy_vol_cap": 0.2, "corr_cap": 0.45}, "parent_oos": 0.6}
{"family": "us_lowvol", "bred_from": "paper_spectral_shrink_20260909", "params": {"vol_window": 60, "top_n": 30}, "parent_oos": 0.6}
{"family": "us_momentum", "bred_from": "paper_reconfig_premium_20260909", "params": {"lookback": 126, "skip": 21, "top_n": 5}, "parent_oos": 0.6}
{"family": "btc_vol", "bred_from": "paper_conformal_kelly_20260909", "params": {"target": 0.3, "vol_window": 30, "gate": 100}, "parent_oos": 0.6}
```

Validation performed (study-session, no loop writes): `json.loads` per line OK; key-set equality vs `SPACES` checked against `evolve_real.py:78-96`; numeric ranges inside bounds; `family` values in `FAMILIES`. Consume path: `evolve_real.py:breed_proposals()` → `run_family()` → `backtest()/_rotation_result()` → `check_track()` + `perm_p/boot_p` overlays. Expectation under gate realism: most plausibly `tail_risk_sentinel` / `conservative_timing` / `high_exposure_momentum` lanes; `buy_hold_companion` / `benchmark_parity` unlikely for proxies (by design — full paper code + edge gate required for those).

## Decision table (per-paper summary)

| # | paper | target family (existing) | param space = SPACES[family] | track cleared (plausible) | primary failure mode |
|---|---|---|---|---|---|
| 1 | FinSMART RL sentiment | `gap_mr` (sentiment-decay timing proxy) | z-window/entry_z/exit_frac/max_hold/vol_filter | `conservative_timing` (fallback `core_timing_overlay`) | phantom Sharpe, `excess` fail + `perm_p` timing screen |
| 2 | Skew-t VRP weights | `btc_regime` (VRP/tail proxy) | target/vol-windows/corr-window/vol_cap/corr_cap | `tail_risk_sentinel` | cash-parking (`excess` fail) vs `maxDD≤0.25` breach |
| 3 | Spectral shrinkage cov | `us_lowvol` (cov proxy) | vol_window/top_n | `high_exposure_momentum` | DSR≥0.90 + `excess` double-bind; rotation `perm_p` |
| 4 | Reconfig premium velocity | `us_momentum` (eigenspace proxy) | lookback/skip/top_n | `high_exposure_momentum` (upside `absolute_return_focus`) | stale `skip`, cost bleed, `boot_p` single-regime fit |
| 5 | Conformal Kelly | `btc_vol` (fractional-Kelly proxy) | target/vol_window/gate | `risk_adjusted_discipline` | miscalibrated intervals → `excess` or `maxDD≤0.28` fail |

*Notes: (i) Bred lines are proxies — real paper alpha needs a code diff at the listed insertion point + pre-registration + walk-forward + permutation + DSR per `AGENTS.md`/`docs/HUNT_PROTOCOL.md` before any `registry.json` entry. (ii) No `strategies/` YAML, no `evolve_real.py`, no registry writes made in this study.*
