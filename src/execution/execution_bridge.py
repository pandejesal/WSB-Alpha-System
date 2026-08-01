from typing import Dict, Any
from src.execution.base_broker import Broker
from src.risk.position_sizer import PositionSizer
from src.risk.circuit_breakers import CircuitBreaker

class ExecutionBridge:
    def __init__(self, broker: Broker, position_sizer: PositionSizer, circuit_breaker: CircuitBreaker):
        self.broker = broker
        self.sizer = position_sizer
        self.circuit_breaker = circuit_breaker
        self.daily_starting_equity = None
        self.peak_equity = None

    def execute_signal(self, ticker: str, signal: int, entry_price: float, atr: float, strategy_confidence: float = 100.0) -> Dict[str, Any]:
        if signal == 0: return {"status": "skipped", "reason": "Flat"}
        current_equity = self.broker.get_account_balance()
        if not self.daily_starting_equity: self.daily_starting_equity = current_equity
        if not self.peak_equity or current_equity > self.peak_equity: self.peak_equity = current_equity

        safety = self.circuit_breaker.check_safety(self.peak_equity, current_equity, self.daily_starting_equity)
        if not safety["safe"]: return {"status": "rejected", "reason": safety["status"]}

        sizing = self.sizer.calculate_size(current_equity, entry_price, atr, confidence_score=strategy_confidence)
        if sizing.get("quantity", 0) <= 0: return {"status": "rejected", "reason": "Zero quantity"}

        side = "buy" if signal == 1 else "sell"
        order_res = self.broker.submit_order(ticker, side, sizing["quantity"])
        return {"status": "executed", "broker_response": order_res}
