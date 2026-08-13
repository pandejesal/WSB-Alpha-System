# Comparable Repos — WSB-Alpha-System Competitive Scan

Date: 2026-08-09
Method: web research (`websearch`, fast + deep mix over several queries) + `gitingest` / engine-side README reads for the top repos. Feature claims come only from README text surfaced on 2026-08-09 — nothing invented.
Scope: repos like WSB-Alpha-System: self-running quant alpha engines (reddit/news sentiment + technical), backtest -> paper -> live, free-tier ($100-account realism), dashboards, CI.

Metrics caveat: stars / last-activity / language / license are exactly as returned by the search provider on 2026-08-09; `n/a` means the provider did not surface a value (not zero). Re-verify before publishing elsewhere.

---

## Part 1 — Candidate Pool (31 repos, grouped)

### Tier A — End-to-end autonomous alpha engines

| # | Repo | Stars | Lang / License | Last activity (captured) | Feature summary |
|---|------|-------|----------------|--------------------------|-----------------|
| A1 | [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | 95,101 | Python | created 2024-12-28; v0.3.1 released 2026-07 | Multi-agent LLM trading framework: fundamental / sentiment / technical analysts + trader + risk team + portfolio manager in LangGraph teamwork debates; persistent decision log, checkpointed resume; provider registry (OpenAI, Gemini, Claude, xAI, DeepSeek, Qwen, GLM, MiniMax, OpenRouter, Ollama, Azure, Bedrock); data vendors incl. FRED + Polymarket; structured-output agents. Research-only (explicit disclaimer). |
| A2 | [dhruvpatel1706/algo-trader](https://github.com/dhruvpatel1706/algo-trader) | n/a | Python 3.12 + TS (proprietary) | pushed 2026-04-23 | **Closest philosophical kin to our mission.** Paper-first multi-agent (equity/gold/bonds/crypto/governance); risk + compliance two-gate execution; append-only JSONL decision journal ("no record, no order"); promotion gate (backtest->paper, 7 criteria) and live-readiness gate (paper->capital, 9 criteria); invariant caps (1% trade / 6% heat / 10% position / -2% daily / -15% DD) protected by tests that forbid loosening; $100 -> $2M ladder in paper-only lanes; dead-man-switch + journal-replay reconciliation on boot; FLATTEN kill switch; LLM as governance, never oracle. Honest limitations documented. |
| A3 | [AI4Finance-Foundation/FinRL-Trading](https://github.com/AI4Finance-Foundation/FinRL-Trading) | n/a | Python 3.11 / Apache-2.0 | active 2026 (arXiv 2603.21330) | FinRL-X: weight-centric contract `w = T( A( S(x) ) )` — one target-weight vector is the interface between strategy and execution (kills drift). Auto data-source selection (FMP > WRDS > Yahoo), SQLite cache, ML + DRL allocators, regime layer (26-week trend + VIX + 3-day risk-off cooldowns), Alpaca paper multi-account, published paper-vs-lambda results (Oct 2025-Mar 2026). |
| A4 | [Aroesler1/LLMStrat](https://github.com/Aroesler1/LLMStrat) | 4 | Python | active 2026 | Staged research stack (QuantaAlpha US-equities): point-in-time S&P 500 universe, CRSP-first with EODHD fallback, walk-forward with 8-gate signal validation, LLM **factor ideation only** under exact model enforcement + expression sanitizer + request/token budgets + early halt, Alpaca paper/live with pre-trade and post-trade risk + reconciliation checks, CLI-only entry hooks, pytest. |
| A5 | [magnaquant/quantcortex](https://github.com/magnaquant/quantcortex) | 0 | Python / MIT | created 2026-06-07 | Auditable research + guarded paper execution on one common portfolio-weight contract (Data -> Alpha -> Portfolio -> Timing -> Risk -> Backtest -> Execution); NeurIPS-2026-format public preprint with exact attribution and a retrospective **negative result**; repo frozen at publication; "not a production system". |
| A6 | [BenPomme/agentictrading](https://github.com/BenPomme/agentictrading) | 8 | Python | active 2026 | Autonomous paper-mode research factory + flagship reference app for Meerkat + Goldfish + MobKit: lineage lifecycle `idea -> proposal -> model_design -> backtest -> walkforward -> shadow -> paper -> retired`; deterministic promotion/retirement gates (never LLM-only); **lineage-scoped paper accounts** (per-strategy P&L / DD / trade history); Goldfish = durable provenance + experiment memory (family DNA packets); control-tower dashboard shows gate blockers; live trading hard-disabled in the public repo; budget governance + circuit breakers active — "prefer explicit failure over fake success". |
| A7 | [jeffthebever2/agentic-trader](https://github.com/jeffthebever2/agentic-trader) | n/a | Python | pushed 2026-05-21 | 15 named paper portfolios running simultaneously on one candidate stream with different risk/size/hold params + live leaderboard; XGBoost win-probability model (walk-forward gate ROC >= 0.49) + HMM regime detector + Qlib alpha factors; 19 leakage tests; FORCE_FLATTEN halt; paper-only by default (no live orders unless enabled). |
| A8 | [predictivelabsai/alpatrade](https://github.com/predictivelabsai/alpatrade) | n/a | Python + FastAPI | pushed 2026-02-17 | Alpaca-centric 5-surface client (CLI, AG-UI chat, WEB, REST, API); multi-agent orchestrator: backtest -> validate -> paper -> validate -> **reconcile** (dedicated Reconciler agent syncs Postgres vs Alpaca), startup order sync, PDT protection, technicals/news/research commands, Plotly equity curves, per-run reports. |
| A9 | [anchapin/QuantChain](https://github.com/anchapin/QuantChain) | n/a | Python / LangGraph | active (2025-11-03 initial) | LangGraph agentic trading framework: multi-LLM backend (OpenAI, Anthropic, local vLLM/Ollama + GPU), RAG market memory (ChromaDB + sentence-transformers), FinRL-backed backtesting, connectors (Alpaca, Alpha Vantage, Polygon.io, Dexscreener, CCXT), paper trading, production Docker, tutorial/educational mode. |
| A10 | [adaline-ankit/ai-trading-framework](https://github.com/adaline-ankit/ai-trading-framework) | 0 | Python (99.8%) / NOASSERTION | v0.6.0 released 2026-03-18; last push 2026-03-26 | Approval-first "reusable layer" (not a one-off bot): Strategy SDK for one-file authoring, plugin interfaces (strategies / brokers / data / notifiers / risk policy / LLMs), event-driven workflow engine **with replay support**, explainability + deterministic risk policy chain, dashboard + Telegram (inline approve/reject + why) + CLI + API on one runtime, Postgres auth, paper broker + approval-gated live path, Railway + Docker. *Verified live execution on the author's own account — no claim of general edge.* |
| A11 | [Sohebdsa/AgentsTrading](https://github.com/Sohebdsa/AgentsTrading) | 2 | Python + React | pushed 2026-03-10 | LangGraph 4-agent swarm (TA, sentiment, order-flow, risk) -> decision aggregation -> mandatory human approval gate (WebSocket, React UI) -> paper ledger (SQLite); crypto via CCXT with fallback. |
| A12 | [ygwyg/MAHORAGA](https://github.com/ygwyg/MAHORAGA) + fork [marianopa-tr/MAKORA](https://github.com/marianopa-tr/MAKORA) | 854 (MAHORAGA); fork n/a | TypeScript / Node | created 2026-02-01 | Autonomous LLM sentiment agent running 24/7 on Cloudflare Workers (Durable Objects, auto-restart): StockTwits + Reddit (4 subreddits) + Twitter confirmation; multi-provider LLM (OpenAI, Anthropic, Gemini, xAI, DeepSeek) via AI SDK or Cloudflare AI Gateway; Alpaca (MAHORAGA) and eToro (MAKORA, known fork) paths, including BTC; max positions + per-dollar caps, TP/SL bands, minimum sentiment + analyst-confidence thresholds, staleness auto-exit, pre-market planning, Discord alerts, optional KILL_SWITCH_SECRET. |

### Tier B — Validation / overfit-prevention statistics (layers on top of an engine)

| # | Repo | Lang | License | Feature summary |
|---|------|------|---------|-----------------|
| B1 | [mnemox-ai/deflated-sharpe](https://github.com/mnemox-ai/deflated-sharpe) | Python | Apache-2.0 | DSR (Bailey & Lopez de Prado 2014), `min_backtest_length`, Benjamini-Hochberg FDR, **RegimeDecayDetector**: live 3-signal decay (Bayesian win-rate < breakeven, drawdown > 1.5x backtest MaxDD, Mahalanobis out-of-sample), 2-of-3 confirm, minimum-flat floor, cooling period, Bonferroni. Zero-dependency core. M=19,200-grid case study shows every strategy rejected — the pattern behind our own careful 90-variants/0-robust result. |
| B2 | [OutOfSampleLab/oos-lab](https://github.com/OutOfSampleLab/oos-lab) | n/a | MIT | PSR, DSR, expected-max-Sharpe, Walk-Forward, **Combinatorial Purged K-Fold with embargo**, CSCV-PBO, Harvey-Liu multiple-testing corrections, 56 metrics, numpy + scipy only, pip-installable. |
| B3 | [fingerprints: BacktestAuditor (aliipou/backtest-audit)](https://github.com/aliipou/backtest-audit) | n/a | n/a | Auditor over any backtest results: DSR (Newey-West L1), Monte-Carlo vs White Reality Check, walk-forward OOS hit-rate, regime-conditional (EWMA vol) audit, 7-scenario robustness suite, economic significance (MDE, break-even bps), optional PBO + parameter-sensitivity; PASS / WARN / FAIL verdicts per strategy. |
| B4 | [esvhd/pypbo](https://github.com/esvhd/pypbo) | n/a | n/a | PBO via CSCV, probability of loss, performance degradation, stochastic dominance, Probabilistic Sharpe Ratio, MinTRL, MinBTL, DSR stats. |
| B5 | [eslazarev/purged-cross-validation](https://github.com/eslazarev/purged-cross-validation) | n/a | n/a | sklearn-compatible: PurgedKFold (+ Group), embargo, CPCV, CSCV, backtest-path reconstruction, per-path metrics, DSR/PSR, `effective_n_trials` for correlated grid searches. |
| B6 | [General-Liquidity/sharpebench](https://pypi.org/project/sharpebench/) | n/a | Rust (pyo3) / MIT OR Apache-2.0 | PyPI package: DSR, PSR, PBO, **White Reality Check**, **Hansen SPA (liberal/consistent)**, Double Boot / Romano-Wolf step-down, BH-FDR, verdict helpers — works on your own return series. |
| B7 | [RSv618/superior-predictive-ability](https://github.com/RSv618/superior-predictive-ability) | n/a | Python | Self-contained Hansen SPA test of multiple strategies (log-log variant, no full bootstrap) — relevant as a call-site wrapper for our locked `validators/statistical.py` (SPA is independently validated there; we do not touch it). |
| B8 | [Free-data audit: "Independent Backtest Audits Reveal No Durable Edge on Free Crypto/Gold Data"](https://github.com/hoangduong6210/Independent-Backtest-Audits-Reveal-No-Durable-Edge-on-Free-Crypto-Gold-Data) | n/a | Python | Reproducible **negative-result** audit on free crypto/gold data: 7-gate audit protocol, DSR / CSCV-PBO / White Reality Check (p=1.000) / Hansen SPA (p=0.9945) — catches 3 inflated Sharpe claims; deterministic re-run script; a ready template for honestly publishing our own -0.30% result with open data. |

### Tier C — Free-tier / infra / small-account stacks

| # | Repo | Lang | License | Stars | Note |
|---|------|------|---------|-------|------|
| C1 | [Th3-H4xx0r/IntelliStock](https://github.com/Th3-H4xx0r/IntelliStock) | Python | MIT | 9 | Self-hosted: container-isolated per-strategy instances, Alpaca (paper/live) + Kalshi + Binance paths, RethinkDB + Neo4j graph store, Dockerized backtest, "always start in paper" rule, Polygon/Benzinga/yfinance mix. |
| C2 | [zinan92/executor](https://github.com/zinan92/executor) | Python | n/a | Order-lifecycle discipline: place -> confirm -> fill -> journal, dry_run local fills, env-only keys, pre-commit secret scan. |
| C3 | [DeepJani05/multi-market-trading-bot](https://github.com/DeepJani05/multi-market-trading-bot) | Python | n/a | One broker-agnostic interface (Alpaca / OANDA / Binance adapters) driving the same signal engine across equities/crypto/FX; XGBoost + LSTM ensemble; Kelly sizing cap 2%; **portfolio-level -8% drawdown circuit breaker**; Streamlit + Telegram. |
| C4 | [Niqnil/rustrade](https://github.com/Niqnil/rustrade) | Rust | 0 | "Unknown" license per provider | Event-driven framework: streaming data, strategy, risk manager; Binance, Alpaca, Hyperliquid, Interactive Brokers adapters. Beginner reference for broker abstraction. |
| C5 | [Leotaby/alpha-engine](https://github.com/Leotaby/alpha-engine) | Python | n/a | Free demo: momentum + 15 indicators, commission/slippage modeling, **run-provenance ("every backtest captures why, not just what")**; paid upgrade = 5 strategies + walk-forward + Monte Carlo fan charts + risk suite. |
| C6 | [satyaaman97/hivemind](https://github.com/satyaaman97/hivemind) | Python | n/a | 2021 | End-to-end WSB sentiment system: PRAW/Kafka -> MongoDB -> VADER + custom lexicon -> MLP regressor -> Investopedia paper simulation; live React dashboard. **Closest historical ancestor to this idea — built 2021 for the exact paper -> live ladder.** |
| C7 | [CyberPunkMetalHead/Cryptocurrency-Sentiment-Bot](https://github.com/CyberPunkMetalHead/Cryptocurrency-Sentiment-Bot) | Python | n/a | "Buy what Reddit says no to" (inverse CC) on /r/CryptoCurrency: VADER, Docker + Postgres, Playwright optional. Small portable proof of the inverse-sentiment concept. |
| C8 | [fsaavedra0003 Agentic AI Trading Bot (LLM reasoning + sentiment)](https://github.com/fsaavedra0003/Agentic-AI-Trading-Bot-With-LLM-reasoning-sentiment-analysis) | Python | n/a | Multi-source ingestion (Twitter/Reddit/News/PDFs), LLM reasoning + tool orchestration, hybrid decision logic, Alpaca/Binance paper adapters, Streamlit dashboard, circuit breakers, CI — the closest "agentic trading bot with sentiment" production-style design. |
| C10 | [kvrancic/algorithmic-trading-bot](https://github.com/kvrancic/algorithmic-trading-bot) | Python | n/a | Battle-tested: XGBoost primary (49.6% vs 29.6% baseline) + LSTM (sequence) + CNN (pattern) + FinBERT (sentiment); 119+ engineered features; pipeline: Data -> Features -> Model -> Strategy Rules -> Risk (VaR) -> Kelly sizer (25% Kelly fraction, 10% cap) -> Execution (Alpaca paper/live); stop-loss, Reddit + News sentiment. |
| C11 | [cryptocontrol/sentiment-trading-bot](https://github.com/cryptocontrol/sentiment-trading-bot) | 25 | Java / Apache-2.0 | Whitebird, a Blackbird fork: trades crypto on news/Reddit/Twitter sentiment vs trend mismatch; opens long/short per coin when divergence detected; InfluxDB + Grafana. 2018-era case study of the mismatch idea. |
| C12 | [ypatel39-commits/sentiment-aggregator](https://github.com/ypatel39-commits/sentiment-aggregator) | Python / MIT | n/a | FinBERT scoring with **VADER fallback** (graceful degradation), yfinance `.news` + Reddit JSON (free — no paid keys), SQLite idempotent cache, median-split long/short backtest with Sharpe + cross-variable correlation, Streamlit demo; honest free-tier notes ("yfinance news is shallow — ~10 items/ticker"). Exactly our free-tier constraint. |

---

## Part 2 — What the top repos actually ship (verified from READMEs — nothing invented)

- TradingAgents: `analysts -> trader -> risk -> PM` debate; LLM never executes directly — PM approval; data vendors incl. FRED + Polymarket via provider registry; research-only disclaimer.
- dhruvpatel1706/algo-trader: promotion (7-stage) + live-readiness (9-stage) gates are the core; hard caps protected by tests that cash-fail on loosening; "no record, no order" journal; journal-replay reconciliation on boot; FLATTEN; `place_order.py` is the sole order-creating path.
- FinRL-X: one weight contract `w = T(A(S(x)))` kills drift between strategy and execution; auto data-source selection; slow-trend + fast-shock regime layer.
- Aroesler1/LLMStrat: LLM constrained to factor *ideation* — exact model enforcement + sanitizer + budgets + early halt; the model is never near order execution.
- BenPomme/agentictrading: deterministic promotion/retirement gates, per-lineage paper accounts, live hard-off in the public repo — the same "research-only" discipline our README promises.
- mnemox-ai/deflated-sharpe: DSR + min-backtest-length + RegimeDecayDetector; the M=19,200 case rejects every grid strategy — directly supports our own negative-result publication.
- OutOfSampleLab/oos-lab: PSR/DSR + CSCV-PBO + CPCV-with-embargo; positions as "a layer on top of any backtester", not a backtester.
- Reproducible negative-result audit (hoangduong6210): free-data audit catching inflated Sharpe claims — the template for publishing our own honest -0.30% result.
- jeffthebever2/agentic-trader: 15 named paper portfolios + leakage-test gate + FORCE_FLATTEN — the paper-stage hardening pattern.
- predictivelabsai/alpatrade: dedicated **Reconciler** agent + startup order sync — the same paper/live fill gap our execution layer has.
- MAHORAGA/MAKORA: 24/7 Cloudflare-Workers sentiment -> Alpaca / eToro with kill-switch secret — a working model for our "no live capital without a kill switch" rule.

---

## Part 3 — TOP-3 "BORROW" LIST

**PROPOSAL — not code.** Each sketch names hook points in `src/` and **wraps, never edits**, the three locked files (`validators/statistical.py`, `permutation_tester.py`, `fred_macro_provider.py`).

### PROPOSAL-1 — Trial ledger + DSR promotion gate (borrow: deflated-sharpe + oos-lab)
What: persist every experiment we run (record hash of params, data range, IS/OOS p-value) in an append-only JSONL ledger under `docs/data/` (next to `strategy_rankings.json`); before any promotion, call a DSR gate using the *total number of trials since last promotion* + `min_backtest_length`, so our 90-variant history becomes the literature-standard multiple-testing censoring.
Hook: new module `src/evolution/trial_ledger.py` (append-only; compute-on-write). Call sites: `src/evolution/strategy_selector.py` and `src/backtest/incubation_manager.py` — read ledger, then `trial_ledger.dsr_gate(observed_sr, n_trials, n_obs)` before emitting "promote".
Value: turns the README's admitted "Overfitting Risk: High" into a measurable, gated admission — and fixes the "90 variants / 0 robust" contradiction with statistics instead of faith.

### PROPOSAL-2 — Order-lifecycle + reconciliation layer (borrow: alpatrade Reconciler + algo-trader journal)
What: `order_lifecycle.py` under `src/execution/` records each order's deterministic `client_order_id` + every state transition (placed -> routed -> accepted -> fills -> unknown) in a durable JSONL; on boot (and on unknown/5xx) a reconciliation sweep re-syncs broker state (Alpaca/CCXT vs ledger) and re-drives retries idempotently.
Hook: `src/execution/base_broker.py` / the exchange client assigns the `client_order_id` exactly once; `main_live.py` and the existing `execute_bridge` retry path call `reconcile()`. Value: closes our measured paper ~100% vs live <=~40% fill gap head-on, and gives the $100 account deterministic, idempotent fills.

### PROPOSAL-3 — 2-gate regime + hard drawdown breakers (borrow: FinRL regime + finrl-trader caps)
What: (a) **two-speed regime**: slow = VIX percentile + long-trend state (drives exposure weighting) and *fast* = 3-day risk-off shock that forces cash (mirrors FinRL's slow+fast split); (b) account-level hard breakers — daily loss -2% / peak-trough drawdown -15% — that force-flatten positions and lock the day; (c) the caps are **protected by tests that fail if anyone loosens them**.
Hook: new `src/alpha/regime_governor.py` (one `regime_state` object), consumed by `src/generator.py` / `fade_strategy.py` (signal gating) and `src/risk/position_sizing.py` (vol target); breaker wiring plugs into the existing `src/risk/circuit_breakers.py` gate. FRED stays untouched (`fred_macro_provider.py` is locked).
Value: implements the two highest-EI items from `regime-detection` (VIX / trend — 45-60% explained variance) and the missing risk-monster gap from synthesis — the exact gap the README's "limited risk management" admission points to.

## Next steps (ranked)

These are the decided, would-be-known follow-ups from this scan. All remain research proposals until explicitly ADOPTED in `docs/` — nothing here modifies `src/` and the three locked files stay untouched.

| # | Step | Do this first | Ready when |
|---|------|---------------|------------|
| 1 | Trial ledger + DSR promotion gate (PROPOSAL-1) | Add `docs/data/trial_ledger.jsonl` (append-only) next to `strategy_rankings.json`; wrap the gate as a call-site check in `strategy_selector` / `incubation_manager`, no edits to `validators/statistical.py` | Every promotion in `strategy_rankings.json` carries a `dsr_passed` field + `n_trials` used |
| 2 | Order lifecycle + reconciliation (PROPOSAL-2) | Assign a deterministic `client_order_id` once per order in `base_broker`; boot sweep in `main_live` | `docs/journals/` shows reconcile-before-retry, never blind re-submit |
| 3 | Regime governor + hard breakers (PROPOSAL-3) | Stand up `src/alpha/regime_governor.py`; wire fast 3-day shock to cash; add failing tests that block loosening of -2% daily / -15% DD | CI fails if the caps are relaxed |
| 4 | Publish the honest negative result | Follow the B8 template (7-gate audit, DSR / CSCV-PBO / SPA re-runs) | `docs/research/` has the rerunnable audit with our -0.30% figure |
| 5 | Refresh metric snapshot | Re-run star/version/README captures before any external sharing | Stale numbers replaced in both research files |

---

## Verification log

- FEATURE-GAP-MATRIX.md: all "Absent" verdicts verified via `grep` over the repo on 2026-08-09 (no matches for reconcile / client_order_id / trial_ledger / dsr / deflated / journal_replay) — and re-confirmed by the same session's capture.
- This file: every row cites the exact URLs returned by the 2026-08-09 captures (search provider README text + PyPI + gitee/organization pages) — no invented repos, no invented features.
- Re-verify any numeric/star/version before external publishing — the crawls move.
- The three "BORROW" entries are marked PROPOSED (not code) and explicitly wrap — never modify — the three locked files.
- Scope: research-only — deliverables under `docs/research/`, zero changes to `src/`.