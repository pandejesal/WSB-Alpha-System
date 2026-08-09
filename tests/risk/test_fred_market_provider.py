import pytest
from unittest.mock import patch
import requests

from src.risk.fred_macro_provider import FredMacroProvider

class MockResponse:
    def __init__(self, json_data, status_code):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

@pytest.fixture
def fred_provider():
    provider = FredMacroProvider()
    provider.api_key = "FAKE_KEY"
    return provider

def test_fetch_series_success(fred_provider):
    mock_data = {"observations": [{"value": "1.25"}]}
    with patch('requests.get', return_value=MockResponse(mock_data, 200)):
        val = fred_provider._fetch_series("T10Y2Y")
    assert val == 1.25

def test_fetch_series_invalid_value(fred_provider):
    mock_data = {"observations": [{"value": "."}]}
    with patch('requests.get', return_value=MockResponse(mock_data, 200)):
        val = fred_provider._fetch_series("T10Y2Y")
    assert val is None

def test_fetch_series_retry_logic(fred_provider):
    mock_responses = [
        MockResponse({}, 429),
        MockResponse({}, 500),
        MockResponse({"observations": [{"value": "2.5"}]}, 200)
    ]
    with patch('requests.get', side_effect=mock_responses) as mock_get:
        with patch('time.sleep', return_value=None):
            val = fred_provider._fetch_series("T10YIE")

    assert mock_get.call_count == 3
    assert val == 2.5

def test_fetch_series_timeout_degrades(fred_provider):
    with patch('requests.get', side_effect=requests.exceptions.Timeout("Timeout")):
        with patch('time.sleep', return_value=None):
            val = fred_provider._fetch_series("T10Y2Y")
    assert val is None

def test_get_regime_risk_on(fred_provider):
    # term_spread > 0, inflation < 2.5
    with patch.object(fred_provider, '_fetch_series', side_effect=[0.5, 2.0, 0.5, 2.0]):
        regime_data = fred_provider.get_regime()
        multiplier = fred_provider.regime_multiplier()

    assert regime_data["regime"] == "RISK_ON"
    assert regime_data["term_spread"] == 0.5
    assert regime_data["inflation"] == 2.0
    assert multiplier == 1.0

def test_get_regime_risk_off(fred_provider):
    # term_spread < 0, inflation < 2.5
    with patch.object(fred_provider, '_fetch_series', side_effect=[-0.2, 2.0, -0.2, 2.0]):
        regime_data = fred_provider.get_regime()
        multiplier = fred_provider.regime_multiplier()

    assert regime_data["regime"] == "RISK_OFF"
    assert multiplier == 0.5

def test_get_regime_stagflation(fred_provider):
    # term_spread < 0, inflation > 2.5
    with patch.object(fred_provider, '_fetch_series', side_effect=[-0.5, 3.0, -0.5, 3.0]):
        regime_data = fred_provider.get_regime()
        multiplier = fred_provider.regime_multiplier()

    assert regime_data["regime"] == "STAGFLATION"
    assert multiplier == 0.4

def test_get_regime_neutral(fred_provider):
    # term_spread > 0, inflation > 2.5
    with patch.object(fred_provider, '_fetch_series', side_effect=[1.0, 3.0, 1.0, 3.0]):
        regime_data = fred_provider.get_regime()
        multiplier = fred_provider.regime_multiplier()

    assert regime_data["regime"] == "NEUTRAL"
    assert multiplier == 0.8

def test_get_regime_fallback_on_failure(fred_provider):
    with patch.object(fred_provider, '_fetch_series', return_value=None):
        regime_data = fred_provider.get_regime()
        multiplier = fred_provider.regime_multiplier()

    assert regime_data["regime"] == "NEUTRAL"
    assert regime_data["confidence"] == 0.0
    assert multiplier == 0.8
