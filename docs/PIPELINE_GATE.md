# PIPELINE_GATE — pipeline > Claude Fable 5 (30-day window)

> Rendered from docs/data/ops/ + .swarm/knowledge.jsonl + mnemosyne stats + quota-ledger.json. Gate per grilling Q15=A, Q17=C.

| Metric | Gate | Current | Source | Status |
|--------|------|---------|--------|--------|
| knowledge applied/shown | >0.3 | 0 / 89 (0.0) | .swarm/knowledge.jsonl | ❌ |
| episodic | >10 | 1 (was 0) | mnemosyne stats | 🟡 |
| Jules PR first-time green | >90% | TBD | ci.yml | ⏳ |
| Hunt PASS | ≥1 / all | 0 / 20+ preregistered candidates through wave-3 (see HUNT_MEGA_PROMPT v8 §4) | docs/data/eval_*.json | ❌ |
| Explorer p95 latency | <30s on wsb_sentiment_alpha.py:953 | ~40-60s (pre-shard; shard PRs released 08-26) | ops/metrics.json | ❌ |

> Refreshed 2026-08-26 after operator grill rulings (`vault 03-Decisions/2026-08-26-grill-rulings.md`):
> G5 dual-track diagnostic required in new evals; auditor rehearsal gates wave-4; wave sizing min-2
> when frontier-constrained; 6 stale upstream PRs closed; 3 queued Jules PRs released.

## Order (Q16=A)
1. ✅ Mnemosyne charmap fix + reindex + sleep 02:00 + backup 03:00
2. ✅ OPTIMIZATION_PLAYBOOK.md real (Muse Spark :xhigh/:low + bridges)
3. ⏳ Shard wsb_sentiment_alpha.py:953 + ops/signals.py:662 → <400 (Jules queues created 2026-08-21)
4. ⏳ Fix 	rial_ledger.py:545 DSR gate → 1 PASS

## Next action
Run 3 Jules PRs above, then re-render this gate via scripts/generate_strategy_data.py + hunt_runner.py status.
