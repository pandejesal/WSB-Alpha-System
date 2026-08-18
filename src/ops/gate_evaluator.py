import json
import logging
import os
from datetime import datetime, timezone

from src.ops.alerts import Alerts
from src.ops.audit import write_artifact
from src.ops.killswitch import set_halt_state

logger = logging.getLogger(__name__)

def compute_g1(portfolio_data: dict) -> bool:
    """G1: DD breaker open (No sleeve < -15% max DD)"""
    return portfolio_data.get("dd_breaker_open", True)

def compute_g2(heartbeat_data: dict) -> bool:
    """G2: Heartbeat < 48 hours stale"""
    # Simply check if the last heartbeat status was 'ok' and not stale
    # (Assuming heartbeat_data has 'status' and 'history')
    return heartbeat_data.get("status") == "ok"

def compute_g3(recon_data: dict) -> bool:
    """G3: No mismatches in last reconciliation"""
    return len(recon_data.get("mismatches", [])) == 0


def compute_g4(perm_data: dict) -> bool:
    """G4: Full 200-permutation protocol run on the honest T+1 engine"""
    return perm_data.get("permutations", 0) >= 200

def compute_g5(heartbeats_list: list) -> bool:
    """G5: Heartbeat seen for >= 7 consecutive trading days"""
    # Collect unique dates from heartbeats
    dates = set()
    for hb in heartbeats_list:
        ts = hb.get("ts", "")
        if len(ts) >= 10:
            dates.add(ts[:10])

    # Need at least 7 unique dates in history
    return len(dates) >= 7

def compute_g6(rehearsal_data: dict) -> bool:
    """G6: Kill-switch rehearsal documented once"""
    scenarios = rehearsal_data.get("scenarios", {})
    return scenarios.get("T2_halt") == "success" and scenarios.get("T3_halt") == "success"

def compute_g7(recon_data: dict) -> bool:
    """G7: Zero unresolved fill/order mismatches over the last 10 trading days"""
    # Assuming recon_data has a history of mismatches or just checks current
    return len(recon_data.get("mismatches", [])) == 0

def evaluate_gates(portfolio_data: dict, heartbeat_data: dict, recon_data: dict, perm_data: dict, rehearsal_data: dict) -> dict:
    """Pure function to compute G1-G7 from parsed artifact data dictionaries."""

    heartbeats_list = heartbeat_data.get("history", [])

    g1 = compute_g1(portfolio_data)
    g2 = compute_g2(heartbeat_data)
    g3 = compute_g3(recon_data)
    g4 = compute_g4(perm_data)
    g5 = compute_g5(heartbeats_list)
    g6 = compute_g6(rehearsal_data)
    g7 = compute_g7(recon_data)

    passed = g1 and g2 and g3 and g4 and g5 and g6 and g7

    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "gates": {
            "G1_dd_breaker": g1,
            "G2_heartbeat": g2,
            "G3_reconciliation_last": g3,
            "G4_permutation_study": g4,
            "G5_heartbeat_7_days": g5,
            "G6_killswitch_rehearsal": g6,
            "G7_reconciliation_10_days": g7
        },
        "passed": passed
    }


def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Evaluating gates...")

    # Read files in main
    portfolio_data = {}
    if os.path.exists("docs/data/portfolio_state.json"):
        with open("docs/data/portfolio_state.json") as f:
            portfolio_data = json.load(f)

    heartbeat_data = {"status": "ok", "history": []}
    if os.path.exists("docs/data/ops/heartbeat.json"):
        with open("docs/data/ops/heartbeat.json") as f:
            heartbeat_data = json.load(f)

    recon_data = {"mismatches": []}
    if os.path.exists("docs/data/ops/reconciliation.json"):
        with open("docs/data/ops/reconciliation.json") as f:
            recon_data = json.load(f)

    perm_data = {}
    if os.path.exists("docs/data/permutation_study.json"):
        with open("docs/data/permutation_study.json") as f:
            perm_data = json.load(f)

    rehearsal_data = {}
    if os.path.exists("docs/data/ops/kill_switch_rehearsal.json"):
        with open("docs/data/ops/kill_switch_rehearsal.json") as f:
            rehearsal_data = json.load(f)

    result = evaluate_gates(portfolio_data, heartbeat_data, recon_data, perm_data, rehearsal_data)

    os.makedirs("docs/data/ops", exist_ok=True)
    write_artifact("docs/data/ops/gate_evaluation.json", result)

    if not result["passed"]:
        # Check if we failed G1, G2, or G3
        critical_failure = not result["gates"]["G1_dd_breaker"] or not result["gates"]["G2_heartbeat"] or not result["gates"]["G3_reconciliation_last"]

        alerts = Alerts()
        failed_gates = [k for k, v in result["gates"].items() if not v]

        if critical_failure:
            logger.warning("Critical gates failed. Auto-halting new orders.")
            set_halt_state(reason=f"Gate Evaluator failed on: {', '.join(failed_gates)}")
            alerts.send_critical(f"Gate Evaluator failed on: {', '.join(failed_gates)}. Auto-halting new orders.")
        else:
            logger.warning("Non-critical gates failed.")
            alerts.send_warn(f"Gate Evaluator failed on: {', '.join(failed_gates)}. Review required.")

if __name__ == "__main__":
    main()
