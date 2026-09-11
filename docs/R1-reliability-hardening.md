# R1 — Reliability Hardening Plan (planner-only, read-only mission)

- Date: 2026-09-11. Model lock: `opencode/muse-spark-1.3-contributor-free` only, sequential solo.
- Scope: plan document ONLY. Zero code edits, zero registry writes, zero network additions.
- Prerequisite note: `_quant_improve/session-flaws/` (F1/F2/F3), `session-plans/` (P1/P2),
  and `_quant_improve/LOOP-5H-strategy-hunt.md` **do not exist in this repo**
  (`git log --all -- _quant_improve` empty; directory absent on disk).
  Prior-phase flaw counts (F1=23, F2=15, F3=38) are therefore UNVERIFIABLE locally and are
  NOT trusted below. The inventory in §1 is rebuilt from what IS verifiable:
  `docs/HANDOFF_IMPROVE.md` Done list × current-code grep (2026-09-11).

## 1. Residual-risk inventory

### 1a. FIXED (Done-list item → current-code verification, all grepped 2026-09-11)

| # | Done item | Verification (file:line) | Status |
|---|-----------|--------------------------|--------|
| 1 | B1a union-gate + DSR | `evolve_real.py`: 21 DSR/deflated hits incl. global-N | FIXED |
| 2 | B1b KillSwitch fail-closed | `src/ops/killswitch.py:37-52` fail-closed strings; dual-flag gate `:128-137` | FIXED |
| 3 | B1c registry FileLock | `evolve_real.py:849-880`, `scripts/evolve_generations.py:468-499` FileLock+tmp+os.replace | FIXED **but scoped** (see R1) |
| 4 | B2a WF wiring | `src/backtest/walk_forward_engine.py` present | FIXED |
| 5 | B2b broker gate | `src/execution/universal_broker.py:123-137` dual-gate | FIXED |
| 6 | B2c breed hygiene | `evolve_real.py:740 breed_proposals` + `scripts/ledger_distill.py` blocked-combos hook | FIXED |
| 7 | B3a prereg fail-closed | `src/ops/preregistration.py:67-126 verify_prereg_freeze` (SHA-256 + claim binding) | FIXED |
| 8 | B3b ledger wiring | `src/backtest/defend/trial_ledger.py` + `scripts/preregister.py:17-78` ledger append | FIXED **but scoped** (see R9) |
| 9 | B3c gatespec alignment | `docs/GATESPEC_TRACKS.md`, `docs/GATESPEC38_TRACKS.md` present | FIXED |
| 10 | Batch 4a cost honesty 2.5bp | `evolve_real.py:411 COST_COMMISSION_BPS = 2.5` | FIXED **but scoped** (see R8) |
| 11 | Batch 4b CI collect-guard | `.github/workflows/ci.yml:40-43` `--collect-only` gate | FIXED |
| 12 | Batch 4b LIVE-GATE-REVIEW.md | `docs/build/LIVE-GATE-REVIEW.md` present | FIXED |
| 13 | Batch 4c tail-hedge adapter | `src/signals/tail_hedge_signal.py` present, INACTIVE | FIXED |
| 14 | Batch 5a hunt taxonomy alias | `scripts/hunt_runner.py:21` alias map | FIXED |
| 15 | Batch 5b scrapling provider | `src/research/scrapling_provider.py` present | FIXED |
| 16 | Batch 6 DSR global-N / tracks_cleared / bookkeeping | `tracks_cleared` in `evolve_real.py` + 12 hunt scripts + `reconstruct_registry.py` | FIXED |
| 17 | G2 CPCV conjunction | `evolve_real.py` + `src/backtest/validators/statistical.py` + `walk_forward_engine.py` | FIXED |
| 18 | E-regime pools best_regime | `evolve_real.py` + `src/backtest/defend/trial_ledger.py` | FIXED |
| 19 | Paper-only invariant | registry 131 rows, sample statuses all `paper`; `LIVE_TRADING_ENABLED` default 0 (`src/risk/position_sizing.py:16`) | FIXED |
| 20 | Hunt loop H1–H12 record | `hunts/high_exposure_momentum/20260911-h{10,11,12}-*/brief.yaml+candidates+results` on disk | FIXED (artifacts present) |

