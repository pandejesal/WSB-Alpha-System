# FinSMART Market-Aligned RL Sentiment — Implementation Study — 2026-09-09

Date: 2026-09-09
Status: STUDY ONLY — zero tracked files edited. New deliverable file only.
Scope: workdir-only. `src/alpha/wsb_sentiment_alpha.py`, `src/research/debate_engine.py`, `src/data/providers/reddit_provider.py`, `src/backtest/validation.py` read-only.
Paper claims under test: **+220% cumulative-return gain vs baseline, +1.15 OOS Sharpe over FinBERT, −34% drawdown**. Treat as unreproduced until repo gates pass.

## 0. What FinSMART is (minimal working model)

FinSMART family claim: classify-then-trade sentiment (FinBERT-style) leaves money on the table because cross-entropy does not equal P&L. Fix by:

1. **Supervised warm-start:** fine-tune a financial LLM/encoder on sentiment labels (FPB-style pos/neu/neg).
2. **Market-aligned RL stage:** continue training with policy-gradient (PPO / REINFORCE-style) where the **reward is forward market outcome**, not label correctness. Typical reward sketch: signed sentiment × forward risk-adjusted return, with penalties for drawdown/volatility and turnover.
3. **Dynamic retraining:** rolling re-fit on an expanding/rolling window (e.g. monthly/quarterly) so the sentiment head tracks regime drift, with strict embargo so no future prices leak into training.

Why it could beat FinBERT in-paper: FinBERT is a static classifier; FinSMART directly optimizes the trading objective and adapts. Why the 220% / +1.15 / −34% numbers must be distrusted by default: small universe + favorable window + weak cost model + static-FinBERT strawman + RL reward-hacking + retraining lookahead are all sufficient to manufacture them.

## 1. Repo-truth mapping (verified reads)

| Claim need | Repo current state | Implication |
|---|---|---|
| Sentiment scorer | `src/alpha/wsb_sentiment_alpha.py:123-129` — `load_finbert()` stubbed to `return None,None,None`; `finbert_sentiment()` returns neutral always. Real scorer is rule-based `src/signals/fingpt_sentiment.py:184-267` (finance lexicon + negators + intensifiers, tanh compression) with `SAMPLE_EVAL_SET` FPB-style eval `run_evaluation()` | There is **no trainable encoder** in-tree. FinSMART cannot "swap FinBERT" — it must introduce a new adapter behind a frozen interface, with lexicon as fail-closed fallback. |
| Multi-agent debate | `src/research/debate_engine.py:6-66` — heuristic bull/bear/neutral vote weighted by confidence, `_stance_to_val` ±1/0, thresholds ±0.33. Not an LLM debate | FinSMART RL signal should feed `base_score`/`q_score`, not replace the engine in Diff 1–3. Debate stays deterministic. |
| Data ingress | `src/data/providers/reddit_provider.py:44-96` — `CacheEngine`-backed `fetch_sentiment_feed()`, PRAW hot + RSS fallback, `ticker=UNKNOWN`, `sentiment_score=0.0` filled later; `wsb_sentiment_alpha.py:155-206,288-423` RSS DD scrape → ticker extract → daily aggregates | Retraining corpus = cached `(post_id, post_date, ticker, title, body)` joined to prices. Must snapshot corpus hash at train time; never re-scrape inside training. |
| Execution truth | `src/backtest/run_historic_backtest.py:58-119` — signal at `post_date`, decision indicators on `t-1` (`decision_iloc=entry_iloc-1`), fill at **Open[t+1]**, GK-vol shield + RSI + confluence `min_confluence_score` | Any market-aligned reward **must** use this timing. Reward computed on T+1-filled, costed returns or it is invalid. |
| Validation truth | `src/backtest/validation.py:35-36,91-156,159-261,318-321` — `NUM_PERMUTATIONS=200`, `compute_metrics` (sum returns + `safe_sharpe` daily, 252), in-sample ticker-wise date shuffle, 90-day walk-forward pooled + per-window win-rate, fail bar `is_pval>0.01 or wf_pval>0.05` → "has not demonstrated it beats random noise" | FinSMART must beat the **permutation null**, not just FinBERT point-estimate. +1.15 Sharpe is meaningless if `p>0.05`. |
| Risk/cost truth | `config/risk_config.py:22-32` + playbook cost footnote — equities 5–7bps slip +1bp commission vol-scaled, BTC 15–25+1, fallback 5bps never 0, `MAX_POSITION_PCT=0.20`, `BASE_RISK_PCT=0.02`, leverage ≤1.0 | Reward must deduct the same tiered cost; sizing capped identically or backtest/RL diverge. |
| Edge-gate law | `AGENTS.md` + `docs/OPTIMIZATION_PLAYBOOK.md §3` + `docs/HUNT_PROTOCOL.md §4` — preregister freeze → `run_full_backtest.py` T+1 + ATR slippage → `validation.py` permutation/CPCV/WFO + DSR ledger, min ~50 trades, honest ABANDON on fail. No `strategies/registry.json` entry without passing. | FinSMART enters as a **hunt family**, not a hot-patch to active sentiment. One family per session. |
| Dependency wall | `requirements.txt` has **no `torch` / `transformers` / `trl` / `peft`**; `wsb_sentiment_alpha.py` header notes torch/transformers removed. GH Actions is zero-cost paper-only | Full LLM PPO is **not deployable** in Diff 1–4. Study proposes a CPU-only, dependency-free path first; torch path is explicitly gated as Diff 5+ (future, optional). |

