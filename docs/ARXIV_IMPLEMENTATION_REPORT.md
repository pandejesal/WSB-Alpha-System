# What We Can Implement — arXiv q-fin → WSB-Alpha-System

**Date:** 2026-08-29 (full run 18903 unique papers, 10828 useful ≥5) — continuous loop PIDs 9928/18280  
**Scraper:** `scrape_arxiv_qfin_v2.py:1` + `continuous_arxiv_loop.ps1:1` — HTML→md via `markdownify`, API pagination 3s, dedup 24222→18903  
**Reports:** `docs/arxiv_qfin/COMPLETE_REPORT.md:1` (top 200) + `USEFUL_PAPERS_REPORT.md` (10828) + `ARXIV_QFIN_EXECUTIVE_SUMMARY.md:1`  
**Vault:** `05-Session-Logs/2026-08-29.md:1` + `02-Research/Findings/arXiv-q-fin-WSB-Usefulness-2026-08-29.md:1`

> All hunt briefs below follow `docs/HUNT_PROTOCOL.md:11` (falsifiable hypothesis, 2019-2026 universe, pre-reg via `scripts/preregister.py freeze`, gates: walk-forward + permutation + DSR in `src/backtest/defend/trial_ledger.py:545`). Registry: `strategies/registry.json:1` (7 ported families: `us_momentum_top5`, `spy_sma200`, `spy_rsi2`, `btc_vol_target_sma100`, `us_lowvol_top30` etc.).

---

## TL;DR — Do these 5 first (2 infra + 3 hunts)

| # | Paper | Type | Why now | Effort | Gate impact |
|---|---|---|---|---|---|
| **I1** | `2608.23808` MinervaScore | Infra — ledger | Fixes "luck vs edge" gap that caused 0/16 hunt PASS; audit layer on top of DSR | 1 week | Hardens PBO, SPA, MTR, regime |
| **I2** | `2505.16136` GDELT+FinBERT macro sentiment | Infra — data | Rebuilds degraded `market_data_2019_2026/news/` (0 articles, GDELT bug) with same source but correctly | 1–2 wks | Unlocks sentiment sleeve |
| **H1** | `2607.01550` Trend demise tick-size filter | Hunt — CTA patch | Explains why short-term trend failed since 2009 (small-tick collapse) → filtered re-entry of our SMA200/CTA sleeves | 2 wks | Direct P&L |
| **H2** | `2605.20636` Continuous timing growth-defensive | Hunt — rotation | Smooth tanh score vs our binary FRED RISK_ON gate; Fama-French attribution, walk-forward | 2 wks | Low marginal cost |
| **H3** | `2511.08571` Gold Forecast-to-Fill (walk-forward 10y→6m, Kelly+impact) | Hunt — new sleeve | Sharpe 2.88 net 0.7bp+sqrt-impact, maxDD 0.52%, ATR exits, billion-dollar capacity | 2–3 wks | Diversifier |

Everything else below is Phase 2 (months 2–3) or research.

---

## 1. Infrastructure: must-do before next hunt cycle

### I1 — `2608.23808` Equity Strategy Backtesting: MinervaScore (score 29, q-fin.ST) — **GATE HARDENING**
**What:** Post-selection robustness grade 0–100 + binary Seal ≥80 only if all 5 gates pass:
1. **DSR** (Deflated Sharpe, already in `trial_ledger.py:545` — `deflated_sharpe_ratio(T,SR,N)`)
2. **PBO** (Probability of Backtest Overfitting, combinatorial splits)
3. **SPA** (Hansen Superior Predictive Ability)
4. **MTR** (Minimum Track Record Length)
5. **Regime stability** diagnostic
Each → signed margin from threshold → raw aggregate → 0–100. Calibrated on 359,062 production backtests; AUROC 0.989 vs lucky backtests in synthetic truth. Single run `rho=0.013, p=0.40` on limited surviving edge (honest: not future-return predictor).

