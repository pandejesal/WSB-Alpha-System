"""
Graph-based volatility forecasting for regime-aware position sizing.

Builds a cross-asset correlation graph from a returns DataFrame and propagates
volatility across graph neighbors for a fixed number of steps using pure numpy
(no torch / networkx dependencies). Outputs a per-asset forecasted volatility
plus a market regime label derived from the cross-asset volatility level.

Fail-closed contract: invalid or empty inputs raise ValueError or return
neutral values; NaN is never silently propagated.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

# Regime thresholds on the cross-asset volatility level (annualized).
REGIME_THRESHOLDS = {
    "calm": 0.10,
    "normal": 0.20,
    "elevated": 0.35,
    "crisis": float("inf"),
}

# Default correlation threshold for building graph edges.
DEFAULT_CORR_THRESHOLD = 0.30

# Minimum number of observations required to estimate a correlation.
MIN_OBS = 5

# Annualization factor for daily returns (252 trading days).
ANNUALIZATION = 252.0


def _validate_returns(returns: np.ndarray) -> None:
    """Validate the returns matrix shape and contents (fail-closed)."""
    if returns is None or returns.size == 0:
        raise ValueError("returns matrix is empty")
    if returns.ndim != 2:
        raise ValueError("returns matrix must be 2-dimensional (obs x assets)")
    if returns.shape[0] < MIN_OBS:
        raise ValueError(
            f"returns matrix needs at least {MIN_OBS} observations, got {returns.shape[0]}"
        )
    if returns.shape[1] < 1:
        raise ValueError("returns matrix must contain at least one asset")
    if not np.isfinite(returns).all():
        raise ValueError("returns matrix contains NaN or infinite values")


def _validate_weights(weights: np.ndarray, n_assets: int) -> None:
    """Validate the adjacency weights matrix (fail-closed)."""
    if weights is None or weights.size == 0:
        raise ValueError("adjacency weights matrix is empty")
    if weights.shape != (n_assets, n_assets):
        raise ValueError(
            f"adjacency weights must be {n_assets}x{n_assets}, got {weights.shape}"
        )
    if not np.isfinite(weights).all():
        raise ValueError("adjacency weights matrix contains NaN or infinite values")


def build_correlation_graph(
    returns: np.ndarray,
    corr_threshold: float = DEFAULT_CORR_THRESHOLD,
) -> np.ndarray:
    """
    Build a cross-asset correlation adjacency matrix from a returns matrix.

    Args:
        returns: (obs x assets) numpy array of asset returns.
        corr_threshold: minimum absolute correlation to create an edge.

    Returns:
        (assets x assets) adjacency matrix where entry [i, j] is the absolute
        Pearson correlation between asset i and asset j when it exceeds the
        threshold, else 0. Diagonal is 0 (no self-edges).

    Raises:
        ValueError: if inputs are invalid or contain non-finite values.
    """
    _validate_returns(returns)
    if not np.isfinite(corr_threshold) or corr_threshold < 0:
        raise ValueError("corr_threshold must be a non-negative finite number")

    # A constant column makes numpy emit a divide-by-zero RuntimeWarning
    # internally; suppress it since we fail closed on the NaN result below.
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(returns, rowvar=False)
    if not np.isfinite(corr).all():
        # A constant column yields NaN correlation; fail closed rather than
        # silently propagating NaN.
        raise ValueError("correlation matrix contains NaN (constant asset column)")

    adj = np.abs(corr)
    np.fill_diagonal(adj, 0.0)
    adj[adj < corr_threshold] = 0.0
    return adj


def propagate_volatility(
    base_vol: np.ndarray,
    adjacency: np.ndarray,
    steps: int = 3,
    decay: float = 0.5,
) -> np.ndarray:
    """
    Propagate volatility across graph neighbors for a fixed number of steps.

    Each step updates each asset's volatility as a weighted blend of its own
    volatility and the volatility of its correlated neighbors:

        vol_{t+1}[i] = (1 - decay) * vol_t[i]
                       + decay * sum_j(adj[i, j] * vol_t[j]) / sum_j(adj[i, j])

    Assets with no neighbors keep their own volatility (no dilution).

    Args:
        base_vol: (assets,) array of per-asset base volatility (annualized).
        adjacency: (assets x assets) correlation adjacency matrix.
        steps: number of propagation steps (>= 0).
        decay: fraction of neighbor influence per step in [0, 1].

    Returns:
        (assets,) array of forecasted volatility after propagation.

    Raises:
        ValueError: if inputs are invalid or contain non-finite values.
    """
    base_vol = np.asarray(base_vol, dtype=float)
    adjacency = np.asarray(adjacency, dtype=float)

    if base_vol.ndim != 1 or base_vol.size == 0:
        raise ValueError("base_vol must be a non-empty 1-dimensional array")
    n_assets = base_vol.size
    _validate_weights(adjacency, n_assets)

    if not np.isfinite(base_vol).all():
        raise ValueError("base_vol contains NaN or infinite values")
    if (base_vol < 0).any():
        raise ValueError("base_vol must be non-negative")
    if not isinstance(steps, int) or steps < 0:
        raise ValueError("steps must be a non-negative integer")
    if not np.isfinite(decay) or not (0.0 <= decay <= 1.0):
        raise ValueError("decay must be a finite value in [0, 1]")

    vol = base_vol.copy()
    neighbor_sum = adjacency.sum(axis=1)

    for _ in range(steps):
        # Neighbor-weighted volatility for each asset.
        neighbor_vol = adjacency @ vol
        # Normalize by neighbor weight; assets with no neighbors keep own vol.
        with np.errstate(divide="ignore", invalid="ignore"):
            neighbor_avg = np.where(
                neighbor_sum > 0, neighbor_vol / np.maximum(neighbor_sum, 1e-12), vol
            )
        vol = (1.0 - decay) * vol + decay * neighbor_avg

    if not np.isfinite(vol).all():
        raise ValueError("propagation produced non-finite volatility")
    return vol


def classify_regime(
    forecasted_vol: np.ndarray,
    thresholds: dict | None = None,
) -> str:
    """
    Classify the market regime from the cross-asset volatility level.

    Uses the mean of the forecasted per-asset volatilities against a threshold
    ladder. Returns a neutral label ("normal") when the input is empty or
    non-finite rather than raising, per the fail-closed contract.

    Args:
        forecasted_vol: (assets,) array of forecasted volatility.
        thresholds: optional dict mapping regime -> upper bound. Defaults to
            REGIME_THRESHOLDS.

    Returns:
        One of "calm", "normal", "elevated", "crisis".
    """
    if forecasted_vol is None or len(forecasted_vol) == 0:
        return "normal"
    arr = np.asarray(forecasted_vol, dtype=float)
    if not np.isfinite(arr).all():
        return "normal"
    if (arr < 0).any():
        return "normal"

    ladder = thresholds if thresholds is not None else REGIME_THRESHOLDS
    level = float(np.mean(arr))
    for regime, upper in ladder.items():
        if level <= upper:
            return regime
    return "normal"


def forecast_volatility(
    returns: np.ndarray,
    steps: int = 3,
    decay: float = 0.5,
    corr_threshold: float = DEFAULT_CORR_THRESHOLD,
) -> dict:
    """
    End-to-end graph-based volatility forecast with regime label.

    Args:
        returns: (obs x assets) numpy array of asset returns.
        steps: number of propagation steps.
        decay: neighbor influence fraction per step.
        corr_threshold: minimum absolute correlation to create an edge.

    Returns:
        dict with keys:
            - "forecasted_volatility": (assets,) array of forecasted volatility.
            - "base_volatility": (assets,) array of base (own) volatility.
            - "regime": str regime label.
            - "adjacency": (assets x assets) correlation adjacency matrix.

    Raises:
        ValueError: if inputs are invalid or contain non-finite values.
    """
    _validate_returns(returns)

    # Base volatility: annualized standard deviation of each asset's returns.
    base_vol = np.std(returns, axis=0, ddof=1) * np.sqrt(ANNUALIZATION)
    if not np.isfinite(base_vol).all():
        raise ValueError("base volatility contains non-finite values")

    adjacency = build_correlation_graph(returns, corr_threshold=corr_threshold)
    forecasted = propagate_volatility(base_vol, adjacency, steps=steps, decay=decay)
    regime = classify_regime(forecasted)

    return {
        "forecasted_volatility": forecasted,
        "base_volatility": base_vol,
        "regime": regime,
        "adjacency": adjacency,
    }
