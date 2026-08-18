import json
import logging
import os

from src.monitoring.telegram_bot import TelegramBot

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self):
        self.bot = TelegramBot()

    def send(self, severity: str, text: str) -> bool:
        """
        Sends an alert with severity INFO, WARN, or CRITICAL.
        """
        return self.bot.send_alert(severity, text)

    def compile_daily_digest(self) -> None:
        """
        Compiles the daily digest from artifacts and sends it as INFO.
        If digest sending fails, degrades to file only (alerts.json).
        """
        try:
            plan_path = "docs/data/ops/plan.json"
            fills_path = "docs/data/ops/fills.json"

            num_orders = 0
            if os.path.exists(plan_path):
                with open(plan_path, "r") as f:
                    plan = json.load(f)
                    num_orders = len(plan.get("targets", []))

            fills = []
            if os.path.exists(fills_path):
                with open(fills_path, "r") as f:
                    fills = json.load(f)

            num_fills = len(fills)

            text = (
                f"<b>Daily Ops Digest</b>\n"
                f"Planned orders: {num_orders}\n"
                f"Filled orders: {num_fills}\n"
                f"All systems nominal."
            )
            success = self.send("INFO", text)

            # Degrade to file if Telegram fails
            if not success:
                self._write_fallback_alert("INFO", text)
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.error(f"Failed to compile daily digest: {e}")

    def _write_fallback_alert(self, severity: str, text: str) -> None:
        filepath = "docs/data/ops/alerts.json"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        alerts = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    alerts = json.load(f)
            except Exception as e:  # noqa: BLE001 - Catching Exception to log error
                logger.error(f"Failed to read alerts fallback file: {e}")

        alerts.append({
            "severity": severity,
            "text": text,
            "ts": "failed_to_send"
        })

        with open(filepath, "w") as f:
            json.dump(alerts, f, indent=2)
