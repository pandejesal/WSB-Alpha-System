import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone

import yaml

from src.backtest.defend.trial_ledger import TrialLedger
from src.ops import preregistration, strategy_registry

KNOWN_FAMILIES = ["momentum", "mean_reversion", "carry", "volatility", "sentiment", "arbitrage"]

# B5a (P2-S9 / F3-H1): hunt→evolve taxonomy alignment.
# The hunt factory briefs use 6 conceptual families (KNOWN_FAMILIES above),
# while the evolve loop (evolve_real.py FAMILIES, READ-ONLY — do not edit)
# searches 10 concrete families:
#   ["spy_sma", "spy_rsi2", "btc_vol", "btc_donchian", "us_momentum",
#    "us_lowvol", "spy_ltrend", "us_ltrend", "gap_mr", "btc_regime"]
# This alias map translates each hunt family to the evolve families that can
# consume its briefs, so hunt output feeds the loop without manual rewrites.
# KNOWN_FAMILIES is intentionally left unchanged for backward compat.
FAMILY_EVOLVE_ALIASES = {
    # Trend/momentum briefs feed the momentum + long-trend evolve families.
    "momentum": ["us_momentum", "spy_sma", "spy_ltrend", "us_ltrend"],
    # Mean-reversion briefs feed the RSI and overnight-gap MR evolve families.
    "mean_reversion": ["spy_rsi2", "gap_mr"],
    # No dedicated carry family exists in the evolve loop; us_lowvol is the
    # nearest proxy (low-vol selection). Documented caveat, not a claim of fit.
    "carry": ["us_lowvol"],
    # Volatility briefs feed the three BTC volatility/regime evolve families
    # (evolve_real._BTC_FAMILIES = btc_vol, btc_donchian, btc_regime).
    "volatility": ["btc_vol", "btc_donchian", "btc_regime"],
    # Sentiment acts as an entry filter / risk modifier; its briefs feed the
    # gap-MR loop where the sentiment overlay is evaluated.
    "sentiment": ["gap_mr"],
    # No arbitrage family exists in the evolve loop: empty list on purpose,
    # so validation emits the no-evolve-target warning below.
    "arbitrage": [],
}


def resolve_evolve_families(family):
    """Return evolve-loop families consuming hunt briefs of `family`.

    Prints a validation warning and returns [] when the brief family has no
    evolve target (unknown family, or a known family with no loop coverage
    such as arbitrage). Never raises: hunt discovery stays fail-open here;
    the edge gate remains the fail-closed enforcement point.
    """
    targets = FAMILY_EVOLVE_ALIASES.get(family, [])
    if not targets:
        print(
            f"WARNING: Hunt family '{family}' has no evolve-loop target. "
            "Brief cannot feed evolve_real.py FAMILIES; add loop coverage or "
            "keep the hunt as registry-only."
        )
    return list(targets)


def load_brief(brief_path):
    with open(brief_path, 'r') as f:
        brief = yaml.safe_load(f)

    if not isinstance(brief, dict):
        raise ValueError(f"Brief at {brief_path} is not a valid YAML mapping")

    required_fields = ["family", "universe", "hypothesis", "acceptance", "lookback_constraints", "edge_gate_params"]
    missing = [f for f in required_fields if f not in brief]
    if missing:
        raise ValueError(f"Brief at {brief_path} is missing required fields: {', '.join(missing)}")

    import re
    family = brief.get("family", "")
    if not re.match(r'^[a-z0-9_]+$', family):
        raise ValueError(f"Invalid family name '{family}'. Must contain only lowercase letters, numbers, and underscores.")

    if family not in KNOWN_FAMILIES:
        print(f"WARNING: Unknown family '{family}'. Discovery is encouraged, but ensure it does not overlap with existing families.")

    # B5a: validate hunt→evolve taxonomy coverage (warns when no loop target).
    resolve_evolve_families(family)

    return brief

