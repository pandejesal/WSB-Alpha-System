"""Tests for the qlib Alpha158 + TopkDropout port.

Covers: no-lookahead, feature count >= 40, rotation determinism, SPY baseline,
turnover accounting, and metric sanity.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.signals.qlib_alpha158 import compute_alpha158, get_feature_names
from src.backtest.qlib_topk import (
    compute_metrics,
    spy_buyhold,
    topk_rotation,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "market_data_2019_2026", "ohlcv")
SPY_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "spy_ohlcv_2019_2026.csv")


def _make_ohlcv(n=200):
    """Synthetic OHLCV for deterministic tests."""
    rng = np.random.RandomState(42)
    dates = pd.bdate_range("2020-01-01", periods=n)
    close = 100 + np.cumsum(rng.randn(n) * 0.5)
    return pd.DataFrame({
        "date": dates,
        "open": close + rng.randn(n) * 0.1,
        "high": close + abs(rng.randn(n) * 0.5),
        "low": close - abs(rng.randn(n) * 0.5),
        "close": close,
        "volume": rng.randint(1_000_000, 10_000_000, n).astype(float),
    })


class TestNoLookahead:
    def test_feature_shift(self):
        df = _make_ohlcv(200)
        result = compute_alpha158(df)
        feats = get_feature_names()
        assert len(feats) > 0
        for f in feats[:10]:
            if f in result.columns:
                first_nonnan = result[f].first_valid_index()
                if first_nonnan is not None:
                    pos = result.index.get_loc(first_nonnan)
                    assert pos >= 1, f"Feature {f} first valid row should be at index >= 1 (shifted)"

    def test_nan_at_start(self):
        df = _make_ohlcv(100)
        result = compute_alpha158(df)
        feats = get_feature_names()
        assert len(feats) > 0
        for f in feats[:5]:
            assert pd.isna(result[f].iloc[0]), (
                f"First row of {f} should be NaN (shifted)"
            )


class TestFeatureCount:
    def test_at_least_40_features(self):
        df = _make_ohlcv(200)
        compute_alpha158(df)
        names = get_feature_names()
        assert len(names) >= 40, f"Expected >= 40 features, got {len(names)}"

    def test_all_feature_families_present(self):
        df = _make_ohlcv(200)
        compute_alpha158(df)
        names = get_feature_names()
        families = ["KMid", "KLen", "KMid2", "KUp", "ROC", "Rank",
                    "Quantile", "Std", "Sum", "Mean", "Max", "Min"]
        for fam in families:
            matching = [n for n in names if n.startswith(fam)]
            assert len(matching) >= 4, (
                f"Family {fam} should have >= 4 window variants, got {len(matching)}"
            )


class TestRotationDeterminism:
    def test_same_universe_same_result(self):
        df1 = _make_ohlcv(200)
        df2 = df1.copy()
        u1 = {"A": df1}
        u2 = {"A": df2}
        r1 = topk_rotation(u1, top_k=1, lookback=30)
        r2 = topk_rotation(u2, top_k=1, lookback=30)
        pd.testing.assert_frame_equal(r1, r2)

    def test_deterministic_with_seed_data(self):
        u = {"A": _make_ohlcv(300)}
        r = topk_rotation(u, top_k=1, lookback=30)
        assert len(r) > 0
        assert not pd.isna(r["portfolio_return"].iloc[0])


class TestSpyBaseline:
    def test_spy_buyhold_loads(self):
        if not os.path.exists(SPY_CSV):
            pytest.skip("SPY CSV not found")
        spy = spy_buyhold(SPY_CSV)
        assert "spy_return" in spy.columns
        assert "spy_equity" in spy.columns
        assert len(spy) > 100

    def test_spy_equity_starts_near_100k(self):
        if not os.path.exists(SPY_CSV):
            pytest.skip("SPY CSV not found")
        spy = spy_buyhold(SPY_CSV)
        assert 50_000 < spy["spy_equity"].iloc[0] < 150_000


class TestTurnoverAccounting:
    def test_turnover_non_negative(self):
        u = {"A": _make_ohlcv(300)}
        r = topk_rotation(u, top_k=1, lookback=30)
        assert (r["turnover"] >= 0).all(), "Turnover must be non-negative"

    def test_num_positions_respects_top_k(self):
        u = {"A": _make_ohlcv(300), "B": _make_ohlcv(300), "C": _make_ohlcv(300)}
        r = topk_rotation(u, top_k=2, lookback=30)
        valid = r[r["num_positions"] > 0]
        assert (valid["num_positions"] <= 2).all(), "Should hold <= top_k"


class TestMetricSanity:
    def test_metrics_are_finite(self):
        u = {"A": _make_ohlcv(300)}
        r = topk_rotation(u, top_k=1, lookback=30)
        m = compute_metrics(r)
        assert np.isfinite(m["sharpe"])
        assert np.isfinite(m["max_drawdown"])
        assert np.isfinite(m["total_return"])

    def test_max_drawdown_negative(self):
        u = {"A": _make_ohlcv(300)}
        r = topk_rotation(u, top_k=1, lookback=30)
        m = compute_metrics(r)
        assert m["max_drawdown"] <= 0, "Max drawdown should be <= 0"


class TestRotationActuallyTrades:
    """Regression: topk_rotation must take positions (never-flat guard)."""

    def test_time_in_market_after_warmup(self):
        u = {"A": _make_ohlcv(300), "B": _make_ohlcv(300), "C": _make_ohlcv(300)}
        r = topk_rotation(u, top_k=2, lookback=30)
        post = r.iloc[30:]
        tim = (post["num_positions"] > 0).mean()
        assert tim > 0.5, f"rotation flat {1 - tim:.0%} of the time after warmup"

    def test_turnover_positive_when_rebalanced(self):
        u = {"A": _make_ohlcv(300), "B": _make_ohlcv(300), "C": _make_ohlcv(300)}
        r = topk_rotation(u, top_k=1, lookback=30, rebalance_freq=5)
        assert r["turnover"].sum() > 0, "no rotation ever occurred"
