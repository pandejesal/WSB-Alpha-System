import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TradingHaltedException(Exception):
    pass

class CircuitBreaker:
    def __init__(self, daily_limit: float = 0.05, weekly_limit: float = 0.10, total_limit: float = 0.15):
        self.daily_limit = daily_limit
        self.weekly_limit = weekly_limit
        self.total_limit = total_limit

        # State tracking (would be loaded from DB/JSON in prod)
        self.starting_equity_daily = None
        self.starting_equity_weekly = None
        self.starting_equity_total = None

    def initialize_state(self, current_equity: float):
        if self.starting_equity_daily is None: self.starting_equity_daily = current_equity
        if self.starting_equity_weekly is None: self.starting_equity_weekly = current_equity
        if self.starting_equity_total is None: self.starting_equity_total = current_equity

    def _send_emergency_alert(self, msg: str):
        # Implementation to send Telegram alert
        logger.critical(f"EMERGENCY ALERT: {msg}")
        try:
            from src.monitoring.telegram_bot import TelegramBot
            bot = TelegramBot()
            bot.send_message(f"🚨 <b>EMERGENCY HALT</b> 🚨\n\n{msg}")
        except Exception as e:
            logger.error(f"Failed to send emergency Telegram alert: {e}")

    def check_circuit_breakers(self, get_equity_func) -> bool:
        """
        Runs the circuit breaker checks.
        Requires a callable that fetches the current equity.
        Enforces a FAILS-CLOSED policy.
        """
        try:
            current_equity = get_equity_func()
            if current_equity is None or current_equity <= 0:
                raise ValueError("Invalid equity returned")
        except Exception as e:
            msg = f"FAILS-CLOSED TRIGGERED: Unable to retrieve account equity. Error: {e}"
            self._send_emergency_alert(msg)
            raise TradingHaltedException(msg)

        self.initialize_state(current_equity)

        daily_drop = (self.starting_equity_daily - current_equity) / self.starting_equity_daily
        weekly_drop = (self.starting_equity_weekly - current_equity) / self.starting_equity_weekly
        total_drop = (self.starting_equity_total - current_equity) / self.starting_equity_total

        if daily_drop > self.daily_limit:
            msg = f"Daily Loss Limit breached ({daily_drop*100:.2f}%). Trading halted."
            self._send_emergency_alert(msg)
            raise TradingHaltedException(msg)

        if weekly_drop > self.weekly_limit:
            msg = f"Weekly Drawdown Limit breached ({weekly_drop*100:.2f}%). Trading halted."
            self._send_emergency_alert(msg)
            raise TradingHaltedException(msg)

        if total_drop > self.total_limit:
            msg = f"Total Portfolio Drawdown Limit breached ({total_drop*100:.2f}%). Liquidating all positions to cash."
            self._send_emergency_alert(msg)
            # Signal the system to liquidate
            raise TradingHaltedException(msg)

        return True