def do_run(args):
    brief = load_brief(args.brief)
    family = brief["family"]

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
            "evolve_targets": resolve_evolve_families(family),
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
    brief_spec_path = os.path.join(out_dir, "brief_spec.yaml")
    with open(brief_spec_path, 'w') as f:
        yaml.safe_dump(brief, f)

    dummy_spec_path = os.path.join(out_dir, "dummy_spec.yaml")
    with open(dummy_spec_path, 'w') as f:
        yaml.safe_dump({"family": family}, f)

    # cycle_int = int(now.strftime('%Y%m%d'))
    cycle_id_str = f"{family}-{run_id_slug}"

    docs_dir = os.path.join(out_dir, "docs", "data")
    os.makedirs(docs_dir, exist_ok=True)

    try:
        preregistration.freeze_preregistration(
            spec_path=dummy_spec_path,
            claim=brief["hypothesis"],
            cycle=cycle_id_str,
            docs_dir=docs_dir
        )
    except FileExistsError as e:
        if not args.force_reuse:
            print(f"Error: {e}")
            print("Use --force-reuse to bypass.")
            sys.exit(2)
        else:
            print("WARNING: Reusing existing preregistration freeze (--force-reuse).")
    except Exception as e: # noqa: BLE001
        print(f"Error freezing preregistration: {e}")
        sys.exit(2)

    # Update session log with frozen prereg
    with open(log_path, 'r') as f:
        log_data = yaml.safe_load(f)

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

def _append_hunt_trial_to_ledger(target_dir, results_dir, cand_file, spec):
    """Best-effort ledger wiring for the non-loop hunt collect path.

    Appends one TrialLedger row per validated candidate (default
    run-logs/trials.jsonl, overridable via TRIAL_LEDGER_PATH). The
    data_range is stable per (run, candidate file) so re-collecting an
    unchanged candidate dedups instead of double-counting. Never raises:
    ledger failure must not fail the collect command.
    """
    try:
        if not isinstance(spec, dict):
            print(f"WARNING: ledger skipped for {cand_file} (spec is not a YAML mapping)", file=sys.stderr)
            return None
        family = str(spec.get("family", "unknown"))
        run = os.path.basename(os.path.normpath(target_dir))
        strategy_id = str(spec.get("id") or spec.get("name") or family)
        params = spec.get("parameters")
        if params is None:
            params = spec.get("params", {})
        if not isinstance(params, dict):
            params = {}
        metrics = {}
        try:
            eval_ref = spec.get("eval_records")
            eval_candidates = []
            if isinstance(eval_ref, str) and eval_ref:
                eval_candidates.append(eval_ref)
                eval_candidates.append(os.path.join(results_dir, os.path.basename(eval_ref)))
            eval_data = {}
            for eval_path in eval_candidates:
                if os.path.exists(eval_path):
                    with open(eval_path, "r") as fh:
                        eval_data = json.load(fh)
                    break
            if isinstance(eval_data, dict):
                wf = eval_data.get("walk_forward")
                if isinstance(wf, dict):
                    for key in ("sharpe", "profit_factor", "max_dd", "max_drawdown_pct",
                                "max_drawdown", "total_trades"):
                        if key in wf:
                            metrics[key] = wf[key]
                dsr = eval_data.get("dsr")
                if isinstance(dsr, (int, float)) and "sharpe" not in metrics:
                    metrics["sharpe"] = dsr
        except Exception:  # noqa: BLE001, S110 - metrics are best-effort
            pass
        data_range = f"hunt:{family}:{run}:{cand_file}"
        ledger_path = os.environ.get("TRIAL_LEDGER_PATH", "run-logs/trials.jsonl")
        sha = TrialLedger(path=ledger_path).append_experiment(
            strategy_id=strategy_id,
            params=params,
            data_range=data_range,
            metrics=metrics,
            provider="hunt:collect",
        )
        if sha is None:
            print(f"WARNING: ledger skipped duplicate trial for {cand_file} (already logged)", file=sys.stderr)
        else:
            print(f"Ledger appended trial {sha} to {ledger_path}")
        return sha
    except Exception as exc:  # noqa: BLE001 - ledger is best-effort
        print(f"WARNING: ledger append failed for {cand_file} ({exc}); collect kept", file=sys.stderr)
        return None


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
            if not isinstance(spec, dict):
                raise strategy_registry.MalformedSpecError(f"Spec {cand_file} is not a YAML mapping")
            strategy_registry.validate_spec(spec, cand_path)

            _append_hunt_trial_to_ledger(
                target_dir=target_dir,
                results_dir=results_dir,
                cand_file=cand_file,
                spec=spec,
            )

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

        except (strategy_registry.MalformedSpecError, yaml.YAMLError, OSError) as e:
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
