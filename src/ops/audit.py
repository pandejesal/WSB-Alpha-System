import json
import os
import tempfile
from datetime import datetime
from typing import Any


def generate_client_order_id(run_id: str, sleeve_id: str, ticker: str, seq: int) -> str:
    """
    Generates a deterministic client_order_id for idempotency.
    Format: <run_id>-<sleeve_id>-<ticker>-<seq>
    """
    return f"{run_id}-{sleeve_id}-{ticker}-{seq}"

def write_artifact(filename: str, data: Any) -> None:
    """
    Atomically writes JSON files to docs/data/ops/ using a temporary file.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filename))
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, filename)

class AuditLogger:
    """
    Appends events to docs/data/ops/audit.jsonl.
    """
    def __init__(self, log_file: str = "docs/data/ops/audit.jsonl"):
        self.log_file = log_file

    def log_event(self, run_id: str, event: str, entity: str, entity_id: str, payload: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        record = {
            "run_id": run_id,
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "entity": entity,
            "id": entity_id,
            "payload": payload
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
