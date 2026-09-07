# GATESPEC_TRACKS — Promotion-Gate Variations for SPY-Beating Strategies

**Calibration window:** Loop window (1910 bars, 2019-2026), SPY total +245.5%, Sharpe 0.94, maxDD ~34%.
**Reference window:** Paper gate report (shorter coverage), SPY total +137.1%, CAGR 13.85%, maxDD -34.1%.
All calibration claims use the loop window since `evolve_real.py` evaluates against it. The paper gate window discrepancy is noted where relevant.

## Track Summary

A candidate promotes by clearing **ANY ONE** track fully (full conjunction). Every track includes both an absolute-excess-vs-SPY term AND a multiple-testing discount (DSR), plus a risk term (maxDD) and a minimum-activity term (trips or tmin).

| # | Track Name | Sharpe≥ | MaxDD≤ | OOS≥ | Excess≥ | DSR≥ | Trips/Tmin | Archetype | SPY Passes |
|---|-----------|---------|--------|------|---------|------|------------|-----------|------------|
| 1 | `core_timing_overlay` | 0.60 | 0.30 | 0.40 | 0.05pp | 0.80 | trips≥8 | Low-exposure timing overlay (10-40% T-in-M) | No (elite-only) |
| 2 | `drawdown_warrior` | 0.55 | 0.35 | 0.35 | 0.10pp | 0.75 | trips≥6 | Low-exposure drawdown-avoidance | No (elite-only) |
| 3 | `conservative_timing` | 0.50 | 0.35 | 0.35 | 0.15pp | 0.70 | trips≥5 | Low-exposure conservative timing | No (elite-only) |
| 4 | `high_exposure_momentum` | 0.75 | 0.35 | 0.50 | 0.05pp | 0.90 | tmin≥0.70 | High-TIM momentum / trend-following | No (elite-only) |
| 5 | `buy_hold_companion` | 0.85 | 0.35 | 0.55 | 0.02pp | 0.95 | tmin≥0.80 | Near-buy-hold momentum / rotation | No (elite-only) |
| 6 | `statistical_rigor` | 0.70 | 0.35 | 0.45 | 0.02pp | 0.92 | trips≥15 | Statistically validated timing/rotation | No (elite-only) |
| 7 | `absolute_return_focus` | 0.65 | 0.35 | 0.40 | 0.20pp | 0.75 | trips≥10 | Absolute-return focused timing | No (elite-only) |
| 8 | `risk_adjusted_discipline` | 0.70 | 0.28 | 0.45 | 0.05pp | 0.85 | trips≥12 | Risk-disciplined timing, strict DD | No (elite-only) |
| 9 | `benchmark_parity` | 0.90 | 0.35 | 0.85 | 0.00pp | 0.95 | trips≥0 | Benchmark parity reference | **Yes** (calibration) |

## Track Details

### Track 1: `core_timing_overlay`
- **Terms:** sharpe≥0.60, maxDD≤0.30, OOS≥0.40, excess≥0.05pp, DSR≥0.80, trips≥8
- **Rationale:**
  1. `sharpe≥0.60` admits timing overlays that sit in cash much of the time yet still generate meaningful risk-adjusted returns — the shape of every near-passing candidate in the current pool.
  2. `excess≥0.05pp` blocks the TOP5 failure mode where low-exposure strategies post Sharpe ~0.9 but trail SPY by 70-137pp in absolute return.
  3. `dsr≥0.80` applies a multiple-testing discount calibrated to the loop's 10000+ trial count, filtering selection-bias luck while remaining achievable for a real but modest edge.
- **Archetype:** Low-exposure timing overlay (10-40% time-in-market)
- **SPY status:** Elite-only — SPY fails excess (0.0 < 0.05) and trips (0 < 8)
- **Current near-miss impact:** Would admit strategies like `spy_rsi2(12,76,7)` IF they had positive excess (they currently have excess ≈ -100pp, so they still fail).

