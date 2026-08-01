from typing import Dict, Any, List
import logging
from brokers.base_broker import Broker
from risk.position_sizer import PositionSizer
from risk.circuit_breakers import CircuitBreaker

class ExecutionBridge:
    """
    Links abstract signals to concrete paper broker executions while
    intercepting orders with the Risk Engine to ensure they are safe to execute.
    """
    def __init__(self, broker: Broker, position_sizer: PositionSizer, circuit_breaker: CircuitBreaker):
        self.logger = logging.getLogger(__name__)
        self.broker = broker
        self.sizer = position_sizer
        self.circuit_breaker = circuit_breaker
        # Track daily starting equity for circuit breaker evaluation
        self.daily_starting_equity = None
        self.peak_equity = None

    def update_equity_high_water_marks(self):
        """Updates internal equity tracking for circuit breakers."""
        current_equity = self.broker.get_account_balance()

        if self.daily_starting_equity is None:
            self.daily_starting_equity = current_equity

        if self.peak_equity is None or current_equity > self.peak_equity:
            self.peak_equity = current_equity

        return current_equity

    def execute_signal(self, ticker: str, signal: int, entry_price: float, atr: float, strategy_confidence: float = 1.0) -> Dict[str, Any]:
        """
        Executes a strategy signal (-1, 0, 1) through the risk engine and down to the broker.
        """
        if signal == 0:
            return {"status": "skipped", "reason": "Signal is flat."}

        current_equity = self.update_equity_high_water_marks()

        # 1. Circuit Breaker Check
        safety_check = self.circuit_breaker.check_safety(self.peak_equity, current_equity, self.daily_starting_equity)
        if not safety_check["safe"]:
            self.logger.warning(f"Order rejected by Circuit Breaker: {safety_check['status']}")
            return {"status": "rejected", "reason": safety_check["status"]}

        # 2. Risk Sizing
        sizing = self.sizer.calculate_size(current_equity, entry_price, atr, confidence_score=strategy_confidence)
        quantity = sizing.get("quantity", 0.0)

        if quantity <= 0:
            self.logger.warning(f"Order rejected by Position Sizer for {ticker}.")
            return {"status": "rejected", "reason": sizing.get("reason", "Zero quantity")}

        side = "buy" if signal == 1 else "sell" # Sell indicates shorting or closing long

        # 3. Execution
        self.logger.info(f"Routing {side} order for {quantity:.4f} {ticker} to Broker.")
        order_res = self.broker.submit_order(ticker, side, quantity)

        return {
            "status": "executed",
            "broker_response": order_res,
            "sizing_details": sizing
        }
