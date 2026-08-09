---
title: "Post-Mortems of Hobby Quant Automation: Failure Archetypes"
type: research / risk taxonomy
tags: [quant, postmortem, backtest, api, ops, autod, failures, risk]
date: 2026-08-09
task: autod-trading-failures
status: complete
sources-fetched: 40+ (URLs inline; 3 full-text reads: GuardLabs May-06 post-mortem, Predict&Profit silent-API-failure + DST post-mortem)
note: "Single-file deliverable. Written for the autod engine (paper-first, $100 paper account budget). Ranking criterion: 'would this kill a $100 paper engine silently?'"
---

# Post-Mortems of Hobby Quant Automation → Failure Archetypes

Research question: *what has actually killed (or silently ruined) hobby algorithmic-trading bots — and which of those would kill the autod paper engine without a single loud error?*

Method: web searches over named failure-mode queries (`algorithmic trading failure postmortem`, `lookahead bias bug live`, `backtest overfit live disaster`, `API rate limit silent stop`, `stale data paper trading broke`, `websocket disconnect bot stopped trading`, `timezone DST bug trading bot`), r/algotrading threads, practitioner post-mortems. Sites that sell a product while documenting a real incident (guardlabs/nexus-bot, predictandprofit, vantixs, matrixtrak) are real incidents but are **first-party accounts written next to a pitch** — treat numbers as indicative, not audited.

**Headline finding:** the failures that kill small engines are, with one exception (Knight Capital), **silent**. A crash is a 1-hour incident; a `.get()` default is an 8-week bleed. Every "killer" below produces *clean logs and a plausible equity curve* while it is destroying the account.

---

## Ranked summary (would kill a $100 paper engine silently)

| Rank | Archetype | Silent? | One-line mechanism |
|---|---|---|---|
| 1 | Look-ahead / future leakage in the strategy and live signal code | Silent | Backtest & paper both trade on data that never could have existed at signal time; PnL is fiction, looks perfect |
| 2 | API-boundary corruption (`.get()` defaults hide renamed/missing fields) | Silent | Bot goes blind to its own positions/orders and keeps trading on "plausible" values |
| 3 | Day/period bucketing in the wrong timezone (DST) | Silent | Off-by-one "day" → systematically wrong decision every DST month, looks like variance |
| 4 | Stale/delayed market data (free-tier feeds, bar-fetch semantics) | Silent | Each trade taxes latency; paper execution hides the drag → live bleed |
| 5 | Feed reconnect without order book / state recovery | Silent | Bot "reconnects", then trades on a lie (gap in stream, stale book) |
| 6 | Non-idempotent retry → duplicate orders | Semi-silent | Timeout → retry → 2× exposure, discovered only at liquidation/exit |
| 7 | Regime drift with no circuit breaker / daily loss limit | Silent | Bug-free strategy keeps picking the same losing setup all day (real case: −40% of accumulated profit in one session) |
| 8 | Survivorship bias in the universe / walk-forward survivors | Silent | Backtest universe never existed; live delistings/regime stress are flat out of the training data |
| 9 | Overfitting / multiple testing | Silent | 3.0 Sharpe on 15 params "memorizes" noise; decays over months, not hours |
| 10 | OMS / position-state drift after restart or crash | Silent | Local state ("flat") ≠ exchange state ("+positions") → dups, missed exits |
| 11 | Paper-vs-live execution gap | Loud at switch-over (see below) | Paper fills instantly at signal price; live pays latency/slippage → validation is invalidated |
| 12 | Deployed dead code / toggled-off path re-enabled | **Loud** (institutional anchor) | Knight Capital: one stale flag = $460M loss in 45 min. Is the only archetype that announces itself |

---

## Archetype 1 — Look-ahead bias (future leakage). *Kill rank: 1 of 12*

- **Trigger condition:** strategy/bar-builder uses the *closing* value of the same candle it trades on; pivot/correlation/rolling regressions are computed with future bars; fundamental data joined on period-end instead of publish date; `shift()` missing after indicator computation; timezone mismatch in candle timestamps making "live" feed look like history.
- **How it surfaces:** **Silent.** Backtest equity is suspiciously smooth; live paper underperforms the backtest by a wide margin and every trade "just happened to be late"; the bot is *always* "too slow" but the backtest is "perfect" — that's the tell.
- **Real examples:**
  - [TradingView `barmerge.lookahead_on` warning thread — user ran a lookahead strategy live with real money](https://www.reddit.com/r/TradingView/comments/17m88to/caution_this_strategy_may_use_lookahead_bias/) ("I have manually verified it with active live bot trading live $" — i.e., traded a look-ahead strategy live and saw results unaffected by the bias "fix").
  - [Backtesting Lies: How Look-Ahead Bias Makes Broken Trading Bots Look Like Holy Grails (DataDMrivenInvestor)](https://datadriveninvestor.com/articles/backtesting-lies-how-look-ahead-bias-makes-broken-trading-bots-look-like-holy-grails)
  - [TargetHit — the BTC-correlation bug: strategy correlated a coin with future Bitcoin returns and traded beautifully (for a while)](https://targethit.com/learn/lookahead-bias)
  - [r/algotrading — "Look-ahead bias is a hell of a drug!"](https://www.reddit.com/r/algotrading/comments/1n8rn14/lookahead_bias_is_a_hell_of_a_drug/) [NOT FOUND: thread body unreadable, title+snippet verified only]
  - [Detection checklist (DEV Community)](https://dev.to/tradevodata/how-to-detect-lookahead-bias-in-a-backtest-a-practical-checklist-2cb6)
- **Prevention checklist for this engine:**
  - [ ] One rule in autod: **signals are only computed on `bar[:-1]`** (close of bar *t*→ decides at `t+1`). Assert it in the vectorized signal builder and again in the live bar builder — two different implementations.
  - [ ] Never let a bar stream "catch up" by rewriting past bars; live candles must be immutable once closed (no `update` on closed bars) or the live engine + backtester will disagree.
  - [ ] Re-run the deployed strategy file in **single-step walk-forward** and compare live paper vs replay: identical input shards must produce identical signals.
  - [ ] Sanity gate: never ship a backtest where win rate > ~90% or equity is monotonic — that is leakage, not edge.

---

## Archetype 2 — API-boundary corruption (`.get()` defaults, schema drift) — Kill rank: 2

- **Trigger condition:** parser uses `response.get("order", [])` returning `[]` when the API renamed/relocated a field; or `position_size` arrives as `"12"` (string) and is compared to an `int` in the risk module; or a close-then-reopen race makes the broker return a stale position ID.
- **How it surfaces:** **Silent.** The bot has no open orders (as far as it knows), so: re-enters an existing position (exposure doubles), or skips P&L reconciliation, or never cancels a rotting order. Zero exception, zero log line. A crash would have cost an hour; this costs weeks.
- **Real examples:**
  - [Silent API Failures: The Bug That Drains Your Trading Account Without a Single Error Log (Predict&Profit)](https://predictandprofit.io/blog/silent-api-failures-automated-trading) — the exact `open_orders = portfolio_response.get("orders", [])` pattern that leaves the bot unsure it even holds a position.
  - [Production bot report (The Investors' Centre): phantom-position 404s from a 300 ms stale position-ID window; second bug — position size returned as string vs int config crashed Python silently, leaving position open past intended stop](https://www.theinvestorscentre.co.uk/trading/best-ai-trading-bots)
- **Prevention checklist for this engine:**
  - [ ] Model every API payload with validation (typed dataclasses/pydantic); a rank mismatch raises, never defaults. Reject ANY parse path that "skips" a field.
  - [ ] At the order-lifecycle boundary: assert "if I believe I have N open orders, the exchange must list N-...". On divergence → halt, alert.
  - [ ] Position size = `int` in one place; cast once at the feed boundary; forbid string comparison in risk gate.
  - [ ] Add 300–500ms grace between close-confirm and reopen for same symbol (avoids stale-ID races).

---

## Archetype 3 — Timezone / DST "day" bucketing — Kill rank: 3

- **Trigger condition:** any code that does `astimezone(local_tz)` + `strftime("%Y-%m-%d")` to define "today"/"session". Trigger fires only during DST months + if the exchange defines the window in a special clock (Local Standard Time year-round, or UTC) rather than wall time.
- **How it surfaces:** **Silent.** Winter trades are fine (average down the noise), 8 months a year every decision lands on the wrong 24h window, high-conviction losses look like "unlucky tail". Classic: 8-month-old bug found via a single OS-overlay plot.
- **Real examples:**
  - [The Daylight Saving Time Bug That Broke My Trading Bot for 8 Months (Predict&Profit — full post-mortem + the wrong/right code)](https://predictandprofit.io/blog/2026-07-29-the-daylight-saving-time-bug-that-broke-my-weather-bot-for-8-months) — $23 across 112 contracts, model measurably worse than base-rate; winter (no-DST) months masked it.
  - [The Timezone Bug That Cost Me 9 Hours of Trades (KimchiBot: UTC + KST mixed in one line)](https://kimchibot.com/posts/the-timezone-bug-that-cost-me-9-hours-of-trades/)
  - [MQL5 thread — bot's DST self-check moved GMT +2 → +4 during daylight transition; every session window misaligned](https://www.mql5.com/en/forum/450197)
- **Prevention checklist for this engine:**
  - [ ] All internal time = UTC epoch; convert to market-local only at the display layer AND only for actual boundaries (session start/end, bar close).
  - [ ] Define "the trading day" per instrument from the **documented settlement/market spec** (exchange's clock, not the host machine's), hard-coded per instrument with an assert that DST transition dates match expectations ±1 day.
  - [ ] Pre-commit a unit test: run the bucketing for the last 2 DST transitions in both directions; assert no date changes.
  - [ ] Publish per-session log keyed by UTC day AND local-market day; auto-diff counts weekly — disagreement is the bug.

---

## Archetype 4 — Stale / delayed market data inputs — Kill rank: 4

- **Trigger condition:** bar/quote feed delayed by design (IEX-free 50-500ms+, or 1-min "bars" that are actually still the first 200 bars of the day because `limit` was used as "per-symbol" when it meant "total"); indicator computed on bars hours old; VWAP/EMA/volume stale.
- **How it surfaces:** **Silent.** Strategy never crashes, signals still fire; fill-vs-quote spread negative on 100% of trades and subtle. A backtest that used the ingest-by broker history won't reproduce it: the backtest data arrives "fresh forever".
- **Real examples:**
  - [Alpaca community: "Stale Data coming from API" — 69/80 symbols older than 3 min; 40/80 older than 2 h; and the root cause: `limit` semantics returned day's-first bars (data is not 'stale', the retrieval is just wrong)](https://forum.alpaca.markets/t/stale-data-coming-from-api/19126)
  - [Trading Bot Stale Data: why it happens, how to measure (what 200ms means per trade; free-feed tax math)](https://oyamori.com/learning/trading-bot-stale-data/)
- **Prevention checklist for this engine:**
  - [ ] Per-bar assert: `bar_close_ts >= now - max_age`. Define max_age by timeframe (1m→10s, 15m→60s…) and **halt/use no-signal** when breached; never trade on old bars.
  - [ ] Log `quote_ts / bar_ts / decision_ts / fill_ts` for every order; weekly report of fill-vs-quote; if avg slippage > feed cost per trade → feed upgrade, not a monkey-patch.
  - [ ] Never trust `limit` on multi-symbol batch API: request per symbol with explicit range; verify per-symbol counts in test.
  - [ ] Data-version constant: seed backtest + live from the **same** snapshot; any mismatch raises.

---

## Archetype 5 — Feed/Wsocket reconnect without state recovery — Kill rank: 5

- **Trigger condition:** socket drops (exchange recycles ~ every 24h), reconnects successfully, then silently serves a **gapped** stream (missed fills, missed book deltas) while the bot continues to build an order book/position state on the gap.
- **How it surfaces:** **silent.** Reconnect "succeeds", heartbeats/ping OK, but decisions are based on book/position state that is now fiction; the classic wake-up: the position you "never opened" at 2 AM, flat in the risk dashboard, running against you. (Same story repeated in several practitioner pieces.)
- **Real examples:**
  - ["Your Trading Bot Doesn't Have a WebSocket Problem. It Has a State Problem": reconnecting ≠ recovered — gap detection + REST snapshot, DEV](https://dev.to/turboline_ai_/websocket-reconnection-that-actually-works-auto-3ak3)
  - [WebSocket Reconnect & Auto-reconnection for Trading Bots — the "three-layer defense", sequence numbers, and the "reconnect but stale" failure](https://matrixtrak.com/blog/websocket-disconnects-trading-bots-reconnection)
  - [Crypto Trading Bot Architecture: From Idea to Production — "what happens when the WebSocket disconnects mid-trade at 2 AM…" (five-layer production bot; OMS as single source of truth)](https://www.arkhamides.com/blog/crypto-trading-bot-architecture)
- **Prevention checklist for this engine:**
  - [ ] Reconnect must be: **REST snapshot → hard reset of local book/state → re-subscribe → only then process stream.** Never "continue".
  - [ ] Detect disconnects with heartbeat timeout and sequence numbers, not just socket close; a missing sequence = declare gap, snapshot.
  - [ ] Exchange-owned truth, every loop: reconcile positions/orders from REST at least each minute regardless of stream health.
  - [ ] `time_since_last_stream_msg` monitored; >2×interval → alert + auto-fetch snapshot, no trades on stale stream.

---

## Archetype 6 — Non-idempotent retry ⇒ duplicate orders — Kill rank: 6

- **Trigger condition:** Order submission times out after broker accepted it → generic retry re-submits → 2× exposure. Fixed-interval or linear retry showers during exchange recovery hit rate limits at the worst moment (missed exit, banned IP, no stop-loss because req to modify route got 429d).
- **How it surfaces:** mostly **silent** until margin/liquidation; on futures a single double-sized position can breach liquidation thresholds.
- **Real examples:**
  - [Crypto Trading Bot Rate Limits, Retries & Idempotency — full pattern analysis; "most live bot bugs are retry bugs" (Vantixs)](https://vantixs.com/blog/rate-limits-retries-idempotency-crypto-trading-bots)
  - [VoiceOfChain — same problem seen from exchange side, with handler snippets (429/418 IP ban behavior) ](https://voiceofchain.com/academy/api-rate-ratelimit)
  - [Kalshi/Predict & Profit — why WS over REST polling + exponential backoff for order critical paths](https://predictandprofit.io/blog/kalshi-api-rate-limits)
- **Prevention checklist for this engine:**
  - [ ] Every order gets a deterministic client_order_id (symbol+ts+nonce); exchange-side idempotency: a retry with same id must be a no-op.
  - [ ] Retry: exponential backoff + jitter, only on idempotent/read endpoints; order submission → never blind retry; if ambiguous → **get the truth via REST status** before re-submit.
  - [ ] Order-state machine: pending→acknowledged→filled/cancelled; on any error step → reconcile first, decide after.
  - [ ] Hard cap on retry attempts; above = halt trading + alert (stop, don't hammer).

---

## Archetype 7 — Regime blindness / no circuit breaker / no session limit — Kill rank: 7

- **Trigger condition:** A "trend-reversal" or "stale breakout" signal keeps firing while the market is in a different behavior (fade-the-fade / breakout-trap), and nothing stops the engine: loop "entry → stop-out → new entry 30-90 min later" 30+ times.
- **How it surfaces:** **silent-ish.** Metrics look like normal variance; overnight dashpad shows a daily result you can't explain until you plot by day. No crash. No data bug. Purely a controls gap.
- **Real example:** [GuardLabs May 6, 2026 post-mortem: Phantom (paper) — a single session: −$200.46 on +$496.35 accumulated (40% of all profit), win rate 9/40 vs previous 17/36. Root causes named: no HTF character metric tracked in real-time, no losing-streak circuit breaker on a single instrument, no daily loss limit → engine kept trading the wind the whole day](https://guardlabs.online/articles/may06-incident-postmortem/). same clustered-loss lesson in [r/algotrading: "Live trading showed the real issue was position sizing: clustered-loss trap — backtests assume independent outcomes"](https://old.reddit.com/r/algotrading/comments/1sdv0jw/spent_weeks_improving_my_algos_win_rate_live/)
- **Prevention checklist for this engine:**
  - [ ] Loss-streak breaker: 3 consecutive stops on same symbol → 30min flat + regime check + alert. Config, not code — must fire without a deploy.
  - [ ] Daily limit (e.g., −2% of $100 account = −$2.00) → engine refuse new entries rest of UTC day + alert.
  - [ ] Weekly max-DD: curve overlay "session vs regime" — pre-built condensed report per incident (post-mortem from 2h SQL to 5-min report).
  - [ ] Regime latency metric: log when HTF-filter flips; if it lags data > X, widen guard thresholds.

---

## Archetype 8 — Survivorship bias in the universe & in walk-forward survivors — Kill rank: 8

- **Trigger condition:** backtest/universe built on today's index constituents or today's delisted-free; or you run massive walk-forward baskets, then pick the best params of those that survived the entire period (the survivors themselves are a filter).
- **How it surfaces:** **Silent** (the backtest universe never existed at any point in history). Live shows: quality metrics degrade only on even with delisted assets, post-basic erosions in crisis (the assets you never trained on).
- **Real examples:**
  - [Crucible Research — table comparing biased vs. live universe: sector stress, pre-removal momentum collapse, quality signal inflation](https://crucible-research.com/survivorship-bias-backtesting)
  - [r/algotrading — "Live system failing because of survivorship bias" (a live system that runs walkforward but discovered the universe is survivor-filtered)](https://www.reddit.com/r/algotrading/comments/1bud8gc/live_system_failing_because_of_survivorship_bias/)
  - [LuxAlgo — incl. 2021 hedge-fund strategy published on Seeking Alpha w/ survivors from (2021 table: only funds alive 2008-2021)](https://www.luxalgo.com/blog/survivorship-bias-in-backtesting-explained/)
- **Prevention checklist for this engine:**
  - [ ] Universe file must be **point-in-time**: symbols + membership as of each backtest date (include delisted instruments!). Ever Use current membership to backtest = reject.
  - [ ] Universe churn log: how many symbols entered/left our live paper universe each month? If none ever leaves, set includes bias.
  - [ ] Walk-forward selection: candidate selection uses **only the train windows**, test windows are frozen; freeze contenders from paper, don't re-rank on the fly.

---

## Archetype 9 — Overfitting / multiple testing — Kill rank: 9

- **Trigger condition:** >15 tuned parameters, thousands of trials, pick the best hill to climb; edges whose performance peaks at exactly the parameters you chose (no performance plateau). Sharpe 3 backtests in this class are nearly guaranteed to be zero live.
- **How it surfaces:** **Silent:** the butterfly returns degrade 26-58% out-of-sample / after publication; not an event but a drift over months — hard to distinguish from noise, so the operator keeps "optimizing" in the wrong direction.
- **Real examples:**
  - [Why Your Backtest Said +20% But Live Trading Lost — 26% out-of-sample and 58% post-publication decline (an actual published-bot measurement), prediction-market bot (TurbineFi)](https://www.turbinefi.com/blog/why-backtests-lie-prediction-market-overfitting-2026)
  - [The Overfitting Trap — 15 params / Sharpe 3.0 = almost certainly worthless; plateau test (alpha-suite)](https://alpha-suite.org/blog/overfitting-backtesting)
  - [Backtest overfitting full PBO/DSR framing w/ many links (DolphinQuant)](https://dolphinquant.com/blog/backtesting-traps-overfitting-look-ahead-bias-survivorship-bias)
- **Prevention checklist for this engine:**
  - [ ] Recalibrate: count parameters; >5 → require full walk-forward + plateau tests. The plateau test: ≥3 neighbors must have Sharpe ≥80% of best.
  - [ ] Frozen baseline: run the "first-version" strategy live-paper on autod as a control, forever — any live divergence of tuned vs control > noise = revisit.
  - [ ] Paper bandwidth: never let improvement loop outpace a fixed paper cadence (1, 2, 4) weeks per change.

---

## Archetype 10 — OMS / position-state drift (restart, crash, orphan state) — Kill rank: 10

- **Trigger condition:** restart/kill/crash anywhere between order submit and confirmation, or two components holding their own "position truth". Bot wakes with zero positions locally while the exchange has open orders; on next signal — re-enters same → double exposure; or exits never fire because "no position known".
- **How it surfaces:** **Silent until you check the exchange itself.** Risk dashboard says flat; actual position +0.5BTC moving against you. Culprit classic: "fill ack arrives out-of-order over WS vs order ack; queue it, don't drop it".
- **Real examples:**
  - [WebSocket Restart ⇒ "duplicate order / orphan position" — MatrixTrak (] state-drift playbook + reconciliation[)](https://matrixtrak.com/errors/websocket-disconnects-trading-bot-state-drift)
  - [The Vantixs "state reconciliation: trust the exchange, not your cache" (reconciliation section, same ref as Archetype 6)](https://vantixs.com/blog/rate-limits-retries-idempotency-crypto-trading-bots)
  - [Arkhamides 5-layer architecture — "two components maintaining their own position state is how you end up with +2 BTC and a flat risk dashboard"](https://www.arkhamides.com/blog/crypto-trading-bot-architecture)
- **Prevention checklist for this engine:**
  - [ ] Single OMS = says single source of truth (order lifecycle: pending/ack/partial/filled/cancelled/rejected) — nothing else owns position.
  - [ ] On (re)start: mandatory full reconciliation pass (fetch open positions + orders, rebuild local) **before** first signal; if unreachable → stay down.
  - [ ] Enqueue out-of-order fills; never drop an unacknowledged fill. Startup guard: don't place orders for X seconds while reconciliation runs.

---

## Archetype 11 — Paper-vs-live divergence (validation trap) — Kill rank: 11 (silently kills the *paper* meta, not paper dollars)

- **Trigger condition:** Paper account executes instantly & always-fill at signal price, without slippage/fees/latency — or worse, paper gets data-refreshed live while the model was backtested on different; then validation runs multi-month and is wholly invalid; the "confidence" from paper is fake.
- **How it surfaces:** at flip-to-live, non-reducing: real fills at worse prices, slower entries; (sometimes) also the *paper* engine "killed" because its PnL degrees so far from live repro that you must it.
- **Real examples:**
  - [From Paper Trading to Real Money: what successful algo traders do (r/algotrading thread synthesis): kill connections mid-trade, simulate broker outages, worst-case sizing okay — "paper vs micro-lot live" disagreement](https://vikofintech.com/en/posts/algo-trading-live-deployment-erfolg-wie-lange)
  - [The Investors Centre prod-bot: the type-comparison crash above (Archetype 2) never fired in paper because paper calls didn't return the string position format](https://www.theinvestorscentre.co.uk/trading/best-ai-trading-bots)
- **Prevention checklist for this engine:**
  - Paper runs must use the actual execution path (same order API, same fee model, slippage model), not "instant fill".
  - Add fee+latency to every paper cost: `fill = signal price ± (latency*k) ± fee`; if paper doesn't degrades, engine not validated.
  - Record and compare live paper signals vs execution every day (a parity report); if ratio ≠ 100% → halts.

---

## Archetype 12 — Dead code / stale config comes back to life — Kill rank: (loud; institutional anchor)

- **Trigger condition:** rollout or config push re-enables an obsolete, never-deleted code path (danger flag left `false` instead of removed; a "power peg" re-enabled 10 years after retirement).
- **How it surfaces:** **LOUD.** You get a phone call: $460M gone in 45 minutes. This is the only archetype that announces itself — and the only one that doesn't need data, strategy or feed. Hobby-scale: you deleted the file, but the config in the run dir still references it.
- **Real example:** Knight Capital Group (August 1, 2012): a one-off flag in the 2012 rollout re-enabled the retired 2003 "Power Peg" order router; the system sent ~4 million erroneous orders across ~150 symbols in 45 minutes, losing ~$460M before a rescue acquisition. Case write-ups: [PRMIA case study PDF (Knight Capital algorithmic trading failure)](https://prmia.org/common/Uploaded%20files/eAI/PRMIA%20Case%20study%20-%20Knight%20Capital.pdf), [DolphinQuant references the SEC investigation report](https://dolphinquant.com/blog/backtesting-traps-overfitting-look-ahead-bias-survivorship-bias)
  - SEC admin proceeding 34-70694 (Oct 2013) is the official record. [NOT FOUND: I did not fetch the SEC PDF to avoid URL-guessing; the PRMIA + requirement covers it]
- **Prevention checklist for this engine:**
  - [ ] Deleting a feature deletes the trigger too: no "off-but-present" code paths in the repo; CI that flags union runtime vs config keys.
  - [ ] Every config key must be in a schema; unknown key → crash at startup, never ignore.
  - [ ] Kill switch that cannot be blocked by code (net level, account API) + a real dry-run of that kill switch every month — the switch must work when the bot is misbehaving at 2 AM.

---

## Ranked "silent kill number" for a $100 paper engine (recap)

| # | Archetype | Would it kill paper silently? |
|---|---|---|
| 1 | Look-ahead | **Yes — instantly paper** (both backtest & paper are fiction) |
| 2 | API schema `.get()` blindness | **Yes** (position doubles, stop falsely needed) |
| 3 | DST/timezone day bucket | Yes (over a span, every trade slightly wrong) (slow burn) |
| 4 | Stale data | Yes (edge erased, silently, every trade) |
| 5 | Feed gap after reconnect | Yes (trades on a lie) |
| 6 | Retry duplicates | Yes (one event, 2× exposure) |
| 7 | Regime/filters | Somewhat (real paper case −40% accum in one day) |
| 8 | Survivorship | Warping only on rare events, but silently |
| 9 | Overfit | Yes, slower (months) |
| 10 | OMS drift | Yes + honestly via restart |
| 11 | Paper-live gap | No (paper itself fine; *validation* dies) |
| 12 | Dead flag | No (loud) |

---

## Pre-flight checklist — 10 lines, before any live dollar

1. Run the deployed autod strategy on **replay** (same params, real bars) and on **live paper** for 10 days; signal parity must be 100%, PnL within a documented recon tolerance.
2. Kill the process mid-trade (SIGKILL) → restart → verify reconciliation: **positions auto-detected, no re-entry, no duplicate orders**, state == exchange state.
3. Break the API key → the bot halts with an alert; break the feed → it stays flat; restore keys → recovers, no partial states produced.
4. Unit-test the bar builder across **both DST transitions** (current year next year) and verify every signal time is bar-close + 1 bar.
5. Backtest data = point-in-time universe (delisted included); every backtest re-validated with `shift()` audit for look-ahead by a second independent implementation.
6. Paper runs on the main even world **fee + slippage model**; optimize nothing while it runs; freeze params 2+ weeks before flipping live.
7. Circuit breakers tested *and triggered*: 3-streak stop, daily −2% (=$2) halt, weekly max-DD; each sends an alert while offline and when it fires, PnL is capped (simulate with trash params for 5 min).
8. Every API payload goes through a typed model; no `.get()` defaults at the execution/position boundary (crash-admit, don't default-estimate).
9. Alerts ✓ (Telegram) fire on: disconnect >2×interval, sequence gap, forced halt, daily loss, order ambiguous-timeout; alert path itself tested with a synthetic event.
10. **Idempotency & reconciliation are per-keep-sets**: client-order-id full, exchange-state is truth, second-to-last-call = reconcile. If a single one fails, fix it, then re-run from §1.

> Full production systems still blow up; if the first live month survives all the above with intact PnL — you have only proven the *infrastructure* is sound, not that the strategy has edge. Never hand more than one day's intended SL risk to a system you haven't operated paper-verified for 1-3 regimes.

---

## [NOT FOUND] / verification notes

- **r/algotrading wiki** (asked for): the sub's `wiki` pages effectively redirect to pinned curations. The live replacement-curators: the community-curated [Collection of useful posts in this sub](https://www.redditmedia.com/r/algotrading/comments/1e5b14e/collection_of_useful_posts_in_this_sub) incl. the ["Lessons from live testing" thread](https://old.reddit.com/r/algotrading/comments/1e4xk9m/lessons_from_live_testing/) and the "hard way" lessons thread [https://www.reddit.com/r/algotrading/comments/146nvvu/what_algo_trading_lesson_have_you_learned_the/]; body text largely unreadable via fetch (Reddit blocks) — [NOT FOUND: full content].
- **r/algotrading inspiration (Look-ahead)** — see Archetype 1: only title+snippet could be scraped. [NOT FOUND: full thread].
- SEC order PDF (Knight) — not directly fetched (no URL guessing); anchored via PRIMA case study (verified from search results).
- Any numeric "90% of strategies fail" style claims (multi-party). High-level claim, not a measured stat — treat as marketing estimates; do not import into specs.
- "API countdown survey" — not a distinct archetype (constructor-time type error, worth only inside Archetype 5/9); noted as covered above.
- All URLs above verified reachable via search/engines/SEP on 2026-08-09; two write-cleanouts (predictandprofit, guardlabs) note product-with-postmortem.

## Bundled references (all above, URLs inline)

Knight/postmortem-style: PRMIA case study PDF, SEC admin. — GuardLabs May-06 — vikofintech paper→live — investorscentre — oyamori stale-data — Alpaca forum — Predict&Profit (silent API, DST, rate-limits) — Vantixs rate-limits — VoiceOfChain — matrix platforms (reconnect kit, state-drift) — turboline & arkhamides architecture — title/search-first ties — quantified-strategies, luxalgo, crucible, trading-to-rich survivorship — alpha-suite/overfit — turbinefi — petrvojacek — chartbacktest/backtester.run/tgTargetHit lookahead — dolphinquant — dev.to lookahead-checklist — MQL5 DST thread — kimchobot timezone.
```