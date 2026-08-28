import os
from unittest import mock

import pytest
import yaml

from scripts.hunt_runner import KNOWN_FAMILIES, do_collect, do_run, load_brief


class DummyArgs:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def test_load_brief_success(tmp_path):
    brief_path = tmp_path / "valid_brief.yaml"
    with open(brief_path, "w") as f:
        yaml.safe_dump({
            "family": KNOWN_FAMILIES[0],
            "universe": "test_universe",
            "hypothesis": "test_hypothesis",
            "acceptance": "test_acceptance",
            "lookback_constraints": "test_lookback",
            "edge_gate_params": {}
        }, f)

    brief = load_brief(str(brief_path))
    assert brief["family"] == KNOWN_FAMILIES[0]

def test_load_brief_missing_fields(tmp_path):
    brief_path = tmp_path / "missing_brief.yaml"
    with open(brief_path, "w") as f:
        yaml.safe_dump({
            "family": KNOWN_FAMILIES[0],
            "universe": "test_universe"
            # Missing hypothesis, etc
        }, f)

    with pytest.raises(ValueError, match="missing required fields"):
        load_brief(str(brief_path))

def test_load_brief_unknown_family(tmp_path, capsys):
    brief_path = tmp_path / "unknown_brief.yaml"
    with open(brief_path, "w") as f:
        yaml.safe_dump({
            "family": "unknown_magic_family",
            "universe": "test_universe",
            "hypothesis": "test_hypothesis",
            "acceptance": "test_acceptance",
            "lookback_constraints": "test_lookback",
            "edge_gate_params": {}
        }, f)

    brief = load_brief(str(brief_path))
    assert brief["family"] == "unknown_magic_family"

    captured = capsys.readouterr()
    assert "WARNING: Unknown family 'unknown_magic_family'" in captured.out

def test_load_brief_invalid_family_name(tmp_path):
    brief_path = tmp_path / "invalid_brief.yaml"
    with open(brief_path, "w") as f:
        yaml.safe_dump({
            "family": "Invalid Family Name!",
            "universe": "test_universe",
            "hypothesis": "test_hypothesis",
            "acceptance": "test_acceptance",
            "lookback_constraints": "test_lookback",
            "edge_gate_params": {}
        }, f)

    with pytest.raises(ValueError, match="Invalid family name"):
        load_brief(str(brief_path))

def test_load_brief_empty_file(tmp_path):
    brief_path = tmp_path / "empty_brief.yaml"
    with open(brief_path, "w") as f:
        f.write("")

    with pytest.raises(ValueError, match="is not a valid YAML mapping"):
        load_brief(str(brief_path))

@mock.patch("scripts.hunt_runner.datetime")
@mock.patch("scripts.hunt_runner.preregistration.freeze_preregistration")
@mock.patch("scripts.hunt_runner.strategy_registry.load_registry")
def test_do_run(mock_load_registry, mock_freeze, mock_datetime, tmp_path):
    from datetime import datetime, timezone
    mock_now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)  # noqa: DTZ001

    mock_load_registry.return_value = ([], {})
    mock_freeze.return_value = "dummy_path"

    brief_path = tmp_path / "brief.yaml"
    with open(brief_path, "w") as f:
        yaml.safe_dump({
            "family": KNOWN_FAMILIES[0],
            "universe": "test",
            "hypothesis": "test",
            "acceptance": "test",
            "lookback_constraints": "test",
            "edge_gate_params": {}
        }, f)

    out_dir = tmp_path / "out"
    args = DummyArgs(brief=str(brief_path), out=str(out_dir), force_reuse=False)

    do_run(args)

    assert os.path.exists(out_dir)
    assert os.path.exists(out_dir / "candidates")
    assert os.path.exists(out_dir / "results")
    assert os.path.exists(out_dir / "brief.yaml")
    assert os.path.exists(out_dir / "session_log.yaml")
    assert os.path.exists(out_dir / "registry_snapshot.json")

    mock_freeze.assert_called_once()

    # check if session log got updated
    with open(out_dir / "session_log.yaml") as f:
        log_data = yaml.safe_load(f)
        assert "prereg_frozen_at" in log_data
        assert "prereg_cycle_id" in log_data

@mock.patch("scripts.hunt_runner.datetime")
@mock.patch("scripts.hunt_runner.preregistration.freeze_preregistration")
@mock.patch("scripts.hunt_runner.strategy_registry.load_registry")
def test_do_run_freeze_fails_aborts(mock_load_registry, mock_freeze, mock_datetime, tmp_path, capsys):
    from datetime import datetime, timezone
    mock_now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)  # noqa: DTZ001

    mock_load_registry.return_value = ([], {})
    mock_freeze.side_effect = Exception("Mocked freeze failure")

    brief_path = tmp_path / "brief.yaml"
    with open(brief_path, "w") as f:
        yaml.safe_dump({
            "family": KNOWN_FAMILIES[0],
            "universe": "test",
            "hypothesis": "test",
            "acceptance": "test",
            "lookback_constraints": "test",
            "edge_gate_params": {}
        }, f)

    out_dir = tmp_path / "out"
    args = DummyArgs(brief=str(brief_path), out=str(out_dir), force_reuse=False)

    with pytest.raises(SystemExit) as e:
        do_run(args)

    assert e.value.code == 2

    # Verify session log DOES exist as a stub, since it's written before freeze in v2
    log_path = out_dir / "session_log.yaml"
    assert os.path.exists(log_path)
    with open(log_path) as f:
        log_data = yaml.safe_load(f)
        assert log_data["status"] == "initialized"
        assert "prereg_frozen_at" not in log_data

    captured = capsys.readouterr()
    assert "Error freezing preregistration: Mocked freeze failure" in captured.out

