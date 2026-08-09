# Quant Backtest Validation: Best Practices 2026 (for the WSB-Alpha-System "$100 engine")

**As of:** 2026-08-09 · **Method:** primary-source research (peer-reviewed papers, library docs, implementation repos) cross-checked with the repo's actual current validator code (`WSB-Alpha-System/src/backtest/`). Only URLs that were reachable or returned content in this session are listed; none are guessed. Sources are marked [PAPER] / [OFFICIAL] / [COMMUNITY] and cited inline.

---

## TL;DR

- The five core validation tools a small auto-trading engine actually needs, in rough priority order: **(1) a multiple-comparison guard** — White's Reality Check (WRC) or Hansen SPA or the Deflated Sharpe Ratio (DSR); **(2) leakage-resistant sample splitting** — purged k-fold / Combinatorial Purged CV (CPCV) instead of naive train/test; **(3) bootstrap confidence intervals** on Sharpe and drawdown instead of point estimates; **(4) walk-forward analysis** with enough OOS windows; **(5) permutation/placebo tests** on the strategy's own category (mean-reversion strategies need *serial-correlation-preserving* permutations, not plain shuffles).
- The two most common and most expensive mistakes in practice are: (a) **selection without correction** — "best of N" backtests look great by construction (the False Strategy Theorem: ≈7 trials ≈ max Sharpe ~1.0 annualized; 1,000 trials ≈ 3+), and (b) **leakage** — overlapping train/test windows, labels that include future information, and parameter tuning on the same data that is later reported as OOS.
- **At a $100 micro-account scale, a valid p-value is worth far less than honest costs.** The dominant validation open question is not "is the edge statistically significant at 5%?" but "does the edge survive $0.005–$0.02/share friction, spread, and $100-capital position sizing?" — the repo already knows this (fees/slippage are explicit blockers in `docs/AUDIT_FINDINGS.md`).
- **The repo already implements two of the five** (`whites_reality_check.py`, `permutation_tester.py`). The known gaps: `statistical.py`'s "SPA test" entry is actually a plain paired-studentised t-test (mislabeled — a real Hansen SPA is available in the same `arch` library they already import), `combinatorial_purged_cv` purges without an embargo and without the follow-up PBO path evaluation, and the permutation null destroys the intra-bar autocorrelation a mean-reversion edge depends on (see §"MeanR").

---

## 1. Summary table — the validation toolbox

