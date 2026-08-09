---
title: "Free-Tier Automation Stack for a Quant Pipeline"
type: research / architecture
tags: [quant, github-actions, vectorbt, scheduling, alerts, pdf, secrets]
date: 2026-08-09
task: paper-pipeline-infra
status: complete
sources-fetched: 20+ (URLs inline)
note: "No installs performed; single-file deliverable. Companion local doc: web-research/financial-data-sources.md (data-source pick)".
---

# Free-Tier Automation Stack for a Quant Pipeline ($0/month)

Stack question: *data fetch → backtest → risk gate → alert / report*, run on a
cron-like schedule, at zero monthly cost, in a repo that can live on GitHub.

**Bottom line:** GitHub Actions is the $0 scheduler of choice for EOD / after-hours
cadences (free tier for private repos: 2,000 job-minutes/month; unlimited on
public repos). VectorBT open-source edition is the free backtest engine. Alerts =
Telegram Bot API `sendMessage` (free, no server needed). Reports = Markdown +
pandoc or WeasyPrint in the same CI job. Self-host (Docker + cron/APScheduler) is
the backup plan, only worth it for sub-5-minute or always-on requirements.

---

## 1. Architecture recommendation (repo-shaped, $0/month)

```
quant-pipeline/                        # one repo = one pipeline
├── .github/workflows/
│   ├── daily-eod.yml                  # THE scheduled job (fetch → backtest → risk → alert)
│   └── manual-run.yml                 # workflow_dispatch for ad-hoc runs with input params
├── src/quantpipe/
│   ├── fetch.py                       # data pull (see web-research/financial-data-sources.md)
│   ├── backtest.py                    # vectorbt community edition
│   ├── risk_gate.py                   # stop/risk caps from configured limits
│   ├── report.py                      # markdown → HTML/PDF (section 4)
│   └── notify.py                      # Telegram sendMessage (HTTP POST, stdlib + requests)
├── config/
│   ├── instruments.yaml               # symbols, timeframes
│   └── risk.yaml                      # max position, drawdown, exposure caps
├── reports/                           # generated artifacts (gitignored)
├── requirements.txt
└── README.md
```

Pipeline order per run: `fetch → backtest (vectorbt) → risk gate (fail-closed) →
alert out of Telegram; report out of pandoc → upload as artifact`.

### GitHub Actions schedule vs self-host — decision

| Concern | GitHub Actions schedule | Self-host (Docker + cron/APScheduler) |
|---|---|---|
| Cost | $0 (free tier; 2000 min/mo private) | $0 software, but hardware/power/Internet + your time |
| Cadence | min interval 5 min; best-effort, can be delayed 10–30 min at top-of-hour | exact, always-on |
| DST for US markets | UTC-only by default + optional IANA timezone; real repos list two cron lines (EST/EDT) + self-gate in script | container TZ configurable |
| Reliability | can be skipped under load; workflow auto-disabled after ~60 days of repo inactivity | dies with the box; you own pagers |
| Secrets | first-class (encrypted secrets, redaction, per-env) | you manage .env files yourself |
| Firewalls | none (GitHub runners call outbound APIs) | inbound exposure risk for webhooks |
| Hit to: | No SLA, no intraday misses; **EOD-only workloads fit perfectly** | Needed for <5-min cadence or 24/7 streaming |

**Recommendation:** Start with CI-only (EOD run at ~20:05 UTC weekday + 22:00 UTC
safety-net roll). Add a Raspberry-Pi/Docker host only when you need <5-min or
intraday streaming; keep the pipeline scripts identical so the host is just a
"second runner".

---

## 2. Component / option / cost table