### Track 2: `drawdown_warrior`
- **Terms:** sharpe≥0.55, maxDD≤0.35, OOS≥0.35, excess≥0.10pp, DSR≥0.75, trips≥6
- **Rationale:**
  1. `maxDD≤0.35` is generous enough to admit strategies that avoid SPY's worst drawdowns by rotating to cash — the only mechanism low-exposure overlays use to reduce risk without holding less of the market.
  2. `excess≥0.10pp` demands more substantial absolute outperformance than Track 1, filtering strategies that merely track SPY with a timing overlay but still lose to buy-hold.
  3. `dsr≥0.75` with the loop's large trial count still rejects pure luck — at N~10000 the DSR correction is severe, so only a genuine signal survives even at this relaxed threshold.
- **Archetype:** Low-exposure drawdown-avoidance timing
- **SPY status:** Elite-only — SPY fails excess (0.0 < 0.10) and trips (0 < 6)
- **Current near-miss impact:** Would admit `spy_sma(127)` IF it had positive excess (currently excess ≈ -100pp).

### Track 3: `conservative_timing`
- **Terms:** sharpe≥0.50, maxDD≤0.35, OOS≥0.35, excess≥0.15pp, DSR≥0.70, trips≥5
- **Rationale:**
  1. `sharpe≥0.50` is the lowest bar among low-exposure tracks, acknowledging that a strategy spending 80%+ of its time in cash will naturally have a lower Sharpe even if it times the market well.
  2. `excess≥0.15pp` is the most stringent absolute-outperformance requirement among low-exposure tracks, ensuring low-TIM strategies add meaningful return.
  3. `dsr≥0.70` is the most permissive DSR threshold, calibrated so that a strategy with a genuine but small edge can survive the 10000+ trial correction.
- **Archetype:** Low-exposure conservative timing overlay
- **SPY status:** Elite-only — SPY fails excess and trips
- **Current near-miss impact:** Would NOT admit any current near-miss because their excess values (-70 to -137pp) are far below the 0.15pp floor.

### Track 4: `high_exposure_momentum`
- **Terms:** sharpe≥0.75, maxDD≤0.35, OOS≥0.50, excess≥0.05pp, DSR≥0.90, tmin≥0.70
- **Rationale:**
  1. `tmin≥0.70` requires the strategy to hold the market at least 70% of the time, admitting only momentum or trend-following strategies that behave like buy-hold with modest timing adjustments.
  2. `sharpe≥0.75` ensures the strategy captures meaningful upside when invested, filtering out high-exposure strategies that hold the market but have poor risk-adjusted returns.
  3. `dsr≥0.90` maintains strong statistical rigor; because high-exposure strategies produce more data points, the DSR correction is proportionally less severe.
- **Archetype:** High time-in-market momentum / trend-following
- **SPY status:** Elite-only — SPY fails excess (0.0 < 0.05)
- **Current near-miss impact:** Would admit `us_momentum` with small lookback if it achieves positive excess.

### Track 5: `buy_hold_companion`
- **Terms:** sharpe≥0.85, maxDD≤0.35, OOS≥0.55, excess≥0.02pp, DSR≥0.95, tmin≥0.80
- **Rationale:**
  1. `tmin≥0.80` requires near-buy-hold exposure, admitting only strategies with slight tilts; this is the shape `us_momentum` and `us_lowvol` produce with small `top_n`.
  2. `sharpe≥0.85` is near-SPY's own 0.94, ensuring high-exposure candidates must match SPY's risk-adjusted performance.
  3. `dsr≥0.95` with `tmin≥0.80` is the most statistically demanding track — only strategies with a very strong genuine signal survive this filter.
- **Archetype:** Near-buy-hold momentum / rotation
- **SPY status:** Elite-only — SPY fails excess (0.0 < 0.02)
- **Current near-miss impact:** Would admit `btc_regime` with high target if it achieves positive excess and high T-in-market.