## 2. Market-aligned reward design (paper-only, T+1, costed)

Pure function, no model dependency. Proposed signature for Diff 2:

```python
def market_aligned_reward(
    signed_signal: float,   # [-1,1]: FinSMART head output (or lexicon score in Diff 1)
    fwd_ret: float,         # T+1-filled forward return over holding horizon H
    spy_fwd: float,         # SPY same-window forward return (excess basis)
    vol_annual: float,      # GK_Vol at decision bar t-1
    turnover: float,        # |signal_t - signal_{t-1}| in [0,2]
    cost_bps: float,        # tiered cost from risk_config for this asset/bar
) -> float: ...
```

Reward sketch (weights preregistered, not tuned after seeing OOS):

```text
excess   = (fwd_ret - spy_fwd) - cost_bps/1e4
risk_pen = 1 + k_vol * max(0, vol_annual - vol_cap)      # vol_cap e.g. 0.30 prereg
turn_pen = k_turn * turnover                             # k_turn e.g. 0.10 prereg
reward   = clip(signed_signal * excess / risk_pen - turn_pen, -1, 1)
```

Rules that keep it honest:

- `fwd_ret` horizon H is **preregistered** (suggest H=5 to match `print_quant_statistics` 5-day horizon; optionally H=10 as secondary, never max-over-H).
- `signed_signal` must be produced from text available at `post_date` only; price features at `t-1` only. Text timestamp > decision bar = leakage → reward void.
- Costs deducted **inside** reward (same tiers as backtest), not as an afterthought.
- Excess over SPY twin, not raw return — prevents bull-market reward-hacking (long-everything looks brilliant 2019–2021).
- Clip to [−1,1] for PPO stability; log unclipped for audit.
- Report Sharpe on **costed excess**, drawdown on costed equity — the −34% drawdown claim is only checkable on this basis.
- RL objective = mean reward; **selection metric = OOS Sharpe + permutation p + DSR**, never in-sample reward. Reward-hacking check: if in-sample reward ↑ but OOS Sharpe flat/down → reject.

Why this fits `validation.py`: the permutation null shuffles `post_date` within ticker/window, which destroys text→forward-return alignment. A reward-hacked or leakage-contaminated head scores well in-sample but its shuffled distribution shifts with it → `beat_both` stays high → `p>0.05` → honest ABANDON. Leakage that survives shuffling (e.g. using future prices as features) is caught by the walk-forward embargo + `business_day_offset` T+1 audit in §4.

## 3. Dynamic retraining pipeline without lookahead

Retraining is the #1 lookahead source. Protocol:

```text
corpus snapshot (hash) → time-split [train | embargo | validation | OOS-locked]
  train:      posts ≤ T_train_end,  labels/returns use prices ≤ T_train_end + H
  embargo:    (T_train_end, T_train_end + H + 5bd] — NO training, NO tuning, NO early-stop peeking
  validation: next block for head-selection (one metric: Sharpe on costed excess)
  OOS-locked: never touched until final validation.py run; single shot
step forward by S (suggest S=63bd / quarterly; monthly S=21bd as sensitivity only)
each vintage: freeze weights + corpus hash + price-cutoff + seed → artifact dir
inference at date d uses latest vintage with T_train_end + embargo < d (point-in-time join)
```

Concretely for this repo:

