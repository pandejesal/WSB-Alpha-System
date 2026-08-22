"""Unit tests for crypto-specific spec gates (verification sweep item 3).

Covers the Task 4.3 additions in src/ops/strategy_registry.py:
- 24/7 session gate for crypto universes
- validate_crypto_data_freshness
"""

import pytest

from src.ops.strategy_registry import (
    MalformedSpecError,
    validate_crypto_data_freshness,
    validate_spec,
)


def _spec(universe, session=None):
    spec = {
        "id": "btc_test_v1",
        "name": "BTC Test",
        "family": "ta-rules",
        "universe": universe,
        "parameters": {"window": 20},
        "signal": {"type": "rsi"},
    }
    if session is not None:
        spec["session"] = session
    return spec


class TestCryptoSessionGate:
    def test_crypto_string_universe_valid_session_passes(self):
        assert validate_spec(_spec("BTC/USD", session="24/7"), "test.yaml") is True

    def test_crypto_list_universe_valid_session_passes(self):
        assert validate_spec(_spec(["ETH/USD", "SOL/USD"], session="crypto"), "test.yaml") is True

    def test_crypto_bad_session_raises(self):
        with pytest.raises(MalformedSpecError, match="24/7"):
            validate_spec(_spec("BTC/USD", session="weekdays-only"), "test.yaml")

    def test_non_crypto_spec_ignores_session(self):
        # Equities spec: session value is NOT validated (gate is crypto-only)
        assert validate_spec(_spec("SPY", session="rth"), "test.yaml") is True


class TestCryptoDataFreshness:
    def test_fresh_timestamp_passes(self, monkeypatch):
        import time
        frozen = 1_800_000_000.0
        monkeypatch.setattr(time, "time", lambda: frozen)
        assert validate_crypto_data_freshness(frozen - 60, max_age_seconds=3600) is True

    def test_stale_timestamp_raises(self, monkeypatch):
        import time
        frozen = 1_800_000_000.0
        monkeypatch.setattr(time, "time", lambda: frozen)
        with pytest.raises(MalformedSpecError, match="stale"):
            validate_crypto_data_freshness(frozen - 7200, max_age_seconds=3600)

    def test_boundary_exact_age_is_not_stale(self, monkeypatch):
        import time
        frozen = 1_800_000_000.0
        monkeypatch.setattr(time, "time", lambda: frozen)
        # age == max_age must NOT raise (strict > comparison)
        assert validate_crypto_data_freshness(frozen - 3600, max_age_seconds=3600) is True
