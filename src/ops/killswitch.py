import logging
import os
import yaml

logger = logging.getLogger(__name__)

STATE_FILE = "config/ops_state.yaml"

def read_ops_state() -> dict:
    """
    Reads the operations state from config/ops_state.yaml.
    Fails-closed on missing/unparseable file (defaults to halt_new_orders).
    """
    if not os.path.exists(STATE_FILE):
        logger.error(f"Kill switch state file {STATE_FILE} not found. Failing closed.")
        return {"state": "halt_new_orders", "manual_override": False}

    try:
        with open(STATE_FILE, "r") as f:
            state = yaml.safe_load(f)
            if not isinstance(state, dict):
                raise ValueError("State is not a dictionary")
            return state
    except Exception as e:
        logger.error(f"Failed to parse {STATE_FILE}: {e}. Failing closed.")
        return {"state": "halt_new_orders", "manual_override": False}

def write_ops_state(state: dict) -> None:
    """
    Writes the operations state to config/ops_state.yaml.
    """
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        yaml.dump(state, f, default_flow_style=False)

def check_new_orders_allowed() -> bool:
    """
    Returns True if new orders are allowed (state is 'off').
    """
    state = read_ops_state()
    return state.get("state") == "off"

def check_flat_state() -> bool:
    """
    Returns True if the system should be flattened.
    Requires manual_override: true to be valid.
    """
    state = read_ops_state()
    if state.get("state") == "flat":
        if state.get("manual_override", False) is True:
            return True
        else:
            logger.warning("Kill switch state is 'flat' but manual_override is False. Ignoring flat command.")
            return False
    return False

def set_halt_state(reason: str = "Automated halt triggered") -> None:
    """
    Updates the state to halt_new_orders.
    """
    state = read_ops_state()
    state["state"] = "halt_new_orders"
    state["reason"] = reason
    state["set_by"] = "workflow"
    from datetime import datetime, timezone
    state["set_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    write_ops_state(state)