**Why WSB now:** Our 0/16 PASS history (`docs/PIPELINE_GATE.md:1`) suggests we report Sharpe/DD but not N-trials or MTR. MinervaScore closes that loop; charter requires honest trial ledger — we have `TrialLedger` append/load/sha256 hash but not SPA/PBO/MTR.

**How to implement:**
- Extend `src/backtest/defend/trial_ledger.py:545` + `src/backtest/validation.py:286` to compute PBO (CPCV splits), SPA (Politis/Romano bootstrap), MTR (`T* = 1 + (1+SR²/2)*(z_{1-α}/SR)²` with deflated correction), regime split (bull/bear 50/50).
- New `src/backtest/defend/minerva_score.py` returning `{raw, display_0_100, seal, margins}`; wire into `scripts/comprehensive_backtest_report.py:1` and `scripts/preregister.py record`.
- No YAML needed; non-blocking display (seal gating does not block promotion — DSR still binding — but flagged CONCERNS if <80).

**Data:** Already have daily OHLCV `market_data_2019_2026/ohlcv/instruments.csv:1`; no new feed.

**Risk:** Low; pure audit layer.

### I2 — `2505.16136` Interpretable ML for Macro Alpha: GDELT+FinBERT+XGBoost (score 34, q-fin.CP) — **DATA REBUILD**
**What:** Daily FinBERT sentiment indices (mean tone, dispersion, event impact) from GDELT worldwide feed → XGBoost (vs LogReg) → next-day EUR/USD, USD/JPY, 10y Treasury futures (ZN). 5-fold expanding-window CV, OOS c.2017–Apr 2025, cost-adjusted.

**Why WSB now:** Exact fix for degraded `market_data_2019_2026/news/news_index.csv:1` (0 articles, GDELT TimelineVol normalization bug). Our harvest tool `market_data_2019_2026/tools/news_harvest.py:1` exists; `news_redo.py` exists.

**How to implement:**
- `news_harvest.py` fixed: switched from TimelineVol to GDELT 2.0 Doc 2.0 API (`g_SENTIMENTS`), added `avg_tone`, `tone_disp`, `event_impact` fields (mapped from `avgTone`/dispersion/`eventImpact`). `news_redo.py` resumable rebuild of `raw/g_*.jsonl` + `news_index.csv` built, lint-clean. **Data rebuild deferred:** GDELT API currently unreachable (network/TLS, 12/12 probes failed) — no fabricated data; rerun `news_redo.py` when reachable.
- Build daily sentiment feature table: groupBy date, aggregate `meanTone`, `stdTone`, `eventCount` → join to `ohlcv` and FRED (`src/data/fred_*.py`).
- Reuse `src/alpha/wsb_sentiment_alpha.py:864` (hotspot — delegate heavy read to Antigravity high); GDELT branch (`compute_gdelt_macro_sentiment`, reads `news/raw/g_*.jsonl`) now wired into `run_sentiment_pipeline` merge step — daily `gdelt_doc_count`, `gdelt_net_tonality`, `gdelt_dispersion`, `gdelt_event_impact` columns keyed on `post_date`; keep existing perf envelope.

**Effort:** 1–2 wks; zero-cost (GDELT free, FinBERT open-source).

### I3 — `2603.09219` AlgoXpert IS→WFA→OOS Protocol (score 32, q-fin.PM) — **PROCESS UPGRADE** (integrate with I1)
Three-stage: IS stable regions (not point optima), WFA rolling + purge gaps + majority-pass & catastrophic veto, OOS parameter-locked. Includes cliff veto, spread/leverage guards. Direct complement to `docs/HUNT_PROTOCOL.md:4` (currently IS→WFA→OOS but gap purge not enforced). Implement as extra validation in `hunt_runner.py:run/collect`.

---

## 2. Hunts — Phase 1 (next cycle, 3–5 concurrent per `HUNT_PROTOCOL:65`)

