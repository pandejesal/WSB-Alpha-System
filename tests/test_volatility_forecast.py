"""
Regression tests for the graph-based volatility forecasting module
(src/risk/volatility_forecast.py).
"""

import numpy as np
import pytest

from src.risk.volatility_forecast import (
    ANNUALIZATION,
    DEFAULT_CORR_THRESHOLD,
    MIN_OBS,
    REGIME_THRESHOLDS,
    build_correlation_graph,
    classify_regime,
    forecast_volatility,
    propagate_volatility,
)


def _make_returns(n_obs: int = 120, n_assets: int = 4, seed: int = 0) -> np.ndarray:
    """Deterministic returns matrix with correlated assets."""
    rng = np.random.default_rng(seed)
    common = rng.normal(0.0, 0.01, size=(n_obs, 1))
    noise = rng.normal(0.0, 0.005, size=(n_obs, n_assets))
    returns = common + noise
    # Give asset 0 a distinct volatility so propagation has an effect.
    returns[:, 0] = returns[:, 0] * 2.0
    return returns


class TestBuildCorrelationGraph:
    def test_returns_adjacency_shape_and_diagonal(self):
        returns = _make_returns()
        adj = build_correlation_graph(returns)
        assert adj.shape == (4, 4)
        assert np.allclose(np.diag(adj), 0.0)
        assert np.all(adj >= 0.0)

    def test_high_threshold_yields_sparse_graph(self):
        returns = _make_returns()
        adj = build_correlation_graph(returns, corr_threshold=0.99)
        assert np.all(adj == 0.0)

    def test_low_threshold_yields_dense_graph(self):
        returns = _make_returns()
        adj = build_correlation_graph(returns, corr_threshold=0.0)
        # Every off-diagonal pair shares the common factor -> positive corr.
        assert np.count_nonzero(adj) > 0

    def test_edges_are_symmetric(self):
        returns = _make_returns()
        adj = build_correlation_graph(returns)
        assert np.allclose(adj, adj.T)

    def test_empty_returns_raises(self):
        with pytest.raises(ValueError):
            build_correlation_graph(np.empty((0, 3)))

    def test_nan_returns_raise(self):
        returns = _make_returns()
        returns[0, 0] = np.nan
        with pytest.raises(ValueError):
            build_correlation_graph(returns)

    def test_constant_column_raises(self):
        returns = np.ones((50, 3))
        with pytest.raises(ValueError):
            build_correlation_graph(returns)

    def test_too_few_observations_raises(self):
        returns = _make_returns(n_obs=MIN_OBS - 1)
        with pytest.raises(ValueError):
            build_correlation_graph(returns)

    def test_negative_threshold_raises(self):
        returns = _make_returns()
        with pytest.raises(ValueError):
            build_correlation_graph(returns, corr_threshold=-0.1)


class TestPropagateVolatility:
    def test_zero_steps_returns_base_vol(self):
        base = np.array([0.2, 0.3, 0.4])
        adj = np.array([[0.0, 0.5, 0.0], [0.5, 0.0, 0.5], [0.0, 0.5, 0.0]])
        out = propagate_volatility(base, adj, steps=0)
        assert np.allclose(out, base)

    def test_no_neighbors_keeps_own_vol(self):
        base = np.array([0.2, 0.3])
        adj = np.zeros((2, 2))
        out = propagate_volatility(base, adj, steps=5)
        assert np.allclose(out, base)

    def test_propagation_moves_toward_neighbors(self):
        # Asset 0 has high vol and is connected to low-vol asset 1.
        base = np.array([0.5, 0.1])
        adj = np.array([[0.0, 0.9], [0.9, 0.0]])
        out = propagate_volatility(base, adj, steps=10, decay=0.5)
        # After many steps both converge toward the mean.
        assert out[0] < base[0]
        assert out[1] > base[1]
        assert np.allclose(out, np.array([0.3, 0.3]), atol=1e-6)

    def test_decay_zero_keeps_own_vol(self):
        base = np.array([0.5, 0.1])
        adj = np.array([[0.0, 0.9], [0.9, 0.0]])
        out = propagate_volatility(base, adj, steps=5, decay=0.0)
        assert np.allclose(out, base)

    def test_output_is_finite(self):
        base = np.array([0.2, 0.3, 0.4])
        adj = np.array([[0.0, 0.5, 0.2], [0.5, 0.0, 0.1], [0.2, 0.1, 0.0]])
        out = propagate_volatility(base, adj, steps=3)
        assert np.isfinite(out).all()

    def test_empty_base_raises(self):
        with pytest.raises(ValueError):
            propagate_volatility(np.array([]), np.zeros((0, 0)))

    def test_nan_base_raises(self):
        with pytest.raises(ValueError):
            propagate_volatility(np.array([0.2, np.nan]), np.zeros((2, 2)))

    def test_negative_base_raises(self):
        with pytest.raises(ValueError):
            propagate_volatility(np.array([0.2, -0.1]), np.zeros((2, 2)))

    def test_wrong_adjacency_shape_raises(self):
        with pytest.raises(ValueError):
            propagate_volatility(np.array([0.2, 0.3]), np.zeros((3, 3)))

    def test_nan_adjacency_raises(self):
        adj = np.zeros((2, 2))
        adj[0, 1] = np.nan
        with pytest.raises(ValueError):
            propagate_volatility(np.array([0.2, 0.3]), adj)

    def test_negative_steps_raises(self):
        with pytest.raises(ValueError):
            propagate_volatility(np.array([0.2, 0.3]), np.zeros((2, 2)), steps=-1)

    def test_out_of_range_decay_raises(self):
        with pytest.raises(ValueError):
            propagate_volatility(
                np.array([0.2, 0.3]), np.zeros((2, 2)), decay=1.5
            )