- Corpus = `CacheEngine` sentiment table + `wsb_factual_research_data.csv` lineage (`post_date`, `ticker`); snapshot to `docs/data/finsmart_corpus_<vintage>.manifest.json` (row count, sha, min/max post_date).
- Price cutoff enforced by filtering `stock_dfs`/duckdb cache to `date ≤ cutoff` before computing `fwd_ret` labels. Audit query: `max(label_end_date) ≤ T_train_end + H` per vintage.
- Debate engine + confluence (HA/EMA/MACD/RSI/BB/GK-vol) stay **frozen** during retraining; only the sentiment head (`signed_signal`) is re-fit. Prevents joint leakage and keeps `min_confluence_score` gate comparable across vintages.
- Seeds fixed and logged (`np.random.seed(42)` convention per `validation.py:381`); retrain determinism check: same vintage + same seed → identical head outputs on fixture corpus.
- No online/intraday updating in paper loop — vintage switch only at scheduled boundaries; daily op reads the pinned vintage id.

## 4. Concrete staged plan — Diff 1–4 (each independently revertable, paper-only)

**Diff 1 — Frozen adapter + fixtures (no ML deps, no behavior change).**
- New module `src/signals/finsmart_adapter.py` (new file): `score_text(text, *, vintage="lexicon-fallback") -> {score, label, confidence, head, vintage}`; default path delegates to `fingpt_sentiment.score_sentiment`; FinSMART head path returns `confidence=0.0` + `head="absent"` unless a preregistered artifact is pinned (fail-closed).
- New fixtures `tests/fixtures/finsmart/{posts_small.csv, prices_small.parquet-or-csv, corpus.manifest.json}`: ≤200 posts, 2–3 tickers + SPY, hand-checkable T+1 fills.
- Acceptance: `PYTHONPATH=. pytest tests/test_finsmart_adapter.py -q` green offline; default output identical to lexicon on fixtures; no new dependency.

**Diff 2 — Market-aligned reward as pure function + property tests.**
- New module `src/research/finsmart_reward.py` (new file): implements §2 exactly, all weights as explicit args with preregistered defaults in one `REWARD_DEFAULTS` dict; raises on NaN/lookahead-flagged inputs (fail-closed, no silent zero).
- Tests: sign correctness (bull+up=positive, bull+down=negative, costs reduce reward, turnover penalized, vol penalty monotonic, clip bounds, SPY-relative not absolute).
- Acceptance: `PYTHONPATH=. pytest tests/test_finsmart_reward.py -q` green; 100% branch coverage on reward module; reward recomputed from fixtures matches hand-computed CSV to 1e-9.

**Diff 3 — Vintage retraining scheduler (CPU-only logistic head first, no torch).**
- New module `src/research/finsmart_vintages.py` (new file): `build_vintages(posts, prices, *, H, S, embargo_bd)` yielding `(train, embargo, validation)` index sets + `cutoff` assertions; `fit_logistic_head()` on frozen text features (lexicon score + debate q-score + length/engagement meta — all known at `post_date`) optimizing §2 reward via simple policy-gradient/CMA-ES-free grid over 3 scalar weights (preregistered grid, e.g. 5×5×3=75 trials max, counted toward DSR trials).
- Why logistic-not-LLM first: zero new deps, hermetic, tests the **reward + embargo machinery** that the 220% claim depends on. LLM PPO is Diff 5+ gated on passing Diff 3 OOS.
- Acceptance: vintage cutoffs audited (`max label date ≤ cutoff+H`), embargo block empty of training influence (mutation test: perturbing embargo prices does not change fitted weights), determinism (two fits same seed → identical weights).

**Diff 4 — Paper-only validation wiring (opt-in flag, no default-path change).**
- New script `scripts/validate_finsmart.py` (new file, thin wrapper): runs `run_historic_backtest` with `custom_posts_df` where `sentiment_score` = adapter output for the pinned vintage, then `validation.py` in-sample + walk-forward (`NUM_PERMUTATIONS=200`), plus DSR ledger entry via `preregister.py record`; flag `--finsmart-vintage <id>`, default off.
- Preregistration: `python scripts/preregister.py freeze` family `finsmart_rl_sentiment` declaring H, S, embargo, reward weights, grid size, universe (suggest liquid large-cap ex-SPY/QQQ, 2019–2026 daily), hypothesis: "market-aligned head OOS Sharpe > lexicon by ≥0.2 with `p≤0.05` both gates and DSR≥0.70" — deliberately weaker than paper's +1.15 to avoid strawman-chasing.
- Acceptance: single-shot OOS run; ABANDON if `is_pval>0.01 or wf_pval>0.05`, or OOS Sharpe gain < preregistered bar, or drawdown reduction not on costed excess, or <50 trades. No `strategies/registry.json` write on fail.

