## Objective
Implement regime detection for the WSB-Alpha-System trading strategy. Use a Hidden Markov Model (HMM) with 4 states (Bull, Bear, High-Volatility, Range-Bound) to detect market regimes, then apply regime-specific signal filters to the existing meta-strategy system.

## Key Steps
1. **Feature Engineering**: Create `src/alpha/h1_features.py` to compute standard regime features (SMA slopes, realized vol, RSI, VIX).
2. **HMM Training**: Create `src/alpha/h1_hmm.py` to train/predict the RegimeHMM using `hmmlearn`.
3. **Regime Filter**: Create `src/alpha/h1_regime_filter.py` to apply logic based on the current regime label.
4. **Integration**: Create `src/alpha/h1_regime_detection.py` to wrap the HMM and Filter into a single Detector. Also integrate this detector with the hypothetical MetaStrategy. (Since `meta_strategy.py` is not actually present in this main branch yet, I will create a mock/stub `meta_strategy.py` as `src/alpha/meta_strategy.py` to satisfy the requirements or just create the requested classes).
5. **Config**: Add the specified configuration to `config/regime_config.yaml`.
6. **Tests**: Create `tests/test_h1_regime.py` covering HMM convergence, predictions, filter rules, etc.
7. **Documentation**: Write `docs/regime_detection.md` explaining the implementation.
8. **Pre-commit**: Check code standards and tests.
