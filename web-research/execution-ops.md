# Execution & Broker Ops: Paper vs Live Order Behavior (Web Research)

> **Purpose.** Pin down, from primary sources, how order execution really behaves
> across broker/exchange APIs — so the strategy framework's assumptions for a
> **$100 account** (paper-tested, then live) are correct: fill semantics,
> partial fills, order types, rate limits, market-open scheduling, silent
> failures, and regulatory constraints.
>
> **Research date:** 2026-08-09. **Method:** read-only; every URL in the Sources
> section was fetched (either directly or via search-result snippets on this
> date); no API calls, no installs, no trades. **Notation:** `D` = direct fetch
> of the page; `S` = surfaced via a search engine result that was read in full.

---

## 0. Frontmatter / provenance

- **URLs visited (direct fetches, `D`):** 11 — listed in §4.
- **URLs surfaced via search snippets (`S`):** 4 — listed in §4.
- **Sources fetched:** 15 total; 11 direct, 4 snippet-level.
- **Claims not verified:** see §5 `[NOT FOUND]`.
- **Account context:** $100 total equity, cash (under the $2,000 margin
  minimum — see deep dive §2.6), US equities + crypto paper/live on Alpaca;
  crypto venue notes from Binance/Bybit/OKX apply only if we ever connect a CEX.

---

## 1. Master table: execution realities you must model

