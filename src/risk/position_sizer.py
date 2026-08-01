from typing import Dict, Any
import logging

class PositionSizer:
    def __init__(self, base_risk_pct: float = 0.02, max_notional_leverage: float = 1.0):
        self.logger = logging.getLogger(__name__)
        self.base_risk_pct = base_risk_pct
        self.max_notional_leverage = max_notional_leverage

    def calculate_size(self, account_equity: float, entry_price: float, atr: float, stop_loss_atr_multiplier: float = 2.0, confidence_score: float = 100.0) -> Dict[str, Any]:
        if account_equity <= 0 or entry_price <= 0 or atr <= 0:
            return {"quantity": 0.0, "reason": "Invalid inputs"}

        normalized_confidence = min(max(confidence_score / 100.0, 0.1), 2.0)
        adjusted_risk_pct = self.base_risk_pct * normalized_confidence
        risk_amount = account_equity * adjusted_risk_pct

        stop_loss_dollar_distance = atr * stop_loss_atr_multiplier
        if stop_loss_dollar_distance == 0: return {"quantity": 0.0}

        quantity = risk_amount / stop_loss_dollar_distance
        notional_value = quantity * entry_price
        max_notional_allowed = account_equity * self.max_notional_leverage

        if notional_value > max_notional_allowed:
            quantity = max_notional_allowed / entry_price

        return {"quantity": quantity, "notional_value": quantity * entry_price, "reason": "Success"}