| Method | What it guards against | Prerequisites | Typical thresholds | Source |
|---|---|---|---|---|
| **White's Reality Check (WRC)** | Lucky best-of-N trials ("data snooping") | A return matrix of *all* candidate strategies vs a benchmark (T×N); stationary bootstrap | p ≤ 0.05 → null ("no rule beats the benchmark") rejected conservatively | [PAPER] White 2000, Econometrica |
| **Hansen SPA test** | Same, but more powerful (consistent, recenters sample moments) | Same matrix; loss-form (lower=better); bootstrap | p ≤ 0.05 → benchmark outperformed by at least one strategy | [PAPER] Hansen 2005 |
| **Deflated Sharpe Ratio (DSR) / PSR** | Selection bias from N trials + skew/kurtosis; per-strategy | T, SR, N trials, skewness, excess kurtosis (closed form) | DSR ≥ 0.95 (95% prob true SR > 0); PSR is the special case N=1 | [PAPER] Bailey & López de Prado 2014 |
| **PBO (CSCV / CPCV paths)** | Chance the in-sample best config is below-median OOS | Matrix of config × backtest return paths | PBO < 0.2 acceptable; > 0.5 reject (strictest sources: reject above 0.05) | [PAPER] Bailey et al. 2017; [COMMUNITY] mlfinlab/CPCV guides |
| **CPCV (Combinatorial Purged CV)** | Leakage from overlapping labels/chunks + high variance of a single split | Split data into N groups, purge+embargo, enumerate all (N choose k) combos | Each train sees (N−k)/N of data; each bar OOS in exactly C(N−1,k−1) paths; look at PBO over paths | [COMMUNITY] eslazarev/purged-cross-validation; [COMMUNITY] KnoSys 2024 (CPCV beats plain CV setups) |
| **Bootstrap CI for Sharpe (approx. + block)** | Treating a point estimate as a truth; autocorrelation | T data points; Lo's iid SE or stationary bootstrap | 95% CI excluding 0 = minimum evidence; also skew/kurtosis-adjusted variance | [PAPER] Lo 2002; [PAPER] Politis-Romano 1994 |
| **Monte-Carlo drawdown envelope** | Disaster tail ("P95 worst drawdown") | trade-level return sequence, ~10k resamples | Report 95th percentile DD; gate against capital buffer | [COMMUNITY] mynameisjanus "Bootstrap and Monte Carlo" ML4T capstone |
| **Walk-Forward Analysis (WFA)** | Parameter overfitting to the in-sample period alone; no true OOS | ≥ 5–8 OOS windows; IS:OOS ≈ 3:1–5:1 (Pardo 4:1 default); OOS ~1yr | WFE (OOS/IS return) ≥ 0.5–0.8; never re-select on OOS | [PAPER] Pardo 2008 "The Evaluation and Optimization of Trading Strategies" |
| **Permutation / placebo test** | "The edge is just chance" (category-specific) | Reproduce strategy on shuffled/synthetic data | p ≤ 0.05 (repo uses 0.01) — but *see §MeanR*: plain shuffle is invalid for mean reversion | [COMMUNITY] janus "Bootstrap & Monte Carlo" ML4T capstone; repo's own `permutation_tester.py` |
| **Minimum sample length (MinTRL/MinBTL)** | Too-short backtests → Sharpe estimates are noise | 2–5y+ per strategy, monthly retuning | If observation count < MinTRL, treat the SR as indistinguishable from luck | [PAPER] Bailey & Lopez de Prado 2012 |

---

## Deep dives (each ~400 words)

### 2. Combinatorial Purged CV (CPCV)

**Problem.** Standard k-fold CV over time-series projects data: if labels contain a horizon (e.g., a 20-day forward return), consecutive folds share information, and a fold boundary cut through a chunk leaks the label period into the training set. Traditional walk-forward (see also deep-dive 5) also destroys the *amount* of usable history and yields only one OOS path. CPCV fixes both.

**Mechanics.** Split the (purely chronological-respecting) panel into **N=10–20 contiguous groups**. Train on some combination of (N−k) groups, test on the remaining k, and — crucially — **purge** training samples whose label windows overlap test groups, then **embargo** a buffer (≈ label horizon) after the test block so autocorrelated samples don't bleed across. You don't run one split: you run all `C(N,k)` splits (`k/N × C(N,k)` equals the number of paths — each bar appears OOS in exactly `C(N−1, k−1)` paths). So you get an entire *distribution* of OOS performances and can compute the **Probability of Backtest Overfitting (PBO)**: fraction of paths in which the model selected on that path's IS data underperforms the OOS median. A PBO < 0.2 is treated as acceptable; > 0.5 is a red flag.

**Evidence.** López de Prado & Bailey (2017) introduced the CSCV method; the combinatorics generalization is in *Advances in Financial Machine Learning* (ch. 12–13). A 2024 independent study (KnoSys) compared CPCV against other strategies and found it a superior generalization estimate with lower PBO than plain walk-forward under typical backtest regimes.

**Gotchas.** (1) You need enough data — with 4–5 years of daily bars and N=10 you give each IS fit ~80% of the record; on micro-strategies with few parameters that's fine, but don't use k of 2 (paths=45) with 300 days of data. (2) Purge must cover the label horizon; for mean-reversion with a 5-day label, an embargo of ≥5 days is mandatory, or the leakage returns. (3) CPCV gives you *distribution*, not a single verdict — report the PBO. (4) Frames: the time cost is a matrix of `configs × C(N,k)` backtests — for an engine that re-optimizes weekly, run CPCV on the *final champion only*, not on every grid point.

