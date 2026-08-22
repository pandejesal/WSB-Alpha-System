"""Fail-closed tests for the LIVE_TRADING_ENABLED gate (Task 5.1).

The flag must default to paper (False) when the env var is absent, blank,
or unrecognized. Only exact tokens 1/true/yes (any case) enable live trading.
"""

import importlib
import os
from unittest.mock import patch

from src.risk import position_sizing


def _reload_flag(env_value):
    with patch.dict("os.environ", {"LIVE_TRADING_ENABLED": env_value}):
        importlib.reload(position_sizing)
        return position_sizing.LIVE_TRADING_ENABLED


def teardown_function(function):
    # Restore module to a LIVE-flag-absent state WITHOUT touching other env
    # vars (e.g. CIRCUIT_BREAKER_ENABLED set by the outer runner must survive).
    os.environ.pop("LIVE_TRADING_ENABLED", None)
    importlib.reload(position_sizing)
    assert position_sizing.LIVE_TRADING_ENABLED is False


def test_default_absent_env_is_paper():
    env_backup = os.environ.pop("LIVE_TRADING_ENABLED", None)
    try:
        mod = importlib.reload(position_sizing)
        assert mod.LIVE_TRADING_ENABLED is False
    finally:
        if env_backup is not None:
            os.environ["LIVE_TRADING_ENABLED"] = env_backup


def test_explicit_zero_is_paper():
    assert _reload_flag("0") is False


def test_blank_is_paper():
    assert _reload_flag("") is False


def test_garbage_value_fails_closed():
    for bad in ("garbage", "TRUE ", " on", "enabled", "2", "1 ", "yes\n"):
        assert _reload_flag(bad) is False, f"env={bad!r} must fail closed"


def test_exact_tokens_enable_live():
    for good in ("1", "true", "yes", "TRUE", "Yes"):
        assert _reload_flag(good) is True, f"env={good!r} should enable live"
