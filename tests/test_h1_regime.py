import pytest
import numpy as np
import pandas as pd
import yaml

from src.alpha.h1_hmm import RegimeHMM
from src.alpha.h1_features import compute_regime_features
from src.alpha.h1_regime_filter import RegimeFilter
from src.alpha.h1_regime_detection import RegimeDetector
from src.alpha.meta_strategy import MetaStrategy

@pytest.fixture
def synthetic_data():
    """Generates synthetic OHLCV + VIX data for HMM testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=200, freq="D")

    # Create a trending up, then high vol, then trending down series
    close = np.linspace(100, 150, 60)
    close = np.append(close, 150 + np.random.normal(0, 10, 80))
    close = np.append(close, np.linspace(150, 90, 60))

    vix = np.random.normal(15, 2, 60)
    vix = np.append(vix, np.random.normal(35, 5, 80))
    vix = np.append(vix, np.random.normal(20, 3, 60))

    df = pd.DataFrame({
        "Close": close,
        "VIX": vix
    }, index=dates)
    return df

@pytest.fixture
def config_yaml():
    """Loads the config file to test against real config."""
    with open("config/regime_config.yaml", "r") as f:
        return yaml.safe_load(f)

def test_hmm_convergence_and_labels(synthetic_data):
    features = compute_regime_features(synthetic_data)

    hmm = RegimeHMM(n_components=4)
    hmm.fit(features)

    assert hmm.is_fitted

    preds = hmm.predict(features)

    # Check return type and valid labels
    assert isinstance(preds, pd.Series)
    assert set(preds.unique()).issubset({0, 1, 2, 3})

def test_hmm_transition_matrix(synthetic_data):
    features = compute_regime_features(synthetic_data)
    hmm = RegimeHMM(n_components=4)
    hmm.fit(features)

    transmat = hmm.get_transition_matrix()

    assert transmat.shape == (4, 4)
    # Rows should sum to 1.0 (with slight floating point tolerance)
    np.testing.assert_allclose(transmat.sum(axis=1), 1.0, rtol=1e-5)

def test_hmm_validation():
    with pytest.raises(ValueError, match="RegimeHMM explicitly expects exactly 4 components"):
        RegimeHMM(n_components=3)

def test_regime_filter():
    rf = RegimeFilter()

    df = pd.DataFrame({
        "signal": ["long", "short", "mean_reversion", "long", "long"]
    })

    regime_labels = pd.Series(["bull", "bear", "high_vol", "range", "bull"])

    config = {
        "bull": {"position_multiplier": 1.2, "allow_signals": ["long", "short", "mean_reversion"]},
        "bear": {"position_multiplier": 0.8, "allow_signals": ["short"]},
        "high_vol": {"position_multiplier": 0.5, "allow_signals": []},
        "range": {"position_multiplier": 1.0, "allow_signals": ["mean_reversion"]}
    }

    out = rf.filter_signals(df, regime_labels, config)

    # Check contexts mapped
    assert list(out["regime_context"]) == ["bull", "bear", "high_vol", "range", "bull"]

    # Check multipliers mapped correctly
    assert list(out["position_multiplier"]) == [1.2, 0.8, 0.5, 1.0, 1.2]

    # Check signals blocked/allowed correctly
    assert out.iloc[0]["signal"] == "long" # allowed in bull
    assert out.iloc[1]["signal"] == "short" # short allowed in bear, but this was 'short' so it should be allowed! wait!
    # Let me fix the test data to be more explicit.
    # Row 1 is 'short' in 'bear' -> should be 'short'
    # Row 2 is 'mean_reversion' in 'high_vol' -> should be blocked ('flat')
    # Row 3 is 'long' in 'range' -> should be blocked ('flat')
    # Row 4 is 'long' in 'bull' -> should be allowed

def test_regime_filter_exact():
    rf = RegimeFilter()
    df = pd.DataFrame({"signal": ["long", "short", "mean_reversion", "long"]})
    regime_labels = pd.Series(["bull", "bear", "high_vol", "range"])
    config = {
        "bull": {"position_multiplier": 1.2, "allow_signals": ["long", "short", "mean_reversion"]},
        "bear": {"position_multiplier": 0.8, "allow_signals": ["short"]},
        "high_vol": {"position_multiplier": 0.5, "allow_signals": []},
        "range": {"position_multiplier": 1.0, "allow_signals": ["mean_reversion"]}
    }
    out = rf.filter_signals(df, regime_labels, config)
    assert list(out["signal"]) == ["long", "short", "flat", "flat"]
    assert list(out["position_multiplier"]) == [1.2, 0.8, 0.5, 1.0]

def test_regime_detector_and_meta_strategy(synthetic_data, config_yaml):
    detector = RegimeDetector(config=config_yaml["regime"])

    # Test detect_regime returns Series with correct string labels
    regimes = detector.detect_regime(synthetic_data)
    assert isinstance(regimes, pd.Series)
    assert set(regimes.dropna().unique()).issubset({"bull", "bear", "high_vol", "range"})

    # Test MetaStrategy integration
    ms = MetaStrategy(config=config_yaml)

    signals = pd.DataFrame({"signal": ["long"] * len(synthetic_data)}, index=synthetic_data.index)
    filtered = ms.select_strategy(synthetic_data, signals)

    assert "regime_context" in filtered.columns
    assert "position_multiplier" in filtered.columns

    # High_vol should block long signals
    if (filtered["regime_context"] == "high_vol").any():
        assert (filtered.loc[filtered["regime_context"] == "high_vol", "signal"] == "flat").all()