class TestClassifyRegime:
    def test_calm(self):
        assert classify_regime(np.array([0.05, 0.08])) == "calm"

    def test_normal(self):
        assert classify_regime(np.array([0.15, 0.18])) == "normal"

    def test_elevated(self):
        assert classify_regime(np.array([0.25, 0.30])) == "elevated"

    def test_crisis(self):
        assert classify_regime(np.array([0.40, 0.50])) == "crisis"

    def test_empty_returns_neutral(self):
        assert classify_regime(np.array([])) == "normal"

    def test_nan_returns_neutral(self):
        assert classify_regime(np.array([0.2, np.nan])) == "normal"

    def test_negative_returns_neutral(self):
        assert classify_regime(np.array([0.2, -0.1])) == "normal"

    def test_custom_thresholds(self):
        custom = {"low": 0.05, "high": float("inf")}
        assert classify_regime(np.array([0.03]), thresholds=custom) == "low"
        assert classify_regime(np.array([0.10]), thresholds=custom) == "high"


class TestForecastVolatility:
    def test_end_to_end_output_contract(self):
        returns = _make_returns()
        result = forecast_volatility(returns)
        assert set(result.keys()) == {
            "forecasted_volatility",
            "base_volatility",
            "regime",
            "adjacency",
        }
        assert result["forecasted_volatility"].shape == (4,)
        assert result["base_volatility"].shape == (4,)
        assert result["adjacency"].shape == (4, 4)
        assert result["regime"] in REGIME_THRESHOLDS
        assert np.isfinite(result["forecasted_volatility"]).all()

    def test_base_volatility_is_annualized_std(self):
        returns = _make_returns()
        result = forecast_volatility(returns)
        expected = np.std(returns, axis=0, ddof=1) * np.sqrt(ANNUALIZATION)
        assert np.allclose(result["base_volatility"], expected)

    def test_forecasted_volatility_is_finite_and_positive(self):
        returns = _make_returns()
        result = forecast_volatility(returns)
        assert np.isfinite(result["forecasted_volatility"]).all()
        assert (result["forecasted_volatility"] > 0).all()

    def test_empty_returns_raises(self):
        with pytest.raises(ValueError):
            forecast_volatility(np.empty((0, 3)))

    def test_nan_returns_raise(self):
        returns = _make_returns()
        returns[0, 0] = np.nan
        with pytest.raises(ValueError):
            forecast_volatility(returns)

    def test_1d_returns_raise(self):
        with pytest.raises(ValueError):
            forecast_volatility(np.array([0.01, 0.02, 0.03]))

    def test_high_volatility_assets_yield_crisis_regime(self):
        rng = np.random.default_rng(7)
        returns = rng.normal(0.0, 0.05, size=(200, 3))
        result = forecast_volatility(returns)
        assert result["regime"] == "crisis"

    def test_low_volatility_assets_yield_calm_regime(self):
        rng = np.random.default_rng(8)
        returns = rng.normal(0.0, 0.005, size=(200, 3))
        result = forecast_volatility(returns)
        assert result["regime"] == "calm"

    def test_default_corr_threshold_constant(self):
        assert DEFAULT_CORR_THRESHOLD == 0.30