import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_rehearsal(cwd: Path):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "kill_switch_rehearsal.py"), "--dry-run"],
        cwd=str(cwd),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_kill_switch_rehearsal_dry_run_no_files_written(tmp_path):
    """The rehearsal CLI in --dry-run must not write any artifact or state file."""
    result = _run_rehearsal(tmp_path)
    assert result.returncode == 0, result.stderr

    artifact = tmp_path / "docs" / "data" / "ops" / "kill_switch_rehearsal.json"
    assert not artifact.exists(), "dry-run must not write the rehearsal artifact"

    state_file = tmp_path / "config" / "ops_state.yaml"
    assert not state_file.exists(), "dry-run must not create or modify ops_state.yaml"


def test_kill_switch_rehearsal_dry_run_does_not_touch_existing_state(tmp_path):
    """Dry-run must leave an existing ops_state.yaml byte-for-byte untouched."""
    state_file = tmp_path / "config" / "ops_state.yaml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("state: off\n")

    before = state_file.read_text()
    result = _run_rehearsal(tmp_path)
    assert result.returncode == 0, result.stderr
    assert state_file.read_text() == before, "dry-run modified ops_state.yaml"


def test_kill_switch_rehearsal_dry_run_logs_plan():
    """Dry-run output must confirm tier-2/tier-3 simulation and restore in the log text."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        result = _run_rehearsal(Path(tmp))
        assert result.returncode == 0, result.stderr
        output = result.stdout + result.stderr
        assert "tier-2" in output and "tier-3" in output
        assert "restored" in output