### 1b. OPEN (residual risks, each verified in current code — N=9)

- **R1 — record path rewrites registry unlocked, family-keyed.** `src/ops/preregistration.py:183-217`:
  plain `open(registry_path,'w')`, no FileLock (unlike evolve paths §1a-#3), no backup, and matches
  rows by `family` (`next(... if s.get("family")==family)`), so recording one candidate mutates the
  first same-family row of 131. Root cause of incident (a).
- **R2 — eval filename collides.** `:177-181`: `cycle{cycle}_eval_{family}.json` opened `'w'`;
  a second record for the same family+cycle silently overwrites the first eval JSON.
- **R3 — record reads a shared mutable report.** `:161-171`: `record_evaluation` ingests
  `docs_dir/backtest_report.json` (single shared path, no content-hash pin, no freeze binding);
  workers re-running finals between interim read and record get different numbers than recorded.
  Root cause of incident (c). Eval JSON carries `spec_fingerprint` but no report-hash.
- **R4 — `validate_spec` two-arg fragility.** `src/ops/strategy_registry.py:17`
  `validate_spec(spec, filepath)`; all in-repo callers pass 2 args (verified: registry:147,
  hunt_runner:293, evaluate_candidate:330, tests), so NO current in-repo TypeError — but any
  stale one-arg call pattern (incident b) fails with bare TypeError instead of a guided error.
- **R5 — `ffill().bfill()` + caching of filled frames.** `src/data/market_data.py:47-56`:
  leading-NaN backfill fabricates pre-history prices; the FILLED frame is then written to the
  parquet cache, baking fills into cache. No zero-init exists in-repo (incident d's exact trap is
  worker-side), but the adjacent in-repo risk is real.
- **R6 — zero-init + ffill no-op trap has no guard.** No constructor/validator in-repo rejects an
  all-zero price frame, so `pd.DataFrame(0,...)` + `ffill()` (no-op on zeros) yields a silent
  zero-price series that passes shape checks. Worker-side trap, in-repo hardening missing.
- **R7 — chained-shell record invocations rejected on this host.** Tooling observation (incident e;
  host fork-exhausts on parallel/chained shells, cf. HANDOFF §Running). No in-repo code to fix;
  hardening = single-command record discipline + docs. Verified as process risk, not code bug.
- **R8 — commission single-source-of-truth split.** `evolve_real.py:411` 2.5bp vs
  `config/risk_config.py:28,31` 1.0bp vs `src/evolution/agentquant_harness.py:200` default 1.0bp.
  Three live commission assumptions across paths; joint experiment (`scripts/joint_coevolution_experiment.py:75-104`)
  snapshots/restores the evolve one only.
- **R9 — ledger double-record path can silently drop rows.** `scripts/preregister.py:64-78`:
  `_append_prereg_trial_to_ledger` treats content-hash collision (`sha is None`) as "already logged"
  WARNING; the record path and loop path can therefore disagree on ledger contents without failing.

## 2. Hunt-loop incident log (2026-09-11, each re-verified in current code)

- **(a) preregister record-tool clobber of registry rows.** VERIFIED: R1 (`preregistration.py:190-217`).
  Family-keyed match + unlocked `'w'` rewrite. (H5 worker restore consistent with this mechanism.)
- **(b) `validate_spec(spec, filepath)` two-arg vs one-arg callers.** VERIFIED AS LATENT:
  signature is two-arg (`strategy_registry.py:17`); zero one-arg callers remain in-repo
  (all 8 call sites pass 2 args). Stale one-arg usage raises bare `TypeError`, not a guided error.
- **(c) interim-vs-recorded eval drift.** VERIFIED: R3 (`preregistration.py:161-171` shared
  `backtest_report.json`, unpinned). Any final re-run between interim read and `record` changes
  recorded numbers; TABOO-line corrections were the symptom, this read path is the disease.
- **(d) zero-init DataFrame + ffill no-op trap.** VERIFIED AS ADJACENT: no zero-init constructor
  in-repo; the in-repo half is R5 (`market_data.py:47-56` fill-then-cache). H2 root-cause pattern
  (zeros → ffill no-op → silent flat series) has no in-repo guard (R6).
- **(e) chained-shell record calls permission-rejected.** VERIFIED AS PROCESS (R7): no in-repo
  shell-chain code; host rejects chained/parallel shells (HANDOFF-documented fork-exhaust).
  Hardening is procedural (single record command per invocation), not a code patch.

## 3. Ranked hardening batches (3 items each)

### Batch R-A — record-path integrity (highest leverage; fixes incident a + R2 + R9)

**R-A1. Lock + backup + id-keyed registry update in `record_evaluation`.**
- Problem: R1 (unlocked, family-keyed, no backup).
- Failing-behavior demo: `cp strategies/registry.json /tmp/reg.before.json &&
  PYTHONPATH=. python scripts/preregister.py record hunts/high_exposure_momentum/20260911-h12-momentum/candidates/high_exposure_momentum_h12.yaml --verdict HONEST_ABANDON --cycle 28 &&
  python3 -c "import json;a=json.load(open('/tmp/reg.before.json'));b=json.load(open('strategies/registry.json'));print([(s.get('id'),s.get('verdict')) for s in b['strategies'] if s.get('family')=='high_exposure_momentum'])"`
  (shows first same-family row mutated regardless of candidate id; restore from /tmp copy).
- Fix shape: mirror `evolve_generations.py:468-499` — FileLock + tmp + os.replace;
  match rows by spec `id` (fall back to family only when id absent); write `.bak-<timestamp>` beside registry before replace.
- Test: `tests/ops/test_prereg_record_integrity.py` — 4 tests (id-keyed match, lock file created, backup written, concurrent-record no-loss).
- Scoped files: `src/ops/preregistration.py`, `tests/ops/test_prereg_record_integrity.py` (new).
- No-touch: `strategies/registry.json` (fixture copies only), `src/ops/killswitch.py`, `src/risk/*`, `src/execution/*`, `.github/*`.

**R-A2. Collision-proof eval filenames.**
- Problem: R2 (same family+cycle record overwrites prior eval JSON).
- Failing-behavior demo: `PYTHONPATH=. python scripts/preregister.py record <spec> --verdict FAIL --cycle 28 && sha1=$(sha256sum docs/data/cycle28_eval_<family>.json) && PYTHONPATH=. python scripts/preregister.py record <spec> --verdict HONEST_ABANDON --cycle 28 && sha256sum docs/data/cycle28_eval_<family>.json`
  (second record destroys first; hashes differ, first verdict unrecoverable).
- Fix shape: refuse overwrite (`FileExistsError`, like `freeze_preregistration:40-41`) OR
  suffix `_<verdict>-<shortsha>`; record path returns the exact filename.
- Test: same file as R-A1 — 2 tests (second record refuses or versions; first file byte-identical).
- Scoped files: `src/ops/preregistration.py`, `tests/ops/test_prereg_record_integrity.py`.
- No-touch: `docs/data/cycle*_eval_*.json` (read-only fixtures), registry, live-trading flags.

**R-A3. Ledger double-record transparency.**
- Problem: R9 (content-hash "already logged" silently drops loop-vs-record disagreements).
- Failing-behavior demo: `TRIAL_LEDGER_PATH=/tmp/trials.jsonl PYTHONPATH=. python scripts/preregister.py record <spec> --verdict FAIL --cycle 28 && TRIAL_LEDGER_PATH=/tmp/trials.jsonl PYTHONPATH=. python scripts/preregister.py record <spec> --verdict FAIL --cycle 28`
  (second run prints "already logged"; ledger row count unchanged — silent divergence between record invocations).
- Fix shape: return structured outcome (`appended|duplicate|failed`) from `_append_prereg_trial_to_ledger`;
  `record` exit code stays 0 but prints machine-readable `ledger=<outcome>`; document which path owns ledger truth (loop).
- Test: `tests/ops/test_prereg_ledger_outcome.py` — 3 tests (first appends, repeat reports duplicate, corrupt eval JSON reports failed, record kept).
- Scoped files: `scripts/preregister.py`, `tests/ops/test_prereg_ledger_outcome.py` (new).
- No-touch: `src/backtest/defend/trial_ledger.py` internals, `run-logs/trials.jsonl` (use TRIAL_LEDGER_PATH override).

### Batch R-B — eval determinism (fixes incidents c + b + R5)

**R-B1. Pin report content-hash at record time.**
- Problem: R3 (shared mutable `backtest_report.json`).
- Failing-behavior demo: `sha256sum docs/data/backtest_report.json && PYTHONPATH=. python scripts/run_research.py 2>/dev/null; sha256sum docs/data/backtest_report.json`
  (report bytes change under the reader; a record taken before/after differs with identical spec).
- Fix shape: `record_evaluation` hashes the report bytes it consumed, stores `report_sha256` in the
  eval JSON next to `spec_fingerprint`; add `verify` subcommand check comparing recorded hash to current file
  (mismatch → loud warning naming both hashes).
- Test: `tests/ops/test_preregistration.py` (extend) — 3 tests (hash recorded, tampered report detected by verify, eval-path branch also hashed).
- Scoped files: `src/ops/preregistration.py`, `scripts/preregister.py` (verify), `tests/ops/test_preregistration.py`.
- No-touch: report producers (`scripts/comprehensive_backtest_report.py`), registry schema, gates.

**R-B2. Guided `validate_spec` signature.**
- Problem: R4 (bare TypeError on stale one-arg calls).
- Failing-behavior demo: `PYTHONPATH=. python3 -c "from src.ops.strategy_registry import validate_spec; validate_spec({'id':'x'})"`
  (bare `TypeError: missing 1 required positional argument: 'filepath'` — no guidance).
- Fix shape: default `filepath: str = "<unknown>"` + explicit `TypeError` message naming the
  two-arg contract and pointing at `hunt_runner.py:293` as the canonical call. No behavior change for 2-arg callers.
- Test: `tests/test_strategy_registry.py` (extend) — 2 tests (one-arg raises guided TypeError; filepath defaults into error text).
- Scoped files: `src/ops/strategy_registry.py`, `tests/test_strategy_registry.py`.
- No-touch: all 8 existing call sites (must stay 2-arg), crypto session rules (`:77-86`).

**R-B3. Fill-policy + cache discipline in `MarketDataManager`.**
- Problem: R5 (bfill fabricates leading prices; filled frames cached).
- Failing-behavior demo: `PYTHONPATH=. python3 -c "
  import pandas as pd
  from src.data.market_data import MarketDataManager
  df = pd.DataFrame({'close':[None,None,100.0]}, index=pd.date_range('2020-01-01',periods=3))
  print(df.ffill().bfill())"` (leading Nones become 100.0 — invented pre-history).
- Fix shape: add explicit `fill_policy` (`ffill_only` default; `ffill_bfill` opt-in with logged warning);
  cache the RAW frame, apply fills after cache load; emit `logger.warning` with filled-cell counts.
- Test: `tests/data/test_market_data_fill.py` (new) — 4 tests (default never backfills leading NaN, opt-in bfill warns, cache stores raw, filled-cell counts logged).
- Scoped files: `src/data/market_data.py`, `tests/data/test_market_data_fill.py` (new).
- No-touch: provider chain (`src/data/providers/*`), cache key format, `qlib_topk.py:94` (separate call site, out of scope).

### Batch R-C — hunt-loop operability (fixes incident d guard + e discipline + R8)

**R-C1. Zero-frame / flat-frame guard helper.**
- Problem: R6 (no in-repo rejection of all-zero / all-flat price frames).
- Failing-behavior demo: `PYTHONPATH=. python3 -c "
  import pandas as pd
  s = pd.Series([0.0]*100); print('ffill no-op:', s.ffill().equals(s), '| flat:', s.nunique()==1)"`
  (shape checks pass; series is economically meaningless).
- Fix shape: `src/data/price_guards.py:assert_tradable_prices(df)` — rejects all-zero / all-NaN /
  zero-variance frames with `ValueError` naming the offending symbol+column; wire into
  `MarketDataManager.fetch_data` post-fill and document for hunt workers (no worker code changes here).
- Test: `tests/data/test_price_guards.py` (new) — 5 tests (zeros rejected, NaN rejected, flat rejected, sane frame passes, NaN-frame error names symbol).
- Scoped files: `src/data/price_guards.py` (new), `src/data/market_data.py` (one call), `tests/data/test_price_guards.py` (new).
- No-touch: providers, backtest engines, registry, thresholds elsewhere.

**R-C2. Single-command record discipline (procedural, near-zero code).**
- Problem: R7 (chained-shell record calls rejected on host).
- Failing-behavior demo: `PYTHONPATH=. python scripts/preregister.py freeze <spec> --claim "x" --cycle 99 && PYTHONPATH=. python scripts/preregister.py record <spec> --verdict FAIL --cycle 99`
  (documents the rejected pattern; the passing pattern is two separate invocations — demo asserts both succeed serially).
- Fix shape: HUNT_PROTOCOL-adjacent doc note (`docs/HUNT_PROTOCOL.md` append-only section, ≤20 lines) +
  `scripts/preregister.py --help` epilog line: "run freeze/record as separate commands; do not chain with &&".
  No behavior change.
- Test: `tests/ops/test_prereg_cli_single.py` (new) — 2 tests (freeze-then-record serially via subprocess succeeds; help text contains single-command note).
- Scoped files: `docs/HUNT_PROTOCOL.md` (append ≤20 lines), `scripts/preregister.py` (help text only), `tests/ops/test_prereg_cli_single.py` (new).
- No-touch: all behavior code paths, CI workflows, registry.

**R-C3. Commission single source of truth.**
- Problem: R8 (2.5 vs 1.0 vs 1.0 across three paths).
- Failing-behavior demo: `grep -n "COST_COMMISSION_BPS = \|EQUITY_COMMISSION_BPS = \|commission_bps: float = " evolve_real.py config/risk_config.py src/evolution/agentquant_harness.py`
  (three live values printed; they disagree).
- Fix shape (proposal, no consensus claimed): canonical constant lives in `config/risk_config.py`;
  `evolve_real.COST_COMMISSION_BPS` and harness default import it (no value change in this batch —
  reconciliation of 2.5 vs 1.0 is a QUANT decision for the user, explicitly out of scope);
  joint experiment snapshot/restore covers the canonical import.
- Test: `tests/test_commission_sot.py` (new) — 2 tests (evolve value equals canonical; harness default equals canonical).
- Scoped files: `config/risk_config.py`, `evolve_real.py` (import only), `src/evolution/agentquant_harness.py` (default only), `tests/test_commission_sot.py` (new).
- No-touch: numeric values (no 2.5↔1.0 change), cost application math (`evolve_real.py:445`, harness `:229`), live-trading flags.

## 4. Measurable acceptance bar per batch

- **R-A green:** `PYTHONPATH=. pytest tests/ops/test_prereg_record_integrity.py tests/ops/test_prereg_ledger_outcome.py`
  9/9 pass; fail-closed demos: re-run R-A1/R-A2/R-A3 demo commands — second record refuses-or-versions,
  backup file exists, ledger outcome line printed. Registry row count before == after on fixture copies.
- **R-B green:** `PYTHONPATH=. pytest tests/ops/test_preregistration.py tests/test_strategy_registry.py tests/data/test_market_data_fill.py`
  all pass (3+2+4 new/extended green, zero regressions); fail-closed demos: tampered report → verify warns
  with both hashes; one-arg `validate_spec` → guided TypeError; leading-NaN frame → stays NaN under default policy.
- **R-C green:** `PYTHONPATH=. pytest tests/data/test_price_guards.py tests/ops/test_prereg_cli_single.py tests/test_commission_sot.py`
  9/9 pass; demos: zero-frame rejected with symbol named; freeze→record serially green; three commission
  imports resolve to one canonical value (values themselves unchanged).
- **Global:** `ruff check evolve_real.py` + `bandit -r src/` clean per repo preflight; paper-only invariant
  re-verified post-batch (131 rows, zero live/active, `LIVE_TRADING_ENABLED` default 0).

## 5. Explicit NON-goals

1. No live-trading flags (no `LIVE_TRADING_ENABLED`, KillSwitch, broker-gate, or executor changes).
2. No circuit-breaker changes (none enabled; none added).
3. No registry promotions (no rows added/ported; HONEST_ABANDON-only posture preserved; fixture copies only).
4. No network additions (no new providers, scrapers, or egress; Scrapegraph-ai stays PARKED).
5. No threshold/gate-value changes (no Sharpe/DSR/perm/CPCV/commission-number tuning — R-C3 unifies the
   reference, changes no value).
6. No `_quant_improve` backfill (F1/F2/F3/P1/P2/LOOP docs stay absent; this plan does not reconstruct them).