**Free implementations:** `purgedcv` (PyPI; MIT — provides CPCV, PurgedKFold, PBO, PSR), `eslazarev/purged-cross-validation` (MIT, sklearn-compatible), or numpy loops over your own splitter. `mlfinlab` historically was the reference but has been paid-only since 2023 (community forks exist).

---

### 3. White's Reality Check and Hansen's SPA

**The problem.** Any optimization over N candidates will eventually produce a "great-looking" strategy by chance alone. In the canonical application (Sullivan, Timmermann & White 1999), 7,846 technical trading rules on the Dow Jones were tested over ~100 years — and the best rule in-sample showed no predictive power out-of-sample. White's Reality Check formalizes this.

**Mechanics.** You hold a benchmark (e.g., buy-and-hold, or the zero-return rule) and a set of candidate rules, each with an excess-return series relative to the benchmark. Test: `H0: max_f E[excess_f] ≤ 0` — no rule beats the benchmark. Under the null you recenter everything at 0 and use the **stationary bootstrap** (Politis & Romano 1994, resampling *blocks* to preserve autocorrelation) to re-estimate the max-statistic distribution; the p-value is the fraction of bootstrap replicas whose max exceeds the observed sample max. Critically, the null is **conservative** — it takes the worst case among candidate rules as the null (LFC), which is why Hansen (2005) proposed the **SPA test** that recenters at the best-performing rule and yields a more powerful, "consistent" p.

**Common pitfalls.** (1) You must feed *all* candidates into the matrix — engineers often "clean up" losers, destroying the very thing the test protects against. Log your trials in full; the repo's engine auto-tunes, so every tuning round adds to N. (2) The test is scores-based, ignoring magnitude of any single rule; the DSR is complementary (a closed-form N-adjusted p). (3) With highly-correlated variants (same signal ±2%), the statistic smooths out and you can pass while the average real rule loses — keep an eye on the *number of independent* parameter families, not just entries.

**In this repo.** `arch` is already a dependency (`validators/statistical.py` imports `StationaryBootstrap`), and `arch.bootstrap.SPA` / `arch.bootstrap.StepM` are exactly the official implementations (BSD; zero extra installs). The current `spa_test` entry in `statistical.py` is a plain studentised-mean t-test on the column — a mislabeled approximation, not Hansen's method. **Recommendation: swap to `arch.bootstrap.SPA` (with `studentize=True`, default stationary bootstrap) and be done.** The repo's `whites_reality_check.py` wrapper → `StatisticalValidator.whites_reality_check(block_size=10, replications=1000)` is structurally close enough but only decent for 1-vs-1; the matrix form is the useful one.

---

### 4. MeanR (mean-reversion strategy validation) — where the standard tool throws

The engine's fade strategy is the *mean-reversion* case. Classic validation tools as typically implemented are **wrong-shaped for MR**:

1. **Plain return-shuffle permutation test (what `permutation_tester.py` does).** Shuffling bar geometry (inter-bar gaps + intra-bar HLC) *destroys* the short-lag autocorrelation that MR exploits, so the "null" is *unfairly easy*: any strategy whose edge depends on inter-bar dependence will pass almost any shuffle — you learn "yes it beats white noise", not "yes it beats the realistic regime of noise+lag structure". **Correct null for MR = circular-shift (preserve sign/block structure) or moving-block permutation** — keep the marginal structure, destroy only the *timing* alignment between signal and return. (If the edge is truly intra-bar, permute *blocks* of at least the label horizon.)

