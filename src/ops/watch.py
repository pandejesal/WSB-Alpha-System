import json
import logging
import os
import sys

from src.monitoring.telegram_bot import TelegramBot
from src.ops.killswitch import KillSwitch

logger = logging.getLogger(__name__)

OFFSET_FILE = "docs/data/ops/watch_offset.json"

def main():
    """
    Polls Telegram for /kill, /halt, /flat commands.
    Updates config/ops_state.yaml appropriately.
    """
    bot = TelegramBot()
    ks = KillSwitch()

    offset = None
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r") as f:
                data = json.load(f)
                offset = data.get("offset")
        except Exception as e:  # noqa: BLE001 - Ignore corrupt offset file
            logger.debug(f"Could not read offset file: {e}")

    updates = bot.poll_commands(offset=offset, timeout=30)

    if not updates:
        logger.info("No new Telegram commands found.")
        sys.exit(0)

    max_update_id = offset if offset else 0
    state_changed = False
    new_state = None

    for update in updates:
        update_id = update.get("update_id")
        if update_id is not None and update_id > max_update_id:
            max_update_id = update_id

        message = update.get("message")
        if not message:
            continue

        text = message.get("text", "").strip()
        if not text.startswith("/"):
            continue

        # Simple command parsing
        if text.startswith(("/kill", "/halt")):
            new_state = "halt_new_orders"
            state_changed = True
        elif text.startswith("/flat"):
            new_state = "flat"
            state_changed = True
        elif text.startswith(("/resume", "/off")):
            new_state = "off"
            state_changed = True

    if state_changed and new_state:
        logger.info(f"Command received. Updating killswitch to {new_state}.")
        ks.set_state(new_state)
        bot.send_alert("WARN" if new_state != "off" else "INFO", f"Kill switch state changed to: {new_state}")

    # Save new offset (+1 so we don't process the same message again)
    try:
        os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
        with open(OFFSET_FILE, "w") as f:
            json.dump({"offset": max_update_id + 1}, f)
    except Exception as e:  # noqa: BLE001 - Ignore failure to write offset
        logger.error(f"Failed to write offset file: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
