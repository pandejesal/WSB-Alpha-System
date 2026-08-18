import os
import yaml
import logging

logger = logging.getLogger(__name__)

class KillSwitch:
    """
    Reads config/ops_state.yaml and enforces the operational state.
    States: off | halt_new_orders | flat
    Fails closed on missing or unparseable state file (defaults to halt_new_orders).
    NEVER auto-flat.
    """
    def __init__(self, filepath: str = "config/ops_state.yaml"):
        self.filepath = filepath
        self.valid_states = {"off", "halt_new_orders", "flat"}

    def get_state(self) -> str:
        """
        Returns the current state. Fails closed (halt_new_orders) on error.
        """
        if not os.path.exists(self.filepath):
            logger.warning(f"Kill switch config {self.filepath} missing. Failing closed.")
            return "halt_new_orders"

        try:
            with open(self.filepath, "r") as f:
                data = yaml.safe_load(f)

            state = data.get("state", "halt_new_orders")
            if state not in self.valid_states:
                logger.error(f"Invalid kill switch state: {state}. Failing closed.")
                return "halt_new_orders"

            return state
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail closed safely
            logger.error(f"Failed to read kill switch config: {e}. Failing closed.")
            return "halt_new_orders"

    def set_state(self, new_state: str) -> None:
        """
        Updates the state file. NEVER set state to flat automatically in operations.
        (Only manual tools or telegram commands can trigger a state change via this,
        and even then, flat does NOT automatically execute market orders, it just sets the state).
        """
        if new_state not in self.valid_states:
            logger.error(f"Cannot set invalid kill switch state: {new_state}")
            return

        data = {"state": new_state}
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w") as f:
                yaml.dump(data, f)
            logger.info(f"Kill switch state set to: {new_state}")
        except Exception as e:  # noqa: BLE001 - Catching Exception to log error
            logger.error(f"Failed to write kill switch state: {e}")

    def can_trade(self) -> bool:
        """
        Returns True if new orders are allowed (state == off).
        """
        return self.get_state() == "off"
