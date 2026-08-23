# C4 Post-Mortem — Train-Consistency Inversion (knowledge task, 2026-08-16)

Scope: read-only analysis of the frozen C4 run (docs/data/cycle3_ml_results.json,
cycle3_ml_evaluation.json). Purpose: learn why the walk-forward train factor
was negative while OOS was positive. This CANNOT change the frozen C4R spec
(kill rule); findings feed future claim design only.

## Measured facts (from cycle3_ml_results.json weekly_factor_returns_net)

| Period | n weeks | mean %/wk | median %/wk |
|--------|---------|-----------|-------------|
| Train 2020 | 53 | -0.249 | +0.020 |
| Train 2021 | 52 | -0.069 | -0.243 |
| Train 2022 | 52 | -0.093 | -0.176 |
| Train 2023 | 52 | -0.149 | -0.038 |
| **Train total** | 209 | **-0.140** | negative |
| OOS 2024 | 52 | +0.211 | +0.233 |
| OOS 2025 | 52 | +0.421 | +0.366 |
| OOS 2026 | 31 | +0.045 | +0.078 |
| **OOS total** | 135 | **+0.254** | +0.234 |

- Train months with negative mean: 29 of 48.
- OOS vs train: all 3 OOS years positive, all 4 train years negative mean.

## Findings

1. **Not instability — a consistent inversion.** Every train year has negative
   mean; every OOS year positive. The GBR decile L/S factor lost systematically
   in-sample and won out-of-sample. This is regime-conditioned sign inversion
   of a weak learned signal, not walk-forward noise.
2. **Mechanism.** Train factor returns come from the walk-forward refit chain
   (models anchored <= d, annual refits); OOS predictions come ONLY from the
   final model (anchor 2023-12-31). The sign flip is between the model
   generations fitted on 2020-2023 data (high-inflation, rising-rates regime)
   and the final 2023-12-31 anchor that generated all OOS predictions. The
   learned feature->return association inverted across the regime boundary.
3. **Costs cannot explain it.** 10 bps/side on turnover is symmetric and
   ~1-2 bps/week magnitude; the gap is 39 bps/week (train -0.140 vs OOS
   +0.254).
4. **The train gate did its job.** A claim whose in-sample signal is
   systematically negative is dead on arrival by design; the OOS positive
   (null fail by 0.011pp) is consistent with noise-level edge, not with a
   recovered signal.
5. **Limitation.** Feature importances per refit were not persisted by the
   frozen engine; per-year decomposition above is the strongest evidence
   available without re-running (re-run would not change outputs and is not
   warranted).

## Implications for future claims

- Annual-refit GBR on rank-normalized targets can invert regime-to-regime;
  single-mechanism claims (C6) avoid learned-parameter inversion by
  construction (no fitting beyond fixed rules).
- A train sign gate alone does not protect against inversion BETWEEN train
  anchors; a per-anchor sign-consistency check (e.g., >= 3 of 4 anchor
  generations positive on train) is a candidate pre-registered gate for any
  future learned-parameter claim — proposed here as a design input, NOT
  adopted (no claim currently pending uses learned parameters).
- The C4R measurement track will confirm whether the +0.254%/wk OOS mean
  survives the full window vs the narrowing null band.