import json
import os
import tempfile

import pandas as pd

from .engine import run_signals
from .schemas import SignalsReport


def generate_signals(run_id: str, date: str, mode: str, market_data: dict[str, pd.DataFrame], output_dir: str = "docs/data/ops") -> SignalsReport:
    """Public API for generating signals and writing atomic artifacts."""
    report = run_signals(run_id, date, mode, market_data)

    # Ensure ops directory exists
    # ops_dir parameter used
    os.makedirs(output_dir, exist_ok=True)

    signals_file = os.path.join(output_dir, "signals.json")

    # Atomic write pattern
    fd, temp_path = tempfile.mkstemp(dir=output_dir)
    with os.fdopen(fd, 'w') as f:
        f.write(report.model_dump_json(indent=2))

    os.replace(temp_path, signals_file)

    # Audit log event append
    audit_file = os.path.join(output_dir, "audit.jsonl")
    audit_event = {
        "run_id": run_id,
        "ts": pd.Timestamp.utcnow().isoformat(),
        "event": "SIGNALS_GENERATED",
        "entity": "SignalsEngine",
        "id": run_id,
        "payload": {
            "mode": mode,
            "sleeves_evaluated": len(report.sleeves)
        }
    }
    with open(audit_file, "a") as f:
        f.write(json.dumps(audit_event) + "\n")

    return report
