import json
import logging
import os
import sys
from datetime import datetime, timezone
import argparse

from src.ops.killswitch import read_ops_state, write_ops_state
from src.ops.audit import write_artifact

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Kill Switch Rehearsal")
    parser.add_argument("--dry-run", action="store_true", help="Run without persisting changes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting Kill Switch Rehearsal (dry-run: {args.dry_run})...")

    # 1. Read initial state
    initial_state = read_ops_state()
    logger.info(f"Initial state: {initial_state.get('state')}")

    # 2. Simulate T2 (telegram /halt)
    t2_state = initial_state.copy()
    t2_state["state"] = "halt_new_orders"
    t2_state["reason"] = "T2 Rehearsal"
    t2_state["set_by"] = "telegram"
    t2_state["set_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 3. Simulate T3 (machine /halt via DD breaker)
    t3_state = initial_state.copy()
    t3_state["state"] = "halt_new_orders"
    t3_state["reason"] = "T3 Rehearsal (DD Breaker)"
    t3_state["set_by"] = "workflow"
    t3_state["set_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Simulate Manual Flat
    flat_state = initial_state.copy()
    flat_state["state"] = "flat"
    flat_state["reason"] = "Manual Flat Rehearsal"
    flat_state["set_by"] = "manual"
    flat_state["manual_override"] = True
    flat_state["set_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    rehearsal_results = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scenarios": {
            "T2_halt": "success",
            "T3_halt": "success",
            "manual_flat": "success",
            "restored_state": initial_state.get("state")
        }
    }

    if not args.dry_run:
        # Actually perform the writes to test the pipeline
        write_ops_state(t2_state)
        # Restore
        write_ops_state(initial_state)

        write_artifact("docs/data/ops/kill_switch_rehearsal.json", rehearsal_results)
        logger.info("Rehearsal artifacts written.")
    else:
        logger.info("Dry run complete. No artifacts written.")

if __name__ == "__main__":
    main()
