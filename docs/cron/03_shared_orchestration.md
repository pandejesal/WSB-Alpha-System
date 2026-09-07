# Spark Scheduled Task 3 — Tracker Digest & Notify

Run thrice daily: 06:30, 14:30, 22:30 UTC (30 minutes after Tasks 1 and 2,
so their entries are in before this reads).
Tracker Doc ID: 1Q6eRu71t8uSio6wQQDQZZmGLtwUfe6FCBBIF9VefqWs (read-only for
this task — Sections 1 and 2 belong to Tasks 1 and 2).
Environment: Google Spark web app. Google Docs read + Gmail send only.

Use these Skills (invoke with /): /wsb-alpha-universe-context
/trackerhygiene. Full detail is repeated inline here so this Task works even
if a Skill fails to load.

---

## 1. What this task does

After the two discovery runs land, check whether anything new appeared today
and tell me. This is the only task that emails me. It never edits the Doc.

---

## 2. Procedure (every run)

Step 1: Open the tracker Doc. Read Section 1 ("1. Relevant GitHub
Repositories & Tools") and Section 2 ("2. Quantitative Research, Papers &
Strategies"). Collect entries whose timestamp headers show today's date
(YYYY-MM-DD in UTC).

Step 2: If NO entries are dated today: stop. No email, no Doc edit, no
output beyond the run log. Stay silent — an empty digest is noise.

Step 3: If new entries exist, build the digest:

  WSB Alpha Tracker Digest — [YYYY-MM-DD]
  New repos (N): [owner/repo] — Verdict — one-line why it matters.
  New papers/datasets (N): [Title] — Verdict — key number (e.g. 1.2%/mo,
  t=4.3, half-life 3.2d).
  Needs laptop follow-up:
    - [Adopt/Implement items] -> Jules PR with the exact module change.
    - [Evaluate/Prototype items] -> Prime evolution hunt.
    - [Monitor/Archive items] -> logged, revisit in 90 days.
  Nothing in this digest is a trading instruction. All strategy changes must
  still pass the laptop-side gate (Sharpe>=0.8, DD<=35%, OOS>=0.5, trips>=10,
  paper only, never auto-live).

Step 4: Email the digest to me via Gmail with subject exactly:
"WSB Alpha Tracker Digest YYYY-MM-DD" (today's date). Body = the digest.
If a digest with today's subject was already sent (e.g. an earlier run today
already emailed), append only the NEW-since-last-email items with subject
"WSB Alpha Tracker Digest YYYY-MM-DD (update N)" — never resend the full day.

---

## 3. Rules (per /trackerhygiene)

Read-only on the Doc: never insert, edit, or delete section content. Dedup
is owned by Tasks 1 and 2; if you spot a duplicate they missed, note it in
the digest under "Hygiene flags" instead of editing. Every verdict and module
path you quote must be copied exactly from the entry — never invent numbers
or verdicts. Timestamps in YYYY-MM-DD HH:MM UTC. If the Doc cannot be opened
(a permissions or outage failure), send one Gmail with subject "WSB Alpha
Tracker Digest YYYY-MM-DD (ERROR)" describing the failure — that is the only
case where an email goes out with zero new entries.