def test_do_collect(tmp_path, capsys):
    target_dir = tmp_path / "run_dir"
    candidates_dir = target_dir / "candidates"
    rejected_dir = target_dir / "rejected"
    os.makedirs(candidates_dir)

    # Valid spec
    valid_spec_path = candidates_dir / "valid.yaml"
    with open(valid_spec_path, "w") as f:
        yaml.safe_dump({
            "id": "test_id",
            "name": "test_name",
            "family": "momentum",
            "universe": "test_univ",
            "parameters": {},
            "signal": {"entry": "e", "exit": "x"}
        }, f)

    # Invalid spec
    invalid_spec_path = candidates_dir / "invalid.yaml"
    with open(invalid_spec_path, "w") as f:
        yaml.safe_dump({
            "id": "test_id"
            # Missing name, family, etc
        }, f)

    args = DummyArgs(dir=str(target_dir), registry="dummy_registry.json")

    do_collect(args)

    captured = capsys.readouterr()

    assert "✅ Valid Spec: valid.yaml" in captured.out
    assert "❌ Rejected: invalid.yaml" in captured.out

    # invalid.yaml should be moved
    assert not os.path.exists(invalid_spec_path)
    assert os.path.exists(rejected_dir / "invalid.yaml")
    assert os.path.exists(rejected_dir / "invalid.yaml.reason")

def test_do_collect_yaml_error(tmp_path, capsys):
    target_dir = tmp_path / "run_dir"
    candidates_dir = target_dir / "candidates"
    rejected_dir = target_dir / "rejected"
    os.makedirs(candidates_dir)

    # Invalid YAML syntax
    invalid_yaml_path = candidates_dir / "invalid_yaml.yaml"
    with open(invalid_yaml_path, "w") as f:
        f.write("family: [unclosed")

    args = DummyArgs(dir=str(target_dir), registry="dummy_registry.json")

    do_collect(args)

    captured = capsys.readouterr()

    assert "❌ Rejected: invalid_yaml.yaml" in captured.out

    # file should be moved to rejected/
    assert not os.path.exists(invalid_yaml_path)
    assert os.path.exists(rejected_dir / "invalid_yaml.yaml")
    assert os.path.exists(rejected_dir / "invalid_yaml.yaml.reason")


def test_do_collect_non_mapping(tmp_path, capsys):
    target_dir = tmp_path / "run_dir"
    candidates_dir = target_dir / "candidates"
    rejected_dir = target_dir / "rejected"
    os.makedirs(candidates_dir)

    # Empty file
    empty_path = candidates_dir / "empty.yaml"
    with open(empty_path, "w") as f:
        f.write("")

    # Scalar file
    scalar_path = candidates_dir / "scalar.yaml"
    with open(scalar_path, "w") as f:
        f.write("just a string")

    # Valid file to ensure loop continues
    valid_path = candidates_dir / "valid.yaml"
    with open(valid_path, "w") as f:
        yaml.safe_dump({
            "id": "test_id",
            "name": "test_name",
            "family": "momentum",
            "universe": "test_univ",
            "parameters": {},
            "signal": {"entry": "e", "exit": "x"}
        }, f)

    args = DummyArgs(dir=str(target_dir), registry="dummy_registry.json")

    do_collect(args)

    captured = capsys.readouterr()

    # The loop should process the valid file successfully
    assert "✅ Valid Spec: valid.yaml" in captured.out

    # Both invalid files should be rejected
    assert "❌ Rejected: empty.yaml" in captured.out
    assert "❌ Rejected: scalar.yaml" in captured.out

    # Valid file remains
    assert os.path.exists(valid_path)

    # Invalid files are moved
    assert not os.path.exists(empty_path)
    assert not os.path.exists(scalar_path)

    assert os.path.exists(rejected_dir / "empty.yaml")
    assert os.path.exists(rejected_dir / "empty.yaml.reason")
    with open(rejected_dir / "empty.yaml.reason") as f:
        assert "is not a YAML mapping" in f.read()

    assert os.path.exists(rejected_dir / "scalar.yaml")
    assert os.path.exists(rejected_dir / "scalar.yaml.reason")
    with open(rejected_dir / "scalar.yaml.reason") as f:
        assert "is not a YAML mapping" in f.read()
