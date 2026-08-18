import json
import os

import pytest
from src.ops.gate_evaluator import GateEvaluator


@pytest.fixture
def mock_data_dir(tmp_path):
    data_dir = tmp_path / "docs" / "data"
    ops_dir = data_dir / "ops"
    paper_dir = data_dir / "paper"

    os.makedirs(ops_dir)
    os.makedirs(paper_dir)

    # G1: 50 fills
    fills = [{"sleeve_id": "us_momentum_top5"} for _ in range(15)]
    fills.extend([{"sleeve_id": "spy_rsi2"} for _ in range(15)])
    fills.extend([{"sleeve_id": "spy_sma200"} for _ in range(20)])
    with open(ops_dir / "fills.json", "w") as f:
        json.dump(fills, f)

    # G3: Sharpe > 0
    with open(paper_dir / "sharpe.json", "w") as f:
        json.dump({"ci_lower": 0.5}, f)

    # G4: Permutation p > 0.05
    with open(data_dir / "permutation_study.json", "w") as f:
        json.dump({"p_value": 0.5}, f)

    # G5: Heartbeat exists
    with open(ops_dir / "heartbeat.json", "w") as f:
        json.dump({"status": "ok"}, f)

    # G6: Kill switch rehearsal restored
    with open(ops_dir / "kill_switch_rehearsal.json", "w") as f:
        json.dump({"restored": True}, f)

    # G7: Recon clean
    with open(ops_dir / "reconciliation.json", "w") as f:
        json.dump({"status": "clean"}, f)

    return str(data_dir)

def test_gate_evaluator_all_pass(mock_data_dir):
    ge = GateEvaluator(data_dir=mock_data_dir)
    results = ge.run_evaluation(auto_halt=False)

    assert results["G1"] is True
    assert results["G2"] is True
    assert results["G3"] is True
    assert results["G4"] is True
    assert results["G5"] is True
    assert results["G6"] is True
    assert results["G7"] is True

def test_gate_evaluator_g1_fails(mock_data_dir):
    ops_dir = os.path.join(mock_data_dir, "ops")
    # Only 10 fills
    fills = [{"sleeve_id": "us_momentum_top5"} for _ in range(10)]
    with open(os.path.join(ops_dir, "fills.json"), "w") as f:
        json.dump(fills, f)

    ge = GateEvaluator(data_dir=mock_data_dir)
    results = ge.run_evaluation(auto_halt=False)

    assert results["G1"] is False

def test_gate_evaluator_g3_fails_negative_ci(mock_data_dir):
    paper_dir = os.path.join(mock_data_dir, "paper")
    with open(os.path.join(paper_dir, "sharpe.json"), "w") as f:
        json.dump({"ci_lower": -0.1}, f)

    ge = GateEvaluator(data_dir=mock_data_dir)
    results = ge.run_evaluation(auto_halt=False)

    assert results["G3"] is False

def test_gate_evaluator_g4_fails_overfit(mock_data_dir):
    with open(os.path.join(mock_data_dir, "permutation_study.json"), "w") as f:
        json.dump({"p_value": 0.01}, f) # < 0.05

    ge = GateEvaluator(data_dir=mock_data_dir)
    results = ge.run_evaluation(auto_halt=False)

    assert results["G4"] is False
