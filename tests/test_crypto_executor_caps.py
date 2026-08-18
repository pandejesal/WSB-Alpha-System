import contextlib
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

# Mock ccxt BEFORE importing live_crypto_executor since it uses ccxt.bybit in type hints
sys.modules['ccxt'] = MagicMock()

from src.execution import live_crypto_executor  # noqa: E402
from src.execution.live_crypto_executor import gates_allow_trading  # noqa: E402
from src.risk import position_sizing as risk_config  # noqa: E402


# ---------------------------------------------------------
# Unit Tests for gates_allow_trading
# ---------------------------------------------------------

def test_gates_allow_trading_all_clear():
    # Setup safe values
    equity = 1000.0
    last_equity = 1000.0
    high_water_mark = 1000.0
    active_pos_count = risk_config.MAX_CONCURRENT_POSITIONS - 1

    allowed, reason = gates_allow_trading(equity, last_equity, high_water_mark, active_pos_count)
    assert allowed is True
    assert reason == ""


def test_gates_allow_trading_daily_loss_trip():
    # Loss exceeds DAILY_LOSS_CIRCUIT_BREAKER_PCT
    equity = 900.0
    last_equity = 1000.0
    high_water_mark = 1000.0
    active_pos_count = 0

    # 10% loss > 5% default
    allowed, reason = gates_allow_trading(equity, last_equity, high_water_mark, active_pos_count)
    assert allowed is False
    assert "DAILY CIRCUIT BREAKER TRIPPED" in reason


def test_gates_allow_trading_weekly_loss_trip():
    # Drawdown exceeds WEEKLY_LOSS_CIRCUIT_BREAKER_PCT
    equity = 800.0
    last_equity = 800.0
    high_water_mark = 1000.0
    active_pos_count = 0

    # 20% drawdown > 10% default
    allowed, reason = gates_allow_trading(equity, last_equity, high_water_mark, active_pos_count)
    assert allowed is False
    assert "WEEKLY/MAX CIRCUIT BREAKER TRIPPED" in reason


def test_gates_allow_trading_max_positions_trip():
    # Active positions >= MAX_CONCURRENT_POSITIONS
    equity = 1000.0
    last_equity = 1000.0
    high_water_mark = 1000.0
    active_pos_count = risk_config.MAX_CONCURRENT_POSITIONS

    allowed, reason = gates_allow_trading(equity, last_equity, high_water_mark, active_pos_count)
    assert allowed is False
    assert "Max positions" in reason


def test_gates_allow_trading_boundary_condition():
    # Loss exactly at the breaker pct should not trip
    last_equity = 1000.0
    loss_amount = last_equity * risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT
    equity = last_equity - loss_amount
    high_water_mark = last_equity
    active_pos_count = 0

    allowed, reason = gates_allow_trading(equity, last_equity, high_water_mark, active_pos_count)
    assert allowed is True
    assert reason == ""


# ---------------------------------------------------------
# End-to-End Regression Tests for main()
# ---------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_env_vars():
    # Make sure we don't hit real APIs. Note: the executor reads BYBIT_API_KEY /
    # BYBIT_API_SECRET at import time (module-level constants), so patching
    # os.environ here is not enough by itself — the e2e tests additionally patch
    # the module-level constants so the gate chain is deterministically reached
    # even in keyless environments (otherwise main() aborts at the key check and
    # assert_not_called() would pass trivially without exercising the gate).
    with patch.dict(os.environ, {
        "BYBIT_API_KEY": "fake_key",
        "BYBIT_API_SECRET": "fake_secret"
    }):
        yield

def _patch_module_keys():
    return [
        patch('src.execution.live_crypto_executor.BYBIT_API_KEY', 'fake_key'),
        patch('src.execution.live_crypto_executor.BYBIT_API_SECRET', 'fake_secret'),
    ]


@contextlib.contextmanager
def _module_keys_patched():
    with _patch_module_keys()[0], _patch_module_keys()[1]:
        yield


@patch('src.execution.live_crypto_executor.execute_bybit_order')
@patch('src.execution.live_crypto_executor.check_rebalance_required')
@patch('src.execution.live_crypto_executor.calculate_target_position_sizes')
@patch('src.execution.live_crypto_executor.get_current_positions_and_scores')
@patch('src.execution.live_crypto_executor.fetch_account_equity')
@patch('src.execution.live_crypto_executor.init_bybit_exchange')
def test_main_max_positions_regression(
    mock_init,
    mock_fetch_equity,
    mock_get_positions,
    mock_calc_sizes,
    mock_check_rebalance,
    mock_execute
):
    # Setup to skip state file load
    with patch('os.path.exists', return_value=False):
        mock_init.return_value = MagicMock()
        mock_fetch_equity.return_value = 1000.0

        # Mock positions to exceed max concurrent
        positions = {f"TICKER_{i}": 100.0 for i in range(risk_config.MAX_CONCURRENT_POSITIONS)}
        scores = {f"TICKER_{i}": 1.0 for i in range(risk_config.MAX_CONCURRENT_POSITIONS)}
        vols = {f"TICKER_{i}": 0.5 for i in range(risk_config.MAX_CONCURRENT_POSITIONS)}

        mock_get_positions.return_value = (positions, scores, vols)

        # Make sure USE_SANDBOX / LIVE_TRADING_ENABLED allow us to proceed to gating.
        # Also patch module-level key constants so the gate is reached even in
        # keyless environments (main() aborts at the key check otherwise).
        with patch('src.execution.live_crypto_executor.USE_SANDBOX', True), _module_keys_patched():
            live_crypto_executor.main()

            # Assert execute_bybit_order is NEVER called
            mock_execute.assert_not_called()

@patch('src.execution.live_crypto_executor.execute_bybit_order')
@patch('src.execution.live_crypto_executor.check_rebalance_required')
@patch('src.execution.live_crypto_executor.calculate_target_position_sizes')
@patch('src.execution.live_crypto_executor.get_current_positions_and_scores')
@patch('src.execution.live_crypto_executor.fetch_account_equity')
@patch('src.execution.live_crypto_executor.init_bybit_exchange')
def test_main_daily_loss_regression(
    mock_init,
    mock_fetch_equity,
    mock_get_positions,
    mock_calc_sizes,
    mock_check_rebalance,
    mock_execute,
    tmp_path
):
    # Setup state file to inject previous equity for daily loss trip
    state_file = tmp_path / "crypto_state.json"
    state_data = '{"last_equity": 1000.0, "high_water_mark": 1000.0}'
    state_file.write_text(state_data)

    # Change directory temporarily so that STATE_FILE='crypto_state.json' finds our temp file
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        mock_init.return_value = MagicMock()

        # 20% loss
        mock_fetch_equity.return_value = 800.0

        # Safe positions
        positions = {"TICKER_1": 100.0}
        scores = {"TICKER_1": 1.0}
        vols = {"TICKER_1": 0.5}

        mock_get_positions.return_value = (positions, scores, vols)

        with patch('src.execution.live_crypto_executor.USE_SANDBOX', True), _module_keys_patched():
            live_crypto_executor.main()

            # Assert execute_bybit_order is NEVER called
            mock_execute.assert_not_called()
    finally:
        os.chdir(original_cwd)
