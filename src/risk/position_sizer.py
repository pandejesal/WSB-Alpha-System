import logging
from typing import Any

from src.risk.fred_macro_provider import FredMacroProvider


class RegimeDetector:
    @staticmethod
    def detect_regime(gk_vol: float) -> str:
        if gk_vol < 0.20:
            return "low_volatility"
        elif gk_vol < 0.50:
            return "normal"
        else:
            return "high_volatility"

    @staticmethod
    def get_risk_multiplier(regime: str) -> float:
        return {
            "low_volatility": 1.5,
            "normal": 1.0,
            "high_volatility": 0.5
        }.get(regime, 1.0)

class PositionSizer:
    def __init__(self, base_risk_pct: float = 0.02, max_notional_leverage: float = 1.0):
        self.logger = logging.getLogger(__name__)
        self.base_risk_pct = base_risk_pct
        self.max_notional_leverage = max_notional_leverage

        # Instantiate FRED provider safely
        try:
            self.macro_provider = FredMacroProvider()
        except Exception as e:
            self.logger.warning(f"Could not initialize FredMacroProvider: {e}")
            self.macro_provider = None

    def calculate_size(self, account_equity: float, entry_price: float, atr: float, stop_loss_atr_multiplier: float = 2.0, confidence_score: float = 100.0, regime: str = "normal") -> dict[str, Any]:
        if account_equity <= 0 or entry_price <= 0 or atr <= 0:
            return {"quantity": 0.0, "reason": "Invalid inputs"}

        normalized_confidence = min(max(confidence_score / 100.0, 0.1), 2.0)
        vol_regime_multiplier = RegimeDetector.get_risk_multiplier(regime)

        # Sub-feature 4f: Macro regime position-size modifier
        macro_multiplier = 1.0
        if self.macro_provider:
            try:
                macro_regime_data = self.macro_provider.get_regime()
                if macro_regime_data.get("regime") != "NEUTRAL" and macro_regime_data.get("confidence", 0.0) >= 0.5:
                    macro_multiplier = self.macro_provider.regime_multiplier()
            except Exception as e:
                self.logger.warning(f"Error fetching macro regime multiplier: {e}. Defaulting to 1.0.")

        adjusted_risk_pct = self.base_risk_pct * normalized_confidence * vol_regime_multiplier * macro_multiplier
        risk_amount = account_equity * adjusted_risk_pct

        stop_loss_dollar_distance = atr * stop_loss_atr_multiplier
        if stop_loss_dollar_distance == 0: return {"quantity": 0.0}

        quantity = risk_amount / stop_loss_dollar_distance
        notional_value = quantity * entry_price
        max_notional_allowed = account_equity * self.max_notional_leverage

        if notional_value > max_notional_allowed:
            quantity = max_notional_allowed / entry_price

        return {"quantity": quantity, "notional_value": quantity * entry_price, "reason": "Success"}
