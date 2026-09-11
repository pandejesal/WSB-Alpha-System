"""Tests for src.alpha.hierarchical_rl — three-tier observation layers
(daily / intraday / execution), regime detection, and the fail-closed trade
timing gate for the RL Signal Engine (HARLF, arXiv 2507.18560)."""

import math

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures (deterministic, no randomness)
# ---------------------------------------------------------------------------

def _ohlcv(close):
    """Build a deterministic OHLCV frame from a close series.

    high = close * 1.01, low = close * 0.99 (close sits at the bar midpoint),
    open = previous close, volume constant at 1e6.
    """
    close = pd.Series(close, dtype=float)
    return pd.DataFrame({
        "open": close.shift(1).fillna(close.iloc[0]),
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": 1e6,
    })


def _low_vol_bull_df(n_choppy=140, n_calm=60):
    """Choppy then calm uptrend -> LowVol-Bull regime."""
    close = [100.0]
    for i in range(n_choppy):
        close.append(102.0 if i % 2 == 0 else 100.0)
    for _ in range(n_calm):
        close.append(close[-1] * 1.002)
    return _ohlcv(close)


def _high_vol_df(n_calm=180, n_alt=20):
    """Calm uptrend then violent alternation -> HighVol-Bull regime."""
    close = [100.0]
    for _ in range(n_calm):
        close.append(close[-1] * 1.001)
    for i in range(n_alt):
        close.append(close[-1] * (1.05 if i % 2 == 0 else 0.96))
    return _ohlcv(close)


def _neutral_df(n=300):
    """Alternating +/-1% -> MidVol-Neutral regime."""
    close = [100.0]
    for i in range(n):
        close.append(101.0 if i % 2 == 0 else 100.0)
    return _ohlcv(close)


# ---------------------------------------------------------------------------
# build_daily_layer
# ---------------------------------------------------------------------------

def test_daily_layer_empty_input():
    from src.alpha.hierarchical_rl import build_daily_layer

    assert build_daily_layer(pd.DataFrame()) == {}
    assert build_daily_layer(None) == {}


def test_daily_layer_missing_column_raises():
    from src.alpha.hierarchical_rl import build_daily_layer

    with pytest.raises(ValueError):
        build_daily_layer(pd.DataFrame({"close": [1.0, 2.0]}))


def test_daily_layer_keys_and_no_nan():
    from src.alpha.hierarchical_rl import DAILY_FEATURE_NAMES, build_daily_layer

    daily = build_daily_layer(_low_vol_bull_df())
    assert set(daily) == set(DAILY_FEATURE_NAMES)
    assert all(isinstance(v, float) for v in daily.values())
    assert not any(pd.isna(v) for v in daily.values())


def test_daily_layer_short_history_no_nan():
    from src.alpha.hierarchical_rl import build_daily_layer

    daily = build_daily_layer(_ohlcv([100.0, 101.0, 102.0, 103.0, 104.0]))
    assert set(daily) == {
        "daily_return_1d",
        "daily_return_21d",
        "daily_vol_21d",
        "daily_vol_ratio_20_60",
        "daily_sma_50_ratio",
        "daily_sma_200_ratio",
        "daily_drawdown_52w",
    }
    # insufficient history must degrade to 0.0, never NaN
    assert not any(pd.isna(v) for v in daily.values())


# ---------------------------------------------------------------------------
# build_intraday_layer
# ---------------------------------------------------------------------------

def test_intraday_layer_empty_input():
    from src.alpha.hierarchical_rl import build_intraday_layer

    assert build_intraday_layer(pd.DataFrame()) == {}


def test_intraday_layer_missing_column_raises():
    from src.alpha.hierarchical_rl import build_intraday_layer

    with pytest.raises(ValueError):
        build_intraday_layer(pd.DataFrame({"close": [1.0, 2.0]}))


def test_intraday_layer_keys():
    from src.alpha.hierarchical_rl import INTRADAY_FEATURE_NAMES, build_intraday_layer

    intraday = build_intraday_layer(_low_vol_bull_df())
    assert set(intraday) == set(INTRADAY_FEATURE_NAMES)
    assert all(isinstance(v, float) for v in intraday.values())


def test_intraday_close_position_midpoint():
    from src.alpha.hierarchical_rl import build_intraday_layer

    # high = close * 1.01, low = close * 0.99 -> close sits at 0.5 of the range
    intraday = build_intraday_layer(_low_vol_bull_df())
    assert intraday["intraday_close_position"] == pytest.approx(0.5, abs=1e-9)


def test_intraday_volume_ratio_constant_volume():
    from src.alpha.hierarchical_rl import build_intraday_layer

    intraday = build_intraday_layer(_low_vol_bull_df())
    assert intraday["intraday_volume_ratio"] == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# build_execution_layer
# ---------------------------------------------------------------------------

def test_execution_layer_empty_fail_closed():
    from src.alpha.hierarchical_rl import build_execution_layer

    layer = build_execution_layer(pd.DataFrame(), position=0.4)
    assert layer == {
        "execution_position": 0.4,
        "execution_liquidity": 0.0,
        "execution_spread_proxy": 0.0,
        "execution_slippage_proxy": 0.0,
    }


def test_execution_layer_keys_and_position():
    from src.alpha.hierarchical_rl import EXECUTION_FEATURE_NAMES, build_execution_layer

    layer = build_execution_layer(_low_vol_bull_df(), position=0.4)
    assert set(layer) == set(EXECUTION_FEATURE_NAMES)
    assert layer["execution_position"] == 0.4


