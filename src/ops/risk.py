import json
import os
import yaml
import tempfile
from typing import Dict, Any

class KillSwitch:
    def __init__(self, state_file: str = "config/ops_state.yaml"):
        self.state_file = state_file

    def get_state(self) -> str:
        """
        Parses config/ops_state.yaml and returns its state.
        Returns 'off' if file doesn't exist.
        Expected states: 'off', 'halt_new_orders'
        """
        if not os.path.exists(self.state_file):
            return "off"
        try:
            with open(self.state_file, "r") as f:
                data = yaml.safe_load(f)
                return data.get("state", "off")
        except Exception:
            # Fails-closed: if we can't read state, assume halted
            return "halt_new_orders"

class DDTracker:
    def __init__(self, metrics_file: str = "docs/data/ops/metrics.json"):
        self.metrics_file = metrics_file
        self.metrics = self._load_metrics()
        self.hwm: Dict[str, float] = {}
        self.dd_from_hwm: Dict[str, float] = {}
        self._calculate_dd()

    def _load_metrics(self) -> Dict[str, Any]:
        if not os.path.exists(self.metrics_file):
            return {}
        try:
            with open(self.metrics_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _calculate_dd(self):
        # In a real scenario, this would compute over a time series in metrics.json.
        # Here we just parse the latest available HWM and compute DD from it.
        # This will be updated each run when P&L is calculated.
        if "sleeves" in self.metrics:
            for sleeve in self.metrics["sleeves"]:
                sleeve_id = sleeve["id"]
                self.hwm[sleeve_id] = sleeve.get("hwm", sleeve.get("equity", 0.0))
                self.dd_from_hwm[sleeve_id] = sleeve.get("dd_from_hwm", 0.0)

    def check_and_update_breaker(self, sleeve_id: str, current_equity: float, model_dd: float) -> bool:
        """
        Updates HWM and DD. Returns True if DD breaches 1.5x MODEL_DD.
        """
        if current_equity <= 0:
            return False

        current_hwm = self.hwm.get(sleeve_id, current_equity)
        if current_equity > current_hwm:
            self.hwm[sleeve_id] = current_equity
            self.dd_from_hwm[sleeve_id] = 0.0
            return False

        dd = (current_hwm - current_equity) / current_hwm
        self.dd_from_hwm[sleeve_id] = dd

        return dd > (1.5 * model_dd)

def update_ops_state(sleeve_id: str, status: str, state_file: str = "config/ops_state.yaml"):
    """
    Atomically updates config/ops_state.yaml.
    Usually used to set state to halt_new_orders when a breaker trips.
    """
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    data["state"] = status
    data["set_by"] = "workflow"
    data["reason"] = f"Breaker tripped for {sleeve_id}"

    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(state_file))
    with os.fdopen(fd, 'w') as f:
        yaml.dump(data, f)
    os.replace(temp_path, state_file)
