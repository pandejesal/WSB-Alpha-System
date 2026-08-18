import logging
import sys
from datetime import datetime, timezone

from src.monitoring.telegram_bot import TelegramBot
from src.ops.killswitch import read_ops_state, write_ops_state

logger = logging.getLogger(__name__)

def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting ops watch poll...")

    bot = TelegramBot()
    updates = bot.poll_updates()

    if not updates:
        logger.info("No updates found.")
        return

    # Process updates looking for commands
    latest_command = None
    for update in updates:
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        if text.startswith("/"):
            latest_command = text

    if not latest_command:
        return

    logger.info(f"Received command: {latest_command}")

    state = read_ops_state()
    changed = False

    if latest_command == "/kill" or latest_command == "/halt":
        if state.get("state") != "halt_new_orders":
            state["state"] = "halt_new_orders"
            state["reason"] = f"Received {latest_command} via Telegram"
            state["set_by"] = "telegram"
            state["set_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            changed = True
    elif latest_command == "/flat":
        if state.get("state") != "flat":
            state["state"] = "flat"
            state["reason"] = "Received /flat via Telegram"
            state["set_by"] = "telegram"
            # Note: manual_override must be true to actually flatten, but we set state here
            state["manual_override"] = True
            state["set_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            changed = True
    elif latest_command == "/resume":
         if state.get("state") != "off":
            state["state"] = "off"
            state["reason"] = "Received /resume via Telegram"
            state["set_by"] = "telegram"
            state["manual_override"] = False
            state["set_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            changed = True

    if changed:
        logger.info(f"Updating ops state to: {state['state']}")
        write_ops_state(state)
        bot.send_message(f"✅ Ops state updated to `{state['state']}`")

if __name__ == "__main__":
    main()