def test_execution_layer_liquidity_log1p():
    from src.alpha.hierarchical_rl import build_execution_layer

    layer = build_execution_layer(_low_vol_bull_df(), position=0.0)
    assert layer["execution_liquidity"] == pytest.approx(math.log1p(1e6))


# ---------------------------------------------------------------------------
# detect_regime
# ---------------------------------------------------------------------------

def test_detect_regime_low_vol_bull():
    from src.alpha.hierarchical_rl import detect_regime

    regime = detect_regime(_low_vol_bull_df())
    assert regime["regime_label"] == "LowVol-Bull"
    assert regime["vol_regime"] == "low"
    assert regime["trend_regime"] == "bull"


def test_detect_regime_high_vol_bull():
    from src.alpha.hierarchical_rl import detect_regime

    regime = detect_regime(_high_vol_df())
    assert regime["regime_label"] == "HighVol-Bull"
    assert regime["vol_regime"] == "high"
    assert regime["trend_regime"] == "bull"


def test_detect_regime_mid_vol_neutral():
    from src.alpha.hierarchical_rl import detect_regime

    regime = detect_regime(_neutral_df())
    assert regime["regime_label"] == "MidVol-Neutral"
    assert regime["vol_regime"] == "neutral"
    assert regime["trend_regime"] == "neutral"


def test_detect_regime_empty_unknown():
    from src.alpha.hierarchical_rl import detect_regime

    regime = detect_regime(pd.DataFrame())
    assert regime["regime_label"] == "Unknown"
    assert regime["vol_regime"] == "unknown"
    assert regime["trend_regime"] == "unknown"
    assert regime["confidence"] == 0.0


def test_detect_regime_missing_column_raises():
    from src.alpha.hierarchical_rl import detect_regime

    with pytest.raises(ValueError):
        detect_regime(pd.DataFrame({"close": [1.0, 2.0]}))


# ---------------------------------------------------------------------------
# suggest_trade_timing
# ---------------------------------------------------------------------------

def test_timing_insufficient_data_blocked():
    from src.alpha.hierarchical_rl import suggest_trade_timing

    timing = suggest_trade_timing(pd.DataFrame())
    assert timing["should_trade"] is False
    assert timing["reason"] == "insufficient data"
    assert timing["confidence"] == 0.0


def test_timing_high_vol_blocked():
    from src.alpha.hierarchical_rl import suggest_trade_timing

    timing = suggest_trade_timing(_high_vol_df())
    assert timing["should_trade"] is False
    assert timing["reason"] == "high volatility regime"
    assert timing["regime"] == "HighVol-Bull"


def test_timing_position_limit_blocked():
    from src.alpha.hierarchical_rl import suggest_trade_timing

    timing = suggest_trade_timing(_low_vol_bull_df(), position=1.0, max_position=1.0)
    assert timing["should_trade"] is False
    assert timing["reason"] == "position limit reached"


def test_timing_allows_trade():
    from src.alpha.hierarchical_rl import suggest_trade_timing

    timing = suggest_trade_timing(_low_vol_bull_df(), position=0.0)
    assert timing["should_trade"] is True
    assert timing["reason"] == "regime supports trading"
    assert timing["regime"] == "LowVol-Bull"


# ---------------------------------------------------------------------------
# build_hierarchical_observation
# ---------------------------------------------------------------------------

def test_observation_structure():
    from src.alpha.hierarchical_rl import (
        build_hierarchical_observation,
        hierarchical_feature_names,
    )

    obs = build_hierarchical_observation(
        _low_vol_bull_df(),
        _low_vol_bull_df(),
        _low_vol_bull_df(),
        position=0.0,
    )
    assert obs.feature_names == hierarchical_feature_names()
    assert len(obs.features) == len(hierarchical_feature_names())
    assert all(isinstance(v, float) for v in obs.features)

    d = obs.to_dict()
    assert set(d) == {
        "daily",
        "intraday",
        "execution",
        "regime",
        "timing",
        "feature_names",
        "features",
    }
    assert d["regime"]["regime_label"] == "LowVol-Bull"
    assert d["timing"]["should_trade"] is True


def test_observation_empty_fail_closed():
    from src.alpha.hierarchical_rl import build_hierarchical_observation

    obs = build_hierarchical_observation(
        pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), position=0.0
    )
    assert obs.features == [0.0] * len(obs.features)
    assert obs.regime["regime_label"] == "Unknown"
    assert obs.timing["should_trade"] is False
    assert obs.timing["reason"] == "insufficient data"


def test_observation_position_passthrough():
    from src.alpha.hierarchical_rl import build_hierarchical_observation

    obs = build_hierarchical_observation(
        pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), position=0.7
    )
    idx = obs.feature_names.index("execution_position")
    assert obs.features[idx] == 0.7


def test_observation_missing_column_raises():
    from src.alpha.hierarchical_rl import build_hierarchical_observation

    with pytest.raises(ValueError):
        build_hierarchical_observation(
            pd.DataFrame({"close": [1.0, 2.0]}),
            _ohlcv([100.0, 101.0]),
            _ohlcv([100.0, 101.0]),
        )


# ---------------------------------------------------------------------------
# Feature space
# ---------------------------------------------------------------------------

def test_feature_names_length():
    from src.alpha.hierarchical_rl import hierarchical_feature_names

    names = hierarchical_feature_names()
    assert len(names) == 16
    assert len(set(names)) == 16  # no duplicates


def test_observation_space_size():
    from src.alpha.hierarchical_rl import observation_space_size

    assert observation_space_size() == 16