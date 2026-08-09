# OpenCode / OpenClaw / Claude Skills: Best Practices 2026

**As of:** 2026-08-09 · **Method:** primary-source web research (official docs fetched directly + search-verified snippets). Only URLs that were reachable or returned content on the research date are listed; none are guessed. Sources are marked [OFFICIAL] or [COMMUNITY] in the Resources section and cited inline.

---

## TL;DR

- A skill is **one directory per skill** containing `SKILL.md` (YAML frontmatter + Markdown body) plus optional `scripts/`, `references/`, `assets/`. This is the now-standardized **Agent Skills** format, cross-compatible between OpenCode, Claude Code, OpenClaw, Codex, Gemini CLI, Copilot, Cursor, etc. ([agentskills.io](https://agentskills.io/), [opencode docs](https://opencode.ai/docs/skills/), [OpenClaw docs](https://docs.openclaw.ai/tools/skills)).
- **Only two frontmatter fields matter for tool-selection:** `name` and `description`. Everything else is metadata. The `description` is the *entire trigger surface* — "what it does **and when to use it**", ~1–3 sentences with concrete trigger words.
- **Loading is progressive, in three levels:** Level 1 = frontmatter (≈100 tokens/skill, always in the skill listing); Level 2 = SKILL.md body (loaded on activation; keep <500 lines); Level 3 = `references/`/`scripts/`/`assets/` (loaded only on demand). This is why "50 installed skills ≈ almost free".
- **Evidence (SkillsBench, Feb 2026):** curated, well-written skills measurably improve agent task success; **self-generated skills produce no benefit**; step-by-step instructions with a working example beat sprawling docs; measure skill value with paired with/without evals, not vibes.
- **Most common failure is overloading:** too-long SKILL.md, vague descriptions ("helps with documents"), skills that teach behavior instead of procedure, and deep reference chains agents refuse to fully read.

---

## 1. Canonical skill anatomy

### 1.1 The three loading levels (progressive disclosure)

This is the core design principle of the format — it exists to keep the context window lean.

| Level | What it contains | Loaded when | Approx. cost | Authoring rule |
|---|---|---|---|---|
| **Level 1** | `name` + `description` from YAML frontmatter | At session start, for **every** installed skill (injected into the `skill` tool description / available-skills listing) | ~100 tokens per installed skill | This is the trigger surface. Optimize discoverability; nothing else matters for whether your skill gets picked |
| **Level 2** | Full `SKILL.md` body (procedures, checklist, links) | Only when the agent activates the skill for the current task | Once loaded, **stays in context for the session** in Claude Code ([skills docs](https://code.claude.com/docs/en/skills)) | Keep it as the "brain": navigation + high-level procedure, <500 lines / <5,000 tokens |
| **Level 3** | Everything else: `references/*.md`, `scripts/*`, `assets/*`, `templates/*` | On demand, only when the agent reads or runs the file | Zero until touched; scripts execute via bash and only their output enters context | Link **directly from SKILL.md**, one level deep only |

Sources: [Agent Skills spec](https://agentskills.io/specification) ("Metadata ~100 tokens… Instructions <5000 tokens recommended… Resources as needed"), [Anthropic engineering blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) ("no practical limit on bundled content"), [Claude platform best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), community breakdowns ([dayfing.dev](https://www.dayfing.dev/blog/claude-agent-skills), [duet.so](https://duet.so/guides/claude-code-skills-complete-guide): "a skill costs about 100 tokens of context until it's needed → fifty skills installed, pay almost nothing").

### 1.2 Canonical frontmatter fields

The Agent Skills standard ([spec](https://agentskills.io/specification)) — implemented by OpenCode, Claude Code, OpenClaw, Pi, and 30+ other harnesses:

| Field | Required | Constraint (agentskills.io) | Behavior |
|---|---|---|---|
| `name` | Yes | ≤64 chars; `^[a-z0-9]+(-[a-z0-9]+)*$`; must match the parent directory name | Identifier, slash-command name |
| `description` | Yes | 1–1024 chars, non-empty, **what the skill does + when to use it** | The trigger; shown in the skill listing |
| `license` | No | License name or bundled license file reference | Portability only (Claude Code "accepts but does not act on it"; OpenCode V1 ignores unknown fields) |
| `compatibility` | No | ≤500 chars; environment requirements (product, system packages, network) | Portability metadata |
| `metadata` | No | string→string map | Reserved for client extensions (e.g. `metadata.openclaw` gating, `metadata.opencode/slash`) |
| `allowed-tools` | No | Space-separated pre-approved tools | **Experimental**; support varies by harness |

**[OFFICIAL] OpenCode specifics** ([opencode.ai/docs/skills](https://opencode.ai/docs/skills/)): recognizes exactly `name`, `description`, `license`, `compatibility`, `metadata`; **unknown fields are ignored** (a cross-platform hazard, see §2.7); `name` must match its folder (`^[a-z0-9]+(-[a-z0-9]+)*$`); `description` 1–1024 chars — "Keep it specific enough for the agent to choose correctly." Discovery roots: `.opencode/skills/<name>/SKILL.md`, `~/.config/opencode/skills/`, plus Claude-compatible `(``.claude`/`~/.claude`) and agent-compatible (`.agents`/`~/.agents`) paths. Newer V2 docs ([opencode.ai/v2/docs/skills](https://opencode.ai/v2/docs/skills)) add `slash`, `metadata.opencode/slash`, `metadata.opencode/autoinvoke`, HTTP catalogs, and relax the name-regex enforcement — bleeding edge, beware.

**[OFFICIAL] Claude Code / Claude platform specifics** ([code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills), [best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)): extends with `when_to_use` (extra trigger context, shares a 1,536-char cap with `description`), `disable-model-invocation` (human-invocable only), `user-invocable`, `allowed-tools`, `context: fork` / `agent`, `model`, `effort`, `paths` (auto-activate by file glob), `argument-hint`/`arguments`, `hooks`, `shell` ([community field map, 15-20 fields](https://github.com/shanraisshan/claude-code-best-practice/blob/main/best-practice/claude-skills.md)).

**[OFFICIAL] OpenClaw specifics** ([docs.openclaw.ai/tools/creating-skills](https://docs.openclaw.ai/tools/creating-skills)): `name` (required slug) + `description` (required; **keep one line, <160 chars** — shown to the agent and in slash-command discovery); optional `user-invocable`, `disable-model-invocation`, `command-dispatch`/`command-tool`/`command-arg-mode`, `homepage`; gates via `metadata.openclaw.requires.{bins,anyBins,env,config}`, `os`, `always`. `{baseDir}` placeholder resolves to the skill's own directory.

Attempt to **portability smock-check**: OpenClaw (supports the full Agent Skills), Pi ([pi.dev/docs/latest/skills](https://pi.dev/docs/latest/skills)) implementing the [standard](https://agentskills.io/specification) warns on violations but stays lenient.

### 1.3 Directory layout

The spec recommends:

```
skill-name/
├── SKILL.md          # Required: metadata + core instructions (<500 lines)
├── scripts/          # Executable code as tiny CLIs (deterministic steps)
├── references/       # Docs read on demand (cheatsheets, API refs, domain logic)
├── assets/           # Templates, schemas, static resources
└── templates/, examples/   # optional
```

Rules that recur across all sources:
- **`SKILL.md` is the hub** — file index + primary procedure. *"Keep SKILL.md under 500 lines; move detail to separate files"* ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [mgechev](https://github.com/mgechev/skills-best-practices)).
- **References stay one level deep** — "Keep references one level deep from SKILL.md… Claude may partially read files (e.g. `head -100`) when nested" ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)); [spec](https://agentskills.io/specification) is explicit: "Avoid deeply nested reference chains".
- **Reference >100 lines → add a table of contents** at top so partial preview reads still reveal scope ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)).
- **Explicit on-demand instructions** — tell the agent when to read a file: *"See `references/auth-flow.md` for error codes"* — JiT loading ([mgechev](https://github.com/mgechev/skills-best-practices)).
- **Relative paths, forward slashes, on every OS** ([mgechev](https://github.com/mgechev/skills-best-practices)).
- **No doc-files for humans** in the skill dir (README/CHANGELOG) — "skills are for agents, not humans" ([mgechev](https://github.com/mgechev/skills-best-practices)).

### 1.4 Description phrasing that reliably triggers tool-selection

The description is the trigger. All official guidance converges on the same shape:

1. **[Capability] + [when] + [explicit trigger words]** — *"Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. **Use when** working with PDF documents **or when the user mentions** PDFs, forms, or document extraction."* (good example in the official [spec](https://agentskills.io/specification)).
2. **Include concrete user-intent verbs** ("create", "review", "Delegates", "Use when", "Do NOT use for…") plus feature — see the production `opencode-jules` skill in this workspace: *"Delegates any coding task to Jules… **Use when** the user says /opencode-jules, or asks to delegate work, send to Jules, background task, review PR, implement feature, fix bug via Jules."*
3. **Exclusion clauses reduce false positives saturations**: *"Do not use for model training or evaluation tasks."* (HF open with a distractor domain).
4. **Keep 1–3 adjacent tasks per skill**; if the description needs an "and also…" list beyond that, split the skill (community consensus, see [skywork guide](https://skywork.ai/blog/ai-bot/claude-code-agent-skills-ultimate-guide)).
5. Anti-examples the docs name explicitly: *"Helps with PDFs."*, *"Processes data."*, *"Does stuff with files."* — never trigger, or trigger everywhere ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [spec](https://agentskills.io/specification)).
6. In Claude Code, this field is the only thing in the listing that counts toward the tool-selection decision — an **A/B-testable unit**; track missed/false triggers ([skywork](https://skywork.ai/blog/ai-bot/claude-code-agent-skills-ultimate-guide)).

## 2. Least-best practices — the common overloading mistakes (with evidence)

1. **Overbroad, trigger-everywhere descriptions.** "Helps with documents" activates in impossible contexts. → Narrow purpose, add explicit triggers, split ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [skywork](https://skywork.ai/blog/ai-bot/claude-code-agent-skills-ultimate-guide)).
2. **Monolithic "do-everything" SKILL.md.** >500 lines = recurring token cost every session it stays loaded; refactor into composable skills ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [mgechev](https://github.com/mgechev/skills-best-practices)).
3. **Deep/nested reference chains.** Agents half-read (e.g. `head -100`) instead of loading; keep one level deep, add ToC to long files ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [spec](https://agentskills.io/specification)).
4. **Teaching behavior instead of procedure.** Say *what to do* rather than narrating why/how; SKILL.md is a Procedure/SOP, not an essay ([code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills): "Once loaded, every line is a recurring token cost — state what to do rather than narrating how or why").
5. **Writing for humans, not agents.** Ship README/CHANGELOG/install guides inside the skill dir; keep only agent-facing files ([mgechev](https://github.com/mgechev/skills-best-practices)).
6. **Assuming tools/packages exist.** Skills break when deps are missing; document installs and environment requirements in `compatibility` + body ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)).
7. **Platform-specific frontmatter leaking into shared skills.** OpenCode ignores unknown fields; OpenClaw reads its own metadata keys. A skill with Claude-only fields silently degrades elsewhere — keep frontmatter to the spec: `name`, `description`, `license`, `compatibility`, `metadata` (this repo's own OpenClaw skills body demonstrated the same pattern reversal: openclaw AI replacing its own requirements; cite [opencode docs](https://opencode.ai/docs/skills/) "unknown fields are ignored").
8. **Skill over-trash (chain with no I/O contract).** Chained skills that don't document expected inputs/outputs produce brittle handoffs ([skywork](https://skywork.ai/blog/ai-bot/claude-code-agent-skills-ultimate-guide)).
9. **Security sloppiness.** Skills are code the agent may execute; Anthropic explicitly warns to audit skills and watch for exfiltration/удаленные network calls ([equipping blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)); OpenClaw community guidance: no `curl | bash`, no credential access, least-privilege, document external dependencies, test `--sandbox` ([clawdocs](https://clawdocs.org/guides/skill-development)).
10. **Self-generated skills as a substitute for curation.** SkillsBench found self-generated skills give **"no performance benefit"** vs curated ones; and skills can hurt when over-complex (variance across models) ([SkillsBench arXiv](https://arxiv.org/abs/2602.12670), [ai-tower write-up](https://ai-tower.io/skillsbench-benchmark-agent-skills-llm-performance/)).
11. **Never testing with different models.** Skills are add-ons — Haiku needs more guidance, Opus reads over-explaining; test across the models you'll actually use ([Claude best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)).
12. **Skill sprawl without governance.** Track skills in version control; gate new skill drafts through review (OpenClaw's Skill Workshop is a model: propose → inspect → evaluate → apply, [docs.openclaw.ai/tools/skill-workshop](https://docs.openclaw.ai/tools/creating-skills)); Anthropic benchmarks the value of every skill (SkillsBench paradigm).
13. **No way to measure value.** Paired A/B evals (with/without the skill) beat intuition; SkillsBench (87 tasks, deterministic verifiers) exists precisely to make skill efficacy measurable ([skillsbench.ai](https://www.skillsbench.ai/)).

## 3. Copy-able templates

All three follow §1 anatomy: portable frontmatter, <500-line body, one-level references, "Use when" triggers, do/don't lists. Drop them into `.opencode/skills/<name>/SKILL.md` (or `~/.claude/skills/`, `~/.openclaw/workspace/skills/`) and edit.

### Template A — research skill

```
research/
├── SKILL.md
└── references/
    └── source-ladder.md
```

```markdown
---
name: research
description: Investigate a question against high-trust primary sources and write the
  findings to a single Markdown file with citations. Use when the user says "research
  X", "how does X work", "gather docs/API facts", or asks for web research into a file.
  Do NOT use for code implementation or quick single-fact answers that need no citation.
license: MIT
compatibility: Requires web/search tool access and the markdown write tool
---

# Research (to a file)

Procedural knowledge for turning a question into a cited findings document the
user can keep or hand to another agent.

## When to use me
- "Web-research X → one .md file"
- "Research the docs for <tool>, cite sources"
- Reading legwork delegation ("find the authoritative answer")

## Procedure
1. Clarify the question and the ONE output file path before researching. If the
   user did not name a file, propose one (e.g. `web-research/<topic>.md`).
2. Prefer primary sources: official vendor docs, specs, source code, first-party
   write-ups. Follow each claim back to the page that owns it (see
   `references/source-ladder.md` for ordering).
3. Web-search per top-level question; then fetch the best 2-5 pages per open
   question (webfetch) and read the exact sections that carry the claim.
4. Answer directly, then write the file: structured Markdown with a
   "## As of <date>" line, [OFFICIAL]/[COMMUNITY] tags on the resource list,
   and an inline link per verifiable claim.
5. Never fill gaps: mark unverified claims as UNVERIFIED; do not invent URLs.
6. Only one file by default — no side files unless the user asked for them.

## Output contract
- Location: the single agreed path (default `<cwd>/web-research/<slug>.md`)
- Structure: TL;DR → findings by question → templates/examples → resources
- Every URL must have been checked during this session

## Don't
- Don't keep research in chat-only; persist it.
- Don't use the "services list" that contradicts the forced sources in the prompt.
- Don't write second-hand summaries when the primary source is reachable.
```

`references/source-ladder.md` (Level 3):

```markdown
# Source ladder (read on demand)

Order of preference for claims:
1. Official vendor docs / spec text (agentskills.io, opencode.ai/docs, code.claude.com/docs)
2. Vendor engineering blogs + official repos (anthropics/skills, anomalyco/opencode)
3. Peer-reviewed/academic (arXiv) and benchmark sites (skillsbench.ai)
4. Reputable community guides and field-exercised configs (shipped skills of
   notable repos: supabase/agent-skills, microsoft/agent-skills, huggingface/upskill)
Mark each resource [OFFICIAL] or [COMMUNITY] in the output.
```

### Template B — risk-tool skill (fail-closed preflight gate)

```markdown
---
name: risk-gate
description: Preflight-gate risky commands (rm -rf, force-push, bulk deletes, credential
  updates, production migrations). Use when the user asks to run a destructive or
  irreversible action, or when a command could touch shared state, network, money,
  or credentials. Blocks execution on any failed check; dry-run by default.
compatibility: Requires the command to exist in PATH and network access only if the
  gated command needs it
---

# Risk gate — fail-closed preflight

Any action that can cause irreversible harm gets these checks BEFORE executing.

## Gate procedure
1. RESOLVE the exact command + its blast radius (files, accounts, targets).
2. RUN all applicable checks; every FAIL === hard block:
   | Check | Pass when |
   | --- | --- |
   | Dry-run exists | produced a dry-run output equal to intent |
   | Target bounded | paths/scope matched the user's explicit request |
   | Reversible | backup/stash/PR-trestle or documented rollback exists |
   | Auth scoped | uses only necessary permissions; no extra secrets |
   | Consent | user confirmed at least once after seeing the scope |
3. If ALL pass, execute; then report `OK <sha/baseline that can be rolled back>`.
4. On ANY fail: stop, report the failing check, propose the safe path.

## Rationalizations the agent MUST defeat
- "It's just one file" — one file can be a source of truth.
- "It's a script I wrote, I know what it does" — the gate is the process, not belief.
- "We will fix it after" — no fresh-rollback plan = no execution.

## When the gate itself is blocked
Escalate to the user as a decision, never quietly skip the gate.
```

### Template C — jules-delegation skill (async background delegation)

Modeled on the production `opencode-jules` skill (verified in this workspace; keeps Level 1/2/3 discipline, an explicit trigger list, a lifecycle procedure — not a prose description).

```markdown
---
name: delegate-to-jules
description: Delegate coding work to Jules (Google's background AI coding agent) that
  runs async on GitHub: PR reviews, feature implement, bug fixes. Use when the user says
  "delegate / send to Jules / background task / review PR / implement issue N / fix bug
  via background agent". Determines review vs feature mode and drives the session
  lifecycle (create → poll → report → cleanup).
compatibility: Requires JULES_API_KEY, jules_* tools (or the opencode-jules plugin), and gh CLI
---

# Delegate to Jules (async)

Jules works on its own branch and returns a PR; this skill owns the handoff
(session scoping, prompt quality, progress reporting). One session per task.

## Workflow
1. GATHER: PR → `gh pr view <n>`; issue → `gh issue view <n>` (capture acceptance
   criteria); else capture user words verbatim + known context.
2. CLASSIFY: review/audit/check/PR → **review mode**; implement/fix/build/add/#n →
   **feature mode**.
3. BUILD THE PROMPT (use these shapes, expand with the real content):
   - review: "Review <branch> vs base. Check: logic bugs, security (tokens,
     input validation), missing tests, type safety, conventions, duplicate/extractable
     code, concurrency, error handling. Give file:line findings."
   - feature: "Implement <issue/user content>. Follow repo conventions for style,
     tests, branch naming. Include tests."
4. SOURCE: `jules_list_sources` → pick repo (or JULES_SOURCE); get branches via
   `jules_get_source`; base branch default.
5. CREATE: `jules_create({prompt, source, branch, title, automationMode:
   AUTO_CREATE_PR})`. NEVER idle-wait inline; report session id and return control.
6. FOLLOW-UP (user asks "how is it going"): `jules_status({sessionId})` → progress,
   plan steps, PR URL. Feedback: `jules_message`; plan approval: `jules_approve`;
   artifacts: `jules_activity`; cancel: `jules_delete(sessionId)`.
7. VERIFY before claiming done: a PR URL exists (or the failure reason), and
   the user's acceptance criteria map to real artifacts.

## Do NOT
- Do NOT duplicate the work locally while Jules runs.
- Do NOT start a session without a source/repo resolved.
- Do NOT pass credentials inside the prompt; keep them in env.
- Do NOT say "done" on an unfinished session — state status + session ID.
```

## 4. Resources

All URLs verified on 2026-08-09. "As of date" caveat: 2026-08-09.

### Official docs & specs

| Name | URL | What it teaches | Tag |
|---|---|---|---|
| Agent Skills (open standard) | <https://agentskills.io/> + `/specification` | Canonical format: frontmatter constraints, progressive disclosure (3 levels), `scripts`/`references`/`assets`, validation via skills-ref. **Read this first.** | [OFFICIAL] Anthropic |
| Agent Skills — Anthropic engineering blog | <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills> | The design pattern & rationale: why SKILL.md folders, how loading works, security & trust guidance, "start with evaluation / structure for scale" | [OFFICIAL] |
| Agent Skills — announcement | <https://claude.com/blog/skills> | What skills are for; where they exist (Claude apps, Code, API) | [OFFICIAL] |
| Claude Code skills docs | <https://code.claude.com/docs/en/skills> | SKILL.md body lifecycle ("stays in context"), full frontmatter reference incl. `context: fork`, hooks | [OFFICIAL] |
| Claude platform — agent-skills best practices | <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices> | The definitive authoring guide: description anti-examples, 500-line cap, one-level refs, ToC, test per model | [OFFICIAL] |
| Claude platform — agent skills overview | <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview> | How skills work; metadata pre-loaded, on-demand reads | [OFFICIAL] |
| anthropics/skills (official repo) | <https://github.com/anthropics/skills> | Reference implementation + skill collections (docx/pdf/xlsx, web dev); `spec/` folder | [OFFICIAL] |
| OpenCode docs — Agent Skills | <https://opencode.ai/docs/skills/> | OpenCode's SKILL.md contract (name/description/license/compatibility/metadata), discovery roots, permissions allow/deny/ask, hidden V2 fields | [OFFICIAL] anomalyco/opencode |
| OpenCode V2 skills docs | <https://opencode.ai/v2/docs/skills> | Bleeding-edge: slash metadata, HTTP catalogs, autoinvoke flags | [OFFICIAL] |
| OpenClaw docs — Skills | <https://docs.openclaw.ai/tools/skills> | Skill roots, loading order, AgentSkills compatibility, ClawHub | [OFFICIAL] |
| OpenClaw docs — Creating skills | <https://docs.openclaw.ai/tools/creating-skills> | Step-by-step authoring, description ≤160 chars advice, gating, publishing | [OFFICIAL] |
| Pi docs — Skills | <https://pi.dev/docs/latest/skills> | Lenient AgentSkills implementer: loading order, `~/.pi/`, using skills from other harnesses, collision rules | [OFFICIAL] (vendor) |

### Benchmarks & evaluation

| Name | URL | What it teaches | Tag |
|---|---|---|---|
| SkillsBench | <https://www.skillsbench.ai/> · paper <https://arxiv.org/abs/2602.12670> · data `benchflow-ai/skillsbench` | Curated vs self-generated vs no-skills, 84–87 tasks; curated wins, self-generated flat; harness matters | [COMMUNITY] research |
| huggingface/upskill | <https://github.com/huggingface/upskill> | Generate + evaluate agent skills (Claude Code/OpenCode/Codex) | [COMMUNITY] HF org |
| Anthropic — Demystifying evals for agents | <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents> | Eval discipline that skill testing should adopt | [OFFICIAL] |

### Ecosystem / tooling / community

| Name | URL | What it teaches | Tag |
|---|---|---|---|
| Superpowers | <https://github.com/obra/superpowers> | Full methodology of auto-triggering skills: brainstorming→plan→execute→review, `description` = trigger, mandatory-skills protocol, eval-driven skill quality | [COMMUNITY] |
| mgechev/skills-best-practices | <https://github.com/mgechev/skills-best-practices> | Engineering-grade authoring rules (structure, 1-level refs, JiT load, no human docs) — the short checklist | [COMMUNITY] |
| skills CLI (`npx skills`) | <https://github.com/vercel-labs/skills> | npm-style skill package manager; GitHub-as-registry; cross-harness install paths; lock file | [COMMUNITY] |
| OpenClaw community skill guide | <https://clawdocs.org/guides/skill-development> | Do/Don't security bank: sandbox, `curl|bash` bans, supply-chain awareness, token cost | [COMMUNITY] |
| Claude Code skills frontmatter cheat-sheet | <https://github.com/shanraisshan/claude-code-best-practice/blob/main/best-practice/claude-skills.md> | Full enumerated frontmatter (15-20 fields) with monthly-changed default values | [COMMUNITY] |
| duet.so complete guide | <https://duet.so/guides/claude-code-skills-complete-guide> | Skill vs MCP vs subagents decision matrix; skill anatomy; costs | [COMMUNITY] |
| dayfing "how to build one" | <https://www.dayfing.dev/blog/claude-agent-skills> | Progressive-disclosure table; where skills run; common mistakes | [COMMUNITY] |
| skills marketplaces | <https://skillsmp.com/>, <https://skills.sh/> | Browsable skill indexes w/ installation prompts (npx/ClawHub) | [COMMUNITY] |

### Community channels

| Name | URL | What it teaches | Tag |
|---|---|---|---|
| r/ClaudeAI — Anthropic best-practices thread | <https://www.reddit.com/r/ClaudeAI/comments/1k5slll/anthropics_guide_to_claude_code_best_practices/> | Practitioner discussion of Claude Code skills/Best practices | [COMMUNITY] |

*Note: no dedicated high-quality r/artificial-intelligence "agent skills" thread surfaced in the research window; the strongest Reddit discussion lives in r/ClaudeAI. Only verified URLs are listed.*

---

## Final word

The 2026 stack is **one file, three levels, one trigger field**. `SKILL.md` + frontmatter is the unit; `description` is the only thing standing between your skill and oblivion; Level 3 (files) is where depth lives without a token tax; subject the whole thing to paired evals and peer review before you trust it — [SkillsBench has the numbers](https://arxiv.org/abs/2602.12670): curated > nothing > self-generated.