### Track 6: `statistical_rigor`
- **Terms:** sharpe≥0.70, maxDD≤0.35, OOS≥0.45, excess≥0.02pp, DSR≥0.92, trips≥15
- **Rationale:**
  1. `trips≥15` ensures a large enough sample for the DSR to be meaningful — with few trades the DSR correction is overly severe and unreliable.
  2. `dsr≥0.92` is the second-highest DSR threshold, requiring very strong evidence that the observed Sharpe is not a product of multiple-comparison selection bias.
  3. `excess≥0.02pp` is a minimal absolute outperformance requirement — this track prioritizes statistical confidence over return magnitude.
- **Archetype:** Statistically validated timing or rotation
- **SPY status:** Elite-only — SPY fails excess and trips
- **Current near-miss impact:** Would NOT admit current near-misses because their DSR values are near 0.0 (far below 0.92) due to the massive trial count.

### Track 7: `absolute_return_focus`
- **Terms:** sharpe≥0.65, maxDD≤0.35, OOS≥0.40, excess≥0.20pp, DSR≥0.75, trips≥10
- **Rationale:**
  1. `excess≥0.20pp` is the most demanding absolute-outperformance requirement among all tracks; this track prioritizes raw alpha over risk-adjusted metrics.
  2. `sharpe≥0.65` is moderate, acknowledging that strategies with high excess may do so through concentrated positions that increase variance; maxDD bounds the risk.
  3. `dsr≥0.75` with `trips≥10` balances the demand: the excess term requires real alpha, the DSR requires it not be luck, and the trips requirement ensures enough data.
- **Archetype:** Absolute-return focused timing or rotation
- **SPY status:** Elite-only — SPY fails excess and trips
- **Current near-miss impact:** Would NOT admit current near-misses because their excess values are deeply negative.

### Track 8: `risk_adjusted_discipline`
- **Terms:** sharpe≥0.70, maxDD≤0.28, OOS≥0.45, excess≥0.05pp, DSR≥0.85, trips≥12
- **Rationale:**
  1. `maxDD≤0.28` is stricter than SPY's own ~34% drawdown — admitting only strategies that demonstrably avoid the worst market downturns. This is an elite-only track because even SPY buy-hold fails.
  2. `sharpe≥0.70` combined with the strict drawdown constraint requires the strategy to earn its risk-adjusted return while taking less risk than the benchmark — the hallmark of genuine timing skill.
  3. `dsr≥0.85` with `trips≥12` ensures the improved risk profile is not a product of lucky timing in a small sample.
- **Archetype:** Risk-disciplined timing with strict drawdown control
- **SPY status:** Elite-only — SPY fails maxDD (0.34 > 0.28), excess, and trips
- **Current near-miss impact:** Would NOT admit current near-misses because their maxDD values are too high or excess is too negative.

### Track 9: `benchmark_parity` (Calibration Reference)
- **Terms:** sharpe≥0.90, maxDD≤0.35, OOS≥0.85, excess≥0.00pp, DSR≥0.95, trips≥0
- **Rationale:**
  1. `excess_min=0.0` is the only track where SPY itself can pass the excess term; this serves as a calibration reference confirming the gate is not impossibly set.
  2. `sharpe≥0.90` and `oos≥0.85` are set near SPY's own values so that this track confirms the gate accepts benchmark-level performance.
  3. `dsr≥0.95` with `trips_min=0` makes this the most statistically rigorous track with no activity floor — it admits benchmark-level strategies that pass the multiple-testing guard.
- **Archetype:** Benchmark parity reference (calibration check)
- **SPY status:** **PASSES** — confirms the gate is calibrated correctly
- **Current near-miss impact:** Would admit SPY itself, confirming the gate is not miscalibrated. Any strategy matching SPY's performance clears this track.

## Calibration Notes

