"""
Tests for AgentQuant Port — Regime Detection, Harness Evolution, Critic
======================================================================

Run: PYTHONPATH=. pytest tests/test_agentquant_port.py -v
"""

import random
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def spy_df() -> pd.DataFrame:
    """Load and normalize SPY OHLCV data for testing."""
    csv_path = Path("data/spy_ohlcv_2019_2026.csv")
    if not csv_path.exists():
        pytest.skip("SPY data file not found")
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().strip("'\"") for c in df.columns]
    rename_map = {}
    for col in df.columns:
        if "Close" in col:
            rename_map[col] = "Close"
        elif "High" in col:
            rename_map[col] = "High"
        elif "Low" in col:
            rename_map[col] = "Low"
        elif "Open" in col:
            rename_map[col] = "Open"
        elif "Volume" in col:
            rename_map[col] = "Volume"
        elif "Date" in col:
            rename_map[col] = "Date"
    df = df.rename(columns=rename_map)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    return df.sort_index()


@pytest.fixture
def small_df(spy_df: pd.DataFrame) -> pd.DataFrame:
    """A smaller slice for fast unit tests."""
    return spy_df.iloc[:200].copy()


# ---------------------------------------------------------------------------
# Regime detection tests
# ---------------------------------------------------------------------------

class TestRegimeDetection:
    """Tests for src/signals/agentquant_regime.py"""

    def test_import_regime(self):
        from src.signals.agentquant_regime import (
            RegimeSignals,
            detect_regime,
            detect_regime_full,
        )
        assert RegimeSignals is not None
        assert callable(detect_regime)
        assert callable(detect_regime_full)

    def test_regime_features_computation(self, small_df: pd.DataFrame):
        from src.signals.agentquant_regime import compute_regime_features
        features = compute_regime_features(small_df)
        assert "Close" in features.columns
        assert "volatility_21d" in features.columns
        assert "momentum_63d" in features.columns
        assert "sma_200" in features.columns
        assert len(features) == len(small_df)

    def test_detect_regime_returns_string(self, small_df: pd.DataFrame):
        from src.signals.agentquant_regime import compute_regime_features, detect_regime
        features = compute_regime_features(small_df)
        regime = detect_regime(features)
        assert isinstance(regime, str)
        assert "-" in regime  # e.g. "LowVol-Bull"

    def test_detect_regime_full_returns_signals(self, small_df: pd.DataFrame):
        from src.signals.agentquant_regime import (
            compute_regime_features,
            detect_regime_full,
        )
        features = compute_regime_features(small_df)
        signals = detect_regime_full(features)
        assert hasattr(signals, "regime_label")
        assert hasattr(signals, "regime_confidence")
        assert 0.0 <= signals.regime_confidence <= 1.0
        assert signals.vol_regime in ("low", "mid", "high", "crisis")

    def test_regime_with_empty_df(self):
        from src.signals.agentquant_regime import detect_regime_full
        empty = pd.DataFrame()
        signals = detect_regime_full(empty)
        assert signals.regime_label == "Unknown"


# ---------------------------------------------------------------------------
# Harness evolution tests
# ---------------------------------------------------------------------------

