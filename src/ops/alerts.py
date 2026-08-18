import logging
from src.monitoring.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)

class Alerts:
    """
    Telegram severity ladder + daily digest.
    Token/chat ID from env or GH secrets ONLY (never hardcoded, handled by TelegramBot init).
    """
    def __init__(self):
        self.bot = TelegramBot()

    def send_info(self, message: str) -> bool:
        """Sends an INFO level alert."""
        return self.bot.send_alert("INFO", message)

    def send_warn(self, message: str) -> bool:
        """Sends a WARN level alert."""
        return self.bot.send_alert("WARN", message)

    def send_critical(self, message: str) -> bool:
        """Sends a CRITICAL level alert."""
        return self.bot.send_alert("CRITICAL", message)

    def send_daily_digest(self, summary_data: dict) -> bool:
        """
        Sends a compact daily digest.
        Expected keys: trades, equity, pnl_pct
        """
        trades = summary_data.get("trades", 0)
        equity = summary_data.get("equity", 0.0)
        pnl_pct = summary_data.get("pnl_pct", 0.0)

        try:
            self.bot.send_daily_summary(trades, equity, pnl_pct)
            return True
        except Exception as e:
            logger.error(f"Failed to send daily digest: {e}")
            return False
