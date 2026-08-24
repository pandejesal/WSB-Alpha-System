# HUNT MEGA PROMPT — WSB Alpha Edge Hunt (self-regenerating)

> OPERATOR INSTRUCTION: paste this entire file into a fresh OpenCode session opened in
> `C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-build`.
> The active session maintains this file (bump version, update ledger/slate) and tells
> you to re-paste it whenever context runs low or a wave completes.

version: 4 · generated: 2026-08-25 · change: wave-1 results folded into §4 ledger (H1/H2/H3 honest FAIL); §6 slate replaced with wave-2 batch frozen @ ddc1fe4 · superseded-by: —

## 0. First actions (before ANY research)

1. Read Vault (`C:\Users\DELL\Documents\Obsidian Vault`): `99-Meta/Vault Guide.md`,
   `01-Context/Workflow.md`, `03-Decisions/2026-08-24-edge-hunt-charter.md`, and the
   newest entries in `05-Session-Logs/`.
2. Recall memory: `memory_recall <task>` + `memory_recall_global <task>`.
3. Read in-repo law, in order: `workspace/CLAUDE.md`, `workspace/CONTEXT.md`,
   `workspace/_config/edge-gates.md`, `docs/HUNT_PROTOCOL.md`,
   `docs/OPTIMIZATION_PLAYBOOK.md`, then §4 of this file.
4. Only then draft Wave preregistrations. Preregistration is ALWAYS committed before any
   in-sample testing. No exceptions.

## 1. Mission

Find at least one strategy whose out-of-sample, net-of-cost performance beats SPY
buy-and-hold on **both CAGR and Sharpe** (identical engine, window, fee model) — i.e.
"makes more returns than the market on average" — while passing all six edge gates.

Provisional baseline: `us_momentum_top5` already clears this bar in-engine
(OOS CAGR 95.1% / Sharpe 1.74 vs SPY 1.47) with declared survivorship-bias and
melt-up-era caveats. Treat it as the incumbent to beat or confirm, not as mission
failure. A win counts fully only when the **paper track record confirms it**: green
months must show SPY-excess, not merely absolute gains.

## 2. Stopping rule

Run indefinitely, in rolling waves, until either (a) the operator stops you, or
(b) the §1 bar is met and paper-confirmed. There is NO time-box. Your context is finite;
§8 makes the hunt immortal anyway.

## 3. The six edge gates (verbatim, non-negotiable)

1. Pre-registration committed to `docs/data/` BEFORE any in-sample testing.
2. In-sample significance p ≤ 0.05 (borderline ≈0.05 is FAILURE, never encouragement).
3. Combinatorially purged cross-validation passes.
4. Walk-forward positive across folds.
5. Permutation-null survival.
6. Positive Deflated-Sharpe ledger entry in `docs/data/eval_<id>.json`.

Kill criteria: falsified IS, WF fail, over-parameterization. Overfitting smells: param
bloat, post-hoc universe/window changes, metric cherry-picking. Any FAIL is recorded
honestly like topic07/H-SLX-1; static/canonical configs stay canonical until beaten
under these rules.

## 4. Closed-directions ledger (cite before retrying anything here)

| Direction | Outcome | Evidence |
|---|---|---|
| ML on entries (GBR weekly decile) | FAIL | `docs/data/cycle3_ml_evaluation.json` |
| ML overlays on cores, 17 variants | FAIL 17/17 | decision `2026-08-16-ml-overlay.md` |
| ML exits, SL-adjusted labels (H-SLX-1) | FAIL all decisive gates | `docs/data/ml_sl_exit_prereg.md`, `eval_ml_sl_exit.json` |
| Round 1 candidate families (11) | 5 FAIL / 6 ABANDON | `round1_consolidation.json` |
| RSI(2)-entry family | saturated; 8 candidates, 0 pass (round 3.5) | `hunt-lessons.md` |
| Confluence/trend/surge universal signal stack | regime CLOSED 2026-08-14 | `improvement_regime_conclusion.md` |
| Mega-cap-only momentum core, Universe A bare scoping (Wave-1 H1) | FAIL all gates (G2 p=0.056, G4 fold-share 2.97) | `docs/data/eval_wave1_h1.json` |
| FRED RISK_ON label gate on momentum core (Wave-1 H2) | FAIL all gates despite charter-bar pass | `docs/data/eval_wave1_h2.json` |
| Vol-target sizing m=clamp(0.15/σ̂21d,.25,1) on incumbent, absolute-excess gates (Wave-1 H3) | FAIL G2/G3/G5; G4+charter+primary pass; obs 1.374 < null MEAN | `docs/data/eval_wave1_h3.json` |

