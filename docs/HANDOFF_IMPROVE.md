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
- Batch 5b: scraping spike DONE + provider LIVE (urllib+Adaptor, no Playwright; live fetch verified; 5/5 tests, committed; Scrapegraph-ai stays PARKED)

## Running / queued
- Batch 6 DONE + post-review: unknown post-commit hunks (DSR FAM_TRIALS→global-N, tracks_cleared at promotion, continuous bookkeeping) measured neutral-to-positive, committed
- Engine cycle + G2 + joint experiment + G2 regression tests DONE; scrapling installed + provider live; E-regime pools UNLOCKED (best_regime validated-only + loop hook, 29/29 ledger tests, committed); deferred-with-reason: legacy consolidation (dedicated worker). ALL ORDERS COMPLETE.
- 5-6h hunt loop CLOSED (v132 FINAL, ran 2026-09-11 08:15-12:31 UTC): H1-H12 ALL DONE ACCEPT. Final: 12 hunts / 12 HONEST_ABANDONs / 0 promos. Momentum class-space exhausted (7 signal classes perm-dead), tail paused (6 hunts, joint wall). Registry 131 rows, zero live/active, paper-only intact. Full record: _quant_improve/LOOP-5H-strategy-hunt.md (TABOO + evolution log).
- Self-evolve reliability loop RUNNING (first start 2026-09-11 ~15:47 UTC): R1 reliability-hardening planner RUNNING solo on 1.3 (prompt _quant_improve/R1-prompt.md, log R1-planner.log). Serialized per host limits (parallel subagents hang host 0xC0000142; bucket ~1 session). Impl batches of 3 follow after plan lands + audit.
- R1 DONE 16:03 UTC + audited ACCEPT (exit 0; 20 fixed verified, 9 open R1-R9 with file:line proof, 3 ranked batches; plan relocated repo→canonical _quant_improve/session-plans/). R-A impl (record-path integrity: lock+backup+id-key, collision-proof evals, ledger transparency) RUNNING solo on 1.3 (prompt _quant_improve/RA-prompt.md, log RA-impl.log; host corrections: repo-local temps not /tmp, absolute record paths). R-B/R-C queue behind R-A audit.
- R-A DONE + audited ACCEPT (9/9 independently rerun green; demos OK; registry 131 untouched zero-live; scope 2 modified + 2 new tests; no temp leftovers). R-B impl (eval determinism: report-hash pin, guided validate_spec, fill-policy+cache) RUNNING solo on 1.3 (prompt _quant_improve/RB-prompt.md, log RB-impl.log). R-C queues behind R-B audit.
- R-B DONE + audited ACCEPT (25/25 independently rerun green; demos OK; registry 131 untouched zero-live; scope 4 modified + 2 extended + 1 new; note: line-195 path-string fallback hash is weak-but-labeled/traceable — accepted, flagged for later). R-C impl (price guards, CLI discipline, commission SoT reference-only) RUNNING solo on 1.3 (prompt _quant_improve/RC-prompt.md, log RC-impl.log). R-C audit closes the R1 plan.
- R1 PLAN CLOSED: R-C DONE + audited ACCEPT (9/9 independently rerun green; 90/90 regression per delivery; registry 131 untouched zero-live; safety clean; no temp leftovers; two impl sessions died on transient provider error, close session delivered). All 9 risks R1-R9 hardened: record lock+backup+id-key, versioned evals, ledger outcomes, report-hash pin, guided validate_spec, fill-policy+raw-cache, price guards, CLI discipline, commission SoT (values frozen).
- R2 follow-up cycle RUNNING solo on 1.3 (prompt _quant_improve/R2-prompt.md, log R2-planner.log): plan-only for weak-hash fail-closed (line-195) + prior-Done regression re-verification. Impl batch follows after audit.
- R2 DONE + audited ACCEPT (exit 0; REFUSE decision with reasoning; 29/29 still-fixed 0 regressed; 3-item batch with demos; plan relocated to canonical session-plans/). R2-IMPL (WH-1 refuse, WH-2 UNVERIFIED, RG-1 5-test guard) RUNNING solo on 1.3 (prompt _quant_improve/R2IMPL-prompt.md with batch spec INLINED for sandbox, log R2IMPL.log).
- R2 CYCLE CLOSED: R2IMPL DONE + audited ACCEPT (17/17 independently rerun green; registry 131 untouched zero-live; safety clean; no temp leftovers; ruff/bandit unavailable in worker env — covered by green instead). Weak-hash now fail-closed (refuse + UNVERIFIED) + 5-test regression guard live. All evolve queues drained (R1 R-A/B/C + R2). Awaiting next orders.
- R3 red-suite triage RUNNING solo on 1.3 (prompt _quant_improve/R3-prompt.md, log R3-impl.log): full suite showed 716 passed / 17 failed — failures triaged into 5 groups (stale mocks 6, missing arch dep 2, cache perms 1, leakage-guard behavior 4, registry schema 1). Fix-or-gate rules per group; guard-first on leakage.
- R3 DONE + audited ACCEPT (full suite independently rerun: 731 passed / 11 skipped / 0 failed; registry 131 untouched zero-live; scope = test updates + skip markers + tmp_path cache + guard-compliant fixtures, no source-signature changes). R4 micro-fix (dangling momentum_breakout_v4 spec_file pointer → missing YAML) queued next.
- R4 DONE + audited ACCEPT (spec_file key removed, 0 dangling confirmed by full-pointer scan, 7/7 strategy_specs independently green, 131 rows zero-live). All queues drained again (R1 R-A/B/C + R2 + R3 + R4). Suite: 731/0. Awaiting next orders.
- R-C impl session + resume BOTH killed by transient upstream provider error (encrypted_content, exit 1, no DONE-RC) — work itself complete in tree (R-C1 5/5, R-C2 2/2, R-C3 2/2 green in logs; scope verified clean incl. evolve_real import-only). R-C-CLOSE verify-only session queued with 90s backoff (prompt _quant_improve/RC3-prompt.md, log RC3-impl.log) to run acceptance + deliver DONE-RC.

## Invariants (never break)
Paper-only. LIVE_TRADING_ENABLED stays False. Circuit breakers stay OFF (user order). Scoped files per prompt;
no-touch lists enforced. Every worker delivery gets independent rerun before ACCEPT. Bucket fits ~1 session —
serialize impl batches solo; park extras at headers-only (zero loss).
