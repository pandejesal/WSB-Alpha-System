import json
import os

import pytest
import yaml


def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def test_registry_exists_and_matches_specs():
    # Direction log (2026-09-11, merge fix): the registry is engine-owned and
    # its root alternates between evolved (strategies/generations) and engine-
    # canonical (strategies/portfolio) shapes depending on writer. The test
    # pins the INVARIANTS (nonempty strategies, no live entries, valid spec
    # pointers, generations bookkeeping consistent when present) — not one
    # root shape.
    assert os.path.exists("strategies/registry.json")
    with open("strategies/registry.json", 'r') as f:
        registry = json.load(f)

    assert "strategies" in registry
    assert "portfolio" in registry or "generations" in registry

    strategies = registry["strategies"]
    assert len(strategies) > 0
    # Dangling-pointer quarantine retired 2026-09-11 (R4 removed the
    # momentum_breakout_v4 spec_file key; full-pointer scan returns []).
    # Any missing spec_file now fails loudly.
    for s in strategies:
        assert isinstance(s["id"], str) and s["id"]
        assert isinstance(s["family"], str) and s["family"]
        # Paper-only fail-closed: no live entries permitted.
        assert str(s.get("status", "")).lower() != "live"
        spec_path = s.get("spec_file")
        if spec_path is not None:
            assert os.path.exists(spec_path), s["id"]
            spec = load_yaml(spec_path)
            # Specs use either `id` or legacy `strategy_name` as identity.
            assert spec.get("id", spec.get("strategy_name")) == s["id"]

    gens = registry.get("generations")
    if gens is not None:
        assert gens["alive"] + gens["retired"] + gens.get("purged_stub", 0) == len(strategies)

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
