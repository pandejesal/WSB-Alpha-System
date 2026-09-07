#!/usr/bin/env python3
"""Watchdog for the evolve loop: restart it if the log goes stale.

Designed for script-only cron (no agent): prints nothing when healthy
(scheduler stays silent), prints ALERT lines only when it acts.
Restart uses Windows DETACHED_PROCESS so the loop survives the parent.

Usage:
  python scripts/evolve_watchdog.py --check [--restart] [--stale-sec 600]
"""
import argparse
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT / "docs/data/evolve_real.log"
LOCK = ROOT / "docs/data/evolve_real.lock"


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def lock_pid() -> int:
    try:
        return int(LOCK.read_text(encoding="utf-8").strip() or "0")
    except (ValueError, OSError):
        return 0


def log_age_sec() -> float:
    try:
        return time.time() - LOG.stat().st_mtime
    except OSError:
        return float("inf")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--restart", action="store_true")
    ap.add_argument("--stale-sec", type=int, default=600)
    args = ap.parse_args()

    age = log_age_sec()
    alive = pid_alive(lock_pid())
    if age <= args.stale_sec or alive:
        return 0  # healthy: silent
    print(f"[{datetime.now(timezone.utc).isoformat()}] ALERT evolve loop stale "
          f"(log age {age:.0f}s, lock pid dead); attempting restart", flush=True)
    if not args.restart:
        return 1
    try:
        py = sys.executable
        out = open(ROOT / "docs/data/evolve_watchdog_spawn.log", "a",
                   encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        subprocess.Popen(
            [py, "evolve_real.py"], cwd=str(ROOT), env=env,
            stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            close_fds=True,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
        )
        print("ALERT evolve loop restarted (detached)", flush=True)
        return 0
    except Exception as e:
        print(f"ALERT restart failed: {e}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
