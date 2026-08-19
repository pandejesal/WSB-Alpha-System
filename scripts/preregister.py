#!/usr/bin/env python3
import argparse
import sys
from src.ops.preregistration import freeze_preregistration, record_evaluation

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
        except Exception as e:
            print(f"Error recording evaluation: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "status":
        print(f"Status check for {args.family} not fully implemented yet.")

if __name__ == "__main__":
    main()
