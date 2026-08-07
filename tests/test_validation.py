import pytest
import numpy as np
import pandas as pd
from src.backtest.validation import compute_risk_analytics

def test_compute_risk_analytics():
    np.random.seed(42)
    # Generate 100 days of random returns with slight positive drift
    returns = pd.Series(np.random.normal(0.001, 0.02, 100))

    # Generate 10 mock benchmark models
    bench_family = np.random.normal(0.0005, 0.02, (10, 100))

    metrics = compute_risk_analytics(returns, benchmark_returns_family=bench_family, num_bootstraps=100)

    # Validate keys
    assert "var_95" in metrics
    assert "cvar_95" in metrics
    assert "var_99" in metrics
    assert "cvar_99" in metrics
    assert "sharpe" in metrics
    assert "sortino" in metrics
    assert "win_rate" in metrics
    assert "max_drawdown_pct" in metrics
    assert "max_drawdown_duration" in metrics
    assert "spa_p_value" in metrics

    # Validate logic bounds
    assert metrics["cvar_95"] <= metrics["var_95"]
    assert metrics["cvar_99"] <= metrics["var_99"]
    assert 0 <= metrics["win_rate"] <= 1.0
    assert metrics["max_drawdown_pct"] <= 0
    assert isinstance(metrics["max_drawdown_duration"], int)

    if metrics["spa_p_value"] is not None:
        assert 0.0 <= metrics["spa_p_value"] <= 1.0

def test_compute_risk_analytics_empty():
    metrics = compute_risk_analytics(pd.Series([], dtype=float))
    assert not metrics