2. **Stationarity assumptions.** A mean-reversion model is only valid on a stationary spread. At the very least run **ADF (statsmodels `adfuller`)**, and for pair-like spreads compute **half-life fit (OU model: θ from regression of Δy on y, λ = −ln2/θ)** — if the estimated half-life is much larger than the holding period, the "reversion" is just drift noise. The engine's `FadeStrategy` logic should report ADF stat + half-life in its output; treat trends (e.g., 2020–21 bear) as out-of-regime and validate on consecutive trending windows.

3. **Cost sensitivity is the deciding test.** MR edges are typically fractions of a percent per trade; on a $100 account, $0.005–$0.02/share commission plus spread can consume the entire edge. No significance of the CI matters until the edge survives at 2–3× realistic friction (AUDIT_FINDINGS already flags slippage explicitly).

4. **Sample horizon vs half-life.** Minimum data length for MR strategies ≈ few half-lives ≥ your holding period; else the null correlation structure is not stationary.

**So the "MeanR" deep dive is a warning**: don't hand the MR strategy to the generic tools letter-perfect — give it (a) the circular-shift/block permutation variant, (b) ADF/half-life pre-check, (c) cost-multiplier stress, (d) DSR treats every candidate reversion-config as one of N trials.

---

### 5. Monte Carlo confidence intervals for Sharpe and drawdown

**Why.** A backtest gives you one number — say SR 0.8. That number has sampling error shaped by: length (√T), skew/kurtosis of returns (fat tails mislead the normal approximation), and serial correlation (iid assumptions understate variance). Bootstrap/MC gives you its true distribution, including extremes, per your actual data, and lets you ask: "can the 95% CI exclude zero?" and "what's the 95% worst drawdown path?"

**Sharpe.** Standard errors: Lo (2002) gave the iid-case approximation `SE(SR̂) ≈ √((1 + ½SR²)/T)`; since your returns are *not* iid (fade strategies have autocorrelation by construction), the right CI is non-parametric: **resample actual returns by stationary bootstrap** (blocks) — report a BCa (bias-corrected, accelerated) percentile CI. `scipy.stats.bootstrap` does this out of the box; pin seeds per run for reproducibility (the repo uses `np.random.seed` in several places — fix it per run).

**Drawdown.** There's no closed form for max DD under autocorrelation; use MC: (a) block-resample the equity-curve return series 10,000×, compute maxDD per path, take the 95/99th percentile envelope; or (b) if your edge is trade-level, shuffle/block-permute the *trade* list 10k× (order changes the DD path) — you get "what's the worst DD a random ordering of my actual trades produces?" That's a *cheap, numpy-only* 10,000-path MC that directly answers the $100-capital question: **"if I ride to $100, what DD must I survive?"** The engine's rule sets a drawdown guardrail; this estimation is its input.

**Repo**: no MC/CI implementation exists yet (only point-statistics + tests). ~40 lines of python connects to existing `statistical.py`.

---

### 6. Walk-forward analysis (out-of-sample by design)

**Mechanics.** Split the data into *rolling* IS/OOS windows; every window: optimize (or finalize params) on IS, produce OOS return into the equity curve, re-fit, advance. Two variants, **anchored** (IS grows; good with little data) vs **rolling** (fixed IS length; trust recent regime). Reasonable defaults: IS 3y / OOS 1y (OOS ≈ 25% of the window, i.e. 3:1), though the practitioner range is IS:OOS 3:1–5:1; use ≥5–8 windows so a single window can't drive the verdict; typical OOS length ~1 year. You do NOT re-tune within OOS; the final parameters from the walk-forward pass are held; and the *last true holdout* never touches the optimizer. Efficiency metric: `WFE = OOS_return / IS_return` (≥0.5 seems the rough "keep going" bar in the practitioner literature; ≥0.8 excellent).

**Why it's underrated at this repo's scale:** Because the engine re-optimizes *every week* on all available history, *any* in-sample test becomes circular, but walk-forward *defines* the liveness: every weekly "IS" is literally last week's data for the next week's "OOS" — so a proper **walk-forward fork of the engine is the only honest nomination** of its weekly performance. Your `backtester.py`-style scripts can generate it without new deps: loop over weekly re-fits, record the subsequent week returns, then aggregate (that is ~40 extra lines). Risk: as the engine is doing systemic parameter re-tuning thousands of times, you *must* also keep the trial ledger (see DSR/N).

