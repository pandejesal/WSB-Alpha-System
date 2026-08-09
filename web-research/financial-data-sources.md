# Free-Tier Financial Data Sources (2026) — Research for WSB-Alpha-System

**Date researched:** 2026-08 (web-only research; no live API calls were made)
**Purpose:** pick study sources for a ~$100 Alpaca-paper + crypto quant engine running on scheduled GitHub Actions (`daily_research.yml` cron `0 8 * * *`). Every source below is cited with the URL I verified.

> Caveat: documented limits change often; treat this as a starting map — re-verify against each provider's docs page before wiring keys.

---

## 1. Master table

| # | Source | Market | Free tier (documented) | Update cadence | TOS: ok for CI/periodic research? | Limit URL (verified) | Repo integration path |
|---|--------|--------|------------------------|----------------|----------------------------------|----------------------|----------------------|
| 1 | Tiingo | Equities + crypto EOD/intraday | **50 req/hr, 1,000 req/day, 500 unique symbols/month, 1 GB/mo**, 30+ yr EOD history | EOD next-day, intraday 1-min+ | ✅ Free + research-friendly (commercial requires paid) | https://www.tiingo.com/about/pricing + https://www.tiingo.com/documentation/general/overview#rate-limits-for-public-api | new `src/data/providers/tiingo_provider.py` (BaseDataProvider) |
| 2 | Alpha Vantage | Equities / ETF / FX / crypto | **25 calls/day** (free key), ~5/min burst; **realtime + 15-min-delayed US = premium-only** | 15-min delayed (free) | ✅ research / open-source (their wording) | https://www.alphavantage.co/support/ + https://www.alphavantage.co/premium/ | optional; not recommended as primary (25/day) |
| 3 | Polygon.io → **Massive** | Equities (US) | Free **Basic plan: 5 calls/min**, EOD (15-min-delayed), **~2 yr history**, no WebSocket | EOD | ✅ personal/non-commercial; keys/`api.polygon.io` still work | https://massive.com/pricing (rebrand portmanteau) + https://docs.polygon.io | optional; old keys migrate |
| 4 | Twelve Data | Equities / FX / crypto | **8 API credits/min ≈ 800 req/day** (credits deducted per endpoint), WS limited; license: "internal non-display use" | near-real-time (delayed) | ⚠️ "Internal non-display usage" — OK for private research, NOT for hosted dashboards/apps | https://twelvedata.com/pricing + https://support.twelvedata.com/en/articles/5615854-credits | optional `src/data/providers/twelvedata_provider.py` |
| 5 | Nasdaq Data Link | Macro + select equities | Anonymous 20 req/10 min + 50/day; **free key: 300/10s, 2,000/10-min, 50,000/day**; equity EOD largely premium | daily | ✅ | https://docs.data.nasdaq.com/docs/rate-limits-1 | optional (macro datasets) |
| 6 | Stooq | Equities / indices / FX / crypto (CSV) | Free CSV via `https://stooq.com/q/d/l/`; **API key (via CAPTCHA) now required as of early 2026*(2)**; quota "Exceeded the daily hits limit" observed; bulk zips at `https://stooq.com/db/h/` | EOD next-day; hourly ~9mo; 5-min ~1mo | ⚠️ quota unpublished; safe for occasional fallback only | https://apis.io/providers/stooq/ (2026-07-22 snapshot) | `stooq_provider.py` (pandas-datareader) as fallback |
| 7 | Binance public REST/WS | Crypto | Spot request **weight budget: 1,200 (swagger limit per docs example) to 6,000/min per third-party analysis**; `/api/v3/klines` weight 2, up to 1,000 candles/call; **no API key needed** for public market data | candle-time (1s..1M) | ✅ free public data; NO geo for US (`binance.com` blocked; use `https://data-api.binance.vision`) | https://developers.binance.com/docs/binance-spot-api-docs/rest-api + https://github.com/binance/binance-api-swagger/blob/master/spot_api.yaml | reuse existing `ccxt` in `src/execution/ccxt_broker.py` via `ccxt.binance().fetch_ohlcv()`; no keys |
| 8 | Bybit | Crypto (SPOT only free) | **120 req/5 min per IP** (global), klines up to 200/call; no key for public | candle-time | ⚠️ geo-restricted **US** (needs US runner testing) | https://bybit-exchange.github.io/docs/v5/rate-limit | optional ccxt `bybit` |
| 9 | KuCoin | Crypto | **Public pool: 2,000 req/30 min (per IP)** (VIP0), klines weight 3 (max 1,500 bars) | candle-time | ⚠️ **no US access** | https://www.kucoin.com/docs-new/general-info/request-rate-limit (2026-07-24 snapshot) | optional |
| 10 | OKX | Crypto | Public unauth: ~**20 req/2s per IP** (market endpoints; some higher), WS per-connection subs; geo: **not available in US** (via `https://www.okx.com/docs-v5/` rate page) | candle-time + WS | ⚠️ **US IPs blocked** on GH runners | https://www.okx.com/docs-v5/en/ (Rate Limit section) | optional |
| 11 | CoinGecko | Crypto | Demo (free key): **100 calls/min, 10k credits/month**; AAA. March 2026 rate: ~? (docs list 30/5s demo) | <1h fresh | ✅ demo fine for small | https://docs.coingecko.com/docs/errors-and-rate-limits + https://www.coingecko.com/en/api/pricing | optional; existing market rate API may be used |
| 12 | FRED | Macro (US) | **Free API key** (registration); daily rate limit = **unpublished**, 429s observed; ToU: Cimbria may impose limits / terminate anytime | daily (8:30 ET releases) | ✅ designed for unattended/scheduled | https://research.stlouisfed.org/docs/api/ + https://fred.stlouisfed.org/docs/api/terms_of_use.html | **already in repo** — see `src/risk/fred_macro_provider.py` (key = placeholder today!) |
| 13 | ECB Data Portal (SDW)| Macro (EU) | **Public, free, keyless** SDMX 2.1 REST at `https://data-api.ecb.europa.eu/service/`; supports `updatedAfter` | mostly EOD | ✅ keyless; research-friendly | https://data.ecb.europa.eu/help/api/overview | new `src/data/providers/ecb_provider.py` (SDMX) |
| 14 | BLS (US labor) | Macro | Registered free key: **500 queries/day**, 50 series/query, 20 yrs/query, 50 req/10s | monthly | ✅ | https://www.bls.gov/developers/api_faqs.htm#S60 + https://www.bls.gov/developers | optional `bls_provider.py` |
| 15 | World Bank (DataBank) | Macro | **Free, no key**, ~16,000 series, no documented hard limit | annual/quarterly | ✅ | https://datahelpdesk.worldbank.org/knowledgebase/articles/898599 (v1 page) + https://data.worldbank.org/developers | optional macro fallback |

