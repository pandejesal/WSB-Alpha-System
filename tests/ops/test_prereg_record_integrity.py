"""R-A1 + R-A2: record-path integrity for `record_evaluation`.

Scoped fixtures only — the real 131-row `strategies/registry.json` is never
touched here (fixture copies under tmp_path only).
"""

import glob
import json
import os
import threading

import pytest
import yaml

from src.ops.preregistration import freeze_preregistration, record_evaluation


def _write_spec(path, spec):
    with open(path, "w") as fh:
        yaml.dump(spec, fh)


@pytest.fixture
def env(tmp_path):
    docs_dir = tmp_path / "docs" / "data"
    docs_dir.mkdir(parents=True)
    registry_path = str(tmp_path / "registry.json")
    spec_a = {
        "id": "strat_alpha",
        "name": "Alpha",
        "family": "shared_family",
        "signal": {"entry": "buy", "exit": "sell"},
    }
    spec_b = {
        "id": "strat_beta",
        "name": "Beta",
        "family": "shared_family",
        "signal": {"entry": "buy2", "exit": "sell2"},
    }
    spec_path_a = str(tmp_path / "alpha.yaml")
    spec_path_b = str(tmp_path / "beta.yaml")
    _write_spec(spec_path_a, spec_a)
    _write_spec(spec_path_b, spec_b)
    # Pre-existing registry with one row per family member (same family,
    # distinct ids) — the R1 clobber mutated the first same-family row.
    with open(registry_path, "w") as fh:
        json.dump(
            {
                "strategies": [
                    {"id": "strat_alpha", "family": "shared_family",
                     "status": "paper", "verdict": "NONE"},
                    {"id": "strat_beta", "family": "shared_family",
                     "status": "paper", "verdict": "NONE"},
                ]
            },
            fh,
        )
    return str(tmp_path), str(docs_dir), registry_path, spec_path_a, spec_path_b


def _freeze_and_record(docs_dir, registry_path, spec_path, verdict="FAIL", cycle=1):
    freeze_preregistration(spec_path, "claim", cycle=cycle, docs_dir=docs_dir)
    return record_evaluation(
        spec_path, verdict, cycle=cycle,
        registry_path=registry_path, docs_dir=docs_dir,
    )


def test_record_matches_row_by_id_not_family(env):
    # R-A1: recording beta must update ONLY the beta row, never the first
    # same-family (alpha) row.
    _, docs_dir, registry_path, _, spec_path_b = env
    _freeze_and_record(docs_dir, registry_path, spec_path_b, verdict="FAIL")
    with open(registry_path) as fh:
        rows = {s["id"]: s for s in json.load(fh)["strategies"]}
    assert rows["strat_beta"]["verdict"] == "FAIL"
    assert rows["strat_alpha"]["verdict"] == "NONE"
    assert len(rows) == 2  # no spurious new row appended


def test_record_creates_lock_file(env):
    # R-A1: a registry ".lock" marker must exist after record.
    _, docs_dir, registry_path, spec_path_a, _ = env
    _freeze_and_record(docs_dir, registry_path, spec_path_a)
    assert os.path.exists(registry_path + ".lock")


def test_record_writes_backup(env):
    # R-A1: a `.bak-<timestamp>` copy of the pre-write registry is kept.
    _, docs_dir, registry_path, spec_path_a, _ = env
    with open(registry_path) as fh:
        before = fh.read()
    _freeze_and_record(docs_dir, registry_path, spec_path_a)
    backups = glob.glob(registry_path + ".bak-*")
    assert len(backups) >= 1
    with open(sorted(backups)[-1]) as fh:
        assert fh.read() == before


def test_concurrent_records_no_loss(env):
    # R-A1: two threads recording distinct ids must both land, with both
    # rows present and valid JSON afterwards.
    tmpdir, docs_dir, registry_path, spec_path_a, spec_path_b = env
    freeze_preregistration(spec_path_a, "claim", cycle=1, docs_dir=docs_dir)
    freeze_preregistration(spec_path_b, "claim", cycle=2, docs_dir=docs_dir)
    errors = []

    def _rec(spec_path, cycle, verdict):
        try:
            record_evaluation(
                spec_path, verdict, cycle=cycle,
                registry_path=registry_path, docs_dir=docs_dir,
            )
        except Exception as exc:  # noqa: BLE001 - collected, asserted below
            errors.append(exc)

    threads = [
        threading.Thread(target=_rec, args=(spec_path_a, 1, "FAIL")),
        threading.Thread(target=_rec, args=(spec_path_b, 2, "HONEST_ABANDON")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    with open(registry_path) as fh:
        rows = {s["id"]: s for s in json.load(fh)["strategies"]}
    assert rows["strat_alpha"]["verdict"] == "FAIL"
    assert rows["strat_beta"]["verdict"] == "HONEST_ABANDON"


def test_second_record_versions_instead_of_overwriting(env):
    # R-A2: a second record for the same family+cycle must NOT reuse the
    # first eval path (refuse-or-version; implementation versions).
    tmpdir, docs_dir, registry_path, spec_path_a, _ = env
    first = _freeze_and_record(docs_dir, registry_path, spec_path_a, verdict="FAIL")
    second = record_evaluation(
        spec_path_a, "HONEST_ABANDON", cycle=1,
        registry_path=registry_path, docs_dir=docs_dir,
    )
    assert second != first
    assert os.path.exists(first)
    assert os.path.exists(second)


def test_first_eval_file_byte_identical_after_second_record(env):
    # R-A2: the first eval file must survive the second record untouched.
    _, docs_dir, registry_path, spec_path_a, _ = env
    first = _freeze_and_record(docs_dir, registry_path, spec_path_a, verdict="FAIL")
    with open(first, "rb") as fh:
        snapshot = fh.read()
    record_evaluation(
        spec_path_a, "HONEST_ABANDON", cycle=1,
        registry_path=registry_path, docs_dir=docs_dir,
    )
    with open(first, "rb") as fh:
        assert fh.read() == snapshot
    assert json.loads(snapshot)["verdict"] == "FAIL"
