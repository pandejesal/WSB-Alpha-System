import argparse
import logging
from datetime import datetime, timezone

from src.ops.audit import write_artifact
from src.ops.killswitch import KillSwitch

logger = logging.getLogger(__name__)

def run_rehearsal(dry_run: bool = False):
    """
    Exercises tier-2 (repo edit of ops_state.yaml) and tier-3 (manual dispatch override).
    Restores state.
    Writes rehearsal log to docs/data/ops/kill_switch_rehearsal.json
    """
    ks = KillSwitch()

    # Store original
    original_state = ks.get_state()
    logger.info(f"Original state: {original_state}")

    # Tier-2 rehearsal (simulating repo edit)
    logger.info("Simulating tier-2: setting to halt_new_orders")
    if not dry_run:
        ks.set_state("halt_new_orders")

    tier2_state = ks.get_state() if not dry_run else "halt_new_orders"
    logger.info(f"Tier-2 state verified: {tier2_state}")

    # Tier-3 rehearsal (simulating manual dispatch halt-only override)
    logger.info("Simulating tier-3: setting to halt_only")
    if not dry_run:
        ks.set_state("halt_only")

    tier3_state = ks.get_state() if not dry_run else "halt_only"
    logger.info(f"Tier-3 state verified: {tier3_state}")

    # Restore
    logger.info(f"Restoring original state: {original_state}")
    if not dry_run:
        ks.set_state(original_state)

    final_state = ks.get_state() if not dry_run else original_state

    rehearsal_record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dry_run": dry_run,
        "original_state": original_state,
        "tier2_tested": tier2_state == "halt_new_orders",
        "tier3_tested": tier3_state == "halt_only",
        "restored": final_state == original_state,
        "note": "halt_only stops new orders; it does NOT flatten positions (audit F5).",
    }

    if not dry_run:
        write_artifact("docs/data/ops/kill_switch_rehearsal.json", rehearsal_record)
        logger.info("Rehearsal record written.")
    else:
        logger.info(f"Dry-run rehearsal record: {rehearsal_record}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run without persisting changes")
    args = parser.parse_args()

    run_rehearsal(dry_run=args.dry_run)
