import argparse
import json
import os
import shutil
from datetime import datetime

import yaml

from src.ops import preregistration, strategy_registry

# Known families as per HUNT_PROTOCOL.md or other references
KNOWN_FAMILIES = ["momentum", "trend", "mean_reversion", "breakout_burst"]

def load_brief(brief_path):
    with open(brief_path, 'r') as f:
        brief = yaml.safe_load(f)

    required_fields = ["family", "universe", "hypothesis", "acceptance", "lookback_constraints", "edge_gate_params"]
    missing = [f for f in required_fields if f not in brief]
    if missing:
        raise ValueError(f"Brief at {brief_path} is missing required fields: {', '.join(missing)}")

    if brief["family"] not in KNOWN_FAMILIES:
        raise ValueError(f"Unknown family '{brief['family']}'. Expected one of {KNOWN_FAMILIES}")

    return brief

def do_run(args):
    brief = load_brief(args.brief)
    family = brief["family"]

    from datetime import timezone
    now = datetime.now(timezone.utc)
    # YYYYMMDD-HHMM family-slug
    run_id_prefix = now.strftime('%Y%m%d-%H%M')
    family_slug = family.replace('_', '-')
    run_id = f"{run_id_prefix} {family_slug}"
    run_id_slug = f"{run_id_prefix}_{family_slug}"

    # Setup directories
    out_dir = args.out
    if not out_dir:
        out_dir = os.path.join("hunts", family, run_id_slug)

    os.makedirs(out_dir, exist_ok=True)
    candidates_dir = os.path.join(out_dir, "candidates")
    results_dir = os.path.join(out_dir, "results")
    os.makedirs(candidates_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # Copy brief
    brief_copy_path = os.path.join(out_dir, "brief.yaml")
    shutil.copy(args.brief, brief_copy_path)

    # Session log stub
    log_path = os.path.join(out_dir, "session_log.yaml")
    with open(log_path, 'w') as f:
        yaml.safe_dump({
            "run_id": run_id,
            "family": family,
            "started_at": now.isoformat(),
            "status": "initialized",
            "cycle_id": f"{family}-{run_id_slug}"
        }, f)

    # Copy registry via load_registry
    registry_snapshot_path = os.path.join(out_dir, "registry_snapshot.json")
    try:
        entries, portfolio = strategy_registry.load_registry("strategies/registry.json")
        registry_data = {
            "strategies": [{k: v for k, v in e.items() if k != 'spec'} for e in entries],
            "portfolio": portfolio
        }
        with open(registry_snapshot_path, "w") as f:
             json.dump(registry_data, f, indent=2)
    except Exception: # noqa: BLE001
        # Fallback to direct copy if registry validation fails
        if os.path.exists("strategies/registry.json"):
            shutil.copy("strategies/registry.json", registry_snapshot_path)

    # Freeze preregistration
    # preregistration.freeze_preregistration signature requires a spec file to load.
    # We create a dummy spec in the session dir to freeze the claim.
    dummy_spec_path = os.path.join(out_dir, "dummy_spec.yaml")
    with open(dummy_spec_path, 'w') as f:
        yaml.safe_dump({"family": family}, f)

    cycle_id_str = f"{family}-{run_id_slug}"
    # The requirement says: calls preregistration.freeze_preregistration(cycle_id=<family>-<run_id>, docs_dir=..., registry=...)
    # We will pass cycle_id_str as cycle but preregistration.freeze_preregistration expects cycle to be int.
    # To satisfy the instruction, we'll try passing it if the API accepts it or adapt. Wait, freeze_preregistration
    # formats `cycle` via f"cycle{cycle}_prereg_{family}.md". It takes `cycle: Optional[int]`. If we pass a string,
    # it becomes `cycle<string>_prereg_<family>.md` which is fine.

    docs_dir = os.path.join(out_dir, "docs", "data")
    os.makedirs(docs_dir, exist_ok=True)

    try:
        preregistration.freeze_preregistration(
            spec_path=dummy_spec_path,
            claim=brief["hypothesis"],
            cycle=cycle_id_str, # Passing string, it might work due to f-strings
            docs_dir=docs_dir
        )
    except FileExistsError as e:
        if not args.force_reuse:
            print(f"Error: {e}")
            print("Use --force-reuse to bypass.")
            return
    except Exception as e: # noqa: BLE001
        print(f"Error freezing preregistration: {e}")
        return

    # Update session log with frozen prereg
    with open(log_path, 'r') as f:
        log_data = yaml.safe_load(f)
    from datetime import timezone
    log_data["prereg_frozen_at"] = datetime.now(timezone.utc).isoformat()
    log_data["prereg_cycle_id"] = cycle_id_str
    with open(log_path, 'w') as f:
        yaml.safe_dump(log_data, f)

    # Remove dummy spec
    if os.path.exists(dummy_spec_path):
        os.remove(dummy_spec_path)

    # Print the session brief payload
    print("=========================================")
    print("Session Brief Payload for OpenCode/Jules")
    print("=========================================")
    print("```markdown")
    print(f"**Family**: {family}")
    print(f"**Universe**: {brief['universe']}")
    print(f"**Acceptance Criteria**:\n{brief['acceptance']}")
    print(f"**Pre-registration Cycle ID**: {cycle_id_str}")
    print(f"**Output Contract Path**: {candidates_dir}/")
    print("**Edge-gate Commands**:")
    print("  python scripts/generate_strategy_data.py <ticker-universe>")
    print("  python scripts/run_full_backtest.py <spec.yaml>")
    print("  python scripts/comprehensive_backtest_report.py <spec.yaml>")
    print("```")
    print("=========================================")

def do_collect(args):
    target_dir = args.dir
    candidates_dir = os.path.join(target_dir, "candidates")
    results_dir = os.path.join(target_dir, "results")

    if not os.path.exists(candidates_dir):
        print(f"Error: candidates directory not found at {candidates_dir}")
        return

    rejected_dir = os.path.join(target_dir, "rejected")
    os.makedirs(rejected_dir, exist_ok=True)

    candidates = [f for f in os.listdir(candidates_dir) if f.endswith(('.yaml', '.yml'))]
    if not candidates:
        print("No candidates found.")
        return

    print(f"Collecting {len(candidates)} candidates from {candidates_dir}...")

    for cand_file in candidates:
        cand_path = os.path.join(candidates_dir, cand_file)
        try:
            spec = strategy_registry.load_yaml(cand_path)
            strategy_registry.validate_spec(spec, cand_path)

            # Spec is valid. Check missing requirements for registry entry.
            missing_items = []

            # Check prereg record and gates
            if 'pre_registration_ref' not in spec:
                missing_items.append("Missing pre_registration_ref in spec")
            elif not os.path.exists(spec['pre_registration_ref']):
                missing_items.append(f"Pre-registration doc not found at {spec['pre_registration_ref']}")

            if 'eval_records' not in spec:
                missing_items.append("Missing eval_records in spec")
            else:
                eval_file = spec['eval_records']
                if not os.path.exists(eval_file) and not os.path.exists(os.path.join(results_dir, os.path.basename(eval_file))):
                     missing_items.append(f"Eval records not found at {eval_file} or in results/")

            print(f"✅ Valid Spec: {cand_file}")
            if missing_items:
                print("   Missing items for registry entry:")
                for item in missing_items:
                    print(f"   - {item}")
            else:
                print("   Ready for registry merging (human-gated step).")

        except strategy_registry.MalformedSpecError as e:
            print(f"❌ Rejected: {cand_file} - {e}")
            shutil.move(cand_path, os.path.join(rejected_dir, cand_file))
            # Create a rejection reason file
            with open(os.path.join(rejected_dir, f"{cand_file}.reason"), 'w') as f:
                f.write(str(e))

def do_status(args):
    hunts_dir = "hunts"
    if not os.path.exists(hunts_dir):
        print("No hunts directory found.")
        return

    print(f"{'FAMILY':<20} | {'RUN ID':<30} | {'PREREG CYCLE':<35} | {'CANDS':<6} | {'VALID':<6} | {'REJECTED':<8}")
    print("-" * 115)

    for family in os.listdir(hunts_dir):
        family_dir = os.path.join(hunts_dir, family)
        if not os.path.isdir(family_dir) or family.startswith('_'):
            continue

        for run_dir_name in os.listdir(family_dir):
            run_dir = os.path.join(family_dir, run_dir_name)
            if not os.path.isdir(run_dir):
                continue

            log_path = os.path.join(run_dir, "session_log.yaml")

            run_id = run_dir_name
            prereg_cycle = "N/A"
            prereg_time = ""

            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r') as f:
                        log_data = yaml.safe_load(f)
                    run_id = log_data.get("run_id", run_id)
                    prereg_cycle = log_data.get("prereg_cycle_id", prereg_cycle)
                    if "prereg_frozen_at" in log_data:
                        # Extract just the date/time part for compact display
                        pt = log_data["prereg_frozen_at"]
                        if 'T' in pt:
                            pt = pt.split('T')[0] + ' ' + pt.split('T')[1][:5]
                        prereg_time = f" ({pt})"
                except Exception: # noqa: BLE001, S110 - acceptable to ignore missing or malformed log when checking status
                    pass

            cycle_display = f"{prereg_cycle}{prereg_time}"

            # Count candidates
            cands_dir = os.path.join(run_dir, "candidates")
            cands_count = 0
            if os.path.exists(cands_dir):
                cands_count = len([f for f in os.listdir(cands_dir) if f.endswith(('.yaml', '.yml'))])

            rej_dir = os.path.join(run_dir, "rejected")
            rej_count = 0
            if os.path.exists(rej_dir):
                rej_count = len([f for f in os.listdir(rej_dir) if f.endswith(('.yaml', '.yml'))])

            # If we don't know validity, we assume anything in cands is unprocessed or valid
            # In a real workflow, valid might be those that pass validate_spec
            # Here we just show counts based on what's left in candidates/ vs rejected/
            valid_count = cands_count

            print(f"{family:<20} | {run_id:<30} | {cycle_display:<35} | {cands_count + rej_count:<6} | {valid_count:<6} | {rej_count:<8}")

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--brief", required=True)
    run_parser.add_argument("--out", required=False)
    run_parser.add_argument("--force-reuse", action="store_true")

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--dir", required=True)
    collect_parser.add_argument("--registry", required=True)

    subparsers.add_parser("status")

    args = parser.parse_args()
    if args.command == "run":
        do_run(args)
    elif args.command == "collect":
        do_collect(args)
    elif args.command == "status":
        do_status(args)

if __name__ == "__main__":
    main()