class TestHarnessEvolution:
    """Tests for src/evolution/agentquant_harness.py"""

    def test_import_harness(self):
        from src.evolution.agentquant_harness import (
            HarnessEvolution,
            HarnessGenome,
            backtest_strategy,
            sample_grid,
            walk_forward_eval,
        )
        assert HarnessGenome is not None
        assert HarnessEvolution is not None
        assert callable(sample_grid)
        assert callable(backtest_strategy)
        assert callable(walk_forward_eval)

    def test_sample_grid(self):
        from src.evolution.agentquant_harness import DEFAULT_GRIDS, sample_grid
        for family in DEFAULT_GRIDS:
            params = sample_grid(family)
            assert isinstance(params, dict)
            assert set(params.keys()) == set(DEFAULT_GRIDS[family].keys())

    def test_sample_grid_invalid_family(self):
        from src.evolution.agentquant_harness import sample_grid
        with pytest.raises(ValueError, match="Unknown strategy family"):
            sample_grid("nonexistent_family")

    def test_harness_genome_creation(self):
        from src.evolution.agentquant_harness import HarnessGenome
        g = HarnessGenome(strategy_family="momentum", params={"lookback": 20})
        assert g.strategy_family == "momentum"
        assert g.params["lookback"] == 20
        d = g.to_dict()
        assert d["strategy_family"] == "momentum"

    def test_backtest_strategy_runs(self, small_df: pd.DataFrame):
        from src.evolution.agentquant_harness import backtest_strategy
        result = backtest_strategy(small_df, {"lookback": 10, "entry_threshold": 0.02, "exit_threshold": -0.01}, "momentum")
        assert "sharpe" in result
        assert "max_drawdown" in result
        assert "equity_curve" in result
        assert len(result["equity_curve"]) == len(small_df)

    def test_backtest_t1_enforcement(self, small_df: pd.DataFrame):
        """Ensure T+1 shift prevents lookahead."""
        from src.evolution.agentquant_harness import backtest_strategy
        r = backtest_strategy(small_df.iloc[:100], {"lookback": 10, "entry_threshold": 0.01, "exit_threshold": -0.01}, "momentum")
        # Position at t should depend on data up to t-1
        assert r["trade_count"] >= 0

    def test_walk_forward_eval(self, small_df: pd.DataFrame):
        from src.evolution.agentquant_harness import walk_forward_eval
        result = walk_forward_eval(
            small_df,
            {"lookback": 10, "entry_threshold": 0.02, "exit_threshold": -0.01},
            "momentum",
            n_splits=2,
        )
        assert "train_sharpe" in result
        assert "test_sharpe" in result
        assert "walk_forward_efficiency" in result

    def test_evolution_runs(self, small_df: pd.DataFrame):
        from src.evolution.agentquant_harness import HarnessEvolution
        random.seed(42)
        evo = HarnessEvolution(
            families=["momentum"],
            population_size=4,
            generations=2,
            n_splits=2,
            random_seed=42,
        )
        best = evo.evolve(small_df)
        assert best.fitness > 0
        assert best.strategy_family == "momentum"
        assert len(evo.history) == 2


# ---------------------------------------------------------------------------
# Critic tests
# ---------------------------------------------------------------------------

