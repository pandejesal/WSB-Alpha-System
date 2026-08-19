import json
import yaml
import pytest
import pandas as pd
from unittest import mock

from src.ops.strategy_registry import load_registry, validate_spec, MalformedSpecError
from src.ops.signals import generate_signals_from_registry, UnsupportedRuleShape

@pytest.fixture
def mock_registry_dir(tmp_path):
    """Creates a temporary directory for registry and specs."""
    reg_dir = tmp_path / "strategies"
    reg_dir.mkdir()
    return reg_dir

def test_validate_spec_success():
    spec = {
        "id": "test_strat",
        "name": "Test Strategy",
        "family": "momentum",
        "universe": "SPY",
        "parameters": {"lookback": 10},
        "signal": {"entry": "buy"}
    }
    assert validate_spec(spec, "mock_path.yaml") is True

def test_validate_spec_missing_required_field():
    spec = {
        "id": "test_strat",
        "name": "Test Strategy",
        "universe": "SPY",
        "parameters": {"lookback": 10},
        "signal": {"entry": "buy"}
    }
    with pytest.raises(MalformedSpecError, match="missing required field: family"):
        validate_spec(spec, "mock_path.yaml")

def test_validate_spec_invalid_type():
    spec = {
        "id": "test_strat",
        "name": "Test Strategy",
        "family": "momentum",
        "universe": 123, # Should be string or list
        "parameters": {"lookback": 10},
        "signal": {"entry": "buy"}
    }
    with pytest.raises(MalformedSpecError, match="invalid type for universe"):
        validate_spec(spec, "mock_path.yaml")

def test_load_registry_success(mock_registry_dir):
    # Create mock spec
    spec = {
        "id": "mock_strat",
        "name": "Mock Strategy",
        "family": "momentum",
        "universe": "SPY",
        "parameters": {"lookback": 10},
        "signal": {"entry": "buy"}
    }
    spec_path = mock_registry_dir / "mock_strat.yaml"
    with open(spec_path, 'w') as f:
        yaml.dump(spec, f)

    # Create mock registry
    registry = {
        "strategies": [
            {
                "id": "mock_strat",
                "spec_file": str(spec_path),
                "status": "active"
            }
        ]
    }
    reg_path = mock_registry_dir / "registry.json"
    with open(reg_path, 'w') as f:
        json.dump(registry, f)

    entries, portfolio = load_registry(str(reg_path))
    assert len(entries) == 1
    assert entries[0]["id"] == "mock_strat"
    assert entries[0]["spec"]["family"] == "momentum"

@mock.patch("src.ops.signals.get_us_momentum_top5_signal")
def test_generate_signals_from_registry(mock_momentum, mock_registry_dir):
    mock_momentum.return_value = {"signal": "LONG", "targets": ["AAPL"]}

    # We don't need a real registry on disk for this, just the entry objects
    mock_entries = [
        {
            "id": "mock_strat",
            "status": "active",
            "spec": {
                "id": "mock_strat",
                "family": "momentum",
                "parameters": {"lookback": 10}
            }
        }
    ]

    mock_data = pd.DataFrame()
    results = generate_signals_from_registry(mock_data, mock_entries, tickers=["AAPL"])

    assert "mock_strat" in results
    assert results["mock_strat"]["signal"] == "LONG"
    mock_momentum.assert_called_once()

def test_generate_signals_unsupported_shape():
    mock_entries = [
        {
            "id": "mock_strat",
            "status": "active",
            "spec": {
                "id": "mock_strat",
                "family": "magic_ai",
                "parameters": {}
            }
        }
    ]

    mock_data = pd.DataFrame()
    with pytest.raises(UnsupportedRuleShape, match="family 'magic_ai' is not supported"):
        generate_signals_from_registry(mock_data, mock_entries)

@mock.patch("src.ops.signals.get_us_momentum_top5_signal", autospec=True)
def test_generate_signals_non_default_parameters(mock_momentum):
    mock_momentum.return_value = {"signal": "LONG", "targets": ["AAPL"]}
    mock_entries = [
        {
            "id": "mock_strat",
            "status": "active",
            "spec": {
                "id": "mock_strat",
                "family": "momentum",
                "parameters": {"lookback_days": 84, "top_n": 8, "invalid_param": 100}
            }
        }
    ]

    mock_data = pd.DataFrame()
    results = generate_signals_from_registry(mock_data, mock_entries, tickers=["AAPL"])

    assert "mock_strat" in results
    # verify delegate was called successfully and parameters passed through (ignoring the invalid one)
    mock_momentum.assert_called_once()
    args, kwargs = mock_momentum.call_args
    assert list(args[1]) == ["AAPL"]
    assert kwargs.get("lookback_days") == 84
    assert kwargs.get("top_n") == 8
    assert "invalid_param" not in kwargs

@mock.patch("src.ops.signals.get_spy_sma200_signal", autospec=True)
def test_generate_signals_parameter_mapping_and_filtering(mock_sma200):
    mock_sma200.return_value = {"signal": "BUY", "sma200": 100.0}
    mock_entries = [
        {
            "id": "mock_trend_strat",
            "status": "active",
            "spec": {
                "id": "mock_trend_strat",
                "family": "trend",
                "parameters": {"window": 200, "exec_delay": 1, "drift_rebal": 0.05}
            }
        }
    ]

    mock_data = pd.DataFrame()
    results = generate_signals_from_registry(mock_data, mock_entries)

    assert "mock_trend_strat" in results
    # verify parameter mapping and filtering
    mock_sma200.assert_called_once()
    args, kwargs = mock_sma200.call_args
    assert kwargs.get("sma_window") == 200
    assert "exec_delay" not in kwargs
    assert "drift_rebal" not in kwargs
