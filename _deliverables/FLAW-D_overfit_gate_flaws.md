# FLAW-D: Overfit & Gate Flaws — Ranked Fix Table

**Date:** 2026-09-08
**Role:** sub3 (fix proposer)
**Status:** Deliverable ready

---

## Ranked Fixes (max 12)

| Rank | Fix | Impact | Effort | File-level target | 1-sentence why |
|------|-----|--------|--------|-------------------|----------------|
| 1 | **5bps → 15bps** | H | S | `config/risk_config.py` | Current cost model underestimates real execution friction; tightening makes all gate clears harder and more realistic |
| 2 | **DSR N-scoping fix** | H | S | `src/backtest/gatespec38_tracks.py` | N=10000 silently demands annualized Sharpe≥2.01 — unattainable; scope DSR test to strategy horizon N bars |
| 3 | **Remove tracks_cleared dead field** | H | S | `evolve_real.py` | Field is always 0; removing eliminates false positive confidence in gate clears |
| 4 | **Deduplicate registry** | H | S | `strategies/registry.json` | 82% dupe bloat wastes compute; dedup once, add uniqueness guard to generation loop |
| 5 | **Add T+1 enforcement** | H | S | `src/backtest/engine.py` | Prevents same-bar entry/exit — a realistic constraint that filters overfit signals |
| 6 | **Out-of-sample holdout** | H | M | `evolve_real.py`, `src/backtest/engine.py` | 20% holdout prevents curve-fitting to in-sample noise; catches regime-dependent strategies |
| 7 | **Lookahead guard** | H | M | `src/backtest/engine.py` | Ensures no future data leaks into past decisions; foundational integrity fix |
| 8 | **Survivorship bias removal** | H | M | `src/data/loader.py` | Adds delisted/failed assets to universe; eliminates upward PnL bias |
| 9 | **Regime-aware filtering** | H | M | `src/backtest/engine.py`, `evolve_real.py` | Filters strategies that only work in one regime; improves robustness across market states |
| 10 | **K=200 → K=1000 bootstrap** | M | S | `evolve_real.py` | 200 Monte Carlo samples lack power; 1000 gives tighter confidence intervals |
| 11 | **Lax excess thresholds** | M | S | `evolve_real.py` | Current gates too permissive; tighten to reduce false positives in paper promotion |
| 12 | **Strict DSR 0.95 tracks** | M | M | `src/backtest/gatespec38_tracks.py` | DSR≥0.95 is mathematically brutal with N-scoping; consider 0.90 for shorter horizons |

---

## Additional High-Impact Fixes (beyond top 12)

| Rank | Fix | Impact | Effort | File-level target | 1-sentence why |
|------|-----|--------|--------|-------------------|----------------|
| 13 | **Anti-monoculture diversity** | M | M | `evolve_real.py` | Current ML proposal biasing clusters around similar strategies; add diversity penalty |
| 14 | **Generational breeding frequency** | L | S | `evolve_real.py` | Every-200-iter breeding may be too slow; consider adaptive frequency based on improvement rate |
| 15 | **Candidate promotion audit trail** | L | S | `evolve_real.py` | Add logging for why candidates pass/fail each track; improves debugging |

---

## Fix Dependency Graph

```
1. 5bps → 15bps (standalone)
2. DSR N-scoping (standalone)
3. Remove tracks_cleared (standalone)
4. Deduplicate registry (standalone, but do first to reduce noise)
5. T+1 enforcement (standalone)
6. OOS holdout (depends on #5 — need realistic execution first)
7. Lookahead guard (standalone)
8. Survivorship bias (standalone)
9. Regime-aware filtering (depends on #8 — need clean universe)
10. K=200 bootstrap (standalone)
11. Lax thresholds (depends on #2 — need realistic DSR first)
12. Strict DSR 0.95 (depends on #2 — need realistic N first)
```

---

## Implementation Order (Recommended)

### Phase 1: Foundation (S-effort, standalone)
1. **Deduplicate registry** — immediate noise reduction
2. **Remove tracks_cleared** — eliminate false confidence
3. **5bps → 15bps** — realistic costs
4. **T+1 enforcement** — realistic execution
5. **K=200 bootstrap** — statistical power

### Phase 2: Integrity (M-effort, some dependencies)
6. **DSR N-scoping fix** — mathematical correctness
7. **Lookahead guard** — prevent future leaks
8. **Survivorship bias** — clean universe
9. **OOS holdout** — prevent curve-fitting

### Phase 3: Robustness (M-effort, dependencies)
10. **Regime-aware filtering** — robustness across markets
11. **Lax excess thresholds** — reduce false positives
12. **Strict DSR 0.95** — mathematical rigor

---

## Key Gate Spec Numbers

- **DSR≥0.95 with N=10000:** demands annualized Sharpe≥2.01 (unattainable)
- **10,000+ scored evaluations:** zero passed
- **82% dupe bloat:** registry waste
- **K=200 Monte Carlo:** low statistical power
- **10-track union gate:** candidate promotes by clearing ANY ONE track

---

## Notes

- **h2h3_no_touch rule:** Evolution lessons dictate H2/H3 rules must not be touched for backtester config — constrains implementation scope
- **User directive:** "Continue if you have next steps" — autonomous continuation confirmed
- **Next step:** Delegate implementation to Jules or user for Phase 1 fixes
