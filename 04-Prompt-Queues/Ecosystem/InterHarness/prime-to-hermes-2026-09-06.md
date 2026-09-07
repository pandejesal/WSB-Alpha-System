# Prime to Hermes — RLM Evolution Strategist Brief — 2026-09-06 Tour 1

**Role:** RLM brain (Prime) — Hermes + evolve_real.py are hands. Single-writer rule: never write registry.json / evolve_real.py / gate code. Paper only.
**Calibration:** Loop window 1910 bars 2019-2026, SPY +245.5% Sharpe 0.94 maxDD 34%. DSR barrier at N=27110 trials: DSR>=0.95 demands Sharpe>=2.01; per-family N~=1000 demands 1.38-1.49. Zero full-gate beaters in 27000+ iters is expected, not broken.
**History tail:** iter 27618 latest. Cited numbers from last 3000 verified trials (evolve_real_history.jsonl) — never invented.

## Tour 1 — 2026-09-06 — 20 proposals appended to docs/data/next_gen_proposals.jsonl

| # | Family | Params | Parent OOS | Why (cite history) | Target Track |
|---|--------|--------|------------|---------------------|--------------|
| 1 | spy_ltrend | window 420 | 1.551 | spy_ltrend last 308 trials best OOS 1.551 Sharpe 1.06 excess -96.0pp max DSR 0.12; mean excess -126pp. Window 152 best but sits at lower bound of extended sweep; extending to 420 raises TIM from ~60% toward 75%+ to clear tmin>=0.70 without cash-drag. Per-family DSR at N~1000 needs Sharpe 1.38 not 2.01. | high_exposure_momentum (Sharpe>=0.75 excess>=0.05pp tmin>=0.70 DSR>=0.90) |
| 2 | spy_ltrend | window 480 | 1.551 | Same history as #1; 480 is intermediate extension testing monotonic TIM increase. Recent spy_sma/spy_ltrend excess -95 to -96pp all negative despite Sharpe 1.06 — only longer window can push excess toward positive. | high_exposure_momentum |
| 3 | spy_ltrend | window 550 | 1.551 | Same; 550 pushes toward buy-hold companion regime (tmin>=0.80). Twin btc_vol shows excess can be positive only at high exposure (btc_vol max excess +2852pp). | buy_hold_companion (Sharpe>=0.85 excess>=0.02pp tmin>=0.80 DSR>=0.95) |
| 4 | spy_ltrend | window 600 | 1.551 | Extreme extension; tests whether 600-day SMA (2.4y) approaches buy-hold with crisis filter, matching paper's demand for 70%+ TIM or yield kicker. | buy_hold_companion |
| 5 | us_momentum | lookback 42 skip5 top_n3 | 1.097 | us_momentum last 288 trials mean excess -218.5pp max -196.9pp Sharpe max 0.75 OOS max 1.097 best lookback 190. Small lookback 42 + top_n3 concentrates winners and raises TIM to 80-85% vs current 100% rotation but with higher turnover; DSR max only 0.021 shows N dilution — new per-family scoping helps. | high_exposure_momentum / buy_hold_companion |
| 6 | us_momentum | 48/7/3 | 1.097 | Variant of #5 with 48-day lookback (~2M) + skip 7 avoids 1-week reversal; tests small window stability. Target TIM 75% excess +2 to +8pp. | high_exposure_momentum |
| 7 | us_momentum | 63/5/4 | 1.097 | 63-day (quarterly) momentum classic; top_n4 diversifies to hold 4/10 names ~40% concentration vs 3 names; balances Sharpe>=0.75 with tmin. | high_exposure_momentum |
| 8 | us_momentum | 55/10/3 | 1.097 | 55-day with skip 10 tests anti-reversal; skip 10 was under-explored (history skip mean ~20). | high_exposure_momentum |
| 9 | gap_mr | gap_z20 entry1.30 exit0.55 hold3 vol1.00 | 1.792 | gap_mr last 189 trials Sharpe max 1.069 OOS max 1.792 but excess worst -241pp mean -220pp DSR 0.12 — Sharpe ok but excess negative because shorts drag? Long-only variant with tight gap_z 20 and entry 1.30 increases selectivity, hold3 captures mean reversion without overnight bleed. Needs excess>=0.05pp Sharpe>=0.60. | core_timing_overlay (Sharpe>=0.60 excess>=0.05pp DSR>=0.80 trips>=8) / tail_risk_sentinel (maxDD<=0.25 excess>=0.03pp) |
| 10 | gap_mr | 30/1.50/0.60/4/1.10 | 1.792 | Median window 30 with higher entry 1.50 reduces false positives; vol_filter 1.10 ensures calm-only entries avoiding crash gaps. | core_timing_overlay |
| 11 | gap_mr | 15/1.40/0.50/2/0.90 | 1.792 | Short window 15 for faster z; exit 0.50 partial fill captures quick snap-back; max_hold 2 limits time decay. | tail_risk_sentinel |
| 12 | gap_mr | 40/1.25/0.65/5/1.20 | 1.792 | Long window 40 with loose entry 1.25 increases trip count toward trips>=8 DSR>=0.80; hold5 allows fuller reversion. | core_timing_overlay |
| 13 | btc_regime | target0.35 btc20 spy30 corr25 cap0.20/0.40 | -0.211 | btc_regime last 197 trials mean excess -165pp best -71pp Sharpe 0.61 OOS -0.21 DSR 0.02 — negative excess but Sharpe near 0.60 threshold; unlevered target 0.35 with tight spy_vol_cap 0.20 dampens drawdown for tail_risk_sentinel maxDD<=0.25. | core_timing_overlay / tail_risk_sentinel |
| 14 | btc_regime | 0.30/30/45/35/0.22/0.50 | -0.211 | Lower target 0.30 reduces vol drag; wider windows smooth regime signal; corr_cap 0.50 allows more BTC exposure when decorrelated. | core_timing_overlay |
| 15 | btc_regime | 0.40/25/60/30/0.18/0.35 | -0.211 | Higher target 0.40 with stricter caps (spy_vol 0.18 corr 0.35) cuts equity beta during stress — aims for Sharpe>=0.60 and positive net excess via yield (BTC trend). | tail_risk_sentinel |
| 16 | btc_regime | 0.45/15/25/20/0.25/0.45 | -0.211 | Aggressive target 0.45 but short windows reactive; tests if faster gates recover OOS from -0.21 toward 0.5 gate. | core_timing_overlay |
| 17 | us_ltrend | lookback260 top_n3 | 0.684 | us_ltrend last 291 trials max Sharpe 0.708 OOS 0.684 excess -200pp DSR 0.016; short end of 252-504 range with top_n3 maximizes concentration and TIM 100%; prior best lookback 291 — 260 tests faster formation. | high_exposure_momentum |
| 18 | spy_sma | window380 | 1.624 | spy_sma history: 378 trials max OOS 1.624 Sharpe 1.06 excess -95.9pp. Window 380 near upper bound 300 extends trend hold, parallels spy_ltrend extension but within original family. | high_exposure_momentum |
| 19 | btc_vol | target0.40 vol25 gate180 | 0.472 | btc_vol last 303 trials Sharpe 1.21 OOS 0.472 excess +907pp mean but gate 50 best; gate 180 tests longer trend filter to reduce whipsaw trips while preserving high excess. | high_exposure_momentum (BTC not SPY excess but validates yield-kicker logic) |
| 20 | btc_donchian | entry_ch20 exit_ch10 | 0.45 | btc_donchian last 301 trials Sharpe 1.00 OOS 0.45 excess +1155pp; 20/10 mid-range Donchian balances Sharpe>=0.75 and trips. Serves as high-exposure yield baseline. | high_exposure_momentum |

