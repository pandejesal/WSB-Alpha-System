from typing import Dict, Any
import logging
import math

class PositionSizer:
    """
    Intelligent adaptive position sizing engine.
    Ensures fractional risk per trade, volatility parity (via ATR), and purchasing power limits.
    """
    def __init__(self, base_risk_pct: float = 0.02, max_notional_leverage: float = 1.0):
        self.logger = logging.getLogger(__name__)
        self.base_risk_pct = base_risk_pct
        self.max_notional_leverage = max_notional_leverage

    def calculate_size(self, account_equity: float, entry_price: float, atr: float, stop_loss_atr_multiplier: float = 2.0, confidence_score: float = 1.0) -> Dict[str, Any]:
        """
        Calculates position size using fractional compounding risk parity.
        Formula: Quantity = (Account_Equity * Base_Risk * Confidence) / (ATR * Multiplier)
        """
        if account_equity <= 0 or entry_price <= 0 or atr <= 0:
            return {"quantity": 0.0, "reason": "Invalid pricing or equity inputs."}

        # Dynamic risk based on strategy confidence
        normalized_confidence = min(max(confidence_score / 100.0, 0.1), 2.0)
        adjusted_risk_pct = self.base_risk_pct * normalized_confidence
        risk_amount = account_equity * adjusted_risk_pct

        # Risk Parity: How much dollar movement represents our stop loss?
        stop_loss_dollar_distance = atr * stop_loss_atr_multiplier

        if stop_loss_dollar_distance == 0:
            return {"quantity": 0.0, "reason": "Stop loss distance is zero."}

        quantity = risk_amount / stop_loss_dollar_distance

        # Purchasing Power Guardrail (Micro-Account constraint: max leverage)
        notional_value = quantity * entry_price
        max_notional_allowed = account_equity * self.max_notional_leverage

        if notional_value > max_notional_allowed:
            quantity = max_notional_allowed / entry_price
            self.logger.info(f"Position size capped by max notional leverage ({self.max_notional_leverage}x).")

        return {
            "quantity": quantity,
            "notional_value": quantity * entry_price,
            "risk_amount": risk_amount,
            "adjusted_risk_pct": adjusted_risk_pct,
            "reason": "Success"
        }
