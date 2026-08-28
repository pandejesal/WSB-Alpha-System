import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock ccxt BEFORE importing executor
sys.modules['ccxt'] = MagicMock()

from src.execution import live_crypto_executor  # noqa: E402
from src.risk import position_sizing as risk_config  # noqa: E402

@pytest.fixture
def setup_env_and_config(monkeypatch):
    monkeypatch.setattr(live_crypto_executor, "BYBIT_API_KEY", "test_key")
    monkeypatch.setattr(live_crypto_executor, "BYBIT_API_SECRET", "test_secret")

    # We must patch risk_config.LIVE_TRADING_ENABLED because the sandbox might be disabled
    # or USE_SANDBOX checks it
    monkeypatch.setattr(risk_config, "LIVE_TRADING_ENABLED", True)
    monkeypatch.setattr(live_crypto_executor, "USE_SANDBOX", False)

    # Let's also patch STATE_FILE so it doesn't write to real dir
    monkeypatch.chdir("/tmp")

@pytest.fixture
def mock_exchange():
    exchange = MagicMock()
    exchange.fetch_ticker.return_value = {"last": 50000.0} # Used in execute_bybit_order
    # Mocking create_market_order to just return a dummy order
    exchange.create_market_order.return_value = {"id": "dummy_order_id"}
    return exchange

@patch("src.execution.live_crypto_executor.init_bybit_exchange")
@patch("src.execution.live_crypto_executor.fetch_account_equity")
@patch("src.execution.live_crypto_executor.get_current_positions_and_scores")
@patch("src.execution.live_crypto_executor.calculate_target_position_sizes")
@patch("src.execution.live_crypto_executor.check_rebalance_required")
@patch("src.execution.live_crypto_executor.execute_bybit_order")
def test_max_concurrent_positions_cap(
    mock_execute_order, mock_check_rebalance, mock_calc_target,
    mock_get_positions, mock_fetch_equity, mock_init,
    setup_env_and_config, mock_exchange, capsys, monkeypatch
):
    """
    Test Case 1: Max concurrent positions check
    Provide a state where MAX_CONCURRENT_POSITIONS are already open.
    Assert that new entries are skipped.
    """
    monkeypatch.setattr(risk_config, "MAX_CONCURRENT_POSITIONS", 2)
    monkeypatch.setattr(risk_config, "MAX_POSITION_SIZE_PCT", 0.25)

    mock_init.return_value = mock_exchange
    mock_fetch_equity.return_value = 1000.0

    # 2 positions already open, hitting the cap
    current_positions = {"BTC-USD": 100.0, "ETH-USD": 100.0, "SOL-USD": 0.0}
    today_scores = {"BTC-USD": 1.0, "ETH-USD": 1.0, "SOL-USD": 1.0}
    today_vols = {"BTC-USD": 0.5, "ETH-USD": 0.5, "SOL-USD": 0.5}
    mock_get_positions.return_value = (current_positions, today_scores, today_vols)

    # Target requests a new entry for SOL-USD
    target_sizes = {"BTC-USD": 100.0, "ETH-USD": 100.0, "SOL-USD": 50.0}
    mock_calc_target.return_value = target_sizes

    # We require a rebalance for SOL-USD to enter
    mock_check_rebalance.return_value = {"BTC-USD": False, "ETH-USD": False, "SOL-USD": True}

    # execute
    live_crypto_executor.main()

    # Assert execute_bybit_order was NEVER called because SOL-USD should be skipped
    mock_execute_order.assert_not_called()

    # Check log output for the skip message
    captured = capsys.readouterr().out
    assert "Skipping SOL-USD entry: MAX_CONCURRENT_POSITIONS" in captured