| Component | Option | Cost | Caveats | URL |
|---|---|---|---|---|
| Backtesting engine | vectorbt (open-source community edition) | $0 (Apache 2.0 + Commons Clause "fair-code") | Can't sell products/services that are *primarily* this software; has numpy/pandas learning curve | https://github.com/polakowo/vectorbt https://www.pypi.org/project/vectorbt/ |
| Backtesting engine (paid) | VectorBT PRO | $19/mo (AlgoPlatforms) or ~$999/yr (Pickuma) — pricing varies by source → [NOT FOUND] single official price | Private GitHub repo, no public checkout; requires sponsorship | https://vectorbt.pro/ |
| vectorbt v0→v1 migration | release v1.0.0 (Apr 22, 2026): optional Rust engine (`pip install vectorbt[rust]`), engine auto-dispatch, new dep groups (`[full]` → `[full-no-talib]`) | $0 | 0.x → 1.x is a breaking change; no official "vectorbt 2" — no dedicated migration doc exists (see §5) | https://github.com/polakowo/vectorbt/releases/tag/v1.0.0 |
| Scheduler (CI) | `on: schedule:` cron | $0 (2,000 min/mo private; unlimited public) | UTC-native; min interval 5 min; best-effort; delays at :00 hour; auto-disable after 60 days of repo) | https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/events-that-trigger-workflows#schedule https://cronpreview.com/dialect/github-actions |
| Scheduler (CI) + timezone | `schedule.timezone: IANA` (e.g. `America/New_York`) | $0 | Now supported on GitHub Actions; DST rules still tramp — many projects still list both EST+EDT crons | https://cronwizard.com/github-actions-cron |
| Multi-symbol runs | dynamic `strategy.matrix` from a JSON output (`fromJSON(needs.X.outputs.Y)`), `max-parallel` | $0 | Matrix expands to N parallel jobs; free-tier minutes multiply | https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/running-variations-of-jobs-in-a-workflow |
| Dependencies in CI | `actions/cache` (key: `hashFiles`), setup-python caching | $0 | Cache is not signed; anyone with PR access can read base-branch cache — no secrets there; use `cache/restore` (read-only) in low-trust paths | https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching |
| Scheduling lib (self-host) | APScheduler (cron/interval/calendar triggers, SQLAlchemy/Mongo job stores) | $0 (MIT) | Not a daemon — a library; embed in your app; job store persists + catches up after restarts | https://github.com/agronholm/apscheduler https://www.pypi.org/project/APScheduler/ |
| Docker scheduling (self-host) | cron inside container (e.g. Raspberry Pi + docker-compose) | $0 + hardware/power | cron gotchas: PYTHONPATH/env not set, `user: root`, full paths, `CMD cron -f` | https://dev.to/conlin/running-a-python-cron-in-docker https://dev.to/ulnit/how-i-built-a-raspberry-pi-automation-lab-that-runs-itself-8am |
| Alerts | Telegram Bot API `sendMessage` | $0 (free for devs; ~30 msg/s per bot) | Bot token = full control; store in Actions Secrets; webhook mode needs HTTPS IP/domain (443/80/88/8443) — not for outbound CI alerts | https://core.telegram.org/bots/api https://dev.to/climentea/push-notifications-from-server-with-telegram-bot-api-32b3 |
| Report: Markdown → PDF | pandoc (free, MIT) + `--pdf-engine=weasyprint` (BSD, pip) | $0 | pandoc → LaTeX needs ~1GB TeX install; wkhtmltopdf deprecated (Qt4.8, no flexbox) — avoid | https://pandoc.org/ https://github.com/pandoc/pandoc-action-example http://www.pandoc.org/demo/example33/2.4-creating-a-pdf.html |
| Report: MD → PDF (headless Chrome) | `md2pdf` / md-to-pdf-cli (Playwright/Chromium) | $0 | One-time ~150MB Chromium download; WYSIWYG output (CJK, mermaid, math) | https://pypi.org/project/md-to-pdf-cli/ |
| Artifacts | `actions/upload-artifact` + download | $0 | Default retention 90 days; downloadable from Actions UI | https://docs.github.com/en/actions/reference/security/secure-use#artifacts https://github.com/actions/upload-artifact enterprise |

---

## 3. Secrets in CI

### What to do (encrypted, encrypted, least-privilege)

1. **Store in the Action's secret store, never in code.** Keys put under
   Organization > repo > environment scope (`secrets.API_KEY`); encrypted with
   Libsodium sealed boxes at rest, redacted from logs; limit 100 repo secrets,
   48 KB each, per GH docs.
2. **Cheapest privilege: keep `GITHUB_TOKEN` read-only by default** (`permissions:
   contents: read`), bump per job only when needed.
3. **Use environment secrets + required reviewers** for anything deployment-level.
4. **Mask non-secret-but-sensitive runtime values** with `::add-mask::`.
5. **Audit order:** never echo secrets; grep logs after tests; delete leaked logs
   and rotate the leaked secret (a `secrets` rotate is a manual task).