Standing rule: any hypothesis overlapping a listed family must cite that failure and
name its CHANGED CONDITIONS in `prior_art.md`. The closure explicitly excluded four
lanes; exits are now also tested-and-closed, and wave-1 closed the absolute-excess
forms of universe scoping, macro gating, and sigma-state sizing.

Wave-1 diagnosis (mine this): under the dominant 2024–26 drift regime, ANY long-biased
path's absolute OOS excess sits inside its own block-shuffle null — H3's observed
excess Sharpe fell BELOW its permutation-null mean. Absolute-excess gate batteries
cannot separate overlay value from beta drift in this window. Wave-2 therefore tests
PAIRED INCREMENTS (overlay-minus-incumbent delta series), not absolutes. Remaining
open lanes: sizing delta (W2-H1/W2-H2), price-derived gating on the scoped core
(W2-H3), new data (H4).

## 5. Wave protocol (rolling)

- Each wave = ONE preregistration batch of 4–6 hypotheses
  (`docs/data/<id>_prereg.md` + `workspace/stages/01_hypothesis/output/{hypothesis_brief.yaml,prior_art.md}`),
  committed before testing, tested serially, every result ledgared honestly
  (HONEST_NO_OP if nothing passes).
- Failures feed the next wave's slate. Never tune post hoc — a new idea is a new
  preregistration with declared changed conditions.

## 6. Approved Wave-2 slate (status @ v4)

Wave-1 outcome: H1 FAIL / H2 FAIL / H3 FAIL — all honest, ledgered in §4.
H4 DEFERRED pending dataset hash-lock. Incumbent `us_momentum_top5` remains
canonical until beaten under rules.

Three new hypotheses PREREGISTERED — frozen specs committed 2026-08-25 at repo
commit `ddc1fe4` (gate-1 provenance; wave-2 DSR trials charged {w2h1:1, w2h2:1,
w2h3:1}; h4 carried {h4:3}). NO in-sample runs exist yet. Next session's job:
SERIAL single-file testing in order W2-H1 → W2-H2 → W2-H3 (all local-data-ready;
extend the `scripts/wave1_h3_test.py` engine lineage), then H4 once its dataset
is acquired and hash-locked.

1. **W2-H1 Vol-target sizing DELTA test** — PREREGISTERED
   `docs/data/wave2_h1_voltarget_delta_prereg.md`. m_t formula byte-identical to
   wave-1 H3 (zero parameter changes, anti-p-hacking); ALL five statistical
   gates computed on the paired daily overlay-minus-incumbent delta series;
   charter bar AND primary Sharpe margin (+0.10) unchanged.
2. **W2-H2 Drawdown-ratchet sizing DELTA test** — PREREGISTERED
   `docs/data/wave2_h2_drawdown_ratchet_delta_prereg.md`. Different state
   variable (own-equity drawdown depth): m_t = clamp(1 - DD_t/0.20, 0.25, 1.00)
   at month-ends; same paired-delta gate machinery as W2-H1; extra frozen claim:
   overlay OOS maxDD shallower than -30%.
3. **W2-H3 Absolute-momentum gate inside Universe A** — PREREGISTERED
   `docs/data/wave2_h3_absmom_gate_prereg.md`. Six gates verbatim from the
   wave-1 H1 spec; price-derived gate = EW Universe-A index 12-1 return > 0 at
   month-end else cash; exec_delay 1 bar on ALL orders including gate flips;
   no SMA fallback permitted.
4. **H4 Politician-trade replication + Cramer follow-vs-fade pair** — CARRYOVER,
   prereg `docs/data/wave1_h4_poltrade_cramer_prereg.md` UNCHANGED. Next session
   FIRST acquires STOCK Act PTRs + public Cramer records via free endpoints,
   hash-locks them (SHA-256 recorded in the run artifact), then tests under the
   frozen spec; <40 events/arm ⇒ INSUFFICIENT_POWER no-op.

## 7. Data policy — FREE TIER ONLY

