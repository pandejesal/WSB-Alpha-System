# Edge Gates (Layer 3)

Source: docs/HUNT_PROTOCOL.md + AGENTS.md edge-gate mandate. Use these numbers
verbatim in hypothesis briefs and review verdicts.

## The gate (all must pass)
1. **Pre-registration**: brief committed BEFORE in-sample testing (this pipeline:
   stage-01 output approved by user before stage-02 runs).
2. **In-sample**: p-value <= 0.05. Falsified if p > 0.05.
3. **Combinatorial cross-validation** (combinatorially purged CV).
4. **Walk-forward**: positive out-of-sample performance across folds; no single
   fold carrying the entire result.
5. **Permutation test**: strategy must survive the permutation null (default
   NUM_PERMUTATIONS from src/backtest/validation.py).
6. **Deflated Sharpe Ratio**: positive DSR ledger entry in eval ledger
   (`docs/data/eval_*.json`).

## Kill criteria (declare in every brief)
- Hypothesis falsified during IS validation (p > 0.05)
- Fails walk-forward OOS
- Over-parameterization detected, or no parameter set survives permutation gate

## Overfitting smells (review-stage flags)
- More parameters than the data can support for the sample size
- Universe or window changes made after seeing results
- Metric cherry-picking (reporting best variant, not declared variant)