### What NOT to do (the classic burn list)

- ✋ **Hardcoding tokens in `env:` or the YAML** (plaintext in the repo = leaked).
- ✋ **Writing secrets into the cache path** — caches are readable by anyone with
  PR access to the repo (docs explicitly warn); cache contents are unsigned.
- ✋ **Committing `.env` files** or real secrets in `git-tracked` files (add
  `.env*` to `.gitignore`).
- ✋ **Passing secrets to forks/dependabot**: fork PRs don't receive secrets —
  test before relying on integrations.
- ✋ **Using self-hosted runners in public repos** — any PR `runner` download can
  compromise the host + all its secrets.
- ✋ **Storing structured secret blobs** (JSON/YAML/XML as one value) — breaks
  redaction matching / exact-match; use flat scalar secrets (and never inline).
- ✋ **Static secrets** — set 30–60-day rotation; GitHub audits rotation twice.

Sources: GitHub secure use reference, secret-types docs, blog on least-privilege.

---

## 4. Report generation — Markdown → HTML/PDF, free

Pipeline: `report.py` writes a Markdown file → one CLI call → PDF/HTML → upload
artifact + optional Telegram send.

### Easy paths (all free)

```bash
# HTML first (fast, diffable, hardware-safe)
pandoc report.md -o report.html --standalone --css theme.css

# PDF via WeasyPrint (BSD, no Chromium; needs libpango on some systems)
pandoc report.md -o report.pdf --pdf-engine=weasyprint

# PDF via headless Chromium (WYSIWYG, CJK/mermaid ok; runs with markdown-it/markdown)
uv tool install md-to-pdf-cli && md2pdf report.md -o reports/daily.pdf

# From Python (write once, reuse in report.py)
from weasyprint import HTML
HTML(string=html, base_url=".").write_pdf("daily.pdf")
```

In CI, pin headless tools with container steps; no browser installation needed:

```yaml
- name: Render PDF
  uses: docker://pandoc/core:3.8
  with:
    args: report.md -o reports/daily.pdf --pdf-engine=weasyprint
- uses: actions/upload-artifact@v4
  with: name: daily-report path: reports/daily.pdf
```

---

## 5. VectorBT — free / PRO facts, and the "v1 migration"

| Fact | Verdict |
|---|---|
| vectorbt community = free, Apache 2.0 + Commons Clause ("fair-code"); safe for private/retail use; can't sell products *primarily* it | ~ $0 forever |
| PRO: `$19/mo` (AlgoPlatforms) vs `$999/yr` (Pickuma report) — **no single official price surfaced in research → [NOT FOUND exact price]**; PRO ships via private GitHub repo + Discord | paid |
| v1.0.0 (Apr 22, 2026): Rust engine optional (`pip install vectorbt[rust]`), `engine="auto"` dispatch, dep groups `[full]`→`[full-no-talib]`; v1.1.0 (Jul 5, 2026): Python 3.14/pandas 3/Numpy 2.4 | 0.x→1.x = breaking changes; "vectorbt 2" does **not** exist — official migration doc:[NOT FOUND], use release notes only |

