---
title: LLM Quota Operations — Running Research Automation on Free LLM Tiers
date: 2026-08-09
scope: gemini-3.1-flash-lite (Gemini API free tier) · openrouter :free variants
status: research notes; quota numbers are ballpark (providers change them without notice)
---

# LLM Quota Ops: Free-Tier Research Automation

Operational cheat-sheet for running automated research/classification workloads on
`gemini-3.1-flash-lite` (Gemini API, free tier) and OpenRouter `:free` variants
(20 RPM / 50-1000 RPD). Covers quota math (RPM/TPM/RPD), batching, retry/backoff,
deep-response guardrails, "when to skip the LLM" fallbacks, and quota probing that
costs nothing.

---

## 1. The two free lanes, side by side

| | Gemini API — free tier | OpenRouter `:free` |
| --- | --- | --- |
| Model in scope | `gemini-3.1-flash-lite` | any `model:free` variant (e.g. `deepseek/deepseek-chat:free`) |
| Cost | $0 in / $0 out (free tier, data may be used to improve products) | $0 token cost; free-model request caps apply |
| Request caps | ~15 RPM, ~250,000 TPM, ~500–1,500 RPD (community-reported mid-2026; varies by project, region, account; NOT published as a fixed grid anymore) | 20 RPM; 50 RPD (< $10 lifetime credits) or 1,000 RPD (≥ $10 credits) |
| Reset | RPD resets at midnight Pacific time | Daily limits on UTC-day basis (OpenRouter governs account-wide) |
| Scope of quota | Per Google Cloud **project** (extra keys don't add quota) | Per **account** (extra keys/accounts don't add quota) |
| Retry support in SDK | Built-in exponential backoff (4 attempts, ~1s → 60s) | Client-side: honor `Retry-After`, then backoff |
| Batch API | Yes (paid lane; 50% price, 10M batch-enqueued tokens for 3.1 Flash Lite) | — (no free batch pool) |
| Deep research / deep mode | PAID ONLY (not free tier) | n/a |

Sources:
- Rate-limits doc (dimensions, per-project, midnight-PT RPD reset, tier spend limits): <https://ai.google.dev/gemini-api/docs/rate-limits>
- Model card (1,048,576 in / 65,536 out token limits): <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite>
- Pricing (free tier $0 rows, grounding 500 RPD free, "used to improve our products"): <https://ai.google.dev/gemini-api/docs/pricing>
- OpenRouter limits (20 RPM; 50 vs 1,000 RPD tables): <https://openrouter.ai/docs/api/reference/limits>
- OpenRouter free-variant guide (account-wide caps, credit threshold behavior): <https://openrouter.ai/docs/guides/routing/model-variants/free>
- Troubleshooting (429 RESOURCE_EXHAUSTED, regional restrictions, SDK retry policy): <https://ai.google.dev/gemini-api/docs/troubleshooting>

