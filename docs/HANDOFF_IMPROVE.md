# HANDOFF — Quant system self-improvement run (started 2026-09-10, 1.3-only, no fallback)

Read this first on every loop wakeup. Source of truth for pipeline state; update it as phases land.

## Orders (user)
Phased: 3 discovery + 3 flaw-hunts + 2 planners + impl batches of 3 until done. All opencode sessions
muse-spark-1.3-contributor-free, 2-3 subagents inside (sequential — parallel hangs this host).
Watchdog fixed+narrowed; VPN running (egress stays residential, bucket relief from ISP churn — do not depend on VPN).
New 2026-09-10: use https://github.com/ScrapeGraphAI/Scrapegraph-ai + https://github.com/d4vinci/Scrapling
for better data/strategies/skills (Batch 5 research task, not started).

## Model lock
opencode.json default = 1.3 only. 1.2 definition block REMOVED. No fallback anywhere. All prompts say 1.3 only.

## Done (audited ACCEPTED, L013 verified)
- D1/D2/D3 discovery → _quant_improve/session-discovery/
- F1 (23 flaws) / F2 (15) / F3 (38 gaps) → _quant_improve/session-flaws/
- P1 (12 gate items) + P2 (12 infra items, inline synthesis) → _quant_improve/session-plans/
- Batch 1: B1a union-gate+DSR, B1b KillSwitch fail-closed, B1c registry FileLock
- Batch 2: B2a WF wiring (inline contract fixes, 10/10 green), B2b broker gate (14/14), B2c breed hygiene (69 pass)
- Batch 3: B3a prereg fail-closed (6/6), B3b ledger wiring (29/29), B3c gatespec alignment (52 tests)
- Batch 4a: cost honesty 2.5bp + tier-aware fallbacks + guard-only regime telemetry (safety clean)
- Batch 4b: CI collect-guard step + LIVE-GATE-REVIEW.md doc (ratchet-proven, temp cleaned, ACCEPTED)
- Batch 4c: tail-hedge BRIEF.yaml + src/signals/tail_hedge_signal.py adapter (INACTIVE, fail-closed; calm 20.2 FLAT / stress 83.6 LONG verified inline on 1.3)
- Batch 5a: hunt/evolve taxonomy alias map in hunt_runner.py (+124/-0, 10/10 hunt tests, ACCEPTED)
- Batch 5b: scraping spike DONE inline on 1.3 (Scrapling ADOPT plain-tier ticket / Scrapegraph-ai PARK on LLM cost)

## Running / queued
- Batch 5 tail: S7 universe fail-closed DONE inline; S11 queue triage DONE inline (F3 orphan claim stale — queue is generator-fed/tracked; #13 ABANDONED as Awake-mirror dedup, rest stay Queued)
- Batch 6: G5 weakest-track raised (0.50/0.70→0.60/0.80) + G6 MLP steering removed (44/44 gatespec green); backup branch quant-improve-20260911 (d3bd30a); lessons L037-L040 written; FULL SUITE running

## Invariants (never break)
Paper-only. LIVE_TRADING_ENABLED stays False. Circuit breakers stay OFF (user order). Scoped files per prompt;
no-touch lists enforced. Every worker delivery gets independent rerun before ACCEPT. Bucket fits ~1 session —
serialize impl batches solo; park extras at headers-only (zero loss).
