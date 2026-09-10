"""OpenProphet phased-heartbeat scheduler port (Python).

Source: https://github.com/JakeNesler/OpenProphet agent/harness.js
  PHASE_DEFAULTS + getCurrentPhase (ET-based market phases).

Same phase table, same per-phase beat intervals (seconds):
  pre_market 900 | market_open 120 | midday 600 | market_close 120 |
  after_hours 1800 | closed 3600.

Delta: this is a pure scheduler. Upstream wakes an LLM agent with live
order tools ("no human approving your actions"). This port wakes a
deterministic beat function (scan -> manage -> log) that is paper-only
and can never place live orders. Weekends always map to `closed`.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PHASES: dict[str, dict] = {
    "pre_market": {"seconds": 900, "label": "Pre-Market", "range": (240, 570)},
    "market_open": {"seconds": 120, "label": "Market Open", "range": (570, 630)},
    "midday": {"seconds": 600, "label": "Midday", "range": (630, 900)},
    "market_close": {"seconds": 120, "label": "Market Close", "range": (900, 960)},
    "after_hours": {"seconds": 1800, "label": "After Hours", "range": (960, 1200)},
    "closed": {"seconds": 3600, "label": "Markets Closed", "range": None},
}


def get_current_phase(now: datetime | None = None) -> str:
    now = now or datetime.now(tz=ET)
    et = now.astimezone(ET)
    if et.weekday() >= 5:  # Sat/Sun
        return "closed"
    mins = et.hour * 60 + et.minute
    for name, cfg in PHASES.items():
        r = cfg["range"]
        if r and r[0] <= mins < r[1]:
            return name
    return "closed"


def beat_interval_seconds(phase: str) -> int:
    return int(PHASES[phase]["seconds"])


def run_beats(beat_fn: Callable[[str, int], dict], phases: list[str] | None = None,
              max_beats: int = 1) -> list[dict]:
    """Drive `max_beats` beats through `beat_fn(phase, beat_no)`.

    `phases` overrides the live clock (for backtest/replay); otherwise the
    current ET phase is used for every beat.
    """
    out = []
    for i in range(max_beats):
        phase = phases[i % len(phases)] if phases else get_current_phase()
        res = beat_fn(phase, i)
        res.setdefault("phase", phase)
        res.setdefault("paper", True)
        out.append(res)
    return out
