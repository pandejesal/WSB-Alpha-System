#!/usr/bin/env python3
"""CLI runner for Lean engine port algorithms.

Usage:
    python scripts/lean_run.py --algo src.backtest.lean_example:SMACrossAlgorithm
    python scripts/lean_run.py --algo src.backtest.lean_example:SMACrossAlgorithm --fast 20 --slow 100
    python scripts/lean_run.py --algo src.backtest.lean_example:SMACrossAlgorithm --json results.json
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_algo(spec: str, **kwargs) -> object:
    """Load an Algorithm subclass from 'module:ClassName' spec."""
    module_path, class_name = spec.rsplit(":", 1)
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Lean engine port algorithm")
    parser.add_argument("--algo", required=True,
                        help="Algorithm spec: module.path:ClassName")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    parser.add_argument("--cash", type=float, help="Starting cash")
    parser.add_argument("--fast", type=int, help="Fast SMA period")
    parser.add_argument("--slow", type=int, help="Slow SMA period")
    parser.add_argument("--csv-root", help="CSV data directory")
    parser.add_argument("--json", help="Write results to JSON file")
    args = parser.parse_args()

    # Build kwargs from CLI args
    kwargs = {}
    if args.fast is not None:
        kwargs["fast"] = args.fast
    if args.slow is not None:
        kwargs["slow"] = args.slow

    algo = load_algo(args.algo, **kwargs)

    # Override settings if provided
    if args.cash is not None:
        algo.SetCash(args.cash)
    if args.start:
        y, m, d = args.start.split("-")
        algo.SetStartDate(int(y), int(m), int(d))
    if args.end:
        y, m, d = args.end.split("-")
        algo.SetEndDate(int(y), int(m), int(d))
    if args.csv_root:
        algo.SetCsvRoot(args.csv_root)

    results = algo.run()

    print(f"Strategy return: {results['strategy_return']:.2%}")
    print(f"Benchmark return: {results['benchmark_return']:.2%}")
    print(f"Total orders: {results['total_orders']}")
    print(f"Total fees: ${results['total_fees']:.2f}")

    if args.json:
        out = ROOT / args.json
        out.write_text(json.dumps(results, indent=2, default=str))
        print(f"Results written to {out}")


if __name__ == "__main__":
    main()
