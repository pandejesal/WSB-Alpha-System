import pytest
from src.ops.gate_evaluator import evaluate_gates

@pytest.fixture
def mock_data():
    return {
        "portfolio": {"dd_breaker_open": True},
        "heartbeat": {"status": "ok", "history": [{"ts": "2026-08-01T00"}, {"ts": "2026-08-02T00"}, {"ts": "2026-08-03T00"}, {"ts": "2026-08-04T00"}, {"ts": "2026-08-05T00"}, {"ts": "2026-08-06T00"}, {"ts": "2026-08-07T00"}]},
        "recon": {"mismatches": []},
        "perm": {"permutations": 200},
        "rehearsal": {"scenarios": {"T2_halt": "success", "T3_halt": "success"}}
    }

def test_gate_evaluator_all_pass(mock_data):
    md = mock_data
    result = evaluate_gates(md["portfolio"], md["heartbeat"], md["recon"], md["perm"], md["rehearsal"])
    assert result["passed"] is True
    assert result["gates"]["G1_dd_breaker"] is True
    assert result["gates"]["G2_heartbeat"] is True
    assert result["gates"]["G3_reconciliation_last"] is True

def test_gate_evaluator_g1_fails(mock_data):
    md = mock_data
    md["portfolio"]["dd_breaker_open"] = False

    result = evaluate_gates(md["portfolio"], md["heartbeat"], md["recon"], md["perm"], md["rehearsal"])
    assert result["passed"] is False
    assert result["gates"]["G1_dd_breaker"] is False

def test_gate_evaluator_g2_fails(mock_data):
    md = mock_data
    md["heartbeat"]["status"] = "failed"

    result = evaluate_gates(md["portfolio"], md["heartbeat"], md["recon"], md["perm"], md["rehearsal"])
    assert result["passed"] is False
    assert result["gates"]["G2_heartbeat"] is False

def test_gate_evaluator_g3_fails(mock_data):
    md = mock_data
    md["recon"]["mismatches"] = [{"diff": 50}]

    result = evaluate_gates(md["portfolio"], md["heartbeat"], md["recon"], md["perm"], md["rehearsal"])
    assert result["passed"] is False
    assert result["gates"]["G3_reconciliation_last"] is False

def test_gate_evaluator_g5_fails(mock_data):
    md = mock_data
    md["heartbeat"]["history"] = [{"ts": "d1"}] # Only 1 day

    result = evaluate_gates(md["portfolio"], md["heartbeat"], md["recon"], md["perm"], md["rehearsal"])
    assert result["passed"] is False
    assert result["gates"]["G5_heartbeat_7_days"] is False