**Recommended for the pipeline:** pin `vectorbt>=1.0` (it's the active branch),
`pip install vectorbt[full-no-talib]` for the smallest Linux runner image, cache
pip via the actions/setup-python cache; Telegram notify built-in in later
vectorbt versions is possible but trivial to do yourself (`notify.py`).

---

## 6. EOD-cadence concretes (works, with the gotchas that matter)

```yaml
on:
  schedule:
    - cron: "15 20 * * 1-5"   # US 16:05 ET (EDT, ~Mar–Oct) — DST-free dual lines pattern from real repos
    - cron: "15 21 * * 1-5"   # US 16:05 ET (EST)
    - cron: "0 2 * * 2-6"     # overnight safety-net after EOD bars settle
```

- GitHub Actions = best-effort; offsets of 10–30 min at :00 are normal; script
  you want precision, schedule a few minutes past the quarter hour (15:17 style).
- 5-minute minimum; `*/2 * * * *` silently rejected at run time.
- Schedule runs consume free-tier minutes; a walk of 10 symbols × daily =
  ~1h / month — well under the 2,000-minute cap.
- 60-day inactivity disables; keep touching the repo or rely on any activity.
- Gate "market open" in code (script self-checks True NY time) rather than
  trusting the cron — patterns used by real quant workflows (mpi-update.yml).

---

## Sources (all URLS used)

(*) = primary source; others secondary.

- https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/running-variants-of-jobs-in-a-workflow (matrix docs)
- https://github.com/polakowo/vectorbt | https://www.pypi.org/project/vectorbt/
- https://github.com/polakowo/vectorbt/releases/tag/v1.0.0 (v1.0 release notes)
- https://vectorbt.pro/ (PRO membership model; private repo)
- https://algoplatforms.com/platforms/vectorbt (PRO "from $19/mo" claim)
- https://pickuma.com/for-investor/quantconnect-vs-backtrader-vs-vectorbt-which-to-start-2026/ ("Pro ~$999/yr")
- https://cronpreview.com/dialect/github-actions (UTC-only + min interval + peak delays)
- https://cronbuilder.dev/blog/github-actions-cron-schedule.html (UTC, 5-min, D storms)
- https://cronwizard.com/github-actions-cron (synergy; timezone property now supported; 5-min minimum)
- https://github.com/aztmm-d/aztmm-mpi-data/blob/a18ec8c9848c143443e4e2b1a8dcc7097373d4.5? (regular example: dual EST/EDT lines + safety-net) — used as pattern reference
- https://finance.yahoo.com — market-hours frames referenced by finmap workflow (see below)
- https://github.com/finmap-org/data-us-actions/blob/main/.github/workflows/fetch-marketdaq.yaml (UTC session times comments; schedule `0 0-6 * * 2-6`)
- https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching (caching + security notes)
- https://github.com/actions/cache (restore-only `actions/cache/restore`, key/hash files)
- https://docs.github.com/en/actions/reference/security/secure-use (secrets; no plaintext; add-mask; audit/rotate; no self-hosted public)
- https://docs.github.com/en/rest/apps/... "Secret types" — Libsodium; limits; dependabot-secrets distinction
- https://github.blog/security/application-security/implementing-least-privilege-for-secrets-in-github-actions/ (least privilege for GITHUB_TOKEN)
- https://core.telegram.org/bots/api | https://core.telegram.org/bots (BotFather, token = full control)
- https://dev.to/apollo_ag/the-fastest-way-to-build-a-telegram-bot-natively-3pd (sendMessage pattern, 30 msg/s cap, webhook notes)
- https://dev.to/clapnea/push-notifications-from-server-with-telegram-bot-api-32b3 (getUpdates/get chat_id; sendMessage code)
- https://github.com/agronholm/apscheduler | https://www.pypi.org/project/APScheduler/ (trigger types; store; not a daemon)
- https://andrewconl.in/til/running-python-in-cron-in-docker/ (cron-in-Docker PYTHONPATH/user/full-path gotchas)
- https://dev.to/ulnit/how-i-built-a-raspberry-pi-automation-lab-that-runs-itself-8am (Pi + Docker + cron + ntfy; scale decision)
- https://mdkit.io/blog/markdown-to-pdf-guide (walker comparison; pandoc decisions)
- https://www.pandoc.org/demo/example33/2.4-creating-a-pdf.html | https://github.com/pandoc/pandoc-action-example (CI pandoc usage)
- https://pypi.org/project/md-to-pdf-cli/ (md2pdf; Chromium one-time dl, CJK/mermaid/math)
- https://docs.makeprint... (Markprint / weasyprint-based MD→PDF mention)
- https://github.com/polakowo/vectorbt/releases (Telegram v20 compat in later v1.x)

### [NOT FOUND]

- Official single published VectorBT PRO price (sources say from $19/mo and ~$999/yr — treat as "paid, price varies").
- Dormant/archived "vectorbt 2" release notes — a v2 does not exist; the migration event is v0.28 → v1.0.0.
- A first-party "safe secrets in Actions" doc beyond the above (the two GH docs are formal; all others are patterns).
- wkhtmltopdf as a recommended engine in 2026 (deprecated; do not start projects on it).

---

*Compliance: no installs executed; single write: `web-research/paper-pipeline-infra.md`.*