### SPY Baseline Metrics (Loop Window)
| Metric | Value |
|--------|-------|
| Sharpe | 0.94 |
| MaxDD | ~0.34 |
| OOS Sharpe | ~0.94 |
| Excess vs SPY | 0.0 |
| DSR (N=10000+) | ~1.0 |
| perm_p | ~0.60 |
| boot_p | ~0.40 |
| Trips | 0 |
| Time-in-Market | 1.0 |
| CAGR | ~18.5% |
| Total Return | +245.5% |

### Window Reconciliation
- **Loop window** (1910 bars, 2019-2026): SPY +245.5%, Sharpe 0.94 — used for all calibration since `evolve_real.py` evaluates against this window.
- **Paper gate window**: SPY +137.1%, CAGR 13.85%, maxDD -34.1% — covers a shorter/different period. The difference in total return (~108pp) reflects different coverage periods.
- All track thresholds are calibrated to the loop window. If evaluated on the paper gate window, SPY's Sharpe would differ and track thresholds may need adjustment.

### Why the Current Gate Fails Everything
The current gate (`REAL_GATE`) requires sharpe≥0.8, maxDD≤0.35, OOS≥0.5, trips≥10, excess>0.0, DSR≥0.95, perm_p≤0.05, boot_p≤0.05. The top 5 strategies from `TOP5_TRIPLE_CHECK.md` have:
- Sharpe 0.86-0.95 ✓ (pass Sharpe)
- maxDD 0.08-0.20 ✓ (pass maxDD)
- OOS Sharpe 1.6-1.63 ✓ (pass OOS)
- Trips 27-189 ✓ (pass trips)
- **Excess -70% to -137%** ✗ (fails excess>0)
- DSR ≈ 0.02 (fails DSR≥0.95 due to massive N)
- perm_p ≈ 0.5 (fails perm_p≤0.05)
- boot_p ≈ 0.4 (fails boot_p≤0.05)

The excess failure is the primary blocker: low-exposure timing overlays (15-40% T-in-M) have Sharpe ~0.9 matching SPY's 0.94 on risk-adjusted terms, but trail SPY by 70-137pp in absolute return because they sit in cash most of the time.

### Which Near-Miss Each Track Would Admit or Still Reject

| Near-Miss Strategy | Sharpe | Excess | Would Pass |
|-------------------|--------|--------|------------|
| `spy_rsi2(12,76,7)` | 0.926 | ~-100pp | None (excess too negative for all tracks) |
| `spy_rsi2(11,76,7)` | 0.912 | ~-100pp | None (excess too negative) |
| `spy_sma(127)` | 0.862 | ~-100pp | None (excess too negative) |
| `spy_rsi2(11,78,7)` | 0.934 | ~-100pp | None (excess too negative) |
| `spy_rsi2(12,78,7)` | 0.948 | ~-100pp | None (excess too negative) |

**Key insight:** The current near-misses fail ALL tracks because their excess values (-70 to -137pp) are far below every track's minimum excess requirement (0.02-0.20pp). These tracks are correctly calibrated — the strategies genuinely do not beat SPY in absolute terms, and no amount of threshold relaxation on non-excess terms can fix this fundamental shortfall. The gate is not miscalibrated; the strategies genuinely lack alpha vs SPY.

## Implementation Notes

The `check_track(metrics_dict)` evaluator in `src/backtest/gatespec_tracks.py` supports the following metric keys:
- `sharpe`, `max_dd`, `oos`, `excess`, `dsr`, `perm_p`, `boot_p`, `trips`, `trades`, `cagr`, `tmin`

If `tmin` is not provided, the evaluator uses `trips` as the activity proxy. All thresholds are checked with `>=` for minimum values and `<=` for maximum values.

The `recompute_dsr(T, sharpe, N)` helper wraps `deflated_sharpe_ratio` from `src.backtest.defend.trial_ledger` for cases where DSR is not pre-computed in the metrics dict.