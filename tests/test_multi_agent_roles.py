"""Tests for multi-agent role templates and role-based routing."""
import numpy as np
import pandas as pd
import pytest

from src.alpha.multi_agent_roles import (
    DEFAULT_PIPELINE,
    EXECUTION,
    RESEARCHER,
    RISK,
    AgentRole,
    get_pipeline_for_family,
    route_signal_through_agents,
)
from src.ops.signals import UnsupportedRuleShape

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bullish_signal() -> dict:
    return {
        "signal": "LONG",
        "targets": [
            {"ticker": "AAPL", "weight": 0.5},
            {"ticker": "MSFT", "weight": 0.5},
        ],
    }


@pytest.fixture
def flat_signal() -> dict:
    return {"signal": "FLAT"}


@pytest.fixture
def no_data_signal() -> dict:
    return {"signal": "FLAT", "data_unavailable": True}


@pytest.fixture
def overweight_signal() -> dict:
    return {
        "signal": "LONG",
        "targets": [
            {"ticker": "AAPL", "weight": 0.80},
            {"ticker": "MSFT", "weight": 0.20},
        ],
    }


@pytest.fixture
def too_many_targets_signal() -> dict:
    targets = [{"ticker": f"T{i}", "weight": 0.05} for i in range(15)]
    return {"signal": "LONG", "targets": targets}


@pytest.fixture
def micro_weight_signal() -> dict:
    return {
        "signal": "LONG",
        "targets": [
            {"ticker": "AAPL", "weight": 0.99},
            {"ticker": "MSFT", "weight": 0.005},  # below min_weight
        ],
    }


@pytest.fixture
def sample_data() -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=250, freq="B")
    return pd.DataFrame({
        "Open": np.linspace(100, 200, 250),
        "High": np.linspace(101, 201, 250),
        "Low": np.linspace(99, 199, 250),
        "Close": np.linspace(100.5, 200.5, 250),
        "Volume": np.random.randint(1000, 10000, 250),
    }, index=dates)


# ---------------------------------------------------------------------------
# Role definition tests
# ---------------------------------------------------------------------------

class TestAgentRoles:
    def test_researcher_role_exists(self):
        assert RESEARCHER.name == "researcher"
        assert RESEARCHER.description  # non-empty description

    def test_risk_role_exists(self):
        assert RISK.name == "risk"
        assert RISK.description  # non-empty description

    def test_execution_role_exists(self):
        assert EXECUTION.name == "execution"
        assert EXECUTION.description  # non-empty description

    def test_all_roles_are_dataclasses(self):
        for role in [RESEARCHER, RISK, EXECUTION]:
            assert isinstance(role, AgentRole)

    def test_pipeline_order_is_research_risk_exec(self):
        names = [r.name for r in DEFAULT_PIPELINE]
        assert names == ["researcher", "risk", "execution"]

    def test_each_role_has_allowed_families(self):
        for role in [RESEARCHER, RISK, EXECUTION]:
            assert len(role.allowed_families) > 0
            assert isinstance(role.allowed_families, frozenset)

    def test_all_core_families_present_in_roles(self):
        core = {"momentum", "trend", "mean_reversion", "ta_rules"}
        for role in [RESEARCHER, RISK, EXECUTION]:
            assert core.issubset(role.allowed_families), (
                f"Role {role.name} missing families: {core - role.allowed_families}"
            )


# ---------------------------------------------------------------------------
# Researcher agent tests
# ---------------------------------------------------------------------------

class TestResearcherAgent:
    def test_bullish_signal_passes(self, bullish_signal):
        result = RESEARCHER.processor(bullish_signal)
        assert result["researcher_verdict"] == "PROCEED"
        assert result["researcher_reason"] == "targets_present"

    def test_flat_signal_no_bid(self, flat_signal):
        result = RESEARCHER.processor(flat_signal)
        assert result["researcher_verdict"] == "NO_BID"

    def test_no_data_signal_no_bid(self, no_data_signal):
        result = RESEARCHER.processor(no_data_signal)
        assert result["researcher_verdict"] == "NO_BID"

    def test_preserves_original_fields(self, bullish_signal):
        result = RESEARCHER.processor(bullish_signal)
        assert result["signal"] == "LONG"
        assert len(result["targets"]) == 2


# ---------------------------------------------------------------------------
# Risk agent tests
# ---------------------------------------------------------------------------

class TestRiskAgent:
    def test_pass_within_limits(self, bullish_signal):
        result = RISK.processor(bullish_signal)
        assert result["risk_verdict"] == "PASS"

    def test_veto_weight_breach(self, overweight_signal):
        result = RISK.processor(overweight_signal)
        assert result["risk_verdict"] == "VETO"
        assert result["signal"] == "FLAT"

    def test_veto_too_many_targets(self, too_many_targets_signal):
        result = RISK.processor(too_many_targets_signal)
        assert result["risk_verdict"] == "VETO"
        assert "too_many_targets" in result["risk_reason"]

    def test_veto_upstream_no_bid(self):
        signal = {
            "signal": "FLAT",
            "researcher_verdict": "NO_BID",
            "researcher_reason": "no_signal",
        }
        result = RISK.processor(signal)
        assert result["risk_verdict"] == "VETO"
        assert result["risk_reason"] == "upstream_no_bid"

    def test_veto_no_targets(self):
        signal = {"signal": "LONG", "targets": []}
        result = RISK.processor(signal)
        assert result["risk_verdict"] == "VETO"

    def test_custom_max_targets(self, too_many_targets_signal):
        result = RISK.processor(too_many_targets_signal, max_targets=20)
        assert result["risk_verdict"] == "PASS"

    def test_custom_max_single_weight(self, overweight_signal):
        result = RISK.processor(overweight_signal, max_single_weight=0.90)
        assert result["risk_verdict"] == "PASS"


