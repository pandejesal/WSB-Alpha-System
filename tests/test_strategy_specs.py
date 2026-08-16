import os
import json
import yaml
import pytest

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def test_registry_exists_and_matches_specs():
    assert os.path.exists("strategies/registry.json")
    with open("strategies/registry.json", 'r') as f:
        registry = json.load(f)

    assert "strategies" in registry
    assert "portfolio" in registry

    strategy_ids = [s["id"] for s in registry["strategies"]]
    expected_ids = ["us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]

    for eid in expected_ids:
        assert eid in strategy_ids

    for s in registry["strategies"]:
        spec_path = s["spec_file"]
        assert os.path.exists(spec_path)
        spec = load_yaml(spec_path)
        assert spec["id"] == s["id"]

    portfolio_spec_path = registry["portfolio"]["spec_file"]
    assert os.path.exists(portfolio_spec_path)
    port_spec = load_yaml(portfolio_spec_path)
    assert port_spec["id"] == registry["portfolio"]["id"]

def test_us_momentum_top5_schema_and_params():
    spec = load_yaml("strategies/us_momentum_top5.yaml")
    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    for k in req_keys:
        assert k in spec

    params = spec["parameters"]
    assert params["top_n"] == 5
    assert params["lookback_days"] == 126
    assert params["skip_days"] == 21

def test_spy_sma200_schema_and_params():
    spec = load_yaml("strategies/spy_sma200.yaml")
    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    for k in req_keys:
        assert k in spec

    params = spec["parameters"]
    assert params["window"] == 200

def test_spy_rsi2_schema_and_params():
    spec = load_yaml("strategies/spy_rsi2.yaml")
    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    for k in req_keys:
        assert k in spec

    params = spec["parameters"]
    assert params["entry"] == 10
    assert params["exit_rsi"] == 70
    assert params["hold_days"] == 5

def test_btc_vol_target_sma100_schema_and_params():
    spec = load_yaml("strategies/btc_vol_target_sma100.yaml")
    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    for k in req_keys:
        assert k in spec

    params = spec["parameters"]
    assert params["target_vol"] == 0.30
    assert params["vol_window"] == 30
    assert params["gate_window"] == 100

def test_dual_momentum_schema_and_params():
    spec = load_yaml("strategies/dual_momentum.yaml")
    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    for k in req_keys:
        assert k in spec

    params = spec["parameters"]
    assert params["lookback_days"] == 21
    assert params["skip_days"] == 21

def test_flagship_portfolio_schema_and_references():
    spec = load_yaml("strategies/flagship_portfolio_v1.yaml")
    req_keys = ["id", "name", "type", "created", "source", "members", "allocation", "fees", "constraints", "expected_metrics", "gates"]
    for k in req_keys:
        assert k in spec

    alloc = spec["allocation"]
    assert alloc["btc_floor"] == 0.05
    assert alloc["vol_window_months"] == 12

    for member in spec["members"]:
        assert os.path.exists(member["spec"])
