import pytest
from unittest.mock import patch, MagicMock
from src.risk.position_sizer import PositionSizer

def test_position_sizer_with_macro_regime():
    with patch('src.risk.position_sizer.FredMacroProvider') as MockProvider:
        mock_provider = MockProvider.return_value
        mock_provider.get_regime.return_value = {"regime": "RISK_OFF", "confidence": 0.8}
        mock_provider.regime_multiplier.return_value = 0.5

        sizer = PositionSizer(base_risk_pct=0.02)

        # calculate_size: equity=1000, price=100, atr=5, stop_loss_atr_multiplier=2.0
        # Normal risk_amount = 1000 * 0.02 = 20.
        # But we have macro multiplier 0.5. So adjusted_risk = 0.02 * 0.5 = 0.01.
        # risk_amount = 1000 * 0.01 = 10.
        # stop distance = 5 * 2 = 10.
        # quantity = 10 / 10 = 1.0.
        res = sizer.calculate_size(1000.0, 100.0, 5.0)
        assert res["quantity"] == 1.0

def test_position_sizer_neutral_macro_regime_noop():
    with patch('src.risk.position_sizer.FredMacroProvider') as MockProvider:
        mock_provider = MockProvider.return_value
        mock_provider.get_regime.return_value = {"regime": "NEUTRAL", "confidence": 0.2}
        mock_provider.regime_multiplier.return_value = 0.8

        sizer = PositionSizer(base_risk_pct=0.02)

        res = sizer.calculate_size(1000.0, 100.0, 5.0)
        # Should ignore the 0.8 because regime is NEUTRAL or confidence < 0.5
        # risk_amount = 1000 * 0.02 = 20
        # stop_dist = 5 * 2 = 10.
        # quantity = 2.0
        assert res["quantity"] == 2.0

def test_position_sizer_macro_provider_failure():
    with patch('src.risk.position_sizer.FredMacroProvider', side_effect=Exception("Failed to init")):
        sizer = PositionSizer(base_risk_pct=0.02)
        assert sizer.macro_provider is None

        res = sizer.calculate_size(1000.0, 100.0, 5.0)
        # Should fallback to standard sizing 2.0
        assert res["quantity"] == 2.0

def test_position_sizer_macro_provider_method_failure():
    with patch('src.risk.position_sizer.FredMacroProvider') as MockProvider:
        mock_provider = MockProvider.return_value
        mock_provider.get_regime.side_effect = Exception("API down")

        sizer = PositionSizer(base_risk_pct=0.02)
        res = sizer.calculate_size(1000.0, 100.0, 5.0)

        # Should gracefully log error and fallback to standard sizing 2.0
        assert res["quantity"] == 2.0