Explicit non-goals for Diff 1–4: no `torch/transformers/trl/peft` install, no LLM weight download, no live-trading path, no change to default sentiment/confluence/cost behavior, no new GH Actions heavy job.

## 5. Hermetic test plan (offline, deterministic, paper-only)

Global: `PYTHONPATH=. pytest tests/test_finsmart_<adapter|reward|vintages>.py -q` one file at a time, serial; `ruff check` on new files only if binary present; `bandit -r src/signals src/research` read-only-safe; no network, no keys, no `yfinance` in tests.

| # | Test file (new) | What it proves | Hermetic tactic |
|---|---|---|---|
| T1 | `test_finsmart_adapter.py` | default == lexicon; absent-head fail-closed; schema stable | fixture texts only; assert `score` equals `fingpt_sentiment.score_sentiment` to 1e-9; `vintage` echoed |
| T2 | `test_finsmart_reward.py` | §2 math + fail-closed | hand-computed table (8–12 rows incl. NaN/vol-shock/turnover/cost edges); property: `reward(bull,up) > reward(bull,down)`; clip bounds |
| T3 | `test_finsmart_vintages.py` | no lookahead | fixtures with a planted future-spike inside embargo/OOS; assert weights + signals unchanged when future block is mutated; `max(train_label_end) ≤ cutoff+H` |
| T4 | `test_finsmart_reward_hack.py` | excess-not-raw | bull-market fixture (all prices +20% + SPY +20%): always-long head gets ~0 reward; shuffle test: date-shuffled corpus → mean reward collapses |
| T5 | `test_finsmart_determinism.py` | reproducibility | same seed twice → identical weights/signals; different seed logged, not silently averaged |
| T6 | `test_finsmart_backtest_parity.py` | T+1 parity | adapter-fed `custom_posts_df` through `run_backtest` on fixtures matches hand-rolled T+1 Open-fill ledger; decision uses t−1 indicators only |
| T7 | `test_finsmart_gate.py` (slow, `dispatch`/schedule only) | paper gate | runs Diff-4 wrapper on fixtures with `NUM_PERMUTATIONS` overridden small (e.g. 20) via env for speed; asserts p-value plumbing + ABANDON branch executes; full K=200 only in scheduled CI |

Leakage tripwires (any trip → stop, do not proceed to registry): fixture future-mutation changes signals; reward uses uncosted returns; `spy_fwd` window mismatched to `fwd_ret`; vintage trains past cutoff; head features include price-derived columns dated > post_date; permutation p computed on reward instead of costed Sharpe+return jointly.

## 6. Claim-to-gate trace (what would rehabilitate each number)

- **220% cumulative-return gain:** reproducible only as costed excess over SPY twin, same universe/window, T+1 fills, pooled walk-forward. If the gain evaporates under tiered costs or SPY-relative accounting → reject as cost/strawman artifact.
- **+1.15 OOS Sharpe over FinBERT:** baseline must be the repo's actual best static head (lexicon + debate + confluence), not a crippled FinBERT-neutral stub. Preregistered bar ≥+0.2 OOS with `p≤0.05` both gates + DSR; +1.15 is a stretch goal, not a promotion criterion.
- **−34% drawdown:** on costed equity with `MAX_POSITION_PCT`/`BASE_RISK_PCT` enforced and confluence shield on. If drawdown reduction comes from trading less (activity collapse <50 trades or `trips` floor) → reject as inactivity artifact.

## 7. Risks & honest-abandon triggers

RL reward-hacking (neutral-everywhere or always-long); tiny-grid overfit (75 trials still counts toward DSR — use per-family trials, not global); regime-specific 220% (2019–2021 meme window); RSS/PRAW survivorship and ticker-extraction noise; debate-engine threshold interaction (±0.33) shifting under a new head; zero-cost runner cannot host LLM training — Diff 5+ needs a funded, pinned (`requirements.txt`) torch path with eval-gated download cache, out of scope here.

## 8. Deliverable contract

This file only. No code, registry, preregistration, or corpus manifest created. Next action if approved: Diff 1 as a Jules single-task session (boilerplate per playbook: source, base branch, acceptance `pytest + ruff` on new files only, one concern, no unrelated files), then Diff 2–4 sequentially with a fresh prereg freeze before any backtest.
