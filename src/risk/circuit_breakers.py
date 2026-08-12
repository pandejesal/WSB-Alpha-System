import logging

logger = logging.getLogger(__name__)

class TradingHaltedException(Exception):
    pass

class CircuitBreaker:
    def __init__(self, regime="normal", daily_limit: float | None = None, weekly_limit: float | None = None, total_limit: float | None = None):
        base_daily = 0.05
        base_weekly = 0.10
        base_total = 0.15

        regime_scale = {
            "low_volatility": 1.2,
            "normal": 1.0,
            "high_volatility": 0.6
        }.get(regime, 1.0)

        self.daily_limit = daily_limit if daily_limit is not None else base_daily * regime_scale
        self.weekly_limit = weekly_limit if weekly_limit is not None else base_weekly * regime_scale
        self.total_limit = total_limit if total_limit is not None else base_total * regime_scale

        self.starting_equity_daily = None
        self.starting_equity_weekly = None
        self.starting_equity_total = None

    def initialize_state(self, current_equity: float):
        if self.starting_equity_daily is None:
            self.starting_equity_daily = current_equity
        if self.starting_equity_weekly is None:
            self.starting_equity_weekly = current_equity
        if self.starting_equity_total is None:
            self.starting_equity_total = current_equity

    def _send_emergency_alert(self, msg: str):
        logger.critical(f"EMERGENCY ALERT: {msg}")
        try:
            from src.monitoring.telegram_bot import TelegramBot
            bot = TelegramBot()
            bot.send_message(f"🚨 <b>EMERGENCY HALT</b> 🚨\n\n{msg}")
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.error(f"Failed to send emergency Telegram alert: {e}")

    def check_circuit_breakers(self, get_equity_func) -> bool:
        try:
            current_equity = get_equity_func()
            if current_equity is None or current_equity <= 0:
                raise ValueError("Invalid equity returned")
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
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
            raise TradingHaltedException(msg)

        return True