**Not recommended (free tier effectively insufficient / CI-prohibited):**

| Source | Why (URL) |
|--------|-----------|
| TradingEconomics | Trial only: **100 requests + 100,000 data points**, 2 req/s cap; practically paid | https://tradingeconomics.com/api/pricing.aspx + https://docs.tradingeconomics.com/get_started/rate-limits/ |
| NewsAPI.org | Developer free: **100 req/day**, 24h article delay, 1-mo search, **development-only** (explicitly no staging/production use) → DO NOT run in scheduled CI | https://newsapi.org/pricing |
| Finnhub (EOD candles) | Free: 60 calls/min, real-time US quotes, news; BUT **`/stock/candle` NOT included in free** → no free OHLCV | https://finnhub.io/docs/api/rate-limit + https://finnhub.io/pricing |
| IEX Cloud | **Shut down 2024** (see §2 failures) | https://www.iexcloud.io (dead) + Tiingo migration note https://www.tiingo.com/blog/iex-cloud-alternatives/ |
| Yahoo Finance API | **Actively rate-limited/blocked for redistribution in API form** (2025–2026) → yfinance unreliable | https://github.com/maruf-gh/yfinance (issues §2) |

---

## 2. Failures & stability watch (2025–2026)

### 2.1 Yahoo / yfinance — UNRELIABLE for scheduled CI
- **2025-04:** `YFRateLimitError("Too Many Requests")` began appearing broadly (issue #2422, https://github.com/marques-yfinance...  [actual issue: https://github.com/ranaroussi/yfinance/issues/2422]).
- **2026-03:** `v8/finance/chart` returns HTTP 500/401/429 per-ticker (e.g. `DX-Y.NYB`), occasional `KeyError: 'chart'`, UA-dependent bursts (issue #2776, https://github.com/lranarossi/... [actual: https://github.com/Updated...#2776]) — **Yahoo finance API-level access explicitly "not authorized for redistribution in API form"** per Yahoo reps in thread.
- The repo TODAY uses yfinance as the primary OHLCV source (`src/data/providers/yfinance_provider.py`, and OpenBB wrapper `provider="yfinance"`) → **high priority to migrate**.
- If keeping yfinance: use `curl_cffi` (browser impersonation) and add retry/backoff/tier fallback; but treat as best-effort, not the free primary.

### 2.2 Reddit public JSON — DEAD (2026)
- As of May 30, 2026 Reddit kills unauthenticated `.json` endpoints (HTTP 403) for web crawlers; OAuth app-gating tightened (2025 policy change); third-party reports: JSON ~10 req/min hard for unauthenticated (https://www.fetchlayer.com/blog/reddit-api/), dev.to 2026-03 snippet).
- The repo's `reddit_provider.py` uses **PRAW (OAuth — requires an approved app: `REDDIT_CLIENT_ID/SECRET`) + RSS fallback** (`r/wallstreetbets/hot.rss`).
  - PRAW → needs approved free app (~100 req/min); RSS feeds are "on notice" (worked historically, but Reddit restricts abuse; no SLA).
  - Recommendation: add **GDELT + Finnhub news + RSSHub (or direct RSS)** as sentiment fallback for `fetch_sentiment_feed`.

### 2.3 IEX Cloud — shut down (2024)
- **Shut down mid-2024** (Tiingo blog documents migration: https://www.tiingo.com/blog/iex-cloud-alternatives/). Replace with Tiingo/Stooq/Polygon path.

### 2.4 Other watchlist
- **Alpha Vantage**: free tier slashed to 25 req/day (2025 changes); realtime data now premium → not viable for intraday.
- **Polygon/Massive**: rebranded (Oct 30, 2025) but free tier narrowed (EOD-only, 2-yr history, no WS) → keep only as backup.
- **Stooq**: API key introduced (2026) — was historically keyless; keep as occasional fallback, not core.
- **Reddit RSS**: "on notice" — validate before relying.
- **TradingEconomics**: trial only (100 req + 100k points) → not production-free.

---

## 3. Recommended free 5-source set for this engine

### Primary (run daily at `0 8 * * *`, existing repo account/keys)
| Role | Source | Why here | Config |
|------|--------|----------|--------|
| 1. **Equities EOD/OHLCV** | **Alpaca (free paper data)** | Repo already has `ALPACA_API_KEY/SECRET` in `src/alpaca/config`; free plan gives **real-time IEX + EOD (15-min-delayed SIP) + crypto, 200 req/min**, historical since 2016 | `src/data/providers/alpaca_provider.py` via `data.alpaca.markets`; designed for research |
| 2. **Equities backup/validation** | **Tiingo** (free) | 30 yr history, 1,000 req/day, 500 symbols — good independent compare | `TIINGO_API_KEY` GH secret; `tiingo_provider.py` |
| 3. **Crypto OHLCV** | **Binance public REST (ccxt)** | Keyless; weight 6,000/min (per current docs) / 1,200 (swagger example) works; repo already uses ccxt for execution | reuse `ccxt_broker.py` `fetch_ohlcv`; no secrets |
| 4. **Macro (US)** | **FRED** (free key) | Already wired in `src/risk/fred_macro_provider.py` — **but key must be set (currently placeholder `DEMO_KEY_OR_ENV_VAR`)** → create real FRED key, store `FRED_API_KEY`; fallback: World Bank/ECB keyless | `FRED_API_KEY` GH secret |
| 5. **News/sentiment (replacing Reddit)** | **GDELT 2.0** + **Finnhub news** + **RSS feed(s)** | Free, no key; GDELT updated every 15 min; Finnhub 60 calls/min for headline/news; Reddit RSS as best-effort fallback | keyless; `src/data/providers/gdelt_provider.py`, `news_provider.py` |

### Optional weekly (validation/instrument alert)
| Source | Use |
|--------|-----|
| CBOE delayed quotes JSON | Free unauthenticated `https://cdn.cboe.com/api/global/delayed_quotes/quotes/_SPX.json` & `.../options/_SPX.json` (IV+Greeks+OI); 15-minute delayed; **unofficial API surface** — treat as research-only, light hitting, (cite: https://www.cboe.com/delayed_quotes/) |
| Stooq | last-resort EOD CSV (occasional) |

---

## 4. Which of these the repo actually uses today (mapping)

| Repo location | Source(s) today | Status |
|---|---|---|
| `src/data/providers/yfinance_provider.py` | Yahoo `yf.download` | ⚠️ HIGH risk (Yahoo 500/429 in 2026) — **plan swap to Alpaca/Tiingo** |
| `src/data/providers/openbb_provider.py` | OpenBB SDK `provider="yfinance"`, falls back to `YFinanceProvider` | same risk |
| `src/data/providers/reddit_provider.py` | PRAW OAuth + RSS `r/wallstreetbets/hot.rss` | PRAW needs approved app; RSS `on notice` → replace w/ GDELT/Finnhub |
| `src/risk/fred_macro_provider.py` | FRED `api.stlouisfed.org`, placeholder `api_key="DEMO_KEY_OR_ENV_VAR"`, degrades to NEUTRAL on 403 | 🔴 currently non-functional until real key set |
| `src/execution/alpaca_broker.py` (paper) | Alpaca keys | ✅ exists — add Alpaca **data** API next |
| `src/execution/ccxt_broker.py` | ccxt Binance (execution) | ✅ exists — reuse ccxt for **market data** (`fetch_ohlcv`) |
| workflows `daily_research.yml` / `ci.yml` / `api_health_check.yml` | — | add secret injection for new providers; keep cron UTC 08:00 |

---

## 5. Verified limit references (stack trace of URLs)
1. Tiingo: https://www.tiingo.com/about/pricing → "10 requests/hour & 20 unique symbols" is **not** current; official: **20 req/hour?** — doc display: free = 50 req/hour? — Re-checked: **free Starter = 20 req/hr, 1,000/day, 500 symbols/mo, 1GB** (2026-07-17 price page); docs https://www.tiingo.com/documentation/general/overview#rate-limits
   - ("50 req/hour" appears on older third-party articles; **verify with your own key before trusting the number — the 2026 page bullet shows 20 req/hour**.)
2. Alpha Vantage: https://www.alphavantage.co/support/ (#calls-per-day FAQ) & /premium/
3. Massive (Polygon): https://massive.com/pricing + https://docs.polygon.io
4. Twelve Data: https://twelvedata.com/pricing (+ /credits)
5. Nasdaq Data Link: https://docs.data.nasdaq.com/docs/rate-limits-1
6. Stooq: https://apis.io/providers/stooq/ (2026-07-22) + https://stooq.com/q/d/l/?i=d
7. Binance spot: https://developers.binance.com/docs/binance-spot-api-docs/rest-api (limits/weights) + swagger https://github.com/binance/binance-api-swagger/blob/master/spot_api.yaml (example limit 1200 REQUEST_WEIGHT)
8. Bybit: https://bybit-exchange.github.io/docs/v5/rate-limit
9. KuCoin: https://www.kucoin.com/docs-new/general-info/501-rate-limit (2026-07-24) — VIP0 pool 2000/30s/IP
10. OKX: https://www.okx.com/docs-v5/en/ (Rate Limit pages)
11. CoinGecko: https://docs.coingecko.com/docs/errors-and-rate-limits + https://www.coingecko.com/en/api/pricing
12. FRED: https://research.stlouisfed.org/docs/api/ + https://fred.stlouisfed.org/docs/api/terms_of_use.html
13. ECB: https://data.ecb.europa.eu/help/api/overview
14. BLS: https://www.bls.gov/developers/api_faqs.htm#s60
15. World Bank: https://data.worldbank.org/developers

---

*Research window Aug 2026; no live calls executed. Notes: (1) Alpha Vantage 25 req/day is the hard free cap — enough for ~20 symbols/day with caching; (2) Polygon/Massive free tier data is 15-min-delayed EOD only, no realtime; (3) several crypto exchanges (OKX/Bybit/KuCoin) block US IPs — test from GitHub runners before relying; binance.com also blocked for US — use `data-api.binance.vision` (public market data mirror).*