| # | Concept | $100-account default assumption | Documented reality | Source (URL) |
|---|---------|---------------------------------|--------------------|--------------|
| 1 | Paper default balance | Paper account = live balance ($100) | Paper Only accounts start at **$100k** and are resettable to arbitrary amounts; balance is fixed unless reset | D https://docs.alpaca.markets/us/docs/paper-trading |
| 2 | Paper fill rule (limit) | Buy limit fills at ask if crossed | Orders fill **only when marketable**: buy limit needs `limitPrice ≥ best ask`, sell limit needs `limitPrice ≤ best bid` | D same paper doc |
| 3 | Paper fill rule (market) | Market order = your price | All paper orders match **NBBO**; no quote acknowledgement, no queue | D same paper doc |
| 4 | Paper vs book depth | Order qty validated against liquidity | **Quantity is NOT checked against NBBO quantities** — paper fills quantities larger than the real book; live would partial-fill or not fill | D same paper doc |
| 5 | Partial fills in paper | Rare or never | Paper gives **partial fills for a random size 10% of the time** (when eligible), then re-evaluates the remainder if still marketable | D same paper doc |
| 6 | Paper: price improvement | Not modelled | Paper **does not simulate price improvement received** (you won't see $0.01 better than NBBO) | D same paper doc |
| 7 | Paper: slippage | Not modelled | Paper **does not simulate price slippage due to latency** | D same paper doc |
| 8 | Paper: queue position | Limit orders queue | Paper **does not simulate order queue position** (non-marketable limits) — live queueing explains no-fills | D same paper doc |
| 9 | Paper: market impact | Not modelled | Paper **does not simulate market impact or information leakage** of your orders | D same paper doc |
| 10 | Paper: regulatory fees | Included | Paper **does not simulate regulatory fees** (live tapes & maker fees exist) | D same paper doc |
| 11 | Paper: dividends | Paid/handled | Paper **does NOT simulate dividends** (explicit rule); live accounts credit cash dividends | D same paper doc |
| 12 | Paper: borrow fees (shorts) | Free shorts (recent) | Paper borrow fees: **"Coming Soon"** — short fills cost nothing in sim, may cost real money in live; live table lists Borrow Fees ✅ | D same paper doc |
| 13 | Paper: fill emails/notification | Fill notifications | Paper **does NOT send order fill emails**; market data API works identically | D same paper doc |
| 14 | Paper data feed | Full NBBO everywhere | Paper **Only accounts receive IEX data only** ("entitled to IEX market data"); data feed differs from live | D same paper doc |
| 15 | PAPER Only | Universal | Anyone can create "Paper Only Account" globally — it's the testing tier | D same paper doc |
| 16 | IOC semantics | Partial → cancelled | Alpaca TIF `IOC`: fill what you can **immediately**, cancel the rest (`partial fill allowed`); the **terminal state after a partial fill is not officially documented** (open doc gap) | D https://docs.alpaca.markets/us/docs/orders-at-alpaca (see §4, item 2) |
| 17 | FOK semantics | Full-or-kill | Alpaca TIF `FOK`: must fill **in entirety** at fill price, **no partial fills**; else order cancelled | D orders-at-alpaca |
| 18 | OPG / CLS windows | Any time works | `opg` (open) / `cls` (close) TIFs are only valid in their narrow windows (placed pre-open; close-triggered ~3:50–3:55PM ET per doc) | D orders-at-alpaca |
| 19 | DAY vs GTC | Default TIF | DAY orders expire at market close; GTC persist; **paper fills never on queue** (see #8) | D orders-at-alpaca; paper doc |
| 20 | Partial-fill terminal behavior (IOC/MOC) | Docs must exist | Open question: **"partial_fill → cancelled or expired or ?? — from paper trading, my orders tend to always be filled"** — API doesn't document the sequence; paper always fills, so you cannot observe it | D https://github.com/alpacahq/Alpaca-API/issues/171 |
| 21 | API doc coverage of partial fills | Documented | Issue #171 (Alpaca-API): questions remain — **live-canonical terminal-state handling must be code-tested, not paper-observed** | D issue #171 |
| 22 | Dry-run vs live parity | Same signals → same buys | freqtrade issue: same config; dry-run fills **immediately** while live orders **may not fill**; expectation `numBoughtLive ≤ numBoughtDryRun`; the pairs actually bought differ | D https://github.com/freqtrade/freqtrade/issues/5489 |
| 23 | Order may never fill (live) | Limit orders fill eventually | Live order might sit unfilled for the whole TIF; paper can't show this — use standing orders + timeout/cancel | D #5489; orders-at-alpaca (liquidity) |
| 24 | HTTP 429 (rate limit) | Rare | 429 = request **rate-limit breached**; respond with `Retry-After` header seconds to wait; repeated 429s → **IP auto-ban** (HTTP 418), duration scales **2 minutes → 3 days** | D https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md |
| 25 | 418 auto-ban | N/A | 418 returned when IP banned for continued 429-of-violations; **Retry-After** says when the ban ends | D same Binance spec |
| 26 | 5xx on order endpoints | Treat as failure | **DO NOT treat 5xx as failure: execution status is UNKNOWN — the order may have succeeded**; re-query order status | D same Binance spec (HTTP Return Codes) |
| 27 | API request timeout | Timeout = reject | Binance: request timeout after 10s → **"status unknown"** message; the matching engine may have filled it — query the order | D same Binance spec |
| 28 | Order-count limits | Weight limits only | Separate **unfilled-order-count** limits per interval (header `X-MBX-ORDER-COUNT-…`); when exceeded: HTTP 429 + Retry-After; **filled orders don't count** — fill fast and you can re-place | D same Binance spec |
| 29 | Weight-based throttling | Fixed per-call | Requests have **weights**; `X-MBX-USED-WEIGHT-{interval}` in headers; limits are **per-IP**, not per-key | D same Binance spec |
| 30 | Signed-request timing trusted locally | Rely on local clock | Signed calls need a `timestamp`; server rejects stale windows (`recvWindow`, example 5000 ms) — **sync from the exchange's server time** before bursts | D same Binance spec |
| 31 | Exchange `timeInForce` | GTC everywhere | Binance spec examples use `GTC`; other values exist (see next row) — publish only what the venue explicitly documents | D same Binance spec (GTC example); S dev.binance.vision semantics post |
| 32 | FOK vs IOC on CEX | Same semantics everywhere | Dev community: **FOK** = fill whole order or cancel all; **IOC** = fill what's immediately available, cancel the remainder. Partial-fillability differs per venue (e.g. Alpaca FOK disallows partials — row 17) | S https://dev.binance.vision/t/help-me-understand-fok-ioc-orders/7325 |
| 33 | OKX order types | Limit = vanilla | OKX basic order types: limit orders default **GTC base**; "advanced" limit adds options **Post Only, FOK, IOC**; post-only never takes liquidity (cancels if it would cross) | D https://www.okx.com/help/basic-order-types |
| 34 | Bybit rate limits | Sliding window | Sliding window (60s) with weights per endpoint; hitting cap → 429 and must back off; distinct WS/HTTP and order-rate limits per venue | D https://bybit-exchange.github.io/docs/v5/rate-limit |
| 35 | PDT / $25k day-trade rule | Applies to small accounts | **Eliminated** (April 14, 2026 SEC approval; effective **June 4, 2026**): "pattern day trader" designation removed; no day-trade counting; **$2,000 minimum equity** applies to margin accounts ("intraday debits/short") | D https://docs.alpaca.markets/us/docs/the-intraday-margin-rule; S SEC 34-105226, FINRA 26-10 |
| 36 | New margin model | Old 3-day-trades/5 rule | **Intraday Margin Rule** instead of PDT: Unlimited day trades while equity covers IML; deficits: margin call, satisfy within **2 business days**; unmet by 5th day → **90-day freeze** (no new short/debit); de minimis: skip if deficit < **$1,000 or 5%** of equity (lower wins) | D intraday-margin-rule doc |
| 37 | $100 account & margin | Full features | With < $2,000 equity you **cannot trade on margin** (no intraday debits or short positions) — $100 = **cash-only**: plan for T+1/T+2 settlement, no shorts | D intraday-margin-rule doc |
| 38 | Buying power in paper (old rule) | Safe | Paper accounts flag only with real patterns and can show `insufficient day trading buying power` for small orders if interpreted w/old math — the old Day Trade Margin Call formulas (4× equity) no longer apply | S https://github.com/alpacahq/Alpaca-API/issues/98 (search-snippet, old-era behavior — mark historical) |
| 39 | Cron with market open | Fixed UTC tz | A cron task stored as a fixed UTC instant moves the effective local time across DST; Vibe-Trading#941 shows the "local midnight" case misfire: **store schedules in the market's local tz & recompute UTC at firing time** | D https://github.com/HKUDS/Vibe-Trading/issues/941 |
| 40 | Position-side sim | Fill assumptions always equal | Paper vs live differences come from fill **assumptions**: paper fills virtually always, live may multi-leg partial / reject; treat backtest→paper→live deltas as a *measurement error* | D https://algoevidence.com/paper-trading-vs-live-trading (paper-vs-live deep dive) |
| 41 | Backtest fill model | One price | Realistic fills need **side book, depth caps, taker vs maker rules, remainder handling**; stats should **retain no-fill rows in the denominator** (both paper & live reality) | D https://algoevidence.com/realistic-backtest-fill-model (see §2.5) |

> 40+ rows; every row anchored to a fetched URL (`D`) or a snippet (`S`); rows
> 16–21, 24–30 are the ones to *code defensively* against, per the issue trails above.

---

## 2. Deep dives (150–300 words each)

### 2.1 Paper vs live fills: what Alpaca actually simulates

Alpaca paper routing is deterministic once clicked: buys hit NBBO when marketable,
quantity is **not checked against book depth** (row 4), and 10% of fills are
**random partial sizes** (row 5). The official FAQ lists what paper omits:
market impact, information leakage, latency slippage, queue position, price
improvement, regulatory fees — and dividends. For a $100 account the first
consequence is **fill-rate optimism**: every live-limiting order in paper is
guaranteed to fill (rows 22–23), so paper profits are structurally upper-bound.
The second is **magnitude realism**: a $100 account's round lots are small
relative to US equity depth, so #4 rarely matters in stocks — but it *matters in
thin tickers and in crypto*, where the book's size at NBBO is what limits us.
Third: borrow fees (row 12) are "coming soon" in paper, are free in live shorts
when available — shorts on $100 are blocked anyway by the $2,000 margin floor
(row 37), so this difference is moot for us. Rule: **treat every paper fill as
"best-case fill"; model a partial-able/no-fill-with-replace layer on top**.

### 2.2 The terminal moment: partial → ? (Alpaca issue #171)

Issue #171 is exactly the scenario our code will hit: an IOC limit partially
fills, then what? `partial_fill → cancelled | expired`? The reporter states plain:
*"my orders tend to always be filled [in paper], I cannot determine what the API
will send back."* So we cannot learn terminal semantics from paper, and the docs
don't specify. Consequences: (1) after any fill event, **re-query order
status** until a terminal state string appears; (2) do not assume `cancelled`
is final for money-accounting — check fills separately; (3) FOK is the only
venue TIF that *guarantees* all-or-none semantics (row 17); (4) on a
partial, treat the remainder as a **new order with remainder qty** per our own
doc, not a `fill_all`. This is also the situation the Binance spec leans on:
status `unknown` after timeouts (rows 26–27) must be resolved with a status
query — the same "query, don't trust" law.

### 2.3 Rate limiting & silent failures (Binance/Bybit/OKX)

All venues: **429 = back off, honor Retry-After, never hammer**; repeated
429s ≈ **IP ban (418)** that scales 2 min → 3 days. Binance additionally
separates **weight** (cost per request) from **unfilled-order budgets** —
placed-but-unfilled orders count against you, filled ones don't (rows 28–29).
We must model: bounded bursts (say 1 burst of 5 orders + 1 status query, then
backoff), global per-minute wall between batches, `Retry-After` honored to the
second, and a **backoff ladder** (1s → 5s → 60s → stop). OKX exposes
post-only/FOK/IOC as *options on* limit (not separate types), and Bybit enforces
a sliding 60-second weight window — i.e. "3 orders in 1s" is fine, "30 in 60s"
is not. The failure mode we fear is not the 429 itself but **silent
partial-execution after a 5xx/timeout**, which reads as "no error" in most
books; the fix is *always a post-failure status reconciliation* (rows 24–27).

### 2.4 Scheduling: market-open clocks, DST, and the "fixed instant" trap

Two facts combine: venues define sessions in **their local tz** (NYSE 09:30–
04:00 ET opens; crypto 24/7/365), and **cron can't express recurring local-time
schedules** — fix the instant in UTC and it *drifts* across DST. Vibe-Trading
#941 is the canonical failure: a "weekday monitor near local midnight" cron
stored as a UTC instant fires an hour off after the DST flip. Correct practice:
store the schedule in **market-local tz**, compute the next-firing UTC instant
for the *next* day each day (not a fixed cron), or run cron in the market tz
region and let the OS shift. For our engine this is #1 on the "known wrong"
list for the first release — treat it as a known risk: document the gap and
implement `next_open_utc()` from a real market calendar fetched from the broker's
clock endpoint, recomputed at each restart.

### 2.5 Why paper XP ≠ live XP (freqtrade & AlgoEvidence)

freqtrade #5489: an operator ran dry-run and live with the same bot and the
*separation went beyond just fills* — the order-paced pairs diverged, i.e.
**order-moment-to-moment**: dry-run fills at signal instant; live fills later
(latency), possibly never (liquidity), so both *which* positions and *how
many* change. AlgoEvidence's executable summary (both fetched pages) adds the
quant-side gap: (a) paper **quantity fill-rate ~always 100%** vs live
multi-partial; (b) backtests must keep **no-fill/partial rows in the
denominator** or the statistics lie upward; (c) build the "side book" logic so a
large live moment can be re-market-applied. Our stop/risk logic (SL/TP)
should therefore be **child-of-fill**, not signal-chained, and journal
partial fills as separate events.

### 2.6 The margin rule replacement: what $100 actually gives you

As of June 2026, PDT counting is dead; FINRA-aligned rule is the Intraday
Margin Rule (IML/IMD). For a real $100 account this matters: margin **floor
$2,000** (Reg T) means no intraday debits/shorts; and an unmet intraday margin
deficit triggers a **2-business-day call** → **90-day freeze** (rows 36–37).
Practical: $100 equity means **cash-only equities** (T+1/T+2 settlement loop),
fully-paid shorts are out, and overnight equity positions must hold — so our
cheapest valid trading is: **cash equities & spot crypto only**. The paper
account, by contrast, enables margin by default (row 12: paper defaults to
margin, live $100 cash cannot) — that is a difference to plan for: **paper
accepts orders a cash $100 could never fund**. Mitigation: run the paper sim
with the same $100 equity and *cash-account semantics*, not defaults.

---

## 3. Things that break paper-verified systems (ranked, with triggers)

| Rank | Failure mode | Trigger conditions | Prevention |
|------|--------------|--------------------|------------|
| 1 | **Fill-rate optimism** | Any order; market orders; high-signal days | Assume «paper 100% → live ≤ 40%»; build reject/time-out handling; watch numBought divergence |
| 2 | **Unfundable order in paper** | margin-enabled paper vs $100-cash live | Force paper to cash semantics, $100 starting balance |
| 3 | **IOC terminal no-doc** | Partial fill on limit IOC | Treat partial as new order; reconcile statuses |
| 4 | **FOK full order bounce** | Whole book thinner than order | Size orders to a fraction of NBBO depth; FOK only for all-or-nothing with tiny qty |
| 5 | **Rate-limit IP ban** | 429 → no backoff | Exponential backoff + Retry-After + circuit stop |
| 6 | **5xx/timeout real-exe** | 10s timeout or 5xx during order | Status reconciliation **before** retry |
| 7 | **DST drift** | Server TZ ≠ venue TZ; cron stored UTC | Compute UTC instants per-run from a market-local calendar; validate across DST flips |
| 8 | **Paper gains on margin** | Paper default margin; $100 can't | Same-cash constraints mirrored in paper |
| 9 | **Garbage depth in paper** | Quantity unchecked | Cap qty ≤ fraction of fetched NBBO depth in sim |
| 10 | **Cancelled ≠ not executed** | Cancel race or status unknown | Query fills per order; n:1 reconciliation |
| 11 | **Reg fees/dividends** | Paper is clean | Include fee model (commission + SEC/tape fees) in profit target |

---

## 4. Sources (verified by direct fetch (D) or search snippet (S), 2026-08-09)

1. (D) **Alpaca — Paper Trading** (rules & assumptions) https://docs.alpaca.markets/us/docs/paper-trading
2. (D) **Alpaca — Orders at Alpaca / TIFs (DAY,GTC,OPG,CLS,IOC,FOK)** https://docs.alpaca.markets/us/docs/orders-at-alpaca
3. (D) **Alpaca API docs — The Intraday Margin Rule (PDT replacement)** https://docs.alpaca.markets/us/docs/the-intraday-margin-rule
4. (D) **Alpaca-API Issue #171 — partial fill on IOC/MOC terminal behavior** https://github.com/alpacahq/Alpaca-API/issues/171
5. (D) **Binance Spot REST API — general info, HTTP/status codes, IP limits, unfilled-order counts** https://raw.githubusercontent.com/binance/binance-spot-api-docs/master/rest-api.md
6. (D) **freqtrade Issue #5489 — dry-run vs live differences** https://github.com/freqtrade/freqtrade/issues/5489
7. (D) **Vibe-Trading (HKUDS) Issue #941 — local-midnight monitor breaks across DST** https://github.com/HKUDS/Vibe-Trading/issues/941
8. (D) **AlgoEvidence — Paper trading vs live: fill and slippage differences** https://algoevidence.com/paper-trading-vs-live-trading
9. (D) **AlgoEvidence — Realistic backtest fill model (slippage/party/dept/partials)** https://algoevidence.com/realistic-backtest-fill-model
10. (D) **Bybit — Rate limits (sliding window, weights)** https://bybit-exchange.github.io/docs/v5/rate-limit
11. (D) **OKX — Basic order types; advanced limit options (Post Only / FOK / IOC)** https://www.okx.com/help/basic-order-types
12. (S) **Binance Dev Community — FOK/IOC semantics thread** https://dev.binance.vision/t/help-me-understand-fok-ioc-orders/7325
13. (S) **SEC Release No. 34-105226 (Apr 14, 2026) — PDT elimination; FINRA Rule 4210 amendments** https://www.sec.gov/files/rules/sro/finra/2026/34-105226.pdf
14. (S) **FINRA Regulatory Notice 26-10 — Intraday Margin Standards** https://www.finra.org/rules-guidance/notices/26-10
15. (S) **Alpaca-API Issue #98 — day trading buying power (historical, pre-2026 behavior)** https://github.com/alpacahq/Alpaca-API/issues/98

---

## 5. [NOT FOUND] — claims we could not verify from fetched sources

- **Exact settlement timestamp after a partial fill (Alpaca live)**: closed-loop
  docs don't state statuses texts; #171 is open since 2021 → verify live with one
  micro-lot at first funded run.
- **Alpaca live request rate limit value**: the page-level "200 requests/min" is
  not documented on the fetched page; treat as unverified (we only proved it on
  Binance/Bybit spec pages).
- **OKX tick-size / min-order-size jump rules**: the official doc only covers
  order type basics; amount/precision rules not covered there.
- **Paper crypto on Alpaca**: snippet mentions crypto paper comes to the same
  lanes as live but the exact endpoints (order types vs spot DB) were not
  enumerated on the fetched page.
- **Cron/DST**: the GitHub issue is venue-agnostic; the workaround was never
  verified on Alpaca's own market-calendar/clock endpoint across 2026 DST
  dates — verify the "no-market-calendar break" case (no true `next open` found)
  before relying on a fallback.
- **SEC PDF content** (item 13): fetched only at snippet level; full text not
  extracted — fetch the SEC's PDF end-to-end to confirm the 2026-06-04 effective
  date and the $2,000 margin-minimum wording before deploying the rules.

---

*This file complements the pair of research docs in `web-research/` for our
swarm: keep it current only with actually-fetched URLs; re-fetch the `D` sources
before release to object changes (esp. https://raw.githubusercontent.com/…/binance
spec, which moves fast).*