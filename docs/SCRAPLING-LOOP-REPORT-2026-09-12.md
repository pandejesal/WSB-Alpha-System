# Scrapling Research Loop — Session Report (loops #1–#40, 2026-09-12)

For: any future session (Hermes / OpenCode / Prime / human). Read this first
before continuing or auditing the loop's outputs.

## Mandate

Recurring /loop task: "Use scrapling to do research for
C:\Users\DELL\Documents\Default Project and write in a doc somewhere in docs."
Self-paced wakeups; each wakeup = one finished cycle against fresh state.

## What was produced

- 39 research docs: `docs/research/scrapling-*.md` (field tests → paper briefs
  → thread syntheses → 2 index/capstone docs).
- This report: `docs/SCRAPLING-LOOP-REPORT-2026-09-12.md`.
- All claims backed by live fetches through the repo's own
  `WSB-Alpha-System-build/src/research/scrapling_provider.py`
  (ScraplingProvider, plain tier: stdlib urllib + scrapling.parser.Adaptor,
  cache-first). Environment throughout: Python 3.11.15, scrapling 0.4.15.
- Scrape cache: `WSB-Alpha-System-build/docs/data/scrape_cache/` (~56 files,
  ~2 MB at last audit). Repeat reads cost zero network.

## Tool-capability findings (verified, stable)

1. Plain tier suffices for: arXiv abs/API, ar5iv HTML full text (when rendered),
   docs.alpaca.markets markdown, generic static pages.
2. Unreachable plain: Reddit (IP-level 403 even with browser UA — PRAW OAuth
   only), GDELT anonymous (429), FRED CSV (timeouts) — keyed paths mandatory.
3. SEC cgi-bin 403s on generic UA; data.sec.gov JSON works with contact UA.
4. Alpaca `.md` trick is docs.alpaca.markets-only; llms.txt = discovery index.
5. ar5iv coverage is a lottery: no HTML → abs-chrome fallback → abstract-only,
   flag PDF-only. Two transient classes seen and retried successfully (ar5iv
   connection drops, DNS getaddrinfo) — backoff 60–90s then retry same prompt.
6. Cached files are FLATTENED text, not XML — parse by splitting on abs-URL
   markers, never XML-parse the cache. Fresh API XML: parse with ElementTree
   (Atom + opensearch namespaces declared); never regex titles across entries
   (100% misalignment rate observed — abs-check every ID).
7. Provider file unchanged all series: UA still generic (R1 open), otherwise
   working as designed.

## Research findings by thread (one line each)

- Gate integrity: leaky Sharpe-35 oracle survives DSR+PBO (PIT discipline
  non-negotiable); trial ledger = deflation instrument (must log discards);
  4 verified gate gaps (equivalence tests, INCONCLUSIVE verdict, positive
  control, survival scenarios); MinervaScore margins+Seal reporting model.
- Costs: everything ML-trend dies ~1.5–3bp (published tables); break-even-bps
  adopted as gate metric; turnover-reg in loss as standard; DeePM structural
  cost model = best practice; 3bp = progress bar since 2019.
- CTA/trend: Oxford-Man trilogy + DMN origin + DRL ingested; CPD severity
  gating = cheap first experiment; asset-holdout zero-shot as gate candidate.
- Regime: SJM vs HMM vs SPX-toolkit vs MS-tensor contestants queued for one
  bake-off; detection-not-prediction; regime routes, never predicts.
- Sizing: fractional Kelly curves (Theorem 2.1), Kelly≡Markowitz, dominance
  test before concentration, frequency-as-parameter.
- Risk live: drawdown modulation + restart as gate complement (joint backtest
  required); CHMM-t synthetic stress lane; beta-penalty in training.
- Sentiment/PEAD/VRP: horizon-split PEAD; LLM-over-lexicon with sarcasm;
  FinSMART same-day→next-day gap warning; reconfiguration premium as overlay
  input; 0DTE ranker designs banked with deflation flags.
- Falsification: intraday triptych (rules/ML/regime-classifier, all null);
  pairs = crisis sleeve; falsification ledger + stack-audit + per-trade
  economics + feature-not-edge routing as factory rules.
- LLM boundary: weekly macro interpretation yes (+0.04 Sharpe is what real
  looks like), intraday timing no; debate = stability device until ablated.

## Consolidated backlog (10 + 5)

From capstone: break-even-bps gate, ledger completeness, positive-control
harness, INCONCLUSIVE+margins, per-instrument costs, falsification ledger,
horizon-split replication, regime bake-off, CHMM stress lane, EDGAR contact UA.
Added later: multi-scale contestant, stack-audit rule, dominance guardrail,
distillation-before-promotion, feature-not-edge routing.

## How to continue

Fresh-scan pattern: dated ET-parsed query → abs-verify → ar5iv full text →
brief doc with Repro + Environment footer. Open threads: SSRN quality-factor
lane, SMC/dual-momentum specifics, 0DTE BP-rank full text when HTML lands,
backlog implementation tickets (out of research-loop scope — file as work
items, do not implement inside research loops).
