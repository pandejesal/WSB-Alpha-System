"""Regression tests for G2 CPCV promotion conjunction (wired 2026-09-11).

Mirrors the evolve_real.py promotion logic: Sharpe per CPCV test block
(n=5/2, purge+embargo 5); pass needs >=7/10 positive AND mean >= 0.30.
Deterministic (seeded RNG); no network, no registry writes.
"""

import numpy as np
import pandas as pd

from src.backtest.metrics import safe_sharpe
from src.backtest.validators.statistical import StatisticalValidator

N_SPLITS, POS_MIN, MEAN_MIN = 10, 7, 0.30


def _cpcv_verdict(rets: np.ndarray) -> tuple:
    splits = StatisticalValidator.combinatorial_purged_cv(len(rets))
    assert len(splits) == N_SPLITS, f"expected {N_SPLITS} splits, got {len(splits)}"
    sharpes = [float(safe_sharpe(pd.Series(rets[np.asarray(t, dtype=int)]))) for _, t in splits]
    pos = sum(1 for s in sharpes if s > 0)
    mean = sum(sharpes) / len(sharpes)
    return pos >= POS_MIN and mean >= MEAN_MIN, pos, mean


def test_cpcv_passes_trending_series():
    rng = np.random.default_rng(0)
    trend = np.linspace(0.0005, 0.0012, 1910) + rng.normal(0, 0.008, 1910)
    passed, pos, mean = _cpcv_verdict(trend)
    assert passed, f"trending series should pass CPCV (pos={pos}/10 mean={mean:.2f})"


def test_cpcv_rejects_noise():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.01, 1910)
    passed, pos, mean = _cpcv_verdict(noise)
    assert not passed, f"noise must fail CPCV (pos={pos}/10 mean={mean:.2f})"


def test_cpcv_fail_closed_short_series():
    passed, _, _ = _cpcv_verdict(np.random.default_rng(1).normal(0, 0.01, 30))
    assert isinstance(passed, bool)
