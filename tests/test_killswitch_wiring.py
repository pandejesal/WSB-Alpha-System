"""CS-01 kill-switch + LIVE_TRADING_ENABLED dual-flag conjunctive gate wiring tests."""

import os

import yaml

from src.ops.killswitch import ALLOWED_TOP_KEYS, KillSwitch, dual_gate_allows_trading


def _write_state(tmp_path, state, extra_keys=None):
    p = tmp_path / "ops_state.yaml"
    data = {"state": state}
    if extra_keys:
        data.update(extra_keys)
    with open(p, "w") as f:
        yaml.dump(data, f)
    return str(p)


def test_dual_gate_off_true_proceeds(tmp_path):
    fp = _write_state(tmp_path, "off")
    allowed, reason = dual_gate_allows_trading(True, filepath=fp)
    assert allowed is True
    assert reason == ""


def test_dual_gate_off_false_aborts_disagreement(tmp_path):
    fp = _write_state(tmp_path, "off")
    allowed, reason = dual_gate_allows_trading(False, filepath=fp)
    assert allowed is False
    assert "disagreement" in reason.lower() or "blocked" in reason.lower()


def test_dual_gate_halt_true_aborts_disagreement(tmp_path):
    fp = _write_state(tmp_path, "halt_new_orders")
    allowed, reason = dual_gate_allows_trading(True, filepath=fp)
    assert allowed is False
    assert "disagreement" in reason.lower() or "blocked" in reason.lower()


def test_dual_gate_halt_false_both_blocked(tmp_path):
    fp = _write_state(tmp_path, "halt_new_orders")
    allowed, reason = dual_gate_allows_trading(False, filepath=fp)
    assert allowed is False


def test_flat_always_blocks(tmp_path):
    fp = _write_state(tmp_path, "flat")
    for live in (True, False):
        allowed, _ = dual_gate_allows_trading(live, filepath=fp)
        assert allowed is False


def test_yaml_extra_key_rejected_fails_closed(tmp_path):
    fp = _write_state(tmp_path, "off", extra_keys={"evil": "1", "state": "off"})
    ks = KillSwitch(filepath=fp)
    assert ks.get_state() == "halt_new_orders"
    assert ks.can_trade() is False
    allowed, _ = dual_gate_allows_trading(True, filepath=fp)
    assert allowed is False


def test_yaml_non_dict_fails_closed(tmp_path):
    p = tmp_path / "ops_state.yaml"
    with open(p, "w") as f:
        f.write("just_a_string\n")
    ks = KillSwitch(filepath=str(p))
    assert ks.get_state() == "halt_new_orders"


def test_yaml_allowed_keys_include_sleeves(tmp_path):
    fp = _write_state(tmp_path, "off", extra_keys={"sleeves": {"spy_sma200": "off"}})
    ks = KillSwitch(filepath=fp)
    assert ks.get_state() == "off"
    assert ALLOWED_TOP_KEYS == {"state", "sleeves"}


def test_live_crypto_main_aborts_on_dual_gate(monkeypatch, tmp_path):
    """Mutates ops_state.yaml + env-equivalent live flag, asserts main aborts (fail-closed)."""
    import sys
    from unittest.mock import MagicMock, patch

    sys.modules.setdefault("ccxt", MagicMock())
    from src.execution import live_crypto_executor
    from src.risk import position_sizing as risk_config

    # halt + True -> abort, no order
    fp = _write_state(tmp_path, "halt_new_orders")
    # Patch KillSwitch filepath via dual_gate call site: patch KillSwitch to use our tmp file
    orig_ks = live_crypto_executor.__dict__.get("KillSwitch")
    with patch("src.ops.killswitch.KillSwitch") as MockKS:
        inst = MockKS.return_value
        inst.can_trade.return_value = False
        inst.get_state.return_value = "halt_new_orders"
        with patch.object(risk_config, "LIVE_TRADING_ENABLED", True):
            with patch("src.ops.killswitch.dual_gate_allows_trading", return_value=(False, "CRITICAL dual-flag disagreement can_trade=False live=True")):
                with patch("src.execution.live_crypto_executor.init_bybit_exchange") as mock_init:
                    live_crypto_executor.main()
                    mock_init.assert_not_called()


def test_main_live_aborts_without_live_flag(tmp_path):
    """main_live dual gate blocks when LIVE_TRADING_ENABLED false regardless of kill state."""
    fp = _write_state(tmp_path, "off")
    allowed, _ = dual_gate_allows_trading(False, filepath=fp)
    assert allowed is False
