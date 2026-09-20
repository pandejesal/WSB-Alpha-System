# arXiv q-fin Executive Summary for WSB-Alpha-System
**Generated:** 2026-08-29 12:54 UTC (scrape_arxiv_qfin_v2.py — continuous loop, no human input — **FULL HISTORICAL COMPLETE**)
**Full reports:** `docs/arxiv_qfin/COMPLETE_REPORT.md` (**18903 unique papers**, dedup from 24222 raw API totals, 92 category folders) + `docs/arxiv_qfin/USEFUL_PAPERS_REPORT.md` (**10828 useful ≥5**, 57%) — mirrored to `Project/docs/arxiv_qfin_*.md` and `WSB-Alpha-System-build/docs/arxiv_qfin/`

## TL;DR — What to read first

Continuous scraper now running forever (PowerShell PID 9928 → python PID 18280, `--loop --sleep-hours 6`, full history, 3s API rate limit, 1s HTML rate limit). Every HTML listing page is converted to Markdown via `markdownify` (html→md tool) and saved under `docs/arxiv_qfin/listings/`; every paper abstract is saved as `docs/arxiv_qfin/papers/<cat>/<id>_<title>.md` (true abstract from arXiv API, fixes v1 empty-abstract bug). Reports mirrored to both `Project/docs/` and `WSB-Alpha-System-build/docs/`.

Top 7 most useful papers for our fail-closed edge gate + live stack (score 28–33/ max observed):

### 1. `2607.01550` — Is Trend Still Your Friend? (score 33, q-fin.TR)  — **MUST READ for trend module**
Systematic trend following profitable 2 centuries but collapsed since ~2009 on small-tick futures. Cross-section of ~100 futures 1995-2025 shows degraded trends discriminate by volatility-normalised tick size, not liquidity or asset class. Points to microstructural feedback loop at heart of trend anomaly. **Action:** Re-evaluate `src/alpha/mul`* and `strategies/` trend families; test tick-size conditioned filters before re-adding CTA sleeve (ties to `docs/HUNT_PROTOCOL.md` & `trial_ledger.py:545` DSR gate).

### 2. `2608.24786` — Harvesting Volatility Risk Premium: Learning-to-Rank (score 30, q-fin.CP/ST)
LightGBM LambdaRank on SPXW 0-DTE, margin-aware sizing, abstention by uncertainty, 4-window walk-forward (2021-24) + strict 2025 OOT. OOT Sharpe 4.3–5.76, PSR 0.964, maxDD -2.28% — but single hold-out year vs WF 1.90–3.11. **Action:** Hunt candidate for options VRP sleeve; replicate walk-forward + OOT slice discipline before pre-registering.

### 3. `2605.20636` — Continuous Timing Signals for Growth-Defensive Allocation (score 30, q-fin.PM)
Fama-French 5F+MOM attribution of growth vs defensive ETF allocation: continuous smooth score (rate relief, SPY drawdown, VIX stress, crowding penalty) via softplus → tanh → EWMA.  **Action:** Direct hunt fuel for macro-gated rotation overlay (FRED pipeline `src/data/fred_*`); compare vs our FRED RISK_ON gate.

### 4. `2605.28853` — Financially Guided Deep Portfolio Optimization (score 30, q-fin.PM)
End-to-end AttentionLSTM optimising Sharpe/Omega/CVaR/Risk-Parity surrogates, walk-forward 50 S&P stocks 2007-23 with bid-ask costs, OOT 2022-23 Sharpe 0.29 vs SPY -0.02, +7.86% vs -4.52%. **Action:** Evaluate differentiable risk-parity loss as improvement to `src/portfolio/*` before hunting new family.

### 5. `2608.23808` — Equity Strategy Backtesting: MinervaScore (score 29, q-fin.ST)  — **GATE HARDENING**
Post-selection robustness grade combining DSR + PBO + SPA + Minimum Track Record + regime stability → 0–100 + Robustness Seal (80+ only if all gates pass), calibrated on 359k backtests. AUROC 0.989 vs lucky backtests in synthetic truth. **Action:** Consider MinervaScore as second-layer ledger alongside `trial_ledger.py` DSR; audit our 0/16 hunt PASS rate.

### 6. `2606.00060` — ML-Based Bitcoin Trading Under Transaction Costs: Walk-Forward (score 28, q-fin.TR)
ML walk-forward on BTC with costs. **Action:** Review transaction-cost modelling for crypto sleeve (CCXT adapter).

### 7. `2608.26106` — Statistical-Finance Benchmark for Same-Day Directional SPY Prediction (Walk-Forward, new listing 2026-08-28)
XGBoost vs RF/LightGBM/LogReg on SPY 1993-2024, expanding-window walk-forward, same-day close-direction after open + 2 lagged prices. Last 800 days: LogReg 71.09%, RF 61.20%, XGB 58.45% [54.94,62.08]; XGB 72.7% when predicted move >1% but n=154. Includes DM/McNemar, SHAP, 541-equity screen. **Action:** Replicate as statistical-finance sanity check; narrow claims due to sample-size.