**Headline gotchas**
- Gemini free-tier numbers are **not guaranteed**; Google cut free quotas 50-80% in Dec 2025 and reserves the right to change them. The live figure is only visible per-project in AI Studio. (community reports: <https://usagebox.com/articles/gemini-api-billing-free-tier-confusion>, <https://juanpabloaj.com/2026/04/30/gemini-free-tier-is-all-you-need/>)
- OpenRouter: failed/429'd requests still count against the 50-1000 RPD pool (<https://openrouter.zendesk.com/hc/en-us/articles/39501163688179-OpenRouter-Rate-Limits-What-You-Need-to-Know>) — a naive tight retry loop burns the day's budget without producing work.
- `:free` variants can fail with 429 even below your own caps when the upstream provider is at capacity; OpenRouter auto-falls back across providers for the same model before surfacing the error (<https://openrouter.ai/docs/api/reference/limits>).
- Negative OpenRouter balance (≤ $0) returns 402 Even for `:free` models (<https://openrouter.ai/docs/faq>).

---

## Decision table — task → model pick → request budget → failure plan

All budgets assume a serialized queue with a token-bucket limiter (see retry section).
"Req budget per run" = requests consumed by one full run of the automation against the given tier.

| Task (research automation component) | Model pick | Req budget per run | Token budget per request | Failure plan (fallback chain) |
| --- | --- | --- | --- | --- |
| Classify/tag 100s of short items (sentiment, intent, relevance) | rules-first cascade → `gemini-3.1-flash-lite` only for the ~10–20% cascade residual | ~20–60 reqs (Gemini) | ≤ 1–2K tokens in/out; use `max_output_tokens` cap | Regex/keyword pass first (see "Skip the LLM"); on 429 → backoff, batch remainder to tomorrow's RPD; on repeated failure → persist raw line + classify offline by rules, mark "unclassified" |
| Bullet/summary of one web page or diff | `gemini-3.1-flash-lite` | 1 req | ≤ 8K in / ≤ 1K out; truncate input above that | Truncate to head; if still >200 lines → stage LLM; if 429 → skip, emit raw excerpt with `[SUMMARY_PENDING]` |
| Named-entity / symbol / ticker extraction from text | rules (regex + dictionary) **first**; LLM only for the residual unmatched | ~0–10 reqs | ≤ 4K in | Pure rule fallback; LLM hits idle pattern; record misses as training data for regex rules |
| Dataset hydration / enrichment of a whole corpus (all rows) | Gemini **Batch API** (paid) or night-queue with the free RPD pool | 50 RPD budget: ≤ 45/day; 1000-RPD budget: all | batch = queued 10M tokens for 3.1 Flash Lite | Requeue failed batch entries; keep unfinished rows on CSV row-status column |
| Multi-turn web research (fetch → read → reason) in a loop | `gemini-3.1-flash-lite` (single-turn, tool loop) | 5–40 reqs (one page = 1 read + 1 reason) | each ≤ 4K in/1K out; cache shared context | Cap at N moves (e.g. 15) via counter; on 429, finish loop with rules + `[PARTIAL]` output |
| Full "deep research" (agentic: planning + dozens of searches) | **Approved, not free** — deep-research preview is paid ($1–7/task) | N/A on free tier | N/A | Replace with staged single-turn pipeline: run searches in parallel, then one synthesis call. Never attempt deep-research interactive on free tier |
| Keyword/pattern scanning of raw feeds (no judgment needed) | NO LLM — regex/grep/threshold | 0 destinations | N/A | Always-off LLM; corpus stays raw and cheap |
| Formatting / fixed-format output (SBFM tables, JSON) | LLM output **post-validated**; schema errors no-retry → re-queue | budget +10% slack | set `response_format`/`json_mode` | Deterministic assembler (template + raw fields) |

### Budget math that matters (worked example)

- Gemini free (typical reporting): **15 RPM / 250K TPM / ~690-ish RPD** for 3.1 Flash Lite. A run of 60 requests at 9K input tokens each = 49K TPM gap fine, but 60 ≥ 50-RPD-capped accounts.
- OpenRouter: 20 rpm sets a **hard floor** of ≥1s spacing between requests (serialize + `asyncio.Semaphore(1)` or delay-lock).
- `req_budget(run) = items × (1 + retry_rate × retry_attempts)` — with 6 retries per failure and 5% failure rate, budget balloons: `N × (1 + 0.05 × 6) = N × 1.3`. Plan the daily cap without the 1.3 coefficient and runs silently overflow RPD.
- TPM is input-tokens; outputs with thinking/chain-of-thought count toward TPM for the next request in the same minute — keep `max_output_tokens` small when the min-window is tight.

---

## Batching (talk to one API, not 1000)

- Gemini Batch API: 50% token cost, 24h turnaround, inline list or input file (2 GB file cap), per-model "batch enqueued tokens" caps (10M for 3.1 Flash Lite) — <https://ai.google.dev/gemini-api/docs/batch-api>. Caveat: batch pricing/availability is listed per model row; historically preview models lacked batch + context-caching on free lane — verify the row on the pricing page before building on it. `[NOT FOUND]` — no search result confirmed free-tier batch availability for `gemini-3.1-flash-lite`; treat as paid-only until verified.
- OpenAI Batch API: 50% discount, separate (much higher) rate-limit pool, up to 50,000 requests/200MB per batch, 24 h completion — <https://developers.openai.com/api/docs/guides/batch>. Batch results are one file; expired batches cancel unfinished requests (still pay completed).
- Anthropic Message Batches: 50% discount, per-model prompt-token queues, most batches finish < 1 h — <https://platform.claude.com/docs/en/build-with-claude/batch-processing>.
- For free tiers there is **no batch lane**: the practical "batch" is a **self-paced queue**: sort requests with priorities, drain slowly against RPD, and persist run-state (`pending/done/failed`) so a crash just requeues.

---

## Retry / backoff — the pattern that survives

Rules that survived production:

1. **Honor `Retry-After` first**, fall back to exponential backoff with **full jitter** only when the header is absent. Cap the delay (32–60 s), cap attempts (3–5 interactive; ~7 for batch workers with longer overall deadline). Full jitter: `sleep = random(0, min(cap, base × 2^attempt))`, base ≈ 1s. (AWS Builder's approximated maths; widely cited, e.g. <https://aiworkflowlab.dev/article/llm-rate-limiting-429-retries-2026>, <https://speedtesthq.com/guides/ai/llm-rate-limits-and-429-handling>)
2. **Only retry transient codes**: 429, 5xx. Never retry 400/401/403/413 — fix the request.
3. **Every 429 during a run counts against RPD** (OpenRouter officially; Gemini when the counter charges) — retrying blindly burns the daily budget. A 429 says "wait for the window", not "try again now".
4. **Concurrency kills**: N parallel workers all 429 → they all retry in lockstep (thundering herd). Use a single process-local token bucket (capacity = RPM, refill 1/min) plus a `Semaphore`; schedule, don't fire-and-then-backoff.
5. **Circuit breaker**: after N consecutive 429s (e.g. 5) on the same model, open for a cooldown (e.g. 30 s), try one probe, reopen — prevents pile-up on a provider that is briefly paralyzed (also applies to OpenRouter provider-side 429s).
6. **Model fallback chain**: on OpenRouter pass `models: [primary:free, backup:free]` so upstream unavailability hops to a different (still-free) model; on Gemini use the other free model family and finally a rule-readable output. Gateway pattern (`Retry-After`, virtual budgets) = LiteLLM/OpenRouter/Portkey per community guidance (<https://aiworkflowlab.dev/article/llm-rate-limiting-429-retries-2026>).

Pseudocode (any language):

```text
for attempt in 0..max_attempts:
    r = call_llm()          # with per-request timeout, max_output_tokens set
    if r.ok: return r
    if r.status == 429:
        wait = r.headers.retry_after or random(0, min(60, 1 * 2**attempt))
        sleep(wait); continue
    if r.status >= 500:
        if idempotent: sleep(random(0, min(32, 1 * 2**attempt))); continue
        return fail
    return fail               # 400-class: never retried
```

Gemini's own SDKs already do this by default (4 retries, sleep grows 1s→60s) — configure, don't fight them (<https://ai.google.dev/gemini-api/docs/troubleshooting>).

---

## Quota-status probing without paying

Probe **anything** that doesn't consume a billable completion / an RPD slot:

### OpenRouter (free lane)
- `GET https://openrouter.ai/api/v1/key` — free, returns `data.limit_remaining`, `usage_daily`, `is_free_tier`, `expires_at`. Do this at run start: if `usage_daily` is already within 10 of your 50/1000 RPD → abort with "queue for tomorrow". Doc: <https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key> (also `GET /api/v1/credits` for balance).
- `GET https://openrouter.ai/api/v1/models` — free; filters `.data[].id | ends_with(":free")` to enumerate what's actually available/open. No generation cost.
- **Successful** inference responses do NOT carry `X-RateLimit-*` headers — only 429 error bodies do (`X-RateLimit-Limit/Remaining/Reset`, plus `Retry-After` when all providers hinted it). So don't depend on headers from success responses for pre-emptive throttling (explicitly documented: <https://openrouter.ai/docs/api/reference/limits>).
- Smallest billable probe: `max_tokens: 1` on the cheapest `:free` model; then read `usage`/`usage_daily` from `/api/v1/key` to confirm the slot decremented.

### Gemini API (free tier)
- `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:countTokens` — free (no tokens charged), verifies the key is valid and reports input token size before committing: <https://ai.google.dev/api/tokens>, (curl example in the docs; REST sample: <https://github.com/google-gemini/deprecated-generative-ai-python/blob/7a7cc5474ddaa0255a4410e05361028a24400abd/samples/rest/count_tokens.sh>). Use a 1-token `countTokens` as a liveness probe without consuming RPM/RPD.
- `GET https://generativelanguage.googleapis.com/v1beta/models/{model}` — returns `inputTokenLimit`/`outputTokenLimit` metadata, no usage cost.
- **There is no free REST endpoint that reports live RPM/TPM/RPD remaining.** The only view is the AI Studio per-project rate-limit page (human-or-subagent browsed): <https://aistudio.google.com/rate-limit> (live values differ by project; usage tab is delayed ~15 min — community note: <https://discuss.ai.google.dev/t/handling-429-503-errors-from-the-gemini-api/124640/1>).
- Watchdog probe: track `usageMetadata.totalTokens` / `promptTokenCount` from each response into a local counter and compare to the project's known cap — works even when the dashboard is delayed.

### Economy of probes
Probing itself costs RPD on OpenRouter (`/api/v1/key` is free; generating 1 token costs 1 of the RPD). Keep probing to once per run start + after each 20-request burst. If you hit 429 mid-run guaranteed-repeatable, don't restritic probe loops; check `/api/v1/key` to see whether the day budget died.

---

## When to skip the LLM — rule-based fallbacks (regex, thresholds)

LLMs a proportional `100-1000x` cost per classification vs rules and 200-2000 ms latency (<https://www.institutepm.com/knowledge-hub/ai-classification-systems-guide>). In a research pipeline the cascade wins: rules → cheap classifier/threshold → LLM only for the residual (esp. on a free tier, "rule first" = 100% of requests, and every skipped LLM call frees a share of 50 RPD).

| Test | If YES → | Typical share of traffic (cascade) |
| --- | --- | --- |
| Is the task deterministic (fixed table, arithmetic, fixed lookup)? | SQL / regex / dataframe — never LLM | these items never touch the LLM |
| Rules expressed as if-then (tickers, exchanges, timeframes, currency, `UTCTime` parse)? | Regex / dict / threshold | 40–60% of input volume |
| JSON/CSV structure errors? | Parser checks / validation — LLM adds variance | N/A (validation gate) |
| Confidence below threshold on a cheap classifier (e.g. 0.85)? | escalate to LLM | 10–20% reaches the LLM |
| Nothing left → LLM | structured prompt + strict output schema | 100 own: yourself ≤ 20% |

Cascade numbers from the guide: rules first handle 40–60% of volume, ML 30–40%, LLM gets 10–20%; total LLM cost drops 70–90% vs everything-through-LLM (<https://www.institutepm.com/knowledge-hub/ai-classification-systems-guide>). The rule engineers recommendation: start with rules, log failures, use them as labeled data — exactly what a periodic free-tier pipeline needs (<https://www.red-gate.com/simple-talk/ai/when-and-when-not-to-use-llms-in-your-data-pipeline/>).

Concrete example for this repo's workload — news/headline triaging:
1. 1st pass regexes: `title contains "<sym>"`, date-range, 200-word min → pass/“definite” row, no LLM (~55% of rows).
2. Reject row (regex miss) → to `gemini-3.1-flash-lite` with `max_output_tokens: 200` → JSON verdict.
3. LLM verdict parse fails → drop into rules fallback (latest-market), record snippet, `[UNVERIFIED]`.

### When NOT to use the LLM for research automation at all

- Structured/deterministic transforms (SQL): LLM = added cost + variance (<https://www.red-gate.com/simple-talk/ai/when-and-when-not-to-use-llms-in-your-data-pipeline/>)
- High-volume enrichment at scale (token cost scales by volume; rules do 5-6 nines of the work)
- Output that must be audited/regulatory → deterministic logic
- Anything that needs `<100 ms` per row → rules
- **Full deep-research automation**: preview interactions (deep-research-preview-04-2026, Max) consume ~80–160 search queries, ~250K–900K input tokens, ~$1–7 per task — paid only, and even then worth 60 h of your time. On free tiers, split deep-research into (a) parallel search fetches (no LLM) + (b) one or two synthesis passes with a strict token budget. Sources: <https://ai.google.dev/gemini-api/docs/interactions/deep-research>, <https://ai.google.dev/gemini-api/docs/models/deep-research-preview-04-2026>.

---

## Failure-plan matrix (merged, ordered)

| Failure | Detect | First move | Second | Third |
| --- | --- | --- | --- | --- |
| 429 | status code | honor Retry-After; cap 3 attempts | above budget → mark item `pending`, queue next window | day cap hit → max priority to tombstone; notify |
| Provider-side 429 on `:free` | metadata `provider_code`/`error_type` | model fallback (alternate `:free` id) | backoff + probe `/models` later | convert to rules fallback |
| 400/403 | status | debug & fix (do NOT retry) | — | — |
| Timeout (read) | request deadline | do not retry non-idempotent | reduce input size (`generateTokens` first) | re-queue |
| SD quota at week start | `GET /api/v1/key` `usage_daily` | validate run size ≤ 80% of daily | shrink items per run | size restarts throttled |

---

## Refs (only real URLs)
- Gemini rate limits / pricing / troubleshooting / batch / deep-research / countTokens everywhere above; full list:
  - <https://ai.google.dev/gemini-api/docs/rate-limits> · <https://ai.google.dev/gemini-api/docs/pricing> · <https://ai.google.dev/gemini-api/docs/troubleshooting> · <https://ai.google.dev/gemini-api/docs/batch-api> · <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite> · <https://ai.google.dev/api/tokens> · <https://ai.google.dev/api> · <https://ai.google.dev/gemini-api/docs/interactions/deep-research> · <https://ai.google.dev/gemini-api/docs/models/deep-research-preview-04-2026>
  - Community measure of free limits: <https://juanpabloaj.com/2026/04/30/gemini-free-tier-is-all-you-need/> · <https://usagebox.com/articles/gemini-api-billing-free-tier-confusion> · <https://www.aifreeapi.com/en/posts/gemini-api-free-tier-complete-guide> · <https://yingtu.ai/en/blog/gemini-api-free-tier> · 429 threading: <https://discuss.ai.google.dev/t/fixing-429-resource-exhausted-at-0-03-of-quota-reproducible-across-projects-tiers-and-endpoints/177317> · <https://discuss.ai.google.dev/t/handling-429-503-errors-from-the-gemini-api/124640/1>
- OpenRouter: <https://openrouter.ai/docs/api/reference/limits> · <https://openrouter.ai/docs/guides/routing/model-variants/free> · <https://openrouter.ai/docs/faq> · <https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key> · <https://openrouter.zendesk.com/hc/en-us/articles/39501163688179-OpenRouter-Rate-Limits-What-You-Need-to-Know>
- Batch across providers: <https://developers.openai.com/api/docs/guides/batch> · <https://platform.claude.com/docs/en/build-with-claude/batch-processing> · <https://www.burnwise.io/blog/llm-batch-processing-guide>
- Retry/backoff: <https://aiworkflowlab.dev/article/llm-rate-limiting-429-retries-2026> · <https://speedtesthq.com/guides/ai/llm-rate-limits-and-429-handling> · <https://tianpan.co/blog/2026-03-11-llm-api-resilience-production> · <https://llmtest.io/blog/llm-rate-limits-production-patterns>
- Rules vs LLM: <https://www.institutepm.com/knowledge-hub/ai-classification-systems-guide> · <https://www.red-gate.com/simple-talk/ai/when-and-when-not-to-use-llms-in-your-data-pipeline/> · <https://www.deepinspect.ai/blog/pii-detection-llm>