import os
import json
import yaml
import pytest
import tempfile
from src.ops.preregistration import freeze_preregistration, record_evaluation

@pytest.fixture
def temp_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        docs_dir = os.path.join(temp_dir, "docs", "data")
        os.makedirs(docs_dir, exist_ok=True)
        registry_path = os.path.join(temp_dir, "strategies", "registry.json")
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)

        spec_content = {
            "id": "test_strat_01",
            "name": "Test Strat",
            "family": "test_family",
            "universe": "test_universe",
            "signal": {"entry": "buy", "exit": "sell"}
        }

        spec_path = os.path.join(temp_dir, "strategies", "test_strat.yaml")
        with open(spec_path, "w") as f:
            yaml.dump(spec_content, f)

        yield temp_dir, docs_dir, registry_path, spec_path

def test_freeze_generates_doc_and_refuses_overwrite(temp_env):
    temp_dir, docs_dir, registry_path, spec_path = temp_env
    claim = "Test claim"

    # 1. Freeze generates doc
    filepath = freeze_preregistration(spec_path, claim, docs_dir=docs_dir)
    assert os.path.exists(filepath)
    assert "cycle1_prereg_test_family.md" in filepath

    with open(filepath, "r") as f:
        content = f.read()
    assert claim in content
    assert "Test Strat" in content

    # 2. Refuses to overwrite
    with pytest.raises(FileExistsError):
        freeze_preregistration(spec_path, claim, cycle=1, docs_dir=docs_dir)

def test_record_refuses_without_prereg_doc(temp_env):
    temp_dir, docs_dir, registry_path, spec_path = temp_env

    with pytest.raises(FileNotFoundError, match="no claim registered"):
        record_evaluation(spec_path, "PASS", registry_path=registry_path, docs_dir=docs_dir)

def test_record_creates_eval_and_updates_registry(temp_env):
    temp_dir, docs_dir, registry_path, spec_path = temp_env
    claim = "Test claim for evaluation"

    freeze_preregistration(spec_path, claim, cycle=1, docs_dir=docs_dir)

    # Create fake backtest_report.json
    report_data = {
        "portfolio_summary": {"sharpe": 1.5},
        "all_strategies": [{"id": "s1"}],
        "benchmark_comparison": {"strategy_sharpe": 1.2}
    }
    with open(os.path.join(docs_dir, "backtest_report.json"), "w") as f:
        json.dump(report_data, f)

    eval_filepath = record_evaluation(spec_path, "PASS", cycle=1, registry_path=registry_path, docs_dir=docs_dir)

    # Check eval JSON
    assert os.path.exists(eval_filepath)
    with open(eval_filepath, "r") as f:
        eval_data = json.load(f)

    assert eval_data["verdict"] == "PASS"
    assert eval_data["declared_claim"] == claim
    assert "spec_fingerprint" in eval_data
    assert eval_data["gate_script"] == "scripts/comprehensive_backtest_report.py"
    assert eval_data["dsr"] == 1.2

    # Check registry update
    assert os.path.exists(registry_path)
    with open(registry_path, "r") as f:
        registry = json.load(f)

    assert len(registry["strategies"]) == 1
    strat = registry["strategies"][0]
    assert strat["family"] == "test_family"
    assert strat["verdict"] == "PASS"
    assert strat["status"] == "ported"

def test_fingerprint_changes_when_spec_changes(temp_env):
    temp_dir, docs_dir, registry_path, spec_path = temp_env
    claim = "Test fingerprint"

    freeze_preregistration(spec_path, claim, cycle=1, docs_dir=docs_dir)
    eval_filepath_1 = record_evaluation(spec_path, "FAIL", cycle=1, registry_path=registry_path, docs_dir=docs_dir)

    with open(eval_filepath_1, "r") as f:
        fp1 = json.load(f)["spec_fingerprint"]

    # Modify spec
    with open(spec_path, "a") as f:
        f.write("\nnew_field: true\n")

    eval_filepath_2 = record_evaluation(spec_path, "FAIL", cycle=1, registry_path=registry_path, docs_dir=docs_dir)

    with open(eval_filepath_2, "r") as f:
        fp2 = json.load(f)["spec_fingerprint"]

    assert fp1 != fp2