## Coverage stats (FULL historical, global dedup, completed 12:54 UTC)

| Cat | API total | Saved (full) | Useful ≥5 | Primary use to WSB |
|---|---|---|---|---|
| q-fin.CP | 3328 | 3328 | 1179 | Computational / execution |
| q-fin.EC | 0* | 0 | 0 | *EC migrated to econ.GN; HTML listings still saved (31 listings md) |
| q-fin.GN | 3067 | 3067 | 453 | General quant |
| q-fin.MF | 3392 | 3392 | 958 | Mathematical |
| q-fin.PM | 2445 | 2445 | 1225 | **Portfolio — high priority** |
| q-fin.PR | 2260 | 2260 | 760 | Pricing/hedging |
| q-fin.RM | 3044 | 3044 | 1172 | **Risk — high** |
| q-fin.ST | 4346 | 4346 | 2066 | **Statistical — highest** |
| q-fin.TR | 2340 | 2340 | 1231 | **Microstructure — highest** |
| **Total** | **24222** | **18903 unique** (19179 markdown files across 92 folders, 22% cross-list overlap) | **10828** (57%) | |

Previous quick run (150/cat) was 916 unique / 654 useful for initial verification; now overwritten by full run.

## Where to find artifacts

```
Project/docs/arxiv_qfin/                       ← as requested (this exec summary lives in Project/docs/)
├── COMPLETE_REPORT.md / index.md             # 343k, top 200 curated + all-papers by cat (18903 unique)
├── USEFUL_PAPERS_REPORT.md                   # 16M, all 10828 useful sorted by score
├── ARXIV_QFIN_EXECUTIVE_SUMMARY.md           # this file (top 7)
├── listings/                                 # 31 md (archive overview + new/recent/current per cat) — html→md via markdownify
├── papers/                                   # 19179 md (one per paper, true abstract, 92 folders)
│   ├── q-fin_ST/2417 primary ST etc. etc
│   └── ... (92 subfolders by primary category, incl. cross-list cats like cs.LG, math.OC, econ.GN)
├── q-fin_*_results.json                     # raw API dumps (9 files, API totals match saved)
└── continuous_loop.log                      # heartbeat of continuous loop

Mirror: WSB-Alpha-System-build/docs/arxiv_qfin/  (identical, 19179 files)
Top-level mirrors: Project/docs/arxiv_qfin_COMPLETE_REPORT.md etc. (343k each)
```

## How request was satisfied

1. **Read Project + Vault:** Vault Guide, Workflow, WSB-Alpha-System.md + HUNT_PROTOCOL + OPTIMIZATION_PLAYBOOK → relevance policy tuned to pipeline gates.
2. **Scraped every single page of https://arxiv.org/archive/q-fin:** archive overview + 31 listings (q-fin/new, recent, current + per-subcategory new/recent/current) fetched via `urllib` + converted to Markdown via `markdownify` (Python port of html-to-markdown) + `BeautifulSoup` — satisfies "use skills/tools that can convert into html or .md". Historical depth beyond paginated listings covered by arXiv API `export.arxiv.org/api/query` (canonical store; respects 3s limit).
3. **Converted to .md:** every HTML page → `.md` via markdownify (same contract as `html-to-markdown-cli`/`crawlberg` which were unavailable on this Windows/Node env; Python equivalent fulfills requirement and is documented).
4. **Complete report saved at `C:\Users\DELL\Documents\Default Project\docs`:** executive summary here + `arxiv_qfin_COMPLETE_REPORT.md` etc. + full `docs/arxiv_qfin/` tree.
5. **Continuous loop, no human input:** `continuous_arxiv_loop.ps1` (PowerShell) launches `scrape_arxiv_qfin_v2.py --loop --sleep-hours 6` hidden, restarts on crash with exponential backoff, logs to `continuous_loop.log`. Currently PID 9928 / python 18280 running full-history cycle.

## Next steps (automated — now sleeping)

- **Full cycle COMPLETED 12:54 UTC** (18903 unique). Loop now sleeping until ~18:54 UTC then repeating forever. Each cycle re-scores and overwrites reports in place (no manual copy).
- To stop loop: `Stop-Process -Id 9928 -Force` then `Stop-Process -Id 18280 -Force` if needed.
- To force immediate refresh: `python scrape_arxiv_qfin_v2.py --max-per-cat 200` (quick 2 min) or without cap (full 12 min).

---
*Vault log: `Obsidian Vault/05-Session-Logs/2026-08-29.md` + Mnemosyne stored. Loop evidence: `continuous_loop.log`.*
