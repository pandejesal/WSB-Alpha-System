# HUNT MEGA PROMPT — WSB Alpha Edge Hunt (self-regenerating)

> OPERATOR INSTRUCTION: paste this entire file into a fresh OpenCode session opened in
> `C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-build`.
> The active session maintains this file (bump version, update ledger/slate) and tells
> you to re-paste it whenever context runs low or a wave completes.

version: 1 · generated: 2026-08-24 · superseded-by: —

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

Standing rule: any hypothesis overlapping a listed family must cite that failure and
name its CHANGED CONDITIONS in `prior_art.md`. The closure explicitly excluded four
lanes, which are therefore YOUR prime hunting ground: **different data, exits were now
also tested-and-closed, remaining open = sizing, claim scoping, new data**.

Mine this structural finding: mega-cap-only conditioning cleared B-gates 3×
independently while full-universe variants failed; A+B never co-passed.

## 5. Wave protocol (rolling)

- Each wave = ONE preregistration batch of 4–6 hypotheses
  (`docs/data/<id>_prereg.md` + `workspace/stages/01_hypothesis/output/{hypothesis_brief.yaml,prior_art.md}`),
  committed before testing, tested serially, every result ledgared honestly
  (HONEST_NO_OP if nothing passes).
- Failures feed the next wave's slate. Never tune post hoc — a new idea is a new
  preregistration with declared changed conditions.

## 6. Approved Wave-1 slate

1. **Mega-cap-only momentum top5** — universe scoping; direct descendant of the 3×
   B-gate passes.
2. **Regime-conditioned momentum** — `data/fred_historical_regimes.json` as exposure
   filter on the momentum core (declare difference vs failed RSI2-era regime variants:
   different core, different regime source).
3. **Vol-targeted sizing overlay** on the best validated core — sizing lane, zero new
   data needed.
4. **Politician-trade replication** — Congressional follow-strategy from STOCK Act
   periodic transaction reports (Senate eFile disclosures / House Clerk PTRs; free
   sources), backtested filing-lag-aware (~30–45 days). Academic prior exists
   (Ziobrowski et al. 2012). Include the **Jim Cramer follow-vs-fade pair as a second
   arm under one preregistration** — both directions tested, gates decide.

Items 1–3 are testable immediately on local data; item 4's scraping engineering may run
in parallel and test in-wave once data lands.

## 7. Data policy — FREE TIER ONLY

Pre-authorized: local OHLCV panel (`market_data_2019_2026/ohlcv/`, gitignored,
~1900 tickers 2019–2026 full OHLCV), `market_data.duckdb`,
`data/fred_historical_regimes.json`, FRED macro series, yfinance fundamentals,
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