### H1 — `2607.01550` Is Trend Still Your Friend? Tick-size microstructural filter (33, q-fin.TR) — **PATCH EXISTING SLEEVES**
**Core finding:** Short-term trend (2 centuries profitable) collapsed since ~2009, but only on small-tick futures; large-tick intact. Discriminant = volatility-normalised tick size, not liquidity nor asset class. Implies CTA failure is microstructure feedback loop (trend signal → directional order flow → tick-size regime).

**WSB hypothesis to pre-reg:**
> "Futures/equities with large volatility-normalised tick size (tick / ATR(20) above median) exhibit positive 5–20d trend following alpha; small-tick names do not. Augmented CTA that trades only large-tick universe outperforms unfiltered CTA OOS."

**Universe:** 100 liquid futures (1995-2025 paper) → map to **equities adaption**: frozen 481-name S&P 500 snapshot `market_data_2019_2026` + yfinance daily, added feature `tickProxy = 0.01 / ATR20_close` (penny tick normalised). Large-tick = top 50% rank.

**Spec sketch `strategies/cta_tick_filtered.yaml`:**
```yaml
id: cta_tick_filtered
family: trend
universe: sp500_481_frozen
indicators: [ATR(20), tickProxy, SMA(20/50/100) cross]
entry: SMA20 > SMA50 on close with tickProxy_rank > 0.5 and volTarget 15%
exit: opposite cross or ATR stop
sizing: volTarget 15%, fractional Kelly 0.3 cap, max_k 3
```
**Validation:** Walk-forward 2019-2026, compare filtered vs unfiltered `cta_ensemble_3speed.yaml:1` and `spy_sma200.yaml:1`; expect filtered OOS Sharpe +0.2–0.4 and maxDD reduction. Falsifies if no discriminant (p>0.05 permutation).

**Gate tie-in:** Directly addresses why `C2 multi-asset SMA200` null failed (median OOS +0.35%/wk but p95 +0.58%) — cost of small-tick noise.

### H2 — `2605.20636` Continuous Timing Growth-Defensive Allocation (30, q-fin.PM) — **ROTATION OVERLAY**
**Edge:** Not a new factor — allocation between growth/tech ETF basket `G` and defensive/value basket `D` using continuous smooth signal vs discrete regime. Signal = softplus(rate relief) + softplus(SPY drawdown depth) + softplus(high-VIX relief) + penalty(crowding) → tanh → EWMA smoothing → weights on G/D. Attribution: `G-D` beta 0.273, HML -0.552, mom 0.117, alpha 1.95% t=0.81 (style portfolio, not anomaly).

**WSB hypothesis:**
> "Continuous macro score allocates to defensive `D` in rate-relief/drawdown/VIX stress, else to growth `G`; smoothed tanh→EWMA weights beat binary FRED RISK_ON gate on risk-adjusted and drawdown."

**Universe:** ETFs `G = [QQQ, VUG, XLK]` vs `D = [VTV, XLP, XLU, TLT]` (or closest liquid proxies available on Alpaca). Daily OHLCV + FRED (rates, VIX via yfinance `^VIX`).

**Spec `strategies/continuous_growth_defensive.yaml`:**
```yaml
family: rotation
universe: [QQQ, VUG, XLK, VTV, XLP, XLU, TLT]
signal: softplus( fedFunds Δ ) + softplus( SPY DD ) + softplus( VIX ) - softplus( crowding )
mapping: tanh(signal) → [-1,1] → EWMA( span 10 ) → w_G = (1+tanh)/2, w_D = 1-w_G
rebalance: daily, drift 5%
```
**Why better than current:** Our active `src/ops/signals.py:662` uses binary regime; this is differentiable and less whipsaw. Compare head-to-head OOS vs current FRED gate on same window/fees; expect similar CAGR but lower turnover and maxDD.

