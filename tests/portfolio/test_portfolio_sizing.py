import pytest
from src.ops.portfolio import PortfolioManager

def test_sizing_engine_at_100_dollars():
    manager = PortfolioManager(registry_path="strategies/registry.json")

    assert len(manager.active_sleeves) == 7

    per_sleeve_targets = {
        "us_momentum_top5": [{"ticker": f"MOM{i}", "weight": 0.2} for i in range(5)],
        "spy_sma200": [{"ticker": "SPY", "weight": 1.0}],
        "spy_rsi2": [{"ticker": "SPY", "weight": 1.0}],
        "btc_vol_target_sma100": [{"ticker": "BTC-USD", "weight": 1.0}],
        "us_lowvol_top30": [{"ticker": f"LOW{i}", "weight": 1/30} for i in range(30)],
        "us_pead_top5": [{"ticker": f"PEAD{i}", "weight": 0.2} for i in range(5)],
        "breakout_burst": [{"ticker": f"BRK{i}", "weight": 0.1} for i in range(10)]
    }

    account_equity = 100.0

    result = manager.compute_merged_targets(per_sleeve_targets, account_equity=account_equity)
    targets = result["targets"]

    total_notional = sum(t["notional"] for t in targets)

    # Must be <= 60%
    assert total_notional <= account_equity * 0.60 + 0.1

    # Every target qty must satisfy min-notional >= $1
    for t in targets:
        assert t["notional"] >= 1.0, f"Target {t['ticker']} has notional < 1.0: {t['notional']}"