Pre-authorized: local OHLCV panel (`market_data_2019_2026/ohlcv/`, gitignored,
~1900 tickers 2019–2026 full OHLCV), `market_data.duckdb`,
`data/cache/fred_historical_regimes.json` (path corrected v3; labels
RISK_ON/NEUTRAL/RISK_OFF/STAGFLATION, daily 2003-01-02..2026-08-14), FRED macro
series, yfinance fundamentals,
the existing sentiment/research pipeline (`src/research/`), crypto OHLCV,
STOCK Act PTR filings, publicly accessible Cramer pick records.

Requires EXPLICIT operator approval before use: paid APIs of any kind
(FMP, Quiver Quantitative paid, Unusual Whales, etc.). Never store secrets anywhere.

## 8. Self-regeneration (MANDATORY)

At every wave boundary OR as context nears exhaustion:

1. Update THIS file: bump `version`, fold new results into §4's ledger, revise §6 slate
   for the next wave, keep everything else stable.
2. `git add docs/HUNT_MEGA_PROMPT.md && git commit && git push` (conventional message,
   e.g. `docs: regenerate hunt mega prompt vN`).
3. Tell the operator verbatim: "Paste docs/HUNT_MEGA_PROMPT.md into a fresh session."

## 9. Session discipline

- **LIVE TRADING DISABLED — paper only, fail-closed.** Anything enabling live execution
  must state paper-only and refuse.
- Report to the operator roughly every 35 minutes. Auto-proceed OFF unless the operator
  issues an explicit directive.
- NEVER run full/batch test suites; serial single-file verification only.
- Commits: conventional style; completed runs use `icm: run <date-slug>`; push to
  `origin/main` at milestones.
- Write-backs every stage/run: vault session-log lines
  (`05-Session-Logs/YYYY-MM-DD.md`), one atomic `memory_store` fact per durable
  finding, gate/eval JSONs in `docs/data/`.
- Benchmark convention everywhere: SPY buy-and-hold, same engine/window/fees, net.

## 10. Environment map

- Repo: `C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-build`
  (standalone clone of github.com/pandejesal/WSB-Alpha-System, branch main).
  After upstream Jules PR merges: `git pull --ff-only` FIRST.
- Signals: `src/ops/signals.py` (`get_us_momentum_top5_signal` et al.).
- Engine references: `scripts/ml_sl_exit_test.py` (portfolio sim + null machinery),
  `scripts/evaluate_candidate.py`, cycle3 engines.
- Strategy registry: `strategies/registry.json` + YAMLs; validation `scripts/port_validation.py`.
- ICM loop: `workspace/CLAUDE.md` (L0), `stages/01–04` contracts, `_config/edge-gates.md`.
- Results ledger: `docs/data/*.json|md`; preregs live beside results.
- Data: `market_data_2019_2026/ohlcv/*.csv`, `market_data.duckdb`,
  `data/fred_historical_regimes.json`, `cache/cycle3_13f_ticker_map.json`.
- Memory layers: Mnemosyne CLI (`mnemosyne`) + plugin tools; Obsidian vault at
  `C:\Users\DELL\Documents\Obsidian Vault`; mirror script
  `06-Mnemosyne/tools/build_mirror.py`.

## 11. Model routing addendum — which model does what, at what effort

> Slugs match `~/.config/opencode/opencode.jsonc` exactly — do not rename.
> Precedence: §§1–10 win on WHAT must be done; §11 wins on WHICH model and EFFORT
> does it. Per §8, this section is STABLE: wave regenerations bump `version` and
> leave §11 byte-identical unless the operator orders a change.

### 11.1 Roster (as configured — respect these caps)

| Role name | Slug | Ctx in/out | Notes |
|---|---|---|---|
| MAIN | opencode-go/ox-alpha-free | 128K/128K | session default; strongest coder per operator's independent tests |
| AUDITOR | opencode/nemotron-3-ultra-free | 128K/16K-out | different vendor than MAIN by design; audits stay terse |
| BUILDER | opencode/muse-spark-1.2-contributor-free | 128K/128K | only model exposing effort variants (minimal..xhigh) |
| SCRAPER-BUILDER + CLERK | opencode/mimo-v2.5-free | 128K/128K | tool-use specialist; token-efficient → cheapest chore lane |
| RESEARCHER | opencode/hy3-free | 64K-in/262K-out | best search agent; scoped excerpts ONLY |

### 11.2 Session roles

- **MAIN = opencode-go/ox-alpha-free.** Owns §0 law chain, wave slate drafting,
  prereg authorship, ALL test execution (serial single-file), ledgers, §8 regeneration.
