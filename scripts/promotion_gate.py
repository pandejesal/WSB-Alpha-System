#!/usr/bin/env python3
"""Promotion Gate: validates paper-approval dashboard for live promotion readiness.

Reads docs/data/paper_dashboard.json and enforces:
  - verdict == "GO"
  - months_tracked >= min_months_required
  - all_months_green == true
  - zero broken_executions

Exit 0 = GO (promotion allowed)
Exit 1 = NO_GO (promotion blocked)

Fail-closed: missing file, unparseable JSON, or zero months tracked → exit 1.
"""

import json
import sys
from pathlib import Path

DASHBOARD_PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "paper_dashboard.json"


def load_dashboard(path) -> dict:
    """Load and parse the paper dashboard JSON. Returns {} on any failure (fail-closed)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return {}


def evaluate_gate(dash: dict) -> dict:
    """Evaluate promotion gate. Returns {"gate": "GO"/"NO_GO"/"FAIL_CLOSED", "go": bool, "reason": str}."""
    if not dash:
        return {"gate": "FAIL_CLOSED", "go": False, "reason": "FAIL_CLOSED: paper_dashboard.json missing or unparseable"}

    verdict = dash.get("verdict", "")
    if verdict != "GO":
        return {"gate": "NO_GO", "go": False, "reason": f"NO_GO: verdict={verdict!r} (expected GO)"}

    months_tracked = dash.get("months_tracked", 0)
    min_months = dash.get("min_months_required", 2)
    if months_tracked == 0:
        return {"gate": "FAIL_CLOSED", "go": False, "reason": "FAIL_CLOSED: months_tracked=0, no evidence"}
    if months_tracked < min_months:
        return {"gate": "NO_GO", "go": False, "reason": f"NO_GO: months_tracked={months_tracked} < min_months_required={min_months}"}

    all_green = dash.get("all_months_green", False)
    if not all_green:
        return {"gate": "NO_GO", "go": False, "reason": "NO_GO: all_months_green=false"}

    broken = dash.get("broken_executions", 0)
    if broken != 0:
        return {"gate": "NO_GO", "go": False, "reason": f"NO_GO: broken_executions={broken} (expected 0)"}

    return {"gate": "GO", "go": True, "reason": "GO: all promotion criteria met"}


def main() -> int:
    result = evaluate_gate(load_dashboard(DASHBOARD_PATH))
    print(result["reason"])
    return 0 if result["go"] else 1


if __name__ == "__main__":
    sys.exit(main())
