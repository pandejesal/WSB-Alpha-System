import logging
import os

import yaml

logger = logging.getLogger(__name__)

ALLOWED_TOP_KEYS = {"state", "sleeves"}


class KillSwitch:
    """
    Reads config/ops_state.yaml and enforces the operational state.
    States: off | halt_new_orders | flat
    Fails closed on missing or unparseable state file (defaults to halt_new_orders).
    NEVER auto-flat.
    Schema: only ALLOWED_TOP_KEYS allowed; extra keys -> fail-closed.
    """
    def __init__(self, filepath: str = "config/ops_state.yaml"):
        self.filepath = filepath
        self.valid_states = {"off", "halt_new_orders", "flat"}

    def get_state(self) -> str:
        """
        Returns the current state. Fails closed (halt_new_orders) on error.
        Rejects YAML with extra top-level keys (strict schema).
        """
        if not os.path.exists(self.filepath):
            logger.warning(f"Kill switch config {self.filepath} missing. Failing closed.")
            return "halt_new_orders"

        try:
            with open(self.filepath, "r") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                logger.error(f"Invalid kill switch YAML type {type(data).__name__}. Failing closed.")
                return "halt_new_orders"

            extra = set(data.keys()) - ALLOWED_TOP_KEYS
            if extra:
                logger.error(f"Invalid kill switch extra keys {extra}. Failing closed.")
                return "halt_new_orders"

            state = data.get("state", "halt_new_orders")
            if state not in self.valid_states:
                logger.error(f"Invalid kill switch state: {state}. Failing closed.")
                return "halt_new_orders"

            return state
        except Exception as e:
            logger.error(f"Failed to read kill switch config: {e}. Failing closed.")
            return "halt_new_orders"

    def set_state(self, new_state: str) -> None:
        """
        Updates the state file. NEVER set state to flat automatically in operations.
        (Only manual tools or telegram commands can trigger a state change via this,
        and even then, flat does NOT automatically execute market orders, it just sets the state).

        S2: single-writer, atomic, sleeve-preserving. Reads the existing file and
        keeps allowed keys (e.g. ``sleeves``) so a crash or concurrent rewrite can
        never erase sleeve states; writes via tmp file + os.replace so readers
        never observe a torn file.
        """
        if new_state not in self.valid_states:
            logger.error(f"Cannot set invalid kill switch state: {new_state}")
            return

        try:
            dirname = os.path.dirname(self.filepath) or "."
            os.makedirs(dirname, exist_ok=True)
            data = {}
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r") as f:
                        loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        data = {k: v for k, v in loaded.items() if k in ALLOWED_TOP_KEYS}
                    else:
                        logger.error(
                            f"Kill switch file has non-dict YAML ({type(loaded).__name__}); "
                            "rewriting with state only (fail-closed)."
                        )
                except (OSError, yaml.YAMLError) as e:
                    logger.error(f"Failed to read existing kill switch file, rewriting state only: {e}")
                    data = {}
            data["state"] = new_state
            tmp_path = self.filepath + f".tmp.{os.getpid()}"
            with open(tmp_path, "w") as f:
                yaml.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.filepath)
            logger.info(f"Kill switch state set to: {new_state}")
        except (OSError, yaml.YAMLError) as e:
            logger.error(f"Failed to write kill switch state: {e}")

    def can_trade(self) -> bool:
        """
        Returns True if new orders are allowed (state == off).
        """
        return self.get_state() == "off"

    def get_sleeve_state(self, sleeve_id: str) -> str:
        """
        Returns per-sleeve state from the ``sleeves`` mapping in the state file.
        Unknown sleeve -> global state (a global halt still halts it).
        Any file error -> "halt_new_orders" (fail closed).
        """
        try:
            with open(self.filepath, "r") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                sleeves = data.get("sleeves", {})
                if isinstance(sleeves, dict) and sleeve_id in sleeves:
                    state = sleeves[sleeve_id]
                    if state in self.valid_states:
                        return state
            return self.get_state()
        except Exception:
            logger.error("Failed to read sleeve state; failing closed.")
            return "halt_new_orders"


def dual_gate_allows_trading(live_enabled: bool, filepath: str = "config/ops_state.yaml") -> tuple[bool, str]:
    """
    Conjunctive dual-flag gate: KillSwitch.can_trade() AND LIVE_TRADING_ENABLED.
    Returns (allowed, reason). Logs CRITICAL on disagreement (fail-closed).
    Only (can_trade=True and live_enabled=True) proceeds; all else abort.
    """
    ks = KillSwitch(filepath=filepath)
    can = ks.can_trade()
    allowed = can and bool(live_enabled)
    if can != bool(live_enabled):
        logger.critical(
            f"Dual-flag disagreement: can_trade={can} LIVE_TRADING_ENABLED={live_enabled} — aborting (fail-closed)."
        )
        return False, f"CRITICAL dual-flag disagreement can_trade={can} live={live_enabled}"
    if not allowed:
        return False, f"Dual gate blocked: can_trade={can} live={live_enabled}"
    return True, ""
