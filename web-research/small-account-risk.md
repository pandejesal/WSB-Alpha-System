# Risk & Position Sizing for Tiny Accounts ($100–$1k)

Internet research compiled from web-search findings only. All claims below carry the URL(s) where they were found. Where anything is extrapolated to a $100 account, it is marked **OPINION**.

---

## 1) Technique table

| Technique | Math / formula | Evidence link(s) | Recommendation for a $100 account |
|---|---|---|---|
| **Fractional Kelly** (quarter/half) | `f* = W − (1−W)/R`; trade at `0.25×f*` or `0.5×f*` | https://tradernest.ai/blog/kelly-criterion-trading · https://pomegra.io/learn/library/track-e-trading-risk/risk-management/chapter-02-the-risk-of-ruin-equation/fractional-kelly · https://blog.elearnmarkets.com/kellys-criterion-explained/ · https://alltradertools.com/blog/kelly-criterion-trading-explained | Only as a **ceiling check**, not a size input. On $100, quarter-Kelly of a typical edge (f*≈20–30%) is 5–7.5% risk = $5–7.50 per trade — still far above the ~1% survival sizing the same sources' ruin tables recommend. **OPINION:** use Kelly to reject no-edge strategies; size with Section 4 caps instead. |
| **Fixed fractional 1% / 2% rule** | `Risk $ = Equity × risk%`; `Units = Risk $ / stop distance` | https://quantstrategy.io/blog/the-power-of-fixed-fractional-position-sizing-calculating · https://www.mrtrader.io/learn/position-sizing-small-accounts · https://traderssecondbrain.com/guides/risk-per-trade-guide · https://edge-ledger.io/blog/crypto-portfolio-risk-management-2026 | 1% of $100 = **$1.00 max risk per trade**. Only executable where instruments allow sub-$1–$5 orders (see §3). Round down, never up. |
| **Fixed fraction 1R/2R (R-multiplier)** | 1R = planned loss at the stop; positions sized so every loss = −1R; daily loss cap 2R–3R | https://www.nvestiq.com/blog/position-sizing-how-much-to-risk-per-trade · https://www.traderegimen.com/blog/r-multiple-position-sizing · https://tradejournal.ai/learn/r-multiple-explained · https://tradeorbit.io/learn/risk-management-trading | Adopt R-thinking as the language: on a $100 account 1R = $1.00–$1.50 (1%–1.5%) **OPINION**. Daily stop 2R–3R = $2–$3. Keeps the math identical no matter where the stop sits. |
| **Max-Drawdown-based sizing** (DD as distribution, 95th pct DD) | Run Monte Carlo on your R-series; target P95 DD within budget (e.g. <25%); shrink if risk-of-ruin >1–2% | https://www.quantifiedstrategies.com/maximum-drawdown-position-sizing/ · https://delvertrade.com/en/blog/max-drawdown-risk-of-ruin · https://sggroup.jp/article/tradingview-backtest-robustness-lab/en-monte-carlo/ · https://backtestme.com/guides/monte-carlo-simulation | DD budget on $100: max acceptable = −20% to −25% (≈ −$20 to −$25) **OPINION**; pick the risk% whose 95th-pct DD lands inside that budget. Any plan whose P95 DD wipes −50% ($50) of the account is a plan discard. |
| **Kelly-constrained combination** | risk ≤ min(fixed %, fractional Kelly, DD budget, heat cap) — the tightest wins | https://blog.quantinsti.com/risk-constrained-kelly-criterion · https://thecapitalprocess.com/position-sizing-mastery-2026-fixed-fractional-volatility-based-kelly-criterion-optimal-f-full-mathematical-breakdown-survival-analysis · https://chartmini.com/blog/the-art-of-position-sizing-how-much-to-trade-2026 | Run as a 4-way AND: risk ≤ 1%? risk ≤ ¼-Kelly? risk ≤ DD-implied? risk ≤ heat budget? Smallest wins. On $100 the winner is almost always 0.5–1%. **OPINION.** |
| **Portfolio heat / correlation cap** | Heat = Σ risk% of all open trades; cap 3–6%; correlated bucket ≤ 3 positions; ≤ 0.5–1% each | https://www.quantum-algo.com/academy/multi-position-management · https://finaur.com/blog/en/risk-management/portfolio-heat-limits-in-trading · https://nexusfi.com/a/risk-management/correlation-adjusted-position-sizing | **OPINION:** for $100, heat cap 3% (a max ~3 simultaneous $1 trades). Correlated stack (2 × BTC-ish longs) counts as ONE position. |
| **Fixed-dollar / fixed-notional** | Position $ = fixed dollar amount per trade | https://thecapitalprocess.com/position-sizing-mastery-2026-fixed-fractional-volatility-based-kelly-criterion-optimal-f-full-mathematical-breakdown-survival-analysis | Not recommended (fixed $ doesn't shrink with equity). Brokers' minimum notional is the only legitimate fixed-$ size on $100. **OPINION.** |
| **Anti-martingale / streak sizing** | Increase size only as account grows; never after a loss; no doubling down | https://en.wikipedia.org/wiki/Gambler%27s_ruin · https://mathworld.wolfram.com/GamblersRuin.html · related: https://quantstrategy.io/blog/the-power-of-fixed-fractional-position-sizing-calculating (anti-martingale linked inside) | The core rule for tiny accounts: fixed % of equity (shrink after loss) *is* the anti-martingale requirement; a martingale cycle at $100 is literally unaffordable. |
| **Volatility-based (ATR)** | `Units = (Equity × Risk%) ÷ (ATR × point value)` | https://blog.quant-view.xyz/tools/position-sizing-guide.html · https://www.nvestiq.com/blog/position-sizing-how-much-to-risk-per-trade | Useful inside the 1% cap — ATR picks where 1R lives. **OPINION:** fine, but on $100 the binding constraint is order minimums, not volatility-model precision. |

---

## 2) Deep dives (200–400 words each)

### Fractional Kelly

Kelly: `f* = W − (1−W)/R`, the fraction of capital that maximizes long-run geometric growth given win rate W and payoff ratio R (avg win ÷ avg loss). John Kelly, Bell Labs 1956 — https://tradernest.ai/blog/kelly-criterion-trading, https://blog.elearnmarkets.com/kellys-criterion-explained/. Consistent worked numbers:
- 55% WR, avg win 1.8R → f* ≈ **30%** — "terrifying, and it should be" (https://tradernest.ai/blog/kelly-criterion-trading).
- 55% WR, R = 1.5 → 32.5% (https://alltradertools.com/blog/kelly-criterion-trading-explained).
- No edge: W = 0.5, R = 1 → f* = 0 → zero size (same source).

Full Kelly is never traded literally. Fractional Kelly sacrifices almost no growth for a huge ruin reduction; the cleanest numbers come from Pomegra's ruin chapter (https://pomegra.io/learn/library/track-e-trading-risk/risk-management/chapter-02-the-risk-of-ruin-equation/fractional-kelly; worked example: 52% WR, avg win $200 / avg loss $150 → f* = 4.36%, 500 trades, $100k):

| Sizing | growth/trade | ruin probability | median max DD |
|---|---|---|---|
| Full (4.36%) | ~2.10% | ~4.2% | ~28% |
| Half (2.18%) | ~2.08% (−1.4%) | ~0.18% (20× lower) | ~15% |
| Quarter (1.09%) | ~2.05% | ~0.0002% | ~8% |

That page's general rule: "If full Kelly produces ruin probability R, half-Kelly ≈ R²". The reason is model error — W and R are estimates from backward-looking samples; "estimation error kills accounts faster than bad trades" (https://tradernest.ai/blog/kelly-criterion-trading). Practical fallout: Kelly's best used as (a) edge validation — negative Kelly = no edge = don't trade at any size (https://completetradersedge.com/kelly-criterion-trading/) and (b) a ceiling. Never compute it on <100–200 trades (https://traderscalc.com/en/calculators/kelly-criterion). On a $100 account even quarter-Kelly (−5–7% ≈ $5–$7/trade) exceeds what the same literature's survival tables imply (~1%); treat it as an upper bound, not a target. **OPINION.**

### Fixed-Fractional sizing (1% / 1R–2R)

Fixed-fractional ("fixed risk") risks the same **percentage of current equity** each trade (Adaptrade: http://www.adaptrade.com/Articles/article-ffps.htm). The defining property is geometric safety: dollar risk shrinks as equity shrinks, so losing streaks cause less geometric decay than fixed-dollar sizing. QuantStrategy's table: $10,000 at 1% → risk $100, then $99, then $98.01; ten straight losses ≈ −9.56%; hitting −50% needs 69 consecutive $1,000 losses under fixed-dollar sizing — but far more under fixed-fractional (https://quantstrategy.io/blog/the-power-of-fixed-fractional-position-sizing-calculating).

The stats every source repeats:
- 1% risk → ~**69 consecutive losses** to reach −50%; 2% → 10 losses ≈ −18.3% (https://traderssecondbrain.com/guides/risk-per-trade-guide; https://blog.quant-view.xyz/tools/position-sizing-guide.html). At 5%, the same losses ≈ −64%, and 20 straight losses at 1% ≈ −18% vs −64% at 5% (https://thecapitalprocess.com/position-sizing-mastery-2026-fixed-fractional-volatility-based-kelly-criterion-optimal-f-full-mathematical-breakdown-survival-analysis).
- Losing streaks are certainties, not anomalies: 50% WR → **>99% chance of a 7-loss streak in 200 trades**; 40% WR → a 7-streak in >50% of 200-trade windows; 30% WR → a 10-streak in most 500-trade windows (https://tradeology.app/academy/risk-psychology/risk-of-ruin-and-streaks).
- Streak × size erosion: 1% risk → 6-streak ≈ −6%, 11-streak ≈ −10%; 2% → −11%/−20% (https://sggroup.jp/article/tradingview-backtest-robustness-lab/en-monte-carlo/).
- Risk of ruin climbs nonlinearly: ~0.01% at 1% (40% WR / 2:1), ~12% at 5%, ~35% at 10% (https://tradeology.app/academy/risk-psychology/risk-of-ruin-and-streaks).
- 1R/2R fluency (Van Tharp): `Expectancy = (WR × avgWinR) − (LR × avgLossR)`; size = risk budget ÷ stop distance; many traders cap daily loss at 2R–3R (https://www.traderegimen.com/blog/r-multiple-position-sizing, https://tradeorbit.io/learn/risk-management-trading, https://tradejournal.ai/learn/r-multiple-explained).

Retail context: ESMA data cited by Backtrex — 74–89% of retail leveraged (CFD) accounts lose money (https://backtrex.com/en/blog/monte-carlo-risk-of-ruin-trading-backtest); practitioners attribute most of it to sizing, not models.

For **$100**: 1% = $1.00/trade; 2% = $2. A guaranteed 7-streak then costs ~7% — survivable. The constraint is execution minimums (§3), not the math. **OPINION:** start at 0.5–1% even if 1% looks possible.

### Max-Drawdown-based sizing

MaxDD is not a fluke — it comes from a probability distribution over trade orderings; the same WR/RR/risk% yields different MaxDDs depending on order; average DD hides the tail, so the actionable number is the 95th-percentile DD, not the single historical value (https://delvertrade.com/en/blog/max-drawdown-risk-of-ruin; https://sggroup.jp/article/tradingview-backtest-robustness-lab/en-monte-carlo/). Monte Carlo / bootstrap of your R-multiple series — ≥100 trades, ideally ≥200, ~5k–10k iterations — converts this distribution into numbers (https://backtestme.com/guides/monte-carlo-simulation, https://backtrex.com/en/blog/monte-carlo-risk-of-ruin-trading-backtest).

Standard practitioner target bands: probability of ruin ≤ 1–2% and a 95th-pct DD within budget (e.g. <25%); if the 95th-pct DD exceeds budget → shrink size rather than accept it (https://backtestme.com/guides/monte-carlo-simulation). Recovery math sharpens it: 10% loss needs +11.1%; 25% → +33.3%; 50% → +100% (https://trendrider.net/blog/position-sizing-and-risk-per-trade). Delver's phrasing: design whether you can survive before you design winning ("bankruptcy is a design flaw, not luck" — https://delvertrade.com/en/blog/max-drawdown-risk-of-ruin). Distribution thinking: even profitable strategies show P95 equity ± big swings; the observed max losing-streak can run roughly 1.5–2× larger at the 95th percentile (https://sggroup.jp/article/tradingview-backtest-robustness-lab/en-monte-carlo/).

Sizing interpolation: ~1% risk gives roughly a 10–15% DD distribution; 5% risk → 40%+. Account-level tripwires circulate as complements: −10% from peak → cut sizes in half; −15% → cash and review (https://edge-ledger.io/blog/crypto-portfolio-risk-management-2026).

For **$100** (budget −20 to −25%): pick risk% so the 95th-pct DD fits inside it; the cited tables show 1% fits, 2–3% borderline, ≥5% does not. The framework therefore converges to ≈1% risk/trade. **OPINION** on the exact numbers — the convergence direction is what the sources support.

### Kelly-constrained combos

The consensus synthesis: compute Kelly, then cap every trade by (a) fractional-Kelly (usually ≤ half), (b) a fixed-fractional survival limit (1–2% equity), (c) a max-DD budget, (d) portfolio heat — the smallest wins:

- QuantInsti "Risk-Constrained Kelly Criterion": Kelly as growth optimizer with explicit risk constraints layered on (https://blog.quantinsti.com/risk-constrained-kelly-criterion).
- The Capital Process: full method matrix — fixed dollar, fixed %, ATR, Full Kelly / Fractional Kelly, optimal-f; Full Kelly → 60–90% DD; "¼–½ Kelly for sanity"; beginner ladder: 1% fixed-fractional first (https://thecapitalprocess.com/position-sizing-mastery-2026-fixed-fractional-volatility-based-kelly-criterion-optimal-f-full-mathematical-breakdown-survival-analysis).
- "Kelly as the ceiling": if your risk/trade exceeds fractional-Kelly plus a margin for estimation error, you are mathematically overbetting; negative Kelly = no edge (https://alltradertools.com/blog/kelly-criterion-trading-explained, https://completetradersedge.com/kelly-criterion-trading/).

Implementation pattern backed by the numbers: compute f* → take 0.25–0.5× → also apply 1% fixed cap → also apply heat cap; effective risk = min of all four. For a 55% WR / 2:1 profile: quarter-Kelly ≈ 8% vs fixed 1% vs DD-implied ~1% → size at 1%. That combination is what makes guaranteed 7-loss streaks cost ~7% instead of ruin.

For **$100**: binding combination = min(1% of equity, ¼–½ Kelly, DD-implied, broker minimum). Output: $0.50–$1.00 risk/trade, 1–3 concurrent positions, ~2–3R daily heat, ~5–8% weekly cap. **OPINION.**

---

## 3) Fractional-share & minimum-lot realities: what actually lets $100 trade

**Alpaca fractional equities**
- Minimum notional order **$1**; fractional quantities via `notional` parameter (9 decimal places); market and limit orders supported, TIF day only; **no fractional short sales** (all fractional sells are long) — https://docs.alpaca.markets/us/docs/fractional-trading, https://www.quantconnect.com/forum/discussion/18853/fractional-shares-with-alpaca-brokerage-model, https://alpaca.markets/learn/fractional-shares-api.
- Not all tickers are fractionable — the broker exposes a `fractionable` flag; industry minimum qty 0.0001 shares, min notional usually $1–5 (https://blog.alltick.co/u-s-fractional-share-trading-rules-a-developers-guide).
- Bracket/OCO orders do NOT work with fractional shares — only simple orders — so trailing/bracket exits on fractional positions require manual multi-order management (https://forum.alpaca.markets/t/bracket-order-with-fractional-shares/12027). A whole-share floor conflicts with small notional: a $287 signal on a $340 stock buys 0 shares without fractions; with fractions it executes 0.844 shares (https://predictandprofit.io/blog/alpaca-fractional-share-position-sizing-python).
- For $100: a **$1 notional fraction** is placeable on any liquid large-cap — that's a risk cap of exactly $1 (1%) when the stop is the full position, or less when the stop is tighter. **OPINION** — fully feasible on Alpaca.

**Crypto minimums (Binance)**
- Binance cut spot/margin minimum order size from **10 → 5 USDT** for USDT/EUR/DAI/FDUSD/GBP/USDC-quoted pairs (2023-08-31) — https://www.binance.com/en/support/announcement/detail/c4706c73b805423a8d36be948e297603 — and further to **1 USDT for several pairs (DOGE/USDT, BOME/USDT, …)** (2024-06-07) — https://www.binance.com/en/support/announcement/detail/4b419936509647a4896e65a48eef2c5e. BTC/USDT trade limits currently minimum order size 1 USDT w/ min trade 0.00001 BTC — https://www.binance.us/trade-limits, https://www.btcc.com/en-US/questions/detail/1845675472839643136.
- Third-party summaries still commonly report a 5–10 USDT floor (https://dappgrid.com/minimum-usdt-to-trade-on-binance, https://faurit.com/articles/what-is-the-minimum-usdt-to-trade-in-binance-spot-trading); the per-pair truth varies — the API `exchangeInfo` is definitive (per the same Binance announcement).
- **Implication for $100:** a 5 USDT minimum order = **5% of the account in one position** before any stop; 10 USDT = **10%**. Only 1-USDT-minimum pairs (DOGE/USDT etc.) let you keep ~1% notional discipline. If your plan says "risk $1" and the pair floor is 5 USDT, your notional is forced to 5% of equity, so your per-trade risk floor jumps to ~5% unless the stop is ~1% away. **OPINION** — this is the single biggest structural reason $100 crypto accounts behave differently from the textbook.
- Fee note: costs eat small orders disproportionately; practitioners put the threshold at ~+0.2R expectancy before commissions/slippage consume the edge (https://gaspntrader.com/blog/how-to-calculate-position-size; https://crosstrade.io/learn/performance-metrics/r-multiple).

**Micro futures** exist to break the full-size minimum: MES ($1.25/tick vs ES $12.50), MNQ ($0.50), MGC ($1.00) — "the micro exists so you can trade it" (https://mrtrader.io/learn/position-sizing-small-accounts). The same source's table starts micros around a $1,000 account ($10/trade, MES 1 contract, tight stops). At $100, even one MES contract risks ~$25–$50 on a bad stop (a few points ≠ 25–50% of the account) → **futures effectively unsuitable below ~$500–$1,000. **OPINION** extrapolation from the published $1,000 floor.**

---

## 4) Recommended $100-account risk framework

Derived from cited research. **Everything marked OPINION is an extrapolation to a $100 context, not direct source content.**

| Cap / rule | Value (on $100) | Derived from |
|---|---|---|
| Per-trade risk | **0.5–1% = $0.50–$1.00**, default 1% = $1; round down; never exceed | [69-loss survival @1%, RoR ≈ 0%](https://blog.quant-view.xyz/tools/position-sizing-guide.html) · [RoR table 1%/5%/10%](https://tradeology.app/academy/risk-psychology/risk-of-ruin-and-streaks) |
| Position-size cap | notional ≤ 20% of account **OPINION**; realistically `notional = risk $ ÷ stop%` (e.g. 1% risk / 10% stop = $10 position; /25% = $4) | [position size = risk ÷ stop length](https://quantstrategy.io/blog/the-power-of-fixed-fractional-position-sizing-calculating) |
| Portfolio heat | **3% cap** (max 3 concurrent $1 trades); correlated positions count as one | [3/5/7% caps](https://chartmini.com/blog/the-art-of-position-sizing-how-much-to-trade-2026) · [0.5%/5%/6% per-pos/sector/heat](https://finaur.com/blog/en/risk-management/portfolio-heat-limits-in-trading) |
| Daily loss cap | **2R–3R = $2–$3** → stop for the day | [daily loss 2R–3R](https://tradeorbit.io/learn/risk-management-trading) |
| Weekly loss cap | **~10% ($10)** → stop and review **OPINION** (no direct weekly figure found; anchored to −15% cash tripwire below) | [–15% cash level](https://edge-ledger.io/blog/crypto-portfolio-risk-management-2026) |
| Drawdown tripwires | −10% from peak → halve sizes; −15% → cash + review | [edge-ledger stepdown](https://edge-ledger.io/blog/crypto-portfolio-risk-management-2026) |
| Cooldown | stop for the day after daily cap (−3R); stop 1 week after weekly cap; full stop + review after −15% | [streak math shows cooldowns are statistically mandatory](https://tradeology.app/academy/risk-psychology/risk-of-ruin-and-streaks) |
| No martingale / stop directly | fixed-% of equity; never size up after losses | [gambler's ruin theorems](https://en.wikipedia.org/wiki/Gambler%27s_ruin) |

**Execution of the caps:**
- Equities: fractional shares (Alpaca $1 min notional) execute the 1% cap exactly — $1 risk limit = $1 notional floor. **OPINION.**
- Crypto: use only pairs with a 1 USDT minimum order (Binance 2024 list); a 5+ USDT floor forces ≥5% notional risk — treat that as your modified risk number or skip. **OPINION.**
- Layered caps form the Kelly-constrained combo of §2.4: `risk = min(1% equity, ¼×Kelly, DD-95th-pct-budget, heat-3%)`.

**Bottom line for $100:** risk ≤ $1/trade, heat ≤ $3 total, daily ≤ $3, weekly ≤ ~$10, cooldown after each cap. A 7-loss streak — statistically guaranteed — then costs ~$7, not $70. **The arithmetic, not the confidence, is what the sources support; dollar caps on tiny accounts are my extrapolation.**

---

## 5) Sources

**Kelly / fractional Kelly**
- https://tradernest.ai/blog/kelly-criterion-trading — formula f* = W − (1−W)/R, worked examples
- https://blog.elearnmarkets.com/kellys-criterion-explained/ — f* = p − q/b; fractional Kelly, Thorp
- https://quantmatter.com/kelly-criterion-formula/ — inputs, edge, fractional Kelly
- https://alltradertools.com/blog/kelly-criterion-trading-explained — full vs half/quarter; "3 losses → 42%"
- https://completetradersedge.com/kelly-criterion-trading/ — Kelly as edge validation / ceiling
- https://pomegra.io/learn/library/track-e-trading-risk/risk-management/chapter-02-the-risk-of-ruin-equation/fractional-kelly — half-Kelly ruin², full/half/quarter $100k tables
- https://blog.quantinsti.com/risk-constrained-kelly-criterion — risk-constrained Kelly
- https://traderscalc.com/en/calculators/kelly-criterion — worked numbers; 100–200 trade minimum
- https://www.axiory.com/trading-resources/basics/calculate-position-siza-forex — $1,000 account worked examples
- https://stoxbox.in/mentorbox/marketopedia/risk-management/kelly-criterion — formula + examples

**Fixed-fractional / R-multiples / 1R–2R**
- http://www.adaptrade.com/Articles/article-ffps.htm — fixed fractional = fixed risk
- https://quantstrategy.io/blog/the-power-of-fixed-fractional-position-sizing-calculating — $10k 1% table, 69-loss math
- https://www.mrtrader.io/learn/position-sizing-small-accounts — micros, $1k+ table, MNQ/MES math
- https://traderssecondbrain.com/guides/risk-per-trade-guide — 2% vs 1% math
- https://blog.quant-view.xyz/tools/position-sizing-guide.html — "69 consecutive losses at 1%"
- https://thecapitalprocess.com/position-sizing-mastery-2026-fixed-fractional-volatility-based-kelly-criterion-optimal-f-full-mathematical-breakdown-survival-analysis — full method matrix, ruin formula
- https://trendrider.net/blog/position-sizing-and-risk-per-trade — 2% rule; recovery asymmetry
- https://www.nvestiq.com/blog/position-sizing-how-much-to-risk-per-trade — R-multiples, Van Tharp, ATR
- https://www.traderegimen.com/blog/r-multiple-position-sizing — R framework; 4 sizing mistakes
- https://tradejournal.ai/learn/r-multiple-explained
- https://crosstrade.io/learn/performance-metrics/r-multiple — R definition, cost thresholds
- https://tradegladiator.com/blog/r-multiple
- https://tradeorbit.io/learn/risk-management-trading — 0.5–1%, daily 2R–3R
- https://gaspntrader.com/blog/how-to-calculate-position-size — crypto unit sizing, stop-first

**Gambler's ruin & risk of ruin**
- https://en.wikipedia.org/wiki/Gambler%27s_ruin — ruin theorems (raise-after-win w/o reduce → certain ruin)
- https://mathworld.wolfram.com/GamblersRuin.html — classical model P₁ = n₂/(n₁ + n₂)
- https://thecapitalprocess.com/position-sizing-mastery-2026-fixed-fractional-volatility-based-kelly-criterion-optimal-f-full-mathematical-breakdown-survival-analysis — ruin approx `Ruin ≈ (1 − Edge/risk)^(cap/risk)`
- https://tradeology.app/academy/risk-psychology/risk-of-ruin-and-streaks — streak math; RoR 0.01%/12%/35%
- https://probabilitycalculator.pro/risk-of-ruin.html — Monte Carlo; 50% WR 10-streak ≈ 1/1000
- https://riskdesks.com/risk-of-ruin-calculator — simulation tool
- https://tradingrisklab.com/tools/risk-of-ruin — Monte Carlo tool with DD distribution
- https://fxbacktest.app/guide/monte-carlo-simulator/ — equity-curve simulator

**Max DD & Monte Carlo (drawdown)**
- https://www.quantifiedstrategies.com/maximum-drawdown-position-sizing/
- https://delvertrade.com/en/blog/max-drawdown-risk-of-ruin — DD is a distribution; 95th pct
- https://sggroup.jp/article/tradingview-backtest-robustness-lab/en-monte-carlo/ — streak-erosion table (1%/2%/5%)
- https://backtestme.com/guides/monte-carlo-simulation — RoR <1–2%, DD 95th <25%, sized-down loop
- https://backtrex.com/en/blog/monte-carlo-risk-of-ruin-trading-backtest — 100+ trades; ESMA 74–89% losing

**Correlation / portfolio heat / drawdown rules**
- https://www.quantum-algo.com/academy/multi-position-management — heat ≈ 6%, 3-position cluster cap
- https://finaur.com/blog/en/risk-management/portfolio-heat-limits-in-trading — 0.5%/5%/6% caps
- https://nexusfi.com/a/risk-management/correlation-adjusted-position-sizing — heat cap, ρ–shrink SF = 1/√(1+ρ)
- https://chartmini.com/blog/the-art-of-position-sizing-how-much-to-trade-2026 — heat 3/5/7% by setup grade
- https://swingfolio.com/education/level-4-risk-money-management/portfolio-heat-and-correlation
- https://positionmath.com/portfolio-heat-calculator/
- https://eliteforextrading.com/portfolio-heat-explained/
- https://edge-ledger.io/blog/crypto-portfolio-risk-management-2026 — 1–2% rule; 10% stepdown / 15% cash; "1% = vanishing RoR via 50% WR / 1000 trades"
- (same page) — number-behind-the-1%-rule paragraph

**Broker / minimum order realities**
- https://docs.alpaca.markets/us/docs/fractional-trading — $1 min, notional, DAY, no frac-short
- https://alpaca.markets/learn/fractional-shares-api
- https://www.quantconnect.com/forum/discussion/18853/fractional-shares-with-alpaca-brokerage-model
- https://forum.alpaca.markets/t/bracket-order-with-fractional-shares/12027
- https://predictandprofit.io/blog/alpaca-fractional-share-position-sizing-python — $1 floor, notional vs qty
- https://brokerchooser.com/invest-long-term/diversification/fractional-shares-alpaca-trading — conditions summary
- https://blog.alltick.co/u-s-fractional-share-trading-rules-a-developers-guide — 0.0001 qty, $1–5 notional
- https://www.binance.com/en/support/announcement/detail/c4706c73b805423a8d36be948e297603 — min order size 10→5 USDT (2023)
- https://www.binance.com/en/support/announcement/detail/4b419936509647a4896e65a48eef2c5e — min order size 5→1 USDT pairs (2024)
- https://www.binance.us/trade-limits — BTC/USDT 0.00001 / 1 USDT
- https://dappgrid.com/minimum-usdt-to-trade-on-binance — 5–10 USDT common floor
- https://faurit.com/articles/what-is-the-minimum-usdt-to-trade-in-binance-spot-trading — per-pair minimums
- https://support.binance.us/en/articles/9843810-binance-us-updates-trading-parameter-step-size-for-sol-usdt-sol-usdc-and-fet-usdt — step-size mechanics

---

## [NOT FOUND] list
- **A peer-reviewed/academic paper grounding the "1% of bankroll" rule** — only blog/summary citations of survival tables found (e.g. https://blog.quant-view.xyz/tools/position-sizing-guide.html states the 69-loss figure without a primary reference). The exact 69-loss figure appears in blogs only.
- **A published "survival probability of a $100 account" numeric study/table** — NOT FOUND. Closest: generic Monte Carlo RoR tools + ESMA broker-loss aggregate (74–89%) cited via https://backtrex.com/en/blog/monte-carlo-risk-of-ruin-trading-backtest.
- **The official complete per-pair minimum-order-size table for Binance spot** — the `exchangeInfo` API is definitive per the announcement, but the full rendered table wasn't captured; only representative pairs (BTC/ETH/XRP/DOGE) were visible.
- **A live per-symbol list of Alpaca-fractionable tickers** — only described ("fractionable" field), not enumerated.
- **Kraken/Coinbase minimum order sizes** — out of scope (Binance + Alpaca covered per the task spec).