**DSR scoping note:** All DSR values cited at N~27000 global. Proposals aim for per-family scope N~1000 where DSR 0.70-0.80 needs Sharpe 1.38-1.49 not 2.01. Excess-vs-SPY >0 mandatory — every proposal targets excess >=+0.02pp to block TOP5_TRIPLE_CHECK failure (-70 to -137pp).

**Verification:** proposals appended, brief written, both files exist on disk. Next tour reads newest history tail and proposes next 20.

---
*Prime RLM — paper only, never live. Single-writer: Hermes executes evolves.*


## Tour 2 — 2026-09-06 — 20 proposals appended (total 60 = 20 seed + 20 t1 + 20 t2)

History tail iter 27631: spy_rsi2 8/77/6 OOS 0.535 excess -115.9 Sharpe 0.81 DSR 0.03 — confirms low-exposure trap persists. Last 3000 stats: btc_vol Sharpe 1.21 OOS 0.469 excess +907pp mean, btc_donchian Sharpe 1.00 OOS 0.45 excess +1155pp; US momentum still negative mean excess -218pp. DSR barrier N=27115 still demands Sharpe 2.01 globally.

| # | Family | Params | Parent OOS | Why | Target Track |
|---|--------|--------|------------|-----|--------------|
| 21 | spy_ltrend | 350 | 1.551 | Window 350 tests mid-extension between original max 400 and Tour1 420 — granularity check for TIM curve; spy_ltrend best window 152 with OOS 1.551 but TIM ~55%. | high_exposure_momentum |
| 22 | spy_ltrend | 450 | 1.551 | 450 bridges Tour1 420-480 gap; monotonic sweep. | high_exposure_momentum |
| 23 | spy_ltrend | 520 | 1.551 | 520 pushes toward buy_hold_companion tmin 0.80; mirrors us_ltrend logic of 1-2y formation. | buy_hold_companion |
| 24 | spy_ltrend | 580 | 1.551 | Near Tour1 600 but 20-day offset tests sensitivity. | buy_hold_companion |
| 25 | us_momentum | 30/5/3 | 1.097 | Shortest lookback 30d (~1M) extreme momentum; history shows lookback 190 best but 30d untested at top_n3 small; high churn but TIM ~85% with yield. | high_exposure_momentum |
| 26 | us_momentum | 70/8/5 | 1.097 | 70d with top_n5 diversifies to 50% of universe, lowers vol for Sharpe>=0.75 while retaining excess. | high_exposure_momentum |
| 27 | us_momentum | 90/12/3 | 1.097 | Quarterly 90d momentum; skip 12 filters reversal documented in us_momentum mean excess -218pp. | high_exposure_momentum |
| 28 | us_momentum | 35/6/4 | 1.097 | 35d with top_n4 hybrid short formation. | high_exposure_momentum |
| 29 | gap_mr | 25/1.35/0.60/3/1.05 | 1.792 | gap_mr best OOS 1.792 at 58/1.43/0.50 — this narrows window 25 with mid entry to lift trips toward core_timing trips>=8. | core_timing_overlay |
| 30 | gap_mr | 18/1.60/0.55/2/0.95 | 1.792 | Tight 18d window high entry 1.60 selective, trip rate low but Sharpe may rise; pairs with #31. | tail_risk_sentinel |
| 31 | gap_mr | 35/1.20/0.70/4/1.15 | 1.792 | Loose entry 1.20 with high exit 0.70 boosts trip count to meet DSR>=0.80. | core_timing_overlay |
| 32 | gap_mr | 50/1.45/0.50/5/1.25 | 1.792 | Long window 50 dilutes noise, vol 1.25 relaxes calm filter to increase opportunities. | tail_risk_sentinel |
| 33 | btc_regime | 0.28/22/35/28/0.19/0.38 | -0.211 | btc_regime best excess -71pp Sharpe 0.613 OOS -0.21 — needs tighter spy_vol 0.19 to cut maxDD below 0.25 for sentinel. | tail_risk_sentinel |
| 34 | btc_regime | 0.32/28/50/32/0.21/0.42 | -0.211 | Moderate target 0.32 with wider spy window 50 smooths regime; corr 0.42 balanced. | core_timing_overlay |
| 35 | btc_regime | 0.38/18/40/24/0.23/0.48 | -0.211 | Higher target 0.38 reactive windows; aims Sharpe>=0.60 with excess>=0.05pp via BTC beta. | core_timing_overlay |
| 36 | btc_regime | 0.50/20/55/40/0.26/0.55 | -0.211 | Max target 0.50 tests unlevered cap; long corr window 40 reduces false de-risk. | tail_risk_sentinel |
| 37 | us_lowvol | vol30 top_n10 | 0.504 | us_lowvol mean excess -222.5pp flat history — best vol_window 46 top_n30 too diffuse; 30/10 concentrates low-vol small-cap tilt with 100% TIM, aims to escape -222pp trap via narrower basket. | high_exposure_momentum |
| 38 | us_lowvol | 60/15 | 0.504 | Mid concentration 60/15 tests vol window stability. | high_exposure_momentum |
| 39 | us_ltrend | 320/4 | 0.684 | us_ltrend best 291/3 OOS 0.684 — 320/4 modestly longer formation + one extra name diversifies. | high_exposure_momentum |
| 40 | spy_sma | 285 | 1.624 | spy_sma best 127 OOS 1.624 but window 285 extends toward 400 boundary; links spy_sma and spy_ltrend curves. | high_exposure_momentum |

