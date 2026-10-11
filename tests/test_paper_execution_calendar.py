"""P1.3: run_paper_execution must not run on non-trading days (audit F2)."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import run_paper_execution as rpe


@pytest.fixture
def plan_exists(tmp_path, monkeypatch):
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    monkeypatch.chdir(tmp_path)
    docs = tmp_path / "docs" / "data" / "ops"
    docs.mkdir(parents=True)
    (docs / "plan.json").write_text("{}")


def test_skips_non_trading_day(plan_exists, monkeypatch):
    """Weekend/holiday -> clean exit, broker never constructed."""
    monkeypatch.setattr(rpe, "is_business_day", lambda day: False)

    class ExplodingExecutor:
        def __init__(self, *a, **k):
            raise AssertionError("executor must not be constructed on a non-trading day")

    monkeypatch.setattr(rpe, "PaperExecutor", ExplodingExecutor)
    with pytest.raises(SystemExit) as exc:
        rpe.main()
    assert exc.value.code == 0


def test_runs_on_trading_day(plan_exists, monkeypatch):
    """Trading day -> executor runs."""
    monkeypatch.setattr(rpe, "is_business_day", lambda day: True)
    ran = []

    class RecordingExecutor:
        def __init__(self, *a, **k):
            ran.append(True)

        def execute_plan(self):
            ran.append("executed")

    monkeypatch.setattr(rpe, "PaperExecutor", RecordingExecutor)
    rpe.main()
    assert ran == [True, "executed"]


def test_missing_plan_exits_early(plan_exists, monkeypatch):
    import os
    os.remove("docs/data/ops/plan.json")
    with pytest.raises(SystemExit) as exc:
        rpe.main()
    assert exc.value.code == 0
