"""R-C2: single-command record discipline (2 tests).

Freeze-then-record run as two SEPARATE subprocess invocations (never
chained with &&) must both succeed; --help must carry the discipline note.
All artifacts stay inside tmp_path (repo-local temp, never /tmp).
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_SPEC = "family: rc2demo\nid: rc2demo_v1\n"


def _run(args, cwd, extra_env=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "preregister.py")] + args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_rc2_freeze_then_record_serially(tmp_path, monkeypatch):
    work = tmp_path / "rc2work"
    work.mkdir()
    docs = work / "docs"
    docs.mkdir()
    spec = work / "rc2demo.yaml"
    spec.write_text(_SPEC)
    registry = work / "registry.json"
    ledger = work / "trials.jsonl"
    monkeypatch.chdir(work)

    freeze = _run(
        ["freeze", str(spec), "--claim", "rc2 discipline check",
         "--cycle", "99", "--docs-dir", str(docs)],
        cwd=str(work),
    )
    assert freeze.returncode == 0, freeze.stderr

    record = _run(
        ["record", str(spec), "--verdict", "FAIL",
         "--cycle", "99", "--registry", str(registry),
         "--docs-dir", str(docs)],
        cwd=str(work),
        extra_env={"TRIAL_LEDGER_PATH": str(ledger)},
    )
    assert record.returncode == 0, record.stderr
    assert (docs / "cycle99_eval_rc2demo.json").exists()


def test_rc2_help_carries_single_command_note(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    proc = _run(["--help"], cwd=str(tmp_path))
    assert proc.returncode == 0
    assert "do not chain with &&" in proc.stdout