@patch("src.execution.live_crypto_executor.init_bybit_exchange")
@patch("src.execution.live_crypto_executor.fetch_account_equity")
@patch("src.execution.live_crypto_executor.get_current_positions_and_scores")
@patch("src.execution.live_crypto_executor.calculate_target_position_sizes")
@patch("src.execution.live_crypto_executor.check_rebalance_required")
@patch("src.execution.live_crypto_executor.execute_bybit_order")
def test_max_position_size_cap(
    mock_execute_order, mock_check_rebalance, mock_calc_target,
    mock_get_positions, mock_fetch_equity, mock_init,
    setup_env_and_config, mock_exchange, capsys, monkeypatch
):
    """
    Test Case 2: Max position size check
    Target exceeds MAX_POSITION_SIZE_PCT. Assert clamped before submission.
    Also tests if clamped size is below MIN_ORDER_SIZE it skips.
    """
    monkeypatch.setattr(risk_config, "MAX_CONCURRENT_POSITIONS", 4)
    monkeypatch.setattr(risk_config, "MAX_POSITION_SIZE_PCT", 0.10)
    monkeypatch.setattr(live_crypto_executor, "MIN_ORDER_SIZE", 10.0)
    monkeypatch.setattr(risk_config, "DAILY_LOSS_CIRCUIT_BREAKER_PCT", 1.0)
    monkeypatch.setattr(risk_config, "WEEKLY_LOSS_CIRCUIT_BREAKER_PCT", 1.0)

    mock_init.return_value = mock_exchange
    mock_fetch_equity.return_value = 1000.0  # 10% max size = 100.0

    current_positions = {"BTC-USD": 0.0, "ETH-USD": 0.0}
    today_scores = {"BTC-USD": 1.0, "ETH-USD": 1.0}
    today_vols = {"BTC-USD": 0.5, "ETH-USD": 0.5}
    mock_get_positions.return_value = (current_positions, today_scores, today_vols)

    target_sizes = {"BTC-USD": 200.0, "ETH-USD": 200.0}
    mock_calc_target.return_value = target_sizes
    mock_check_rebalance.return_value = {"BTC-USD": True, "ETH-USD": False}

    # execute
    live_crypto_executor.main()

    # Assert clamped to 100.0
    mock_execute_order.assert_called_once_with(mock_exchange, 'BTCUSDT', 100.0, 0.0)

    captured = capsys.readouterr().out
    assert "Target size exceeds max allowed. Clamping from $200.00 to $100.00" in captured

    # Now test the MIN_ORDER_SIZE skip logic
    mock_execute_order.reset_mock()
    mock_fetch_equity.return_value = 80.0 # 10% max size = 8.0 < 10.0

    mock_check_rebalance.return_value = {"BTC-USD": False, "ETH-USD": True}
    live_crypto_executor.main()

    mock_execute_order.assert_not_called()
    captured = capsys.readouterr().out
    assert "Clamped size below MIN_ORDER_SIZE" in captured

@patch("src.execution.live_crypto_executor.init_bybit_exchange")
@patch("src.execution.live_crypto_executor.fetch_account_equity")
@patch("src.execution.live_crypto_executor.get_current_positions_and_scores")
@patch("src.execution.live_crypto_executor.calculate_target_position_sizes")
@patch("src.execution.live_crypto_executor.check_rebalance_required")
@patch("src.execution.live_crypto_executor.execute_bybit_order")
def test_normal_execution(
    mock_execute_order, mock_check_rebalance, mock_calc_target,
    mock_get_positions, mock_fetch_equity, mock_init,
    setup_env_and_config, mock_exchange, monkeypatch
):
    """
    Test Case 3: Normal execution below caps
    """
    monkeypatch.setattr(risk_config, "MAX_CONCURRENT_POSITIONS", 4)
    monkeypatch.setattr(risk_config, "MAX_POSITION_SIZE_PCT", 0.50)
    monkeypatch.setattr(live_crypto_executor, "MIN_ORDER_SIZE", 10.0)
    monkeypatch.setattr(risk_config, "DAILY_LOSS_CIRCUIT_BREAKER_PCT", 1.0)
    monkeypatch.setattr(risk_config, "WEEKLY_LOSS_CIRCUIT_BREAKER_PCT", 1.0)

    mock_init.return_value = mock_exchange
    mock_fetch_equity.return_value = 1000.0  # max size 500

    current_positions = {"BTC-USD": 0.0}
    today_scores = {"BTC-USD": 1.0}
    today_vols = {"BTC-USD": 0.5}
    mock_get_positions.return_value = (current_positions, today_scores, today_vols)

    target_sizes = {"BTC-USD": 150.0}
    mock_calc_target.return_value = target_sizes
    mock_check_rebalance.return_value = {"BTC-USD": True}

    live_crypto_executor.main()

    mock_execute_order.assert_called_once_with(mock_exchange, 'BTCUSDT', 150.0, 0.0)
