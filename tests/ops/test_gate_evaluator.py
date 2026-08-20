import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from src.ops.gate_evaluator import GateEvaluator


def _trading_days(n: int) -> list[str]:
    """Returns the last n trading days (Mon-Fri) ending yesterday, oldest first."""
    days: list[str] = []
    d = datetime.now(timezone.utc) - timedelta(days=1)
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    return list(reversed(days))


def _heartbeat_artifact(days: list[str]) -> dict:
    history = []
    for day in days:
        history.append({
            "run_id": f"test-{day}",
            "ts": f"{day}T12:00:00Z",
            "status": "ok",
            "job": "test"
        })
    return {"history": history, "latest": history[-1] if history else None}


def _fills() -> list[dict]:
    fills = [{"sleeve_id": "us_momentum_top5"} for _ in range(15)]
    fills.extend([{"sleeve_id": "spy_rsi2"} for _ in range(15)])
    fills.extend([{"sleeve_id": "spy_sma200"} for _ in range(20)])
    return fills


def _pass_data(**overrides) -> dict:
    data = {
        "fills": _fills(),
        "sharpe": {"ci_lower": 0.5},
        "permutation": {"p_value": 0.5},
        "heartbeats": _heartbeat_artifact(_trading_days(7)),
        "rehearsal": {"restored": True},
        "reconciliation": {"status": "clean"},
    }
    data.update(overrides)
    return data


def test_gate_evaluator_all_pass():
    results = GateEvaluator().evaluate_all(_pass_data())
    for gate in ("G1", "G2", "G3", "G4", "G5", "G6", "G7"):
        assert results[gate] is True


def test_gate_evaluator_g1_fails_under_50():
    data = _pass_data(fills=[{"sleeve_id": "us_momentum_top5"} for _ in range(10)])
    results = GateEvaluator().evaluate_all(data)
    assert results["G1"] is False


def test_gate_evaluator_g2_fails_sleeve_under_10():
    fills = _fills()
    fills = [f for f in fills if f["sleeve_id"] != "spy_rsi2"]
    fills.extend([{"sleeve_id": "spy_rsi2"} for _ in range(5)])
    data = _pass_data(fills=fills)
    results = GateEvaluator().evaluate_all(data)
    assert results["G2"] is False


def test_gate_evaluator_g2_fails_no_fills():
    data = _pass_data(fills=[])
    results = GateEvaluator().evaluate_all(data)
    assert results["G1"] is False
    assert results["G2"] is False


def test_gate_evaluator_g3_fails_negative_ci():
    data = _pass_data(sharpe={"ci_lower": -0.1})
    results = GateEvaluator().evaluate_all(data)
    assert results["G3"] is False


def test_gate_evaluator_g4_fails_overfit():
    data = _pass_data(permutation={"p_value": 0.01})
    results = GateEvaluator().evaluate_all(data)
    assert results["G4"] is False


def test_gate_evaluator_g5_fails_short_history():
    data = _pass_data(heartbeats=_heartbeat_artifact(_trading_days(3)))
    results = GateEvaluator().evaluate_all(data)
    assert results["G5"] is False


def test_gate_evaluator_g5_fails_gap_in_history():
    days = _trading_days(8)
    days = days[:3] + days[4:]  # drop one day mid-sequence -> two segments of 3 and 4
    data = _pass_data(heartbeats=_heartbeat_artifact(days))
    results = GateEvaluator().evaluate_all(data)
    assert results["G5"] is False


def test_gate_evaluator_g5_passes_weekend_gap():
    # Mon-Fri + following Mon = 7 trading days with a legitimate weekend gap
    days = _trading_days(7)
    # Ensure the sequence bridges a weekend: take a Thu..Fri of week 1 and Mon..Thu of week 2
    seq = []
    d = datetime.now(timezone.utc) - timedelta(days=1)
    while len(seq) < 14:
        if d.weekday() < 5:
            seq.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    seq = list(reversed(seq))
    # find Fri->Mon bridge
    bridge = None
    for i in range(len(seq) - 1):
        if datetime.strptime(seq[i], "%Y-%m-%d").weekday() == 4 and \
           datetime.strptime(seq[i + 1], "%Y-%m-%d").weekday() == 0:
            bridge = i
            break
    assert bridge is not None, "no Fri->Mon bridge in generated window"
    week = seq[max(0, bridge - 2):bridge + 5]  # Wed..Thu across the weekend (7 trading days)
    if len(week) < 7:
        week = seq[-7:]
    assert len(week) == 7, f"expected 7-day window, got {len(week)}"
    data = _pass_data(heartbeats=_heartbeat_artifact(week))
    results = GateEvaluator().evaluate_all(data)
    assert results["G5"] is True


def test_gate_evaluator_g6_fails_not_restored():
    data = _pass_data(rehearsal={"restored": False})
    results = GateEvaluator().evaluate_all(data)
    assert results["G6"] is False


def test_gate_evaluator_g7_fails_unresolved():
    data = _pass_data(reconciliation={"status": "unresolved"})
    results = GateEvaluator().evaluate_all(data)
    assert results["G7"] is False


@pytest.fixture
def mock_data_dir(tmp_path):
    data_dir = tmp_path / "docs" / "data"
    ops_dir = data_dir / "ops"
    paper_dir = data_dir / "paper"

    os.makedirs(ops_dir)
    os.makedirs(paper_dir)

    with open(ops_dir / "fills.json", "w") as f:
        json.dump(_fills(), f)
    with open(paper_dir / "sharpe.json", "w") as f:
        json.dump({"ci_lower": 0.5}, f)
    with open(data_dir / "permutation_study.json", "w") as f:
        json.dump({"p_value": 0.5}, f)
    with open(ops_dir / "heartbeat.json", "w") as f:
        json.dump(_heartbeat_artifact(_trading_days(7)), f)
    with open(ops_dir / "kill_switch_rehearsal.json", "w") as f:
        json.dump({"restored": True}, f)
    with open(ops_dir / "reconciliation.json", "w") as f:
        json.dump({"status": "clean"}, f)

    return str(data_dir)


def test_gate_evaluator_load_artifacts_and_evaluate(mock_data_dir):
    ge = GateEvaluator(data_dir=mock_data_dir)
    data = ge.load_artifacts()
    results = ge.evaluate_all(data)
    for gate in ("G1", "G2", "G3", "G4", "G5", "G6", "G7"):
        assert results[gate] is True


def test_gate_evaluator_pure_no_io(tmp_path):
    """evaluate_all must work with data dicts only - no filesystem access needed."""
    ge = GateEvaluator(data_dir=str(tmp_path / "nonexistent"))
    results = ge.evaluate_all(_pass_data())
    assert results["G5"] is True
    assert results["G1"] is True