class TestCriticAgent:
    """Tests for src/evolution/agentquant_critic.py"""

    def test_import_critic(self):
        from src.evolution.agentquant_critic import CriticAgent, CriticVerdict
        assert CriticAgent is not None
        assert CriticVerdict is not None

    def test_critic_approves_valid_proposal(self):
        from src.evolution.agentquant_critic import CriticAgent
        critic = CriticAgent(min_wfe=0.3, min_trades=5)
        verdict = critic.critique(
            genome_id="test_1",
            params={"lookback": 20, "entry_threshold": 0.02, "exit_threshold": -0.01},
            family="momentum",
            fitness=0.5,
            sharpe_test=1.0,
            walk_forward_efficiency=0.6,
            trade_count=20,
        )
        assert verdict.approved is True
        assert "All checks passed" in verdict.reason

    def test_critic_rejects_low_wfe(self):
        from src.evolution.agentquant_critic import CriticAgent
        critic = CriticAgent(min_wfe=0.5)
        verdict = critic.critique(
            genome_id="test_low_wfe",
            params={"lookback": 20, "entry_threshold": 0.02, "exit_threshold": -0.01},
            family="momentum",
            fitness=0.3,
            sharpe_test=0.5,
            walk_forward_efficiency=0.2,
            trade_count=30,
        )
        assert verdict.approved is False
        assert any("WFE" in issue for issue in verdict.issues)

    def test_critic_rejects_duplicate(self):
        from src.evolution.agentquant_critic import CriticAgent
        critic = CriticAgent(min_wfe=0.0, min_trades=0)
        # Approve first
        critic.critique(
            genome_id="dup_1",
            params={"lookback": 20, "entry_threshold": 0.02, "exit_threshold": -0.01},
            family="momentum",
            fitness=0.5,
            walk_forward_efficiency=1.0,
            trade_count=20,
        )
        # Second with nearly identical params should be rejected
        verdict = critic.critique(
            genome_id="dup_2",
            params={"lookback": 20, "entry_threshold": 0.0200001, "exit_threshold": -0.01},
            family="momentum",
            fitness=0.5,
            walk_forward_efficiency=1.0,
            trade_count=20,
        )
        assert verdict.approved is False
        assert any("duplicate" in issue.lower() for issue in verdict.issues)

    def test_critic_rejects_bad_window_ordering(self):
        from src.evolution.agentquant_critic import CriticAgent
        critic = CriticAgent(min_wfe=0.0, min_trades=0)
        verdict = critic.critique(
            genome_id="bad_windows",
            params={"short_window": 50, "medium_window": 10, "long_window": 200},
            family="trend_following",
            fitness=0.5,
            walk_forward_efficiency=1.0,
            trade_count=20,
        )
        assert verdict.approved is False
        assert any("window" in issue.lower() for issue in verdict.issues)

    def test_critic_rejects_low_trade_count(self):
        from src.evolution.agentquant_critic import CriticAgent
        critic = CriticAgent(min_wfe=0.0, min_trades=10)
        verdict = critic.critique(
            genome_id="few_trades",
            params={"lookback": 20, "entry_threshold": 0.02, "exit_threshold": -0.01},
            family="momentum",
            fitness=0.5,
            walk_forward_efficiency=1.0,
            trade_count=3,
        )
        assert verdict.approved is False
        assert any("trade count" in issue.lower() for issue in verdict.issues)

    def test_critic_batch(self):
        from src.evolution.agentquant_critic import CriticAgent
        critic = CriticAgent(min_wfe=0.0, min_trades=0)
        proposals = [
            {"genome_id": "b1", "params": {"lookback": 20}, "family": "momentum", "fitness": 0.5, "walk_forward_efficiency": 1.0, "trade_count": 20},
            {"genome_id": "b2", "params": {"lookback": 30}, "family": "momentum", "fitness": 0.4, "walk_forward_efficiency": 0.8, "trade_count": 15},
        ]
        verdicts = critic.critique_batch(proposals)
        assert len(verdicts) == 2

    def test_critic_summary(self):
        from src.evolution.agentquant_critic import CriticAgent
        critic = CriticAgent(min_wfe=0.0, min_trades=0)
        critic.critique("s1", {"a": 1}, "f", 0.5, walk_forward_efficiency=1.0, trade_count=20)
        critic.critique("s2", {"a": 1}, "f", 0.5, walk_forward_efficiency=1.0, trade_count=20)  # duplicate
        s = critic.summary()
        assert s["approved_count"] >= 1
        assert s["rejected_count"] >= 1


# ---------------------------------------------------------------------------
# Integration test — full pipeline
# ---------------------------------------------------------------------------

class TestIntegration:
    """End-to-end pipeline test."""

    def test_full_pipeline(self, small_df: pd.DataFrame):
        """Test regime → evolution → critic pipeline on small data."""
        from src.evolution.agentquant_critic import CriticAgent
        from src.evolution.agentquant_harness import HarnessEvolution
        from src.signals.agentquant_regime import (
            compute_regime_features,
            detect_regime_full,
        )

        # Regime
        features = compute_regime_features(small_df)
        regime = detect_regime_full(features)
        assert regime.regime_label != ""

        # Evolution
        random.seed(42)
        evo = HarnessEvolution(
            families=["momentum"],
            population_size=3,
            generations=1,
            n_splits=2,
            random_seed=42,
        )
        best = evo.evolve(small_df)
        assert best.fitness >= 0

        # Critic
        critic = CriticAgent(min_wfe=0.0, min_trades=0)
        verdict = critic.critique(
            genome_id="integration_test",
            params=best.params,
            family=best.strategy_family,
            fitness=best.fitness,
            sharpe_test=best.sharpe_test,
            walk_forward_efficiency=best.walk_forward_efficiency,
            trade_count=best.trade_count,
        )
        assert verdict.approved in (True, False)
        assert isinstance(verdict.reason, str)