### Minimum sample length companion metric (MinTRL)
Short backtests make Sharpe a noisy number: at SR ≈ 0.5 and T ≈ 2,500 daily bars the standard error is already ~0.09 — the border zone where SR starts to mean something. For every production claim, state the observation count alongside the SR; DSR folds T into the test itself, so report it together. (Formula and tables: Bailey & López de Prado 2012, "The Sharpe Ratio Efficient Frontier".)

---

## 7. Recommended free implementations (and the repo's current state)

### Use these (all free, no installs beyond what the engine has)

| Tool | Use | License/status |
|---|---|---|
| `arch` (already a dependency!) — `bootstrap.SPA`, `bootstrap.StepM` (WRC/SPA with recentering), `bootstrap.StationaryBootstrap` | Real WRC/SPA — swap out `spa_test` | BSD; verified in-repo |
| `scipy.stats.bootstrap` | BCa percentile CIs for SR (and any stat) | BSD |
| `statsmodels` (`adfuller`, `coint` / Johansen; OU half-life fit) | MeanR stationarity pre-check | BSD |
| `purged_cv` (PyPI) / `eslazarev/purged-cross-validation` | CPCV + PBO + DSR/PSR; K-fold with embargo, sklearn-style | MIT |
| numpy-only ~10k-path MC (in-repo) | DD envelope, trade-permutation | — |
| `walk-forward`: hand-rolled loop over re-fits (no lib needed) | weekly production OOS | — |

**Repo current state (what exists, what is naive/misleading):**
- `validators/statistical.py` — `StationaryBootstrap` block_size=10 (default), replications=1000, p≤0.05 — OK skeleton for WRC; **`spa_test` is a plain t-test, not SPA**; `combinatorial_purged_cv` purges *adjacent blocks* but does not embargo and evaluates no label-horizon purge (CPCV defined in §2, not fully); no PBO paths.
- `whites_reality_check.py` — thin wrapper delegating proper method; fine as-is.
- `permutation_tester.py` — 1000 permutations, p_threshold=0.01, PF>1 gate, shuffles OHLC geometry; **plain shuffle null: invalid for MR (see §4)**; also uses unseeded global numpy RNG and evaluates the strategy on synthetic OHLC where costs are not applied — order-sensitive. Suggest a `--null circular` variant + seed + cost injection.
- `alpha/fade_strategy.py` — MeanR logic; pair with section 4 checks.

## 8. Practical how-to — which validations earn their keep at the $100 scale

### Do these (cheap, high signal-to-noise)

1. **Honest trial ledger + DSR.** Every agent tuning round is a "trial" for selection bias. Count N honestly (all configs tried, including discarded ones) and feed it into the DSR formula — it corrects the reported Sharpe for the number of trials. If the engine logs candidate backtests, computing DSR is ≈15 lines (formula in §2 of Bailey–López de Prado 2014).
2. **1–2-param perturbation sensitivity.** Re-run the champion ±10–20% around its chosen parameters; if performance collapses, that's a local-optimum red flag. (Cheap, and it directly informs the engine's self-optimizing loop.)
3. **Walk-forward per strategy** as §6; the weekly OOS export is just ledger columns.
4. **MC DD envelope** on the *trade-level* sequence alone (10k paths, numpy) — gives you "what DD must I survive with $100", which feeds your existing drawdown guardrail constants, and works even when T for Sharpe is short.
5. **Cost multiplier stress ×2–3×** — as the dominant risk, per AUDIT_FINDINGS.

### Skip (properly, with reason)

