# PIPELINE_GATE — pipeline > Claude Fable 5 (30-day window)

> Rendered from docs/data/ops/ + .swarm/knowledge.jsonl + mnemosyne stats + quota-ledger.json. Gate per grilling Q15=A, Q17=C.

| Metric | Gate | Current | Source | Status |
|--------|------|---------|--------|--------|
| knowledge applied/shown | >0.3 | 0 / 89 (0.0) | .swarm/knowledge.jsonl | ❌ |
| episodic | >10 | 1 (was 0) | mnemosyne stats | 🟡 |
| Jules PR first-time green | >90% | TBD | ci.yml | ⏳ |
| Hunt PASS | ≥1 /4 families | 0/16 | docs/data/eval_*.json | ❌ |
| Explorer p95 latency | <30s on wsb_sentiment_alpha.py:953 | ~40-60s (pre-shard) | ops/metrics.json | ❌ |

## Order (Q16=A)
1. ✅ Mnemosyne charmap fix + reindex + sleep 02:00 + backup 03:00
2. ✅ OPTIMIZATION_PLAYBOOK.md real (Muse Spark :xhigh/:low + bridges)
3. ⏳ Shard wsb_sentiment_alpha.py:953 + ops/signals.py:662 → <400 (Jules queues created 2026-08-21)
4. ⏳ Fix 	rial_ledger.py:545 DSR gate → 1 PASS

## Next action
Run 3 Jules PRs above, then re-render this gate via scripts/generate_strategy_data.py + hunt_runner.py status.
