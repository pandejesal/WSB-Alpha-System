import json
import yaml
import pytest

STRATEGIES = [
    "us_momentum_top5",
    "spy_sma200",
    "spy_rsi2",
    "btc_vol_target_sma100",
    "dual_momentum"
]

EXPECTED_KEYS = [
    "id", "name", "family", "venue", "universe", "indicators", "parameters",
    "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result",
    "robustness_notes", "feasibility_at_100", "risks"
]

@pytest.fixture
def registry():
    with open("strategies/registry.json", "r") as f:
        return json.load(f)

@pytest.mark.parametrize("strat_id", STRATEGIES)
def test_strategy_spec_schema(strat_id):
    with open(f"strategies/{strat_id}.yaml", "r") as f:
        spec = yaml.safe_load(f)

    for key in EXPECTED_KEYS:
        assert key in spec, f"Missing key {key} in {strat_id}.yaml"

    assert spec["id"] == strat_id

def test_registry_entries(registry):
    assert "strategies" in registry
    assert "portfolio" in registry

    reg_strats = {s["id"]: s for s in registry["strategies"]}
    for strat_id in STRATEGIES:
        assert strat_id in reg_strats
        assert reg_strats[strat_id]["spec_file"] == f"strategies/{strat_id}.yaml"

    assert registry["portfolio"]["id"] == "flagship_portfolio_v1"
    assert registry["portfolio"]["spec_file"] == "strategies/flagship_portfolio_v1.yaml"

def test_parameter_sanity():
    with open("strategies/us_momentum_top5.yaml", "r") as f:
        spec = yaml.safe_load(f)
        assert spec["parameters"]["top_n"] == 5
        assert spec["parameters"]["lookback_days"] == 126
        assert spec["parameters"]["skip_days"] == 21

    with open("strategies/spy_sma200.yaml", "r") as f:
        spec = yaml.safe_load(f)
        assert spec["parameters"]["window"] == 200

    with open("strategies/spy_rsi2.yaml", "r") as f:
        spec = yaml.safe_load(f)
        assert spec["parameters"]["entry"] == 10
        assert spec["parameters"]["exit_rsi"] == 70
        assert spec["parameters"]["hold_days"] == 5

    with open("strategies/btc_vol_target_sma100.yaml", "r") as f:
        spec = yaml.safe_load(f)
        assert spec["parameters"]["target_vol"] == 0.30
        assert spec["parameters"]["vol_window"] == 30
        assert spec["parameters"]["gate_window"] == 100

    with open("strategies/dual_momentum.yaml", "r") as f:
        spec = yaml.safe_load(f)
        assert spec["parameters"]["lookback_days"] == 21
        assert spec["parameters"]["skip_days"] == 21

def test_portfolio_spec():
    with open("strategies/flagship_portfolio_v1.yaml", "r") as f:
        spec = yaml.safe_load(f)

    for key in ["id", "name", "type", "created", "source", "members", "allocation", "fees", "constraints", "expected_metrics", "gates"]:
        assert key in spec

    assert spec["id"] == "flagship_portfolio_v1"

    member_specs = [m["spec"] for m in spec["members"]]
    for strat_id in STRATEGIES:
        assert f"strategies/{strat_id}.yaml" in member_specs
