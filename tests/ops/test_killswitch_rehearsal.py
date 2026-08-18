import json
import os
import pytest
from unittest.mock import patch

from scripts.kill_switch_rehearsal import main as rehearsal_main
from src.ops.killswitch import read_ops_state

@patch("scripts.kill_switch_rehearsal.sys.argv", ["kill_switch_rehearsal.py", "--dry-run"])
@patch("scripts.kill_switch_rehearsal.write_ops_state")
@patch("scripts.kill_switch_rehearsal.write_artifact")
def test_killswitch_rehearsal_dry_run(mock_write_artifact, mock_write_ops_state):
    # Ensure current state before run
    initial_state = read_ops_state()

    # Run in dry-run mode
    rehearsal_main()

    # Assert state writing was NOT called
    mock_write_ops_state.assert_not_called()
    mock_write_artifact.assert_not_called()

    # Assert actual state on disk was untouched
    final_state = read_ops_state()
    assert initial_state == final_state

@patch("scripts.kill_switch_rehearsal.sys.argv", ["kill_switch_rehearsal.py"])
@patch("scripts.kill_switch_rehearsal.write_ops_state")
@patch("scripts.kill_switch_rehearsal.write_artifact")
def test_killswitch_rehearsal_real_run(mock_write_artifact, mock_write_ops_state):
    # Run in real mode
    rehearsal_main()

    # Assert state writing WAS called (multiple times to set, then restore)
    assert mock_write_ops_state.call_count >= 2

    # Assert artifact writing WAS called
    mock_write_artifact.assert_called_once()
    args, kwargs = mock_write_artifact.call_args
    assert args[0] == "docs/data/ops/kill_switch_rehearsal.json"
    assert args[1]["scenarios"]["T2_halt"] == "success"