- **Full CPCV at every re-opt** — expends data you don't have at micro-scale; use purged k-fold/5 windows for mid-size, CPCV once for the final champion.
- **PBO/CSCV matrix** — needs the full config×path matrix of the whole optimizer history; DSR approximates the same info cheaper; revisits when the engine has months of run logs.
- **WRC/SPA across thousands of near-identical agent variants** — the independent-family count is low; SPA on the *family-average* matrix if you must.
- **GARCH/regime parametric MC, deep param grids** — overkill with ~2.5k days of daily bars; stationary bootstrap is enough.

### Operating rules (non-negotiable)
Canonical: Don't touch the final holdout. Don't re-validate on OOS. Log every trial (losers included). Seed every RNG. State observation count alongside any Sharpe.

---

## Resources (all verified in-session 2026-08-09)

| Source | URL | Tag |
|---|---|---|
| White, "Reality Check for Data Snooping" (Econometrica 68(3), 2000) | https://doi.org/10.1111/1468-0262.00152 | [PAPER] |
| Hansen, "A Test for Superior Predictive Ability" (JBES 23(4), 2005) | https://doi.org/10.1198/073500105000000063 | [PAPER] |
| Sullivan, Timmermann & White (1999), Dow rules study | https://doi.org/10.1111/0022-1082.00163 | [PAPER] |
| Bailey & López de Prado, "The Deflated Sharpe Ratio" (JPM 40(5), 2014) | https://doi.org/10.3905/jpm.2014.40.5.094 | [PAPER] |
| Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (JCF 20(4), 2017) | https://ssrn.com/abstract=2326253 | [PAPER] |
| Bailey, Borwein, López de Prado & Zhu, "The False Strategy Theorem" (Am. Math. Monthly 128(9)) | https://doi.org/10.1080/00029890.2021.1965068 | [PAPER] |
| Lo, "The Statistics of Sharpe Ratios" (FAJ 58(4), 2002) | https://ssrn.com/abstract=377260 | [PAPER] |
| Politis & Romano, "The Stationary Bootstrap" (JASA 89(428)) | https://doi.org/10.1080/01621459.1994.10476870 | [PAPER] |
| Pardo, *The Evaluation and Optimization of Trading Strategies* 2e (2008, pub. 2012), Wiley — ch. 11 "Walk-Forward Analysis" | https://onlinelibrary.wiley.com/doi/abs/10.1002/9781119196969.ch11 | [PAPER] |
| `arch` 8.x docs — Multiple Comparison Procedures (`bootstrap.SPA`, `StepM`, `MCS`; module `arch.bootstrap`) | https://bashtage.github.io/arch/multiple-comparison/multiple-comparisons.html | [OFFICIAL] |
| `purged_cv` (PyPI) | https://pypi.org/project/purgedcv/ | [COMMUNITY] |
| `eslazarev/purged-cross-validation` (GitHub, MIT) | https://github.com/eslazarev/purged-cross-validation | [COMMUNITY] |
| KnoSys 2024 CPCV-vs-CV benchmark study (found via search S52; primary page retrieved in-session) | *search-recorded in `.swarm` (S52); URL not pinned* | [COMMUNITY] |
| ML4T capstone "Bootstrap and Monte Carlo" (janus.ml) | https://mynameisjanus.github.io/part-03-statistics/05-bootstrap-and-monte-carlo/ | [COMMUNITY] |

[COMMUNITY] marks verified-in-session community sources; [PAPER] peer-reviewed with stable DOI/SSRN.

---

## Final word

The $100 engine is a testing shop — validation is not a checkbox at the end; it is a per-decision pipeline (trial ledger → DSR → sensitivity → weekly WF → DD MC at the capital guardrail). The repo is one import away from a proper SPA (the `arch` package it already ships), one log away from DSR (trial count), and one `--null-mode circular` flag away from making the existing permutation test honest for the fade strategy. Do not add complexity (CPCV-every-round, parametric regimes) before costs at $0.03/share are proven survivable — that is the real discipline at $100.