"""S3/F2-R03: UniversalBroker.place_order live-route dual-gate regression tests.

Live-broker routes must fail CLOSED behind dual_gate_allows_trading()
(KillSwitch AND LIVE_TRADING_ENABLED) with a loud error naming the
blocking flag. No network, no file writes — the gate is patched.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.execution import universal_broker as ub_mod
from src.execution.universal_broker import UniversalBroker


def _make_broker() -> UniversalBroker:
    """Construct without touching real broker SDKs (keyless env safe)."""
    with patch.object(ub_mod, "AlpacaExecutor"), patch.object(ub_mod, "CryptoExecutor"):
        return UniversalBroker()


def test_live_route_raises_when_killswitch_off():
    """Gate denied (killswitch halt + live flag on) -> RuntimeError, no broker touch."""
    broker = _make_broker()
    broker.get_executor = MagicMock(side_effect=AssertionError("broker must not be touched when gate denies"))
    with patch(
        "src.ops.killswitch.dual_gate_allows_trading",
        return_value=(False, "CRITICAL dual-flag disagreement can_trade=False live=True"),
    ), pytest.raises(RuntimeError) as excinfo:
        asyncio.run(broker.place_order("equity", "strat_s3", "SPY", "buy", 1.0, 1.0))
    assert "dual gate" in str(excinfo.value).lower()
    assert "LIVE_TRADING_ENABLED" in str(excinfo.value)
    broker.get_executor.assert_not_called()


def test_live_route_raises_when_live_flag_off():
    """Gate denied (killswitch off + live flag off) -> RuntimeError, no broker touch."""
    broker = _make_broker()
    broker.get_executor = MagicMock(side_effect=AssertionError("broker must not be touched when gate denies"))
    with patch(
        "src.ops.killswitch.dual_gate_allows_trading",
        return_value=(False, "CRITICAL dual-flag disagreement can_trade=True live=False"),
    ), pytest.raises(RuntimeError, match="dual gate"):
        asyncio.run(broker.place_order("crypto", "strat_s3", "BTC-USD", "buy", 0.01, 1.0))
    broker.get_executor.assert_not_called()


def test_live_route_proceeds_when_gate_allows():
    """Gate allowed -> risk check runs, order routes to executor."""
    broker = _make_broker()
    fake_exec = MagicMock()
    fake_exec.get_account_equity.return_value = 10000.0
    fake_exec.execute_order.return_value = True
    broker.get_executor = MagicMock(return_value=fake_exec)
    with patch("src.ops.killswitch.dual_gate_allows_trading", return_value=(True, "")), patch.object(
        ub_mod, "send_telegram_alert", new_callable=AsyncMock
    ):
        result = asyncio.run(broker.place_order("equity", "strat_s3", "SPY", "buy", 1.0, 10.0))
    assert result is True
    fake_exec.execute_order.assert_called_once_with("SPY", "buy", 1.0)