# ---------------------------------------------------------------------------
# Execution agent tests
# ---------------------------------------------------------------------------

class TestExecutionAgent:
    def test_execute_on_valid(self, bullish_signal):
        result = EXECUTION.processor(bullish_signal)
        assert result["execution_verdict"] == "EXECUTE"
        assert result["execution_reason"] == "ready"

    def test_skip_on_veto(self):
        signal = {"signal": "FLAT", "risk_verdict": "VETO"}
        result = EXECUTION.processor(signal)
        assert result["execution_verdict"] == "SKIP"

    def test_skip_on_flat(self, flat_signal):
        result = EXECUTION.processor(flat_signal)
        assert result["execution_verdict"] == "SKIP"

    def test_weight_normalization(self, bullish_signal):
        result = EXECUTION.processor(bullish_signal)
        total = sum(t["weight"] for t in result["targets"])
        assert abs(total - 1.0) < 1e-9

    def test_clips_micro_positions(self, micro_weight_signal):
        result = EXECUTION.processor(micro_weight_signal, min_weight=0.01)
        assert len(result["targets"]) == 1
        assert result["targets"][0]["ticker"] == "AAPL"

    def test_all_micro_clipped_to_flat(self):
        signal = {
            "signal": "LONG",
            "risk_verdict": "PASS",
            "targets": [
                {"ticker": "X", "weight": 0.001},
                {"ticker": "Y", "weight": 0.002},
            ],
        }
        result = EXECUTION.processor(signal, min_weight=0.01)
        assert result["signal"] == "FLAT"
        assert result["execution_reason"] == "all_targets_below_min_weight"

    def test_no_normalize_option(self, bullish_signal):
        result = EXECUTION.processor(bullish_signal, normalize=False)
        # Weights should remain as-is (0.5 each)
        assert result["targets"][0]["weight"] == 0.5


# ---------------------------------------------------------------------------
# Pipeline routing tests
# ---------------------------------------------------------------------------

class TestPipelineRouting:
    def test_known_family_returns_default_pipeline(self):
        pipeline = get_pipeline_for_family("momentum")
        assert [r.name for r in pipeline] == ["researcher", "risk", "execution"]

    def test_unknown_family_raises(self):
        with pytest.raises(UnsupportedRuleShape, match="Unknown strategy family"):
            get_pipeline_for_family("nonexistent_family_xyz")

    @pytest.mark.parametrize("family", [
        "momentum", "trend", "mean_reversion", "breakout_burst",
        "low_vol", "event_driven", "vol_targeting", "ta_rules",
        "sentiment_overlay", "xgboost_exits",
    ])
    def test_all_known_families_route(self, family):
        pipeline = get_pipeline_for_family(family)
        assert len(pipeline) >= 1


# ---------------------------------------------------------------------------
# End-to-end pipeline routing tests
# ---------------------------------------------------------------------------

class TestRouteSignalThroughAgents:
    def test_bullish_through_full_pipeline(self, bullish_signal):
        result = route_signal_through_agents(
            bullish_signal, "momentum",
        )
        assert result["researcher_verdict"] == "PROCEED"
        assert result["risk_verdict"] == "PASS"
        assert result["execution_verdict"] == "EXECUTE"
        assert result["signal"] == "LONG"
        assert len(result["targets"]) == 2

    def test_flat_short_circuits(self, flat_signal):
        result = route_signal_through_agents(flat_signal, "trend")
        assert result["researcher_verdict"] == "NO_BID"
        assert result["pipeline_vetoed_by"] == "researcher"
        assert result["signal"] == "FLAT"

    def test_weight_breach_vetoed_by_risk(self, overweight_signal):
        result = route_signal_through_agents(overweight_signal, "momentum")
        assert result["researcher_verdict"] == "PROCEED"
        assert result["risk_verdict"] == "VETO"
        assert result["pipeline_vetoed_by"] == "risk"
        assert result["signal"] == "FLAT"

    def test_execution_normalizes_weights(self, bullish_signal):
        result = route_signal_through_agents(bullish_signal, "ta_rules")
        total = sum(t["weight"] for t in result["targets"])
        assert abs(total - 1.0) < 1e-9

    def test_unknown_family_raises(self):
        with pytest.raises(UnsupportedRuleShape):
            route_signal_through_agents(
                {"signal": "LONG", "targets": []}, "nonexistent_family"
            )

    def test_custom_risk_params(self, overweight_signal):
        result = route_signal_through_agents(
            overweight_signal, "momentum",
            risk_params={"max_single_weight": 0.90},
        )
        assert result["risk_verdict"] == "PASS"

    def test_execution_stamp_always_present(self, bullish_signal):
        result = route_signal_through_agents(bullish_signal, "trend")
        assert "execution_verdict" in result

    def test_vetoed_pipeline_includes_veto_marker(self, overweight_signal):
        result = route_signal_through_agents(overweight_signal, "momentum")
        assert "pipeline_vetoed_by" in result
        assert result["pipeline_vetoed_by"] in ("researcher", "risk", "execution")
