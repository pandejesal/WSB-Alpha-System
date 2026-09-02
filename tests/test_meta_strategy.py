import pytest

from src.alpha.meta_strategy import MetaStrategy, StrategyConfig


def test_select_strategy_defaults():
    meta = MetaStrategy()

    config = meta.select_strategy("trending_up")
    assert isinstance(config, StrategyConfig)
    assert config.name == "momentum_breakout_v2"

    config = meta.select_strategy("trending_down")
    assert config.name == "cash/defensive"

    config = meta.select_strategy("mean_reverting")
    assert config.name == "mean_reversion_enhanced"

    config = meta.select_strategy("volatile")
    assert config.name == "volatile"
    assert config.parameters == {"sizing": "reduced", "stops": "wider"}

    config = meta.select_strategy("quiet")
    assert config.name == "trend_following_v3"


def test_select_strategy_custom_override():
    custom_mapping = {
        "trending_up": {"name": "custom_trend_strategy", "parameters": {"custom_param": 42}},
        "quiet": {"name": "custom_quiet_strategy"}
    }
    meta = MetaStrategy(custom_mapping=custom_mapping)

    config = meta.select_strategy("trending_up")
    assert config.name == "custom_trend_strategy"
    assert config.parameters == {"custom_param": 42}

    config = meta.select_strategy("quiet")
    assert config.name == "custom_quiet_strategy"
    assert config.parameters == {}

    # Defaults still apply for non-overridden
    config = meta.select_strategy("mean_reverting")
    assert config.name == "mean_reversion_enhanced"


def test_select_strategy_unknown_regime():
    meta = MetaStrategy()
    with pytest.raises(ValueError, match="Unknown regime label: unknown_regime"):
        meta.select_strategy("unknown_regime")


def test_run_meta_strategy():
    import numpy as np
    import pandas as pd

    meta = MetaStrategy()

    # Create mock data
    dates = pd.date_range(start="2023-01-01", periods=100)
    data = pd.DataFrame({
        "Close": np.random.randn(100).cumsum() + 100
    }, index=dates)
    regime_series = pd.Series(["trending_up"] * 50 + ["mean_reverting"] * 50, index=dates)

    portfolio = meta.run_meta_strategy(data, regime_series)
    assert portfolio is not None
    assert hasattr(portfolio, "sharpe_ratio")


def test_parameter_tuner(tmp_path):
    import csv

    import numpy as np
    import pandas as pd

    from src.alpha.meta_strategy import ParameterTuner

    # Write mock grid config
    grid_config = tmp_path / "mock_grids.yaml"
    grid_config.write_text("""
mock_strategy:
  lookback: [10, 20]
  threshold: [0.01, 0.02]
""")

    # Create mock data
    dates = pd.date_range(start="2023-01-01", periods=100)
    data = pd.DataFrame({
        "Close": np.random.randn(100).cumsum() + 100
    }, index=dates)

    output_csv = tmp_path / "results.csv"

    tuner = ParameterTuner(str(grid_config))
    tuner.tune(["mock_strategy"], data, str(output_csv))

    assert output_csv.exists()

    # Verify CSV schema and content
    with open(output_csv, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        assert len(rows) == 4  # 2x2 grid search
        for row in rows:
            assert "strategy" in row
            assert "params" in row
            assert "sharpe" in row
            assert "max_dd" in row
            assert "win_rate" in row
            assert "total_trades" in row
            assert row["strategy"] == "mock_strategy"