Verification: both deliverables exist — proposals 60 lines, brief exists.


## Tour 3 — 2026-09-06 — 20 proposals appended (total 80)

History tail iter 27636: still spy_rsi2 dominated (196 trips) excess -146pp — validates loop reading newest tail. N=27120 global. All cited numbers from last 3000: spy_ltrend max excess -96pp, us_momentum mean -218pp, gap_mr Sharpe 1.069 OOS 1.792, btc_regime best excess -71pp.

| # | Family | Params | Parent OOS | Why | Target Track |
|---|--------|--------|------------|-----|--------------|
| 41 | spy_ltrend | 320 | 1.551 | Window 320 interior extension; tests TIM 65-70% threshold between conservative and high_exposure. | high_exposure_momentum |
| 42 | spy_ltrend | 400 | 1.551 | At original max 400 boundary — validates whether boundary itself can clear tmin 0.70. | high_exposure_momentum |
| 43 | spy_ltrend | 620 | 1.551 | Ultra-long 620 beyond Tour1 600; maximal buy-hold companion test. | buy_hold_companion |
| 44 | spy_ltrend | 380 | 1.551 | 380 between 350-420 for dense coverage. | high_exposure_momentum |
| 45 | us_momentum | 40/7/3 | 1.097 | 40-day short formation variant; anticipates 70-85% TIM yield. | high_exposure_momentum |
| 46 | us_momentum | 50/5/3 | 1.097 | 50-day bridges 42-63 range. | high_exposure_momentum |
| 47 | us_momentum | 60/15/4 | 1.097 | 60d with skip 15 heavier reversal filter. | high_exposure_momentum |
| 48 | us_momentum | 80/10/3 | 1.097 | 80d near 90d quarterly alternative. | high_exposure_momentum |
| 49 | gap_mr | 22/1.50/0.60/2/1.00 | 1.792 | Tight hold2 + entry1.50 tail-risk calibrated maxDD<=0.25. | tail_risk_sentinel |
| 50 | gap_mr | 28/1.40/0.55/3/1.10 | 1.792 | 28d mid variant. | core_timing_overlay |
| 51 | gap_mr | 35/1.30/0.65/4/0.85 | 1.792 | Strict vol 0.85 calf filter maxDD. | tail_risk_sentinel |
| 52 | gap_mr | 45/1.55/0.50/5/1.20 | 1.792 | Long hold5 broader gap. | core_timing_overlay |
| 53 | btc_regime | 0.33/24/32/26/0.17/0.36 | -0.211 | Strict spy_vol 0.17 tightest DD guard for sentinel. | tail_risk_sentinel |
| 54 | btc_regime | 0.36/26/38/30/0.19/0.40 | -0.211 | Moderate 0.36 balanced. | core_timing_overlay |
| 55 | btc_regime | 0.42/30/48/34/0.22/0.45 | -0.211 | 0.42 higher beta but longer windows. | tail_risk_sentinel |
| 56 | btc_regime | 0.30/20/28/22/0.18/0.34 | -0.211 | Low target 0.30 strict caps minimal drawdown. | tail_risk_sentinel |
| 57 | us_ltrend | 400/3 | 0.684 | Long formation 400d tests slow rotation with TIM 100%. | high_exposure_momentum |
| 58 | us_lowvol | 45/12 | 0.504 | 45/12 intermediate concentration vs 30/10 and 60/15. | high_exposure_momentum |
| 59 | btc_vol | 0.35/30/150 | 0.469 | btc_vol mid gate 150 vs 180 prior. | high_exposure_momentum |
| 60 | btc_donchian | 15/8 | 0.45 | Shorter entry 15 vs 20 tests Donchian sensitivity. | high_exposure_momentum |

Verification: both deliverables exist — proposals 80 lines, brief exists. Loop continues every cycle reading newest history tail.
