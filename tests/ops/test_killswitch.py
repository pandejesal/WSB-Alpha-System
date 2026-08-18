import yaml

from src.ops.killswitch import KillSwitch


def test_killswitch_missing_file_fails_closed(tmp_path):
    filepath = str(tmp_path / "ops_state.yaml")
    ks = KillSwitch(filepath=filepath)

    assert ks.get_state() == "halt_new_orders"
    assert ks.can_trade() is False

def test_killswitch_valid_states(tmp_path):
    filepath = str(tmp_path / "ops_state.yaml")
    ks = KillSwitch(filepath=filepath)

    # Set to off
    ks.set_state("off")
    assert ks.get_state() == "off"
    assert ks.can_trade() is True

    # Set to halt
    ks.set_state("halt_new_orders")
    assert ks.get_state() == "halt_new_orders"
    assert ks.can_trade() is False

    # Set to flat
    ks.set_state("flat")
    assert ks.get_state() == "flat"
    assert ks.can_trade() is False

def test_killswitch_invalid_state_ignored(tmp_path):
    filepath = str(tmp_path / "ops_state.yaml")
    ks = KillSwitch(filepath=filepath)

    ks.set_state("off")
    ks.set_state("invalid_state")

    # State should still be off
    assert ks.get_state() == "off"

def test_killswitch_unparseable_file_fails_closed(tmp_path):
    filepath = str(tmp_path / "ops_state.yaml")
    with open(filepath, "w") as f:
        f.write("state: { invalid_yaml: [\n")

    ks = KillSwitch(filepath=filepath)
    assert ks.get_state() == "halt_new_orders"
    assert ks.can_trade() is False

def test_killswitch_unknown_state_in_file_fails_closed(tmp_path):
    filepath = str(tmp_path / "ops_state.yaml")
    with open(filepath, "w") as f:
        yaml.dump({"state": "some_other_state"}, f)

    ks = KillSwitch(filepath=filepath)
    assert ks.get_state() == "halt_new_orders"
    assert ks.can_trade() is False