### H3 — `2511.08571` Gold Forecast-to-Fill, `2511.12490` Drift-Regime 13-Sharpe, `2602.18912` Overreaction — **NEW SLEEVES (pick one, not all)**
- **Gold walk-forward (H3a, safest):** `2511.08571` — rolling 10y train / 6m test walk-forward (2793 days 2015-2025) on gold futures/ETF `GLD`, smoothed trend-momentum regime → vol-targeted fractional Kelly with sqrt-impact (γ=0.02) + ATR exits. Reported Sharpe 2.88 net 0.7bp + impact, maxDD 0.52%, CAGR 43%/alpha 37% at 15% vol. **Hunt:** `strategies/gold_trend_kelly.yaml` on `GLD`/`GC=F` via yfinance → Alpaca `GLD`. Billion-dollar capacity claim helps tiny $100 account. Falsify if OOS Sharpe ≤ buy-and-hold gold.
- **Drift-regime equity factor (H3b, high-risk high-return):** `2511.12490` — value+short-term reversal only when stock has >60% up days in trailing 63d (drift regime). Claims OOS Sharpe >13, CAGR 158%, vol 12%, DD -11.9% over 20y S&P 500 — **unrealistically high → must survive DSR deflation**. Use as stress test of MinervaScore (I1). If passes, huge; if fails, honest abandon validates gate.
- **Overreaction momentum with transformer emotions (H3c):** `2602.18912` — AAPL intraday volatility-normalized overreaction (extreme return vs contemporaneous vol) predicted via Twitter-transformer emotions + XGBoost/RF/BiLSTM at 1/5/10/15 min. Intraday but adaptable to daily WSB sentiment: map `Twitter emotion → Reddit WSB emotion` using same transformer on `src/alpha/wsb_sentiment_alpha.py`. Intraday data gap → try daily proxy first.

**Recommendation:** Pre-register H3a (gold) this cycle; queue H3b as second if capacity allows, but require MinervaScore (I1) to deflate its Sharpe.

---

## 3. Phase 2 — Next 4–8 weeks (queue after Phase 1 gates)

| Paper | Score | What | Implement how | WSB mapping |
|---|---|---|---|---|
| `2608.24786` Volatility Risk Premium LambdaRank SPXW 0-DTE (30) | LightGBM LambdaRank on 8 short-put deltas + SKIP, path-aware Sortino label at 1-min, margin-aware sizing, abstention by uncertainty, 4-window walk-forward + strict 2025 OOT | **Options sleeve expansion** — currently no options in `registry.json` (all venues alpaca equities). Needs data: SPXW weekly options minute bars (Alpaca options API or CBOE). Complexity high (margin, fees, bid-mid). Defer until equities gates green. |
| `2605.28853` Deep Portfolio Optimization — AttentionLSTM direct Sharpe/Omega/CVaR/RiskParity (30) | End-to-end weights via backprop, 50 S&P 2007-23, quarterly rebalance, OOT Sharpe 0.29 vs SPY -0.02 | Replace predict-then-optimize in `src/portfolio/*`; walk-forward comparison vs current mean-variance. Needs GPU, heavy. |
| `2512.12420` Deep Hedging RL for index options (30) | RL hedging SPY with cost-aware actor-critic, daily panel SPX/SPY vol term structure | Hedge `us_lowvol_top30` tail risk; complements vol-targeting. |
| `2510.26438` Hawkes LOB Impulse Control market making (30) | Hawkes process LOB with impulse control (limit/cancel/market) → HJB-QVI | Requires L2 LOB data (Binance top-20 for crypto proxy) — not our venue; research only via `ABIDES-MARL` `2511.02016`. |
| `2606.00060` Bitcoin ML walk-forward hourly 70k obs, cost-aware threshold (28) | XGBoost/LSTM/iTransformer 27-fold walk-forward BTC-USDT, profitability restored only with cost threshold (10bp) | Direct plug to `btc_vol_target_sma100` + `btc_donchian_20_10` — add forecast-magnitude filter. Low effort. |
| `2602.17098` DRL vs Mean-Variance (28) | DRL PPO vs equal-weight/mean-variance, drawdown/vol constraints | Benchmark `src/portfolio` optimisers; many DRL papers underperform on risk-adjusted after conservatism — gate will catch. |
| `2601.05975` DeePM Macro Portfolio + ragged filtration (27) | Directed Delay causal sieve + macro graph prior + EVaR worst-window | Macro sleeve for FRED pipeline. |
| `2607.09230` When Does Order Flow Matter? L2 state transitions crypto (27) | Event-conditioned L2 state predicts post-event liquidity; blocked permutation tests | Reuse Binance L2 top-20 from `market_data_2019_2026` if captured; otherwise defer. |
| `2512.12924` Hypothesis-driven RL + 34 rolling windows, Sharpe 0.33 maxDD -2.76% market-neutral (28) | Strict information set + RL across 100 equities 2015-24 | Template for interpretable microstructure hypotheses — adopt its 34-window protocol verbatim. |
| `2311.14759` Crypto forecasting Twitter/Reddit + BART MNLI bullish/bearish zero-shot (29) | News/social → local extrema vs daily | Upgrade `wsb_sentiment_alpha.py` sentiment classifier from FinBERT to BART MNLI zero-shot + local extrema framing. |

