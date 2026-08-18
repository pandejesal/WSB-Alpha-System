import json
import logging
import os

import requests

from src.utils.config import config

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        try:
            self.bot_token = config.api_keys.telegram_bot_token.get_secret_value()
        except AttributeError:
            self.bot_token = config.api_keys.telegram_bot_token

        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.approved_file = "strategies/approved.json"

    def send_message(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials (bot token or chat ID) missing. Cannot send message.")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            res.raise_for_status()
            return True
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.error(f"Telegram send failed: {e}")
            return False

    def send_daily_summary(self, trades: int, equity: float, pnl_pct: float):
        msg = (
            f"📈 <b>Daily Trade Summary</b> 📈\n\n"
            f"Executed Trades: {trades}\n"
            f"Total Equity: ${equity:,.2f}\n"
            f"Daily P&L: {pnl_pct*100:.2f}%\n"
        )
        self.send_message(msg)

    def request_strategy_approval(self, strategy_id: str, metrics: dict):
        msg = (
            f"🤖 <b>Strategy Approval Required</b> 🤖\n\n"
            f"Strategy ID: <code>{strategy_id}</code>\n"
            f"Sharpe: {metrics.get('sharpe', 0):.2f}\n"
            f"Profit Factor: {metrics.get('profit_factor', 0):.2f}\n\n"
            f"Reply with `/approve {strategy_id}` or `/reject {strategy_id}`"
        )
        self.send_message(msg)


    def send_alert(self, level: str, message: str) -> bool:
        """
        Severity ladder: INFO, WARN, CRITICAL
        """
        prefix = ""
        if level == "INFO":
            prefix = "ℹ️ [INFO]"
        elif level == "WARN":
            prefix = "⚠️ [WARN]"
        elif level == "CRITICAL":
            prefix = "🚨 [CRITICAL]"

        return self.send_message(f"{prefix} {message}")

    def poll_updates(self, offset: int = None) -> list:
        """
        Polls for updates (commands)
        """
        if not self.bot_token:
            return []

        url = f"{self.base_url}/getUpdates"
        params = {"timeout": 10}
        if offset:
            params["offset"] = offset

        try:
            res = requests.get(url, params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            if data.get("ok"):
                return data.get("result", [])
            return []
        except Exception as e:
            logger.error(f"Telegram poll failed: {e}")
            return []

    def handle_command(self, text: str) -> str:
        """
        Basic implementation of command handling.
        For production, this would be hooked up to a webhook or polling loop.
        """
        if not text.startswith('/'):
            return "Ignored"

        parts = text.split(' ')
        if len(parts) != 2:
            return "Invalid format"

        cmd, strat_id = parts[0], parts[1]

        # Load approved strategies
        approved = []
        if os.path.exists(self.approved_file):
            try:
                with open(self.approved_file, "r") as f:
                    approved = json.load(f)
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                logger.debug(f"Failed to read approved file: {e}")

        if cmd == '/approve':
            if strat_id not in approved:
                approved.append(strat_id)
                with open(self.approved_file, "w") as f:
                    json.dump(approved, f)
            return f"Approved strategy {strat_id}"
        elif cmd == '/reject':
            if strat_id in approved:
                approved.remove(strat_id)
                with open(self.approved_file, "w") as f:
                    json.dump(approved, f)
            return f"Rejected strategy {strat_id}"

        return "Unknown command"

    def is_approved(self, strategy_id: str) -> bool:
        if not os.path.exists(self.approved_file):
            return False
        try:
            with open(self.approved_file, "r") as f:
                approved = json.load(f)
            return strategy_id in approved
        except Exception:  # noqa: BLE001 - Catching Exception to fail gracefully
            return False
