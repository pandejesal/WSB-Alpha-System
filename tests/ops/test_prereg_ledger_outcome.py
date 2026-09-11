"""R-A3: ledger double-record transparency for the preregister record path."""

import json
import os

import pytest
import yaml

from scripts.preregister import _append_prereg_trial_to_ledger


@pytest.fixture
def env(tmp_path, monkeypatch):
    ledger_path = str(tmp_path / "trials.jsonl")
    monkeypatch.setenv("TRIAL_LEDGER_PATH", ledger_path)
    spec = {
        "id": "ledger_strat",
        "name": "Ledger Strat",
        "family": "ledger_family",
        "parameters": {"w": 1},
    }
    spec_path = str(tmp_path / "spec.yaml")
    with open(spec_path, "w") as fh:
        yaml.dump(spec, fh)
    eval_path = str(tmp_path / "eval.json")
    with open(eval_path, "w") as fh:
        json.dump({"evaluated_at": "2026-09-11T00:00:00", "walk_forward": {}}, fh)
    return spec_path, eval_path, ledger_path


def test_first_record_appends(env):
    spec_path, eval_path, ledger_path = env
    sha, outcome = _append_prereg_trial_to_ledger(spec_path, eval_path)
    assert outcome == "appended"
    assert sha is not None
    with open(ledger_path) as fh:
        assert len(fh.readlines()) == 1


def test_repeat_record_reports_duplicate(env):
    spec_path, eval_path, _ = env
    _, first_outcome = _append_prereg_trial_to_ledger(spec_path, eval_path)
    assert first_outcome == "appended"
    # Same eval file -> same content hash -> duplicate, not a silent drop.
    sha, outcome = _append_prereg_trial_to_ledger(spec_path, eval_path)
    assert outcome == "duplicate"
    assert sha is None


def test_corrupt_eval_reports_failed_and_record_kept(env, tmp_path):
    spec_path, _, _ = env
    bad_eval = str(tmp_path / "bad_eval.json")
    with open(bad_eval, "w") as fh:
        fh.write("{not valid json!!!")
    sha, outcome = _append_prereg_trial_to_ledger(spec_path, bad_eval)
    assert outcome == "failed"
    assert sha is None
    # Record kept: the helper never raises on ledger failure.
    assert os.path.exists(spec_path)