- If MAIN is ever swapped, only AUDITOR may inherit the seat without rewriting §11.

### 11.3 Subagent routing

| Job class | Model | Effort | Notes |
|---|---|---|---|
| Adversarial gate audit (prereg pre-commit review; cold eval_<id>.json read) | AUDITOR | max | MUST remain non-OX lineage |
| Web research: STOCK Act PTRs, Cramer records, prior art | RESEARCHER | high | returns URLs+quotes, never conclusions-as-facts |
| Engine/script implementation | BUILDER | high (xhigh for stats code) | writes code, never runs tests |
| Scraper engineering against live filing endpoints | SCRAPER-BUILDER | high | writes code, never runs tests |
| Ledger templating, vault log lines, memory_store facts, commit msgs, reports | CLERK (= MiMo-V2.5) | low | DEFERS to MAIN-inline whenever a scraper build is actively running in the same wave |
| Gate-verdict tie-break (MAIN vs AUDITOR disagree) | RESEARCHER | max | if disputed item came FROM hy3, tiebreak via SCRAPER-BUILDER |

### 11.4 Reasoning-effort law

MAX=xhigh where model variants exist (BUILDER); otherwise state intended level
explicitly in every Task prompt (adaptive-thinking plugin handles the rest).

- **MAX**: prereg authorship, purged-CV/permutation/DSR design, gate verdicts,
  wave-slate drafting, §8 regeneration edits, adversarial audits, tie-breaks.
- **HIGH**: engine/script/scraper implementation, data validation, research synthesis.
- **LOW**: templating, vault logs, memory facts, commits, 35-min status reports (CLERK).
- MAIN idles at HIGH between waves, drops to LOW for chores only when CLERK is
  unavailable, and is ALWAYS at MAX whenever anything touches §3's six gates.

### 11.5 Verification law (non-negotiable)

1. Every subagent response is UNTRUSTED INPUT until MAIN verifies it.
2. Only MAIN executes tests. Builders write; MAIN runs serial single-file checks
   and reads raw output itself. CLERK never computes or alters any number — it
   only reformats values MAIN hands it verbatim.
3. No number enters docs/data/ unless MAIN executed the run producing it.
4. Each gate verdict requires two lineages: producer (OX Alpha) + cold auditor
   (Nemotron Ultra). Disagreement ⇒ verdict = FAIL, recorded honestly (fail-closed).
5. Escalation: SCRAPER-BUILDER/BUILDER fail twice on one task ⇒ MAIN absorbs it
   inline (CLERK duties revert to MAIN for that span). MAIN rate-limited/stalled
   >10 min ⇒ checkpoint (vault log + memory_store + git commit), then BUILDER
   assumes the main seat under identical rules; recover OX Alpha next wave.

### 11.6 Inheritance block — prepend to EVERY subagent prompt

"You operate under WSB Alpha Hunt law: LIVE TRADING DISABLED, paper-only,
fail-closed. Preregistration exists before any in-sample test you touch. Serial
single-file verification only — never full/batch suites. Benchmark everywhere =
SPY buy-and-hold, same engine/window/fees, net. Cite the closed-directions
ledger before proposing anything overlapping a listed family, naming changed
conditions. Never store secrets. Your context cap is [insert slug's cap]; expect
scoped excerpts, not full documents. Return a STRUCTURED verdict: {status,
files_touched[], commands_run[], key_numbers[] (each with the command that
produced it), uncertainties[], next_step_suggestion}. You have NO authority to
mark anything PASS."

### 11.7 Context hygiene + fallback chain

- All lanes fit ≤128K; RESEARCHER sees ≤50K excerpts (64K input cap).
- AUDITOR's 16K output cap: verdicts + top findings only, never dumps.
- MAIN keeps the full law chain resident; compact aggressively between waves and
  trigger §8 regeneration BEFORE ~90K tokens, not after.
- Stall/fallback ladder: SCRAPER-BUILDER fail×2 → MAIN inline (CLERK reverts to
  MAIN); BUILDER fail×2 → MAIN inline; MAIN down → BUILDER seat-swap;
  RESEARCHER down → MAIN absorbs research at HIGH.
- All endpoints are free/community channels: assume prompts and outputs may be
  retained or trained on. Strategy hypotheses pass through them knowingly —
  accepted by operator.
