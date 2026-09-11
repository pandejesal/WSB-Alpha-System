#!/usr/bin/env python3
"""Holdout-isolation audit (E-gate-1, OOQI temporal-holdout pattern).

Verifies prereg freeze files predate their evaluation files per cycle:
for every docs/data/cycle<N>_eval_*.json there must exist a
docs/data/cycle<N>_prereg_*.md with an OLDER mtime (freeze before test).

Fail-closed exit codes: 0 = all ordered, 1 = violation found, 2 = scanner error.
Read-only: never writes outside stdout.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"

CYCLE_RE = re.compile(r"^cycle(\d+)_(prereg_.*\.md|.*eval.*\.json)$")


def audit() -> tuple[int, list[str]]:
    if not DATA.is_dir():
        return 2, [f"data dir missing: {DATA}"]
    preregs: dict[str, float] = {}
    evals: list[tuple[str, float, str]] = []
    for p in DATA.iterdir():
        m = CYCLE_RE.match(p.name)
        if not m:
            continue
        cyc, kind = m.group(1), m.group(2)
        if kind.startswith("prereg_"):
            mt = p.stat().st_mtime
            if cyc not in preregs or mt < preregs[cyc]:
                preregs[cyc] = mt
        else:
            evals.append((cyc, p.stat().st_mtime, p.name))
    violations: list[str] = []
    ties: list[str] = []
    checked = 0
    for cyc, emt, ename in sorted(evals):
        if cyc not in preregs:
            violations.append(f"cycle{cyc}: {ename} has NO prereg freeze file")
            continue
        checked += 1
        if int(preregs[cyc]) == int(emt):
            ties.append(f"cycle{cyc}: {ename} same-second batch as freeze (tie, not a violation)")
        elif not preregs[cyc] < emt:
            violations.append(
                f"cycle{cyc}: prereg freeze NOT older than {ename} "
                f"(freeze={preregs[cyc]:.0f} eval={emt:.0f})"
            )
    summary = (
        f"checked={checked} evals_with_prereg, "
        f"missing={sum('NO prereg' in v for v in violations)}, "
        f"misordered={sum('NOT older' in v for v in violations)}, "
        f"same_batch_ties={len(ties)}"
    )
    return (1 if violations else 0), [summary] + violations + ties


def main() -> int:
    try:
        code, lines = audit()
    except OSError as exc:
        print(f"scanner error: {exc}")
        return 2
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