**Defer/low priority:** Pure mathematical finance `q-fin.MF/PR` pricing PDE papers (1067 papers, low tradability), `q-fin.GN` general theory, `econ.GN` migrated EC — unless hunting new maths overlay.

---

## 4. Roadmap & resourcing

**Week 1:** Implement I1 (MinervaScore) + I2 (GDELT rebuild) in same branch, `ruff check + bandit -r src/ + PYTHONPATH=. pytest` per `AGENTS.md`.
**Weeks 2–3:** Parallel hunts H1 (tick filter) + H2 (growth-defensive) via `hunt_runner.py run` (2 of 5 concurrent slots). H3 gold pre-reg in parallel if bandwidth.
**Weeks 4–6:** Collect & gate; honest abandon vs promotion via `preregister.py record`. Wire promoted YAMLs to `registry.json` — no code change in `signals.py` needed.
**Month 2:** Pick one Phase 2 (recommend `2606.00060` BTC cost filter — lowest risk — vs `2608.24786` options — highest complexity).
**Continuous:** Scraper sleeps 6h, refreshes `COMPLETE_REPORT.md` — review top-5 delta each Monday via `04-Prompt-Queues/Research-Awake/` for user paste.

**Risk controls throughout:** All hunts use frozen `preregister.py freeze` before any backtest; walk-forward with purge gaps; permutation `validation.py:286`; DSR + new MinervaScore; live `PIPELINE_GATE.md` 30-day window; kill-switch rehearsal `KILLSWITCH_REHEARSAL.md`.

---

## 5. What *not* to chase

- Papers claiming Sharpe >5 on single assets with tiny hold-out (e.g. `2511.12490` Sharpe 13) without deflated correction — flag for PBO audit, not blind replication.
- L2 market-making Hawkes models needing full LOB replay (we lack venue data and Alpaca equities not L2 crypto).
- Mathematical finance stochastics without executable signal (high `q-fin.MF` count 3392 but low hunt yield).

---

**Artifacts ready now:**
- `docs/arxiv_qfin/USEFUL_PAPERS_REPORT.md:1` — all 10828 useful sorted; `COMPLETE_REPORT:65` — curated 100
- Per-paper md: `docs/arxiv_qfin/papers/<id>_<title>.md:1`
- Their abstracts: `C:\Users\DELL\Documents\Default Project\docs\arxiv_qfin\papers\q-fin_ST\2508.26106_*.md` etc.

**Next action:** paste Hunt Briefs H1/H2/H3 into `04-Prompt-Queues/Coding/` for Jules, or run `python scripts/hunt_runner.py run --brief hunts/cta_tick_filtered/brief.yaml --out hunts/cta_tick_filtered/...` locally.
