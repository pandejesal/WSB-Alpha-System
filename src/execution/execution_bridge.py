from typing import Any

from src.execution.base_broker import BaseBroker as Broker
from src.risk.circuit_breakers import CircuitBreaker
from src.risk.position_sizer import PositionSizer


class ExecutionBridge:
    def __init__(self, broker: Broker, position_sizer: PositionSizer, circuit_breaker: CircuitBreaker):
        self.broker = broker
        self.sizer = position_sizer
        self.circuit_breaker = circuit_breaker
        self.daily_starting_equity = None
        self.peak_equity = None

    def execute_signal(self, ticker: str, signal: int, entry_price: float, atr: float, strategy_confidence: float = 100.0, regime: str = "normal") -> dict[str, Any]:
        if signal == 0:
            return {"status": "skipped", "reason": "Flat"}
        balance = self.broker.get_account_balance()
        current_equity = balance['equity'] if isinstance(balance, dict) else float(balance)
        if not self.daily_starting_equity:
            self.daily_starting_equity = current_equity
        if not self.peak_equity or current_equity > self.peak_equity:
            self.peak_equity = current_equity


        try:
            if not self.circuit_breaker.starting_equity_daily and self.daily_starting_equity:
                self.circuit_breaker.starting_equity_daily = self.daily_starting_equity
            self.circuit_breaker.check_circuit_breakers(lambda: current_equity)
        except Exception as e:
            return {"status": "rejected", "reason": str(e)}


        sizing = self.sizer.calculate_size(current_equity, entry_price, atr, confidence_score=strategy_confidence, regime=regime)
        if sizing.get("quantity", 0) <= 0:
            return {"status": "rejected", "reason": "Zero quantity"}

        side = "buy" if signal == 1 else "sell"
        order_res = self.broker.place_order(ticker, qty=sizing["quantity"], side=side, order_type="market")
        return {"status": "executed", "broker_response": order_res}
