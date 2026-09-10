#!/usr/bin/env python3
import argparse
import json
import os
import sys

import yaml

from src.backtest.defend.trial_ledger import TrialLedger
from src.ops.preregistration import (
    freeze_preregistration,
    record_evaluation,
    verify_prereg_freeze,
)


def _append_prereg_trial_to_ledger(spec_path: str, eval_filepath: str) -> str | None:
    """Best-effort ledger wiring for the non-loop preregister record path.

    Appends one TrialLedger row per record_evaluation call (default
    run-logs/trials.jsonl, overridable via TRIAL_LEDGER_PATH). The data_range
    embeds the evaluation timestamp so repeated records grow the ledger
    instead of colliding on the content hash. Never raises: ledger failure
    must not fail the record command.
    """
    try:
        with open(spec_path, "r") as fh:
            spec = yaml.safe_load(fh)
        if not isinstance(spec, dict):
            print("WARNING: ledger skipped (spec is not a YAML mapping)", file=sys.stderr)
            return None
        with open(eval_filepath, "r") as fh:
            eval_data = json.load(fh)
        if not isinstance(eval_data, dict):
            eval_data = {}
    except Exception as exc:  # noqa: BLE001 - ledger is best-effort
        print(f"WARNING: ledger skipped (could not read spec/eval: {exc})", file=sys.stderr)
        return None

    try:
        family = str(spec.get("family", "unknown"))
        strategy_id = str(spec.get("id") or spec.get("name") or family)
        params = spec.get("parameters")
        if params is None:
            params = spec.get("params", {})
        if not isinstance(params, dict):
            params = {}
        metrics: dict = {}
        try:
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
        evaluated_at = str(eval_data.get("evaluated_at", "unknown"))
        data_range = f"prereg:{family}:{evaluated_at}"
        ledger_path = os.environ.get("TRIAL_LEDGER_PATH", "run-logs/trials.jsonl")
        sha = TrialLedger(path=ledger_path).append_experiment(
            strategy_id=strategy_id,
            params=params,
            data_range=data_range,
            metrics=metrics,
            provider="preregister:record",
        )
        if sha is None:
            print("WARNING: ledger skipped duplicate trial (already logged)", file=sys.stderr)
        else:
            print(f"Ledger appended trial {sha} to {ledger_path}")
        return sha
    except Exception as exc:  # noqa: BLE001 - ledger is best-effort
        print(f"WARNING: ledger append failed ({exc}); record kept", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Pre-registration and evaluation tool for OpenCode/Jules hunt sessions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Freeze command
    freeze_parser = subparsers.add_parser("freeze", help="Generate a frozen pre-registration doc from a strategy spec")
    freeze_parser.add_argument("spec_path", help="Path to the strategy spec YAML")
    freeze_parser.add_argument("--claim", required=True, help="The core hypothesis or edge being targeted")
    freeze_parser.add_argument("--cycle", type=int, help="Hunt cycle number (defaults to latest + 1)")
    freeze_parser.add_argument("--docs-dir", default="docs/data", help="Directory to store pre-registration docs")

    # Record command
    record_parser = subparsers.add_parser("record", help="Record an evaluation verdict and output evaluation JSON")
    record_parser.add_argument("spec_path", help="Path to the strategy spec YAML")
    record_parser.add_argument("--verdict", required=True, choices=["PASS", "FAIL", "HONEST_ABANDON"], help="The evaluation verdict")
    record_parser.add_argument("--cycle", type=int, help="Hunt cycle number (defaults to latest)")
    record_parser.add_argument("--eval-path", help="Path to raw evaluation output if backtest_report.json is unavailable")
    record_parser.add_argument("--registry", default="strategies/registry.json", help="Path to the registry.json file")
    record_parser.add_argument("--docs-dir", default="docs/data", help="Directory containing pre-registration docs")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get status of a family's pre-registration")
    status_parser.add_argument("family", help="The family name to check")
    status_parser.add_argument("--docs-dir", default="docs/data", help="Directory containing pre-registration docs")

    # Verify command (B3a/G9 fail-closed freeze gate)
    verify_parser = subparsers.add_parser("verify", help="Verify a freeze exists with matching spec SHA-256 (fails closed)")
    verify_parser.add_argument("spec_path", help="Path to the strategy spec YAML")
    verify_parser.add_argument("--claim", help="Expected frozen claim (checked when provided)")
    verify_parser.add_argument("--cycle", type=int, help="Hunt cycle number (defaults to latest)")
    verify_parser.add_argument("--docs-dir", default="docs/data", help="Directory containing pre-registration docs")

    args = parser.parse_args()

    if args.command == "freeze":
        try:
            filepath = freeze_preregistration(args.spec_path, args.claim, args.cycle, args.docs_dir)
            print(f"Successfully generated pre-registration doc at {filepath}")
        except Exception as e:
            print(f"Error freezing pre-registration: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "record":
        try:
            filepath = record_evaluation(args.spec_path, args.verdict, args.cycle, args.eval_path, args.registry, args.docs_dir)
            print(f"Successfully recorded evaluation at {filepath}")
            _append_prereg_trial_to_ledger(args.spec_path, filepath)
        except Exception as e:
            print(f"Error recording evaluation: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "status":
        print(f"Status check for {args.family} not fully implemented yet.")

    elif args.command == "verify":
        try:
            filepath = verify_prereg_freeze(args.spec_path, args.claim, args.cycle, args.docs_dir)
            print(f"Pre-registration freeze verified at {filepath}")
        except Exception as e:
            print(f"Pre-registration freeze verification failed: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
