# Hunt Lessons — Failed Candidate Ledger (Layer 3)

Compiled from docs/data/round1_consolidation.json + round 3.5 outcomes.
Internalize as constraints: do not re-propose these edges without CHANGED
conditions, and say what changed.

## Round 1 consolidation (11 candidates: 5 FAIL, 6 HONEST_ABANDON, 0 winners)
- All 11 round-1 candidates failed the edge gate or were abandoned honestly
  before full evaluation. Verdict: HONEST_NO_OP — the pipeline worked; no edge
  was found in those directions.
- Lesson: absence of edge is a valid result. Do not resurrect abandoned specs
  unchanged.

## Round 3.5 hunt (8 candidates, 0 passed)
- Closest: `ta_rules_rsi2_stop_v1` — IS p=0.05 borderline; failed downstream gates.
- Lesson: RSI(2)-family entries are saturated territory in this universe;
  differentiation must come from regime/exit structure, not entry tweak.

## Standing rules
1. Any new hypothesis overlapping a listed family must cite that failure and
   name its changed condition in prior_art.md.
2. "HONEST_ABANDON" reasons (data insufficiency, untestable claim) apply with
   equal force today unless data/tooling changed.
3. Borderline IS results (p near 0.05) are FAILURES, not encouragements.
