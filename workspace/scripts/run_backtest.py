"""ICM stage-02 backtest wrapper.

Thin mechanical shell around the repo's evaluate_candidate.py. Takes a
hypothesis brief YAML (or spec path) and writes raw results JSON to the
stage output dir. No evaluation logic lives here.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVALUATOR = REPO_ROOT / "scripts" / "evaluate_candidate.py"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", help="Path to candidate spec/brief YAML")
    ap.add_argument("--out", required=True, help="Stage output directory for results.json")
    ap.add_argument("--tickers", default=None, help="Comma separated tickers override")
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--permutations", type=int, default=None)
    args = ap.parse_args()

    spec_path = Path(args.spec).resolve()
    if not spec_path.exists():
        print(f"FAIL: spec not found: {spec_path}", file=sys.stderr)
        return 2
    if not EVALUATOR.exists():
        print(f"FAIL: evaluator missing: {EVALUATOR}", file=sys.stderr)
        return 2

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, str(EVALUATOR), str(spec_path)]
    if args.tickers:
        cmd += ["--tickers", args.tickers]
    if args.days is not None:
        cmd += ["--days", str(args.days)]
    if args.seed is not None:
        cmd += ["--seed", str(args.seed)]
    if args.permutations is not None:
        cmd += ["--permutations", str(args.permutations)]

    print("RUN:", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)

    (out_dir / "evaluator_stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (out_dir / "evaluator_stderr.txt").write_text(proc.stderr or "", encoding="utf-8")

    results = None
    for candidate in (proc.stdout or "").splitlines():
        line = candidate.strip()
        if line.startswith("{"):
            try:
                results = json.loads(line)
            except json.JSONDecodeError:
                continue

    if results is not None:
        (out_dir / "results.json").write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8"
        )
        print(f"WROTE: {out_dir / 'results.json'}")
    else:
        print(
            "NOTE: no JSON object found on stdout; check evaluator_stdout.txt "
            "and the evaluator's own artifact locations.",
            flush=True,
        )

    if proc.returncode != 0:
        print(f"EVALUATOR EXIT: {proc.returncode}", file=sys.stderr)
        return proc.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
