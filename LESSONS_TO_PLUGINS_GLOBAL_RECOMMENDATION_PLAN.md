# Lessons to Plugins Global Recommendation Plan

> **Study + planning only.** This document is read-only analysis. No plugin was created, renamed, or edited to produce it. The only file written under `plugins/` is this report.
>
> **Inputs:** `C:\Users\ahmed\.claude\LESSONS.md` (2,040 lines) and every plugin under `C:\MY-WorkSpace\claude_plugins\plugins`.
> **Method:** a 21-agent analysis workflow — 10 agents performed a live structural inventory of every plugin, then 11 agents mapped each LESSONS.md line-range chunk to a plugin destination with a 5-axis grade, using the live plugin catalog as context. Aggregation, de-duplication, priority scoring, and the data tables (§2, §3, §4, §9, §10) are script-generated for accuracy; the analysis and recommendations (§1, §5–§8, §11–§12) are authored.
> **Naming update applied throughout:** the planned `react-admin-kit` plugin is now **`react-kit`** — reusable React/Next.js patterns generally (admin panels remain one capability inside it, not the whole scope).
>
> **How to read a "destination":** an existing plugin folder (`devops-plugin`, `odoo-plugin`, `rag-plugin`, `paper-plugin`, `ntfy-plugin`, `pandoc-plugin`, `remotion-plugin`); a planned plugin (`react-kit`, `qa-browser`, `docs-wiki` — scaffolds already exist as `react-admin-kit-plugin`/`qa-browser-plugin`/`docs-wiki-plugin`); `future:<name>` (a new plugin justified only if the pattern recurs); `wiki-sop` (belongs in a project Wiki/SOP, not a plugin); `memory-sync-rule` (a future Wiki→memory sync rule); or `no-action` (project-specific, one-off, or better handled by CI/tests).

---

## 1. Executive summary

The lessons file is overwhelmingly an **engineering-discipline and environment-debugging** corpus, not a feature corpus. The two biggest clusters are *AI-agent workflow* (30 lessons) and *Windows/WSL/Claude-Code environment* (23), followed by *security/RBAC/auth* (19) and *DevOps/deployment* (15). That shape drives the headline conclusion: the single highest-value move is **not** a new feature plugin — it is hardening the verification, environment, and review disciplines that already cut across every project.

### By the numbers

| Metric | Count |
|---|---|
| Distinct lessons/sub-lessons analyzed | **183** (extracted from ~110 LESSONS.md headings; independently-actionable sub-bullets counted separately) |
| Existing plugins inspected | **10** |
| Plugin-actionable lessons | **125** (68%) |
| → map to an existing marketplace plugin | **30** (devops 11, odoo 12, rag 6, paper 1; ntfy/pandoc/remotion **0**) |
| → map to the `claude-plugin-builder` meta-skill | 1 |
| → map to a planned plugin | **56** (react-kit 32, qa-browser 15, docs-wiki 9) |
| → justify a future plugin | **38** (claude-env-doctor 18 is the standout) |
| SOP/Wiki-only | **20** |
| Future Wiki→memory sync rule | **1** |
| Project-specific / one-off / no-action | **37** |
| Risk profile | Critical 8 · High 35 · Medium 78 · Low 62 |
| Priority profile | P0 8 · P1 49 · P2 63 · P3 63 |

### What the distribution tells us

- **`react-kit` is the heaviest single destination (32 lessons)** — but ~20 of those are *React-quality / lint-triage / React-19-migration* lessons (the React Doctor passes), and only a handful are genuine UI-architecture patterns. react-kit should therefore lead with a **lint/finding-triage discipline** and a **React-19 migration reference**, with admin-panel scaffolding as a secondary capability — exactly why the rename off `react-admin-kit` matters.
- **`qa-browser` is the highest-*quality* destination (15 lessons, and it owns 7 of the top-10 by score).** The browser-QA plugin is where the security-verification lessons land: trust the auth API over UI labels, read 403-vs-400/409 to prove an RBAC change, route-scope auth headers to dodge CORS, treat client-rendered codes as non-authenticating. This is the most concentrated risk-reduction opportunity in the whole corpus.
- **A new `claude-env-doctor` plugin is strongly justified (18 lessons)** — the Windows/WSL/MCP/Claude-Code environment cluster (WSL DNS, HCS timeouts, `~/.claude.json` quirks, the 401 login loop, LSP npm-shim spawn failures, Playwright chrome-vs-chromium, Railway CLI version) has no natural home today and recurs across machines.
- **Three mature plugins absorb well:** `odoo-plugin` (12 — i18n/PO workflow, theme load, volume drift, Postgres pinning), `devops-plugin` (11 — GitHub-side hardening, permission-first writes, identity auto-switch, work-item semantics), `rag-plugin` (6 — MCP wiring / `~/.claude.json` truths).
- **Three plugins get zero lesson-driven work:** `ntfy-plugin`, `pandoc-plugin`, `remotion-plugin`. This is an honest finding — the corpus simply contains no notification, document-conversion, or video lessons. Their inventory gaps are real but out of scope for a *lessons-driven* plan; see §5 and §7.
- **58 lessons (32%) should stay out of the plugin layer** — they are Aqraboon/Royal-Preps/Odoo-client business specifics or one-off environment incidents. The generic pattern was still extracted for each so a future plugin can absorb it if it recurs in a second project.

### Top 10 highest-impact recommendations

| # | Recommendation | Destination | Artifact | Score / Prio |
|---|---|---|:--:|:--:|
| 1 | **Three-layer RBAC verification** (route guard ≠ UI gate ≠ service guard; dev-OTP bypass awareness) as a QA checklist | qa-browser | checklist | 18 / P0 |
| 2 | **Guard-hygiene rule**: lowercase/canonicalize host before any allow/deny match; treat `*prod*` substring guards as unsafe | qa-browser (+devops) | hook | 18 / P0 |
| 3 | **Trust the auth API over UI labels** when verifying logged-in identity in browser QA | qa-browser | skill | 17 / P1 |
| 4 | **Read 403-vs-400/409 to prove an RBAC change** on disposable data without crafting a destructive payload | qa-browser | skill | 17 / P0 |
| 5 | **Lint/finding-triage discipline**: classify every analyzer finding as safe-mechanical / needs-judgment / false-positive / forbidden-zone before touching code | react-kit | skill | 17 / P0 |
| 6 | **Security source-to-sink review** (tainted input → sink → mitigation at each hop → sibling-route parity → control-replacement check) | qa-browser | skill | 16 / P0 |
| 7 | **Host-scope auth/bypass headers** in browser automation to avoid CORS-killing every data call | qa-browser | skill | 16 / P0 |
| 8 | **SHA-pin third-party GitHub Actions**; an `environment:` block is not an approval gate | devops-plugin | hook | 15 / P0 |
| 9 | **Treat any pasted secret as compromised** → revoke/reissue least-privilege before use | future:secrets-hygiene-guard | hook | 15 / P0 |
| 10 | **Data-fetching hooks must surface errors** (403→access-required, 404→not-found), not render empty shells | react-kit | skill | 15 / P1 |

### Top existing plugins to enhance (lesson-driven)

1. **odoo-plugin (12)** — i18n/PO gettext workflow, theme `_theme_load`, volume-drift safety, Postgres version pinning.
2. **devops-plugin (11)** — GitHub identity auto-switch + permission-first write hooks, work-item-type verification, branch-protection/linear-history awareness.
3. **rag-plugin (6)** — canonical `~/.claude.json` MCP-wiring truths, concurrent-session clobber warning, failing-MCP diagnosis ladder.
4. **paper-plugin (1)** — minor: WebFetch-can't-send-custom-headers note (better hosted in claude-env-doctor).

### Top planned-plugin recommendations

1. **react-kit (32)** — lead with lint-triage discipline + React-19 migration reference + data-fetching error/empty/loading-state patterns; admin-panel/CRUD/table scaffolding as secondary.
2. **qa-browser (15)** — the security-verification powerhouse: identity-over-labels, RBAC proof via status codes, source-to-sink review, CORS-safe header injection, destructive-action safeguards, PASS/FAIL/BLOCKED reports.
3. **docs-wiki (9)** — source-of-truth ordering, target-vs-current separation, stale-checkbox distrust, flat-namespace link validation, safe doc-tree deletion, code-vs-wiki discrepancy reports.

### Blockers / unclear lessons

- **No technical blockers.** All inputs were readable; no secrets were copied (patterns summarized only).
- **`react-admin-kit-plugin` → `react-kit` is a rename that has not been executed** (this is a planning pass). The mapping uses the target name `react-kit`; the actual folder/`plugin.json`/`marketplace.json` rename is Phase 2 work.
- **One destination, `claude-plugin-builder`, is a session skill, not a marketplace plugin** — the single lesson there (skill-library layering) is folded into the `future:plugin-authoring-guide` / `docs-wiki` discussion.
- **qa-browser vs a hypothetical `secure-code-review` plugin** is the one genuinely contestable boundary: 6–8 security-review lessons could seed either. This plan keeps them in qa-browser (verification is its core) and flags the alternative in §7/§8.

---

## 2. Full marketplace inventory

Ten plugins were inspected under `plugins/`. Three of them — `react-admin-kit-plugin` (→ **react-kit**), `qa-browser-plugin` (→ **qa-browser**), `docs-wiki-plugin` (→ **docs-wiki**) — are the partially-scaffolded "planned" plugins; the other seven are mature. Each entry below is generated from a live structural read.

### devops-plugin  `(registered: devops)` — v6.3.0

**Purpose.** Azure DevOps hybrid (CLI + MCP) integration that lets you manage work items, sprints, time logging, and pull requests through natural language and slash commands. Enforces team business rules (hierarchy, role-based state transitions, naming, required fields) via a persistent user profile, validation hooks, and a write-confirmation gate.

**Structure.** `.claude-plugin/ (manifest)`, `commands/ (9 slash commands)`, `agents/ (3 subagents)`, `devops/ (core skill: SKILL.md, EXAMPLES.md, MCP_FAILURE_MODES.md)`, `rules/ (3 behavioral contracts)`, `data/ (6 source-of-truth files)`, `hooks/ (hooks.json + 5 shell scripts)`, `tests/ (pytest suite + validators)`, `.mcp.json (Azure DevOps MCP server declaration)`, `ARCHITECTURE.md, CHANGELOG.md, README.md, LICENSE, .local.md.template`

**Skills.**

| Skill | Purpose |
|---|---|
| devops | Core hybrid Azure DevOps skill. Routes between CLI (automation, batch, variables, extensions) and MCP (interactive queries, code review, test plans, search, security). Defines 9 workflows: work-item create, sprint query, state update with pre-flight validation, comment with @mention resolution, PR creation, log time, daily standup, monitor assignments, plus a WIQL appendix. Sidecar docs: EXAMPLES.md (usage examples) and MCP_FAILURE_MODES.md (server recovery + CLI fallback matrix). |

**Commands.**

| Command | Purpose |
|---|---|
| init | Full setup: installs CLI, configures MCP, generates user profile (~/.claude/devops.md) with team GUIDs, role permissions, project defaults. Routes to skill. /init profile regenerates profile. |
| create | Create work item (task/bug/enhancement/story) with auto-type detection; enforces hierarchy, naming, sprint assignment. Agent: work-item-ops. |
| workday | Daily login dashboard: work items, hours, compliance. Flags --sync/--tasks/--todo. Agent: work-item-ops. |
| log-time | Log hours against work items or general categories. Agent: work-item-ops. |
| sprint | Sprint progress summary; --full adds builds, tests, PRs, security. read_only. Agent: sprint-planner. |
| standup | Generate daily standup notes (Yesterday/Today/Blockers) from work items. read_only. Agent: sprint-planner. |
| task-monitor | Periodic alerts on new assignments, designed for /loop 15m. Agent: work-item-ops. |
| timesheet | Local-only time tracking + time-off management (--week/--month/--date/--off...). No API calls. No agent. |
| cli-run | Direct raw Azure DevOps CLI execution. Explicitly bypasses all plugin guards (write gate, state/hierarchy/mention validation) — for CLI-only features or MCP fallback. No agent. |

**Hooks.**

| Event | Purpose |
|---|---|
| PreToolUse | Matches write MCP tools (wit_create_work_item, wit_update_work_item, wit_add_work_item_comment, wit_work_items_link, repo_create_pull_request) and runs pre-write-validate.sh — enforces state transitions, hierarchy, bug-creation authority, close/remove restriction, and blocks unresolved @mentions. |
| PostToolUseFailure | Matches all mcp__azure-devops__* tools and runs error-recovery.sh — classifies failures (incl. ECONNREFUSED/MCP-unavailable) and points to MCP_FAILURE_MODES.md. |

**Agents.**

| Agent | Model | Purpose |
|---|---|---|
| work-item-ops | haiku | High-volume routine CRUD, queries, status checks, and simple updates (my tasks, create/update #ID, assignments). Enforces tool-selection guard and write gate. Cheap model for high-frequency ops. |
| sprint-planner | sonnet | Analytical synthesis: sprint reports, capacity analysis, standup summaries, release notes, velocity metrics across many work items. |
| pr-reviewer | sonnet | Pull request analysis, review-thread management, PR creation, reviewer assignment, branch validation, and code-diff review. |

**Strengths.**
- Exemplary single-owner layered architecture (commands -> skill -> agents -> rules -> data) documented in ARCHITECTURE.md; logic lives in exactly one layer and other layers reference it (write-gate.md, guards.md, state_machine.json).
- Model-tier discipline: haiku for high-volume CRUD (work-item-ops), sonnet for analytical work (sprint-planner, pr-reviewer) — minimizes cost while matching capability to task.
- Strong safety/enforcement posture: a mandatory write-confirmation gate plus a PreToolUse validation hook that hard-blocks invalid state transitions, unauthorized bug creation, close/remove, and unresolved @mentions.
- Real automated test suite (state-machine schema, cross-file consistency, integration/wiring, legacy validator) that runs without Azure DevOps access — rare among plugins and catches drift.
- Data-driven business rules (state_machine.json, hierarchy_rules.json, project_defaults.json) so team conventions are editable config rather than hardcoded prose.
- Mature operational hygiene: schema versioning on the profile, SessionStart consistency/version checks, MCP failure-mode docs with a CLI fallback matrix, and a persistent user profile for identity/role/team GUIDs.

**Gaps.**
- Hook wiring is thinner than documented: hooks.json only wires PreToolUse and PostToolUseFailure, but README/structure list session-start.sh, pre-bash-check.sh, and post-bash-suggest.sh — these scripts exist but appear unwired (no SessionStart/PreToolUse-Bash/PostToolUse entries), a documentation-vs-config drift.
- No GitHub or GitLab support — the plugin is Azure DevOps-only despite the workspace using gh CLI; cross-platform DevOps abstraction is missing.
- No pipeline/build authoring or CI-CD generation workflow beyond a natural-language mention; no command/agent that actually scaffolds or edits Azure Pipelines YAML.
- No dashboards/burndown/velocity visualization output (charts or rendered reports) — reporting is text-only.
- Test plan / QA management is exposed via MCP tools but has no dedicated command, agent, or guided workflow (e.g., create test case, link to PBI, record results).
- No bulk/batch work-item operations command (mass state transition, bulk reassign, bulk tag) despite CLI being positioned for batch work.
- No webhook/notification integration (e.g., ntfy on new assignment or failing build) — task-monitor is poll-only via /loop.
- Org/identity values are placeholder-driven (YOUR-ORG) and rely on env vars; no validation command to confirm MCP auth/org wiring health beyond /init.

**Can absorb lessons:** Yes. A natural home for lessons about Azure DevOps API/MCP quirks (auth, WIQL, identity GUID resolution, state-transition gotchas), team work-tracking conventions (hierarchy, naming prefixes, required-field rules), and write-safety/confirmation patterns. New error signatures belong in state_machine.json errorPatterns + MCP_FAILURE_MODES.md; new business rules belong in the data/ files; tool-selection and mention-resolution lessons belong in rules/guards.md.

**Recommended enhancement areas.**
- Reconcile hook wiring with docs: either wire session-start.sh (SessionStart), pre-bash-check.sh (PreToolUse Bash), post-bash-suggest.sh (PostToolUse Bash) in hooks.json or update README/ARCHITECTURE to match — and add a test asserting every shell script in hooks/ is referenced by hooks.json.
- Add a pipelines workflow: a /pipeline command + agent that lists/triggers builds, tails logs, and scaffolds Azure Pipelines YAML (mirrors the existing build-status MCP tools).
- Add a test-plan command/agent for QA: create test cases, attach to suites/PBIs, and record results, with role gating consistent with the bug-creation authority rule.
- Add a bulk-ops command for batch state transitions / reassign / tagging routed through the write gate, leveraging CLI for true batch performance.
- Add notification integration (ntfy/webhook) so task-monitor and failing-build detection can push proactively instead of poll-only.
- Add a /doctor or health command that validates MCP auth, org binding, profile schema, and data-file integrity in one pass (extending the SessionStart checks into an explicit diagnostic).
- Add lightweight report rendering (markdown/CSV/burndown export) for sprint and velocity output to make reports shareable.
- Generalize toward a platform abstraction layer so the same commands/rules can target GitHub/GitLab DevOps backends, not only Azure DevOps.

**Lessons mapped here (this study):** 11. _(See §5 for the enhancement plan.)_

---

### docs-wiki-plugin  `(registered: docs-wiki)` — v0.2.0

**Purpose.** A generic toolkit for creating, organising, editing, validating, and auditing a project Wiki across multiple flavours (GitHub Wiki sibling repos, in-repo wiki/ folders, GitLab Wiki, Azure DevOps Wiki, MkDocs/Docusaurus). It owns flat-namespace + filename-uniqueness + internal-link conventions, Mermaid authoring rules, broken-link sweeps, code-vs-wiki drift reporting, and a non-negotiable push-approval gate. Wiki-to-memory sync is explicitly out of scope.

**Structure.** `agents/`, `commands/`, `hooks/ (hooks.json + 2 python scripts)`, `skills/ (7 skill dirs, each a single SKILL.md)`, `.claude-plugin/ (plugin.json)`, `README.md`, `CHANGELOG.md`, `LICENSE`

**Skills.**

| Skill | Purpose |
|---|---|
| wiki-structure | GitHub Wiki organization rules: flat-namespace, filename-uniqueness, internal-link convention (no .md extension), Home/_Sidebar/_Footer ownership, sibling-clone path, rename-on-collision, no-numeric-prefix labels. Flavour adapter switches behavior for GitLab/Azure DevOps/MkDocs (tree namespaces). |
| wiki-authoring | Content template catalogue (SOP, runbook, role-guide, onboarding, release-handover, user-manual, workflow, architecture, decision-record) plus universal conventions: audience header, last-reviewed line, one-paragraph summary, canonical section ordering, anchor-friendly headings. |
| wiki-mermaid | Mermaid diagram authoring rules: top-down (TD) default, fixed shape vocabulary, four-class colour palette (ok/block/external/audit) with hex values, label hygiene (no code/secrets/paths in business diagrams), code-path scrub, sequence/ER exceptions, diagram-as-source (no rendered PNG). |
| wiki-link-validation | Five+ read-only scans: filename collisions (flat-namespace), broken internal links, missing-page-from-sidebar, internal-link convention check, visible-numeric-prefix scan, orphan-page detection. Severity-tagged findings; never auto-fixes. Flavour-aware. |
| wiki-code-vs-docs-discrepancy | Reports disagreements between wiki and code/config/schema/CI with file:line evidence. Owns the never-silently-choose gate, the doc-drift/code-drift/intentional-gap/unknown classification, evidence-pinning convention, and a two-author suspicion heuristic. User makes the directional call. |
| wiki-safe-updates | Safe edit/publish workflow: diff-preview-before-write, push-approval gate (explicit user phrase), no force-push ever, retired-folder awareness, revert-based rollback (never reset --hard), one-purpose-per-commit. |
| wiki-vs-stray-docs | Refuses to create or grow stray docs/, doc/, documentation/, project-docs/ folders when a wiki exists; surfaces the conflict; encodes the wiki-is-source-of-truth rule; retired-folder pass-through; stop-and-surface (never silently writes or refuses). |

**Commands.**

| Command | Purpose |
|---|---|
| /wiki-init | Initialise a wiki: verify sibling clone or in-repo folder, scaffold Home/_Sidebar/optional _Footer, cache adapter inputs to .docs-wiki.local.json, refuse to populate a repo with filename collisions. Routes through wiki-structure/wiki-authoring/wiki-safe-updates. |
| /wiki-audit | Run all read-only checks (link validation, filename collisions, internal-link convention, visible numeric prefixes, orphan pages, optional stray-docs); produce a severity-grouped findings table. Never auto-fixes. |
| /wiki-update | Edit an existing wiki page with diff preview before write; supports targeted section edits without rewriting the whole page; routes through wiki-safe-updates. Never pushes. |
| /wiki-new | Create a new wiki page from an authoring template; asks for audience + summary; validates against filename collision; diff-previews; routes through wiki-safe-updates. |
| /wiki-drift | Code-vs-wiki discrepancy sweep against source-of-truth roots; produces a classified table (doc-drift/code-drift/intentional gap/unknown) with evidence; never auto-resolves. |
| /wiki-sync-audit | Audit-first composite of /wiki-audit + /wiki-drift into one read-only report for a release manager; never pushes, never applies changes. |

**Hooks.**

| Event | Purpose |
|---|---|
| PreToolUse (matcher: Bash) | Push-approval gate (pre_wiki_push_gate.py): intercepts git push against wiki repos (detected via .wiki basename or adapter cache wikiPath). BLOCKING unless DOCS_WIKI_PUSH_APPROVED=1 per session; force-push always refused even with approval. 5s timeout. |
| PreToolUse (matcher: Write\|Edit) | Stray-docs check (pre_stray_docs_check.py): a new file under docs/doc/documentation/project-docs when a wiki is present is BLOCKED; an edit to an existing stray file WARNs (advisory). Retired folders + exceptions pass through; override via DOCS_WIKI_ALLOW_STRAY=1. 5s timeout. |

**Agents.**

| Agent | Model | Purpose |
|---|---|---|
| wiki-link-auditor | sonnet | Read-only auditor running every wiki-link-validation check on a wiki path; returns a compact findings table grouped by category (collisions/broken-links/convention/numeric-prefix/orphans). Respects retired folders + exceptions. Table only, never edits. |
| wiki-cleanup-validator | sonnet | Read-only pre-delete reference check: before any approved page deletion/archive move, verifies candidates have no active inbound references from other pages/sidebar/Home/footer. Returns per-candidate GO/NO-GO/NEEDS-USER-DECISION with evidence. Does not perform the deletion. |
| wiki-drift-reporter | sonnet | Read-only code-vs-wiki drift sweep comparing behaviour-asserting claims against source-of-truth roots; returns a per-block table classified doc-drift/code-drift/intentional gap/unknown with file:line evidence on both sides. Never picks a direction, never edits. |

**Docs / examples.** `README.md (full feature/safety/adapter/roadmap doc)`, `CHANGELOG.md (Keep a Changelog format, 0.1.0 scaffold + 0.2.0 content)`, `LICENSE (MIT)`, `Page templates are described inline inside the wiki-authoring SKILL.md (SOP/runbook/role-guide/onboarding/release-handover/user-manual/workflow/architecture/decision-record) — there are no separate template files on disk`, `No skills/*/references/, examples/, or scripts/ directories present — each skill is a single SKILL.md`

**Validation patterns.** No plugin-local validator script — relies on the repo-level python validate_plugin.py docs-wiki-plugin (CHANGELOG records 0 errors); Genericness sweep documented in CHANGELOG: grep across all skill/command/agent/hook files for project-specific tokens (aqraboon, beneficiar, coupon, qid, qatar, etc.) -> 0 hits; Skill contract enforced by convention: every SKILL.md has frontmatter (name, description, version, last_reviewed, owns, defers_to, user_invocable) + a 10-section body; Runtime guardrails act as validation: filename-collision refusal in /wiki-init and /wiki-new, secret/PII scan before write, link-validation scans, push-approval gate hook, stray-docs hook; wiki-link-validation provides five read-only audit scans; agents (link-auditor, drift-reporter, cleanup-validator) are pure read-only verification passes

**Strengths.**
- Clean single-owner layering: commands route to skills, skills declare owns/defers_to, agents are read-only verification passes, hooks enforce without reasoning — no logic duplication
- Strong safety posture baked in at multiple layers: blocking push-approval gate hook, no-force-push, diff-preview-before-write, secret/PII scan, filename-collision refusal, stray-docs hook
- Never-silently-choose drift discipline with file:line evidence and explicit classification (doc-drift/code-drift/intentional gap/unknown) — the human always makes the directional call
- Genuinely generic and multi-flavour: adapter design (github-wiki/gitlab-wiki/azure-devops-wiki/mkdocs-tree) with project-specific token sweep proving portability
- Read-only agents correctly tiered to sonnet for analytical scanning work, with clear color/tool scoping (Read/Glob/Grep/Bash only)
- Crisp, well-documented scope boundary (wiki-to-memory sync explicitly excluded) plus a versioned roadmap and Keep-a-Changelog discipline

**Gaps.**
- No mechanical Mermaid syntax linter — wiki-mermaid documents rules but does not validate diagram syntax (explicitly deferred to 0.3.0)
- No /wiki-archive command for one-step archive-with-cleanup-validation, and no ADR auto-numbering helper (user supplies NN) — both deferred to 0.3.0
- GitLab and Azure DevOps adapters are documented but not battle-tested; only github-wiki is the well-exercised path
- No bundled page-template files on disk (references/examples/) — templates live only as prose inside wiki-authoring SKILL.md, so they cannot be linted, diffed, or reused programmatically
- No external-link (HTTP) checker — link validation covers internal links only; dead outbound URLs go undetected
- No spell/style/terminology-consistency check or vale-style prose linting for authored pages
- No tests/ directory or automated hook unit tests — hook behavior (push gate, stray-docs) is documented but not covered by repeatable tests
- No staleness/last-reviewed enforcement (wiki-authoring defines a last-reviewed convention but nothing audits pages whose last-reviewed date is too old)

**Can absorb lessons:** Yes. A natural home for lessons about documentation/wiki hygiene: GitHub Wiki flat-namespace and filename-collision gotchas, internal-link conventions per wiki flavour, Mermaid authoring pitfalls, code-vs-docs drift detection patterns, safe-publish workflows (push gates, force-push avoidance, revert-based rollback), and how to keep team SOPs/runbooks/onboarding docs from going stale. Lessons would land in the relevant skill's owns list or the safe-updates/structure rules.

**Recommended enhancement areas.**
- Add a mechanical Mermaid linter script (skills/wiki-mermaid/scripts/) that parses fenced mermaid blocks and flags direction, disallowed shapes, off-palette colors, and code/secret leakage in labels
- Add a /wiki-archive command + the wiki-cleanup-validator pre-delete gate as a one-step archive-with-cleanup flow, plus an ADR auto-numbering helper
- Add an external/outbound-link checker (HTTP HEAD with caching) to wiki-link-validation and a corresponding flag on /wiki-audit
- Extract authoring templates into real files under skills/wiki-authoring/templates/ so they can be diffed, version-controlled, and scaffolded mechanically rather than reproduced from prose
- Add a staleness audit: scan last-reviewed dates and report pages past a configurable freshness threshold as a /wiki-audit severity tier
- Add a tests/ directory with hook unit tests (push-gate approval/force-push refusal, stray-docs block/warn/pass-through) and a fixture wiki to regression-test the audit scans
- Add a prose-quality/terminology-consistency check (vale-style) and a glossary-enforcement pass for project-specific terms
- Harden and add fixtures for the GitLab/Azure DevOps/MkDocs adapters so non-github-wiki flavours reach parity with the github-wiki path

**Lessons mapped here (this study):** 9. _(See §5 for the enhancement plan.)_

---

### ntfy-plugin  `(registered: ntfy-notifications)` — v3.0.0

**Purpose.** Pushes notifications to the user's phone via ntfy.sh when Claude completes tasks, needs input, or hits errors, with two-way phone Q&A so Claude can ask a question and wait for a response. 100% free, no account required; supports retry, deduplication, rate limiting, and local notification history.

**Structure.** `.claude-plugin/ (manifest)`, `commands/ (2 slash commands)`, `hooks/ (hooks.json — present but EMPTY)`, `ntfy/ (skill folder containing SKILL.md, config.default.json, config.json, scripts/)`, `ntfy/scripts/ (7 Python modules + session_state.json)`

**Skills.**

| Skill | Purpose |
|---|---|
| ntfy | Single skill (declares model: sonnet) that teaches Claude when/how to send push notifications and run two-way phone Q&A. Maps event types to priorities (task complete=high, action required=urgent, blocked/error=high, long task=low), documents the layered Python API (claude_actions, notification_checker, task_helpers, interactive), config schema, priority levels, and a CRITICAL REMINDER that notifying is mandatory because the user is not watching the terminal. |

**Commands.**

| Command | Purpose |
|---|---|
| ntfy | Unified push-notification command. Bare /ntfy defaults to status (config + connectivity); sub-commands setup, test, status, history (--export/--search), config <key> <value>; any other argument is sent as a quick message. NOTE: references scripts send.py and history.py that do not exist (actual files are notify.py / notification_logger.py). |
| ntfy-mode | Toggle session auto-notify on/off/status (bare call toggles). When ON, Claude auto-notifies on task completion, actions needing input, errors, and long-task milestones, with optional custom topic. |

**Hooks.**

| Event | Purpose |
|---|---|
| (none wired) | hooks/hooks.json exists but is empty ({"hooks":{}}). Despite README/SKILL/commands repeatedly referencing a SessionEnd and Stop hook for auto-notification, NO hook is actually registered — auto-notify currently depends entirely on the model invoking the skill, not on the harness. |

**Agents.** _none_

**Strengths.**
- Cleanly layered Python architecture (7 documented layers: transport, reliability, interaction, session, helpers, storage, state) with single-owner separation of concerns
- Rich, well-documented API surface: session-aware claude_actions (need_action, task_done, ask_proceed, blocked, error_occurred) plus lower-level checker, interactive Q&A, and decorator/context-manager helpers
- Genuine two-way communication with platform-aware presentation (Android action buttons vs iOS numbered options vs universal)
- Production-grade reliability features: retry with backoff, deduplication, rate limiting, timeout handling, and local JSON history with stats/export
- Config-driven with committed config.default.json template and gitignored user config.json, supports self-hosted servers with token/basic auth
- Thoughtful fallback design documented (Windows Toast + terminal bell when ntfy unreachable) and GitHub Actions integration example
- Zero-friction onboarding: no account required, clear 5-minute quick start, /ntfy setup wizard and /ntfy test verification

**Gaps.**
- hooks/hooks.json is empty — the advertised automatic SessionEnd/Stop notification never fires from the harness; auto-notify is entirely model-driven, contradicting the docs and the 'mandatory' framing
- Command/script drift: /ntfy command references send.py and history.py which do not exist (real modules are notify.py and notification_logger.py), so documented paths are broken
- No CHANGELOG.md despite version 3.0.0, conflicting with the workspace convention to bump version + add CHANGELOG entry on every change
- Documented Windows Toast / terminal-bell fallback appears only as README prose, not as a shipped reusable function in the scripts layer
- No validator/tests for the plugin's own Python (no tests/ dir, no lint config) — reliability claims are unverified
- Two-way Q&A polling has no documented secure-topic guidance enforcement; topic acts as a password but nothing warns at send-time if a weak/empty topic is configured
- No batching/digest mode to coalesce many small notifications into one summary, which the rate-limit-heavy design hints is needed
- config.json and session_state.json are committed/present in the tree even though .gitignore claims to exclude user state — risk of leaking a real topic

**Can absorb lessons:** Yes. A natural home for lessons about notification UX and delivery reliability: when to notify vs. stay silent, choosing priority/tags per event, avoiding notification spam (dedup/rate-limit tuning, digest patterns), two-way Q&A timeout/fallback handling, cross-platform (iOS/Android/Windows) delivery quirks, and self-hosted ntfy auth/security practices. Could also absorb hook-wiring lessons (SessionEnd/Stop/Notification events) once real hooks are added.

**Recommended enhancement areas.**
- Wire real hooks in hooks.json (Stop / SubagentStop / SessionEnd for completion notices, Notification event for permission/idle prompts) gated by ntfy-mode session state, so auto-notify works without relying on the model
- Reconcile command-to-script naming (either add thin send.py/history.py shims or update ntfy.md to call notify.py / notification_logger.py) and add a small validator/test that asserts every referenced script path exists
- Add a CHANGELOG.md and adopt the workspace version-bump-on-every-change convention
- Promote the Windows Toast / terminal-bell fallback from README prose into a real shipped fallback function in the scripts layer, used by ensure_notification when ntfy is unreachable
- Add a digest/batch mode skill+config to coalesce bursty notifications into a single summary message
- Add a setup-time guard that warns on empty or low-entropy topic names (treats topic as a secret) and a /ntfy doctor sub-command for end-to-end delivery diagnosis
- Add tests/ with offline-mockable unit tests for retry, dedup, rate-limit, and interactive polling-timeout paths

**Lessons mapped here (this study):** 0. _(See §5 for the enhancement plan.)_

---

### odoo-plugin  `(registered: odoo)` — v2.0.0

**Purpose.** Unified Odoo development toolkit for Claude Code spanning eight capability areas (version upgrade/migration, website theme/frontend, testing, security auditing, i18n, email/QWeb reports, Docker infrastructure, and server/service lifecycle) across Odoo versions 14-19. Consolidates what used to be separate odoo-*-plugins into one plugin organized as area sub-skills with thin command entry points, model-tiered agents, and safety hooks.

**Structure.** `commands/ (17 slash commands)`, `agents/ (4 subagent definitions)`, `skills/ (12 SKILL.md across frontend/, docker/, i18n/, report/, security/, service/, test/, upgrade/)`, `hooks/ (hooks.json + frontend/ + upgrade/ python scripts)`, `rules/ (behavioral contracts: core-odoo-guard, scss-load-order)`, `data/ (frontend, report JSON + md source-of-truth)`, `memories/ (i18n, report, security, test domain knowledge md)`, `reference/ (docker, report, service, upgrade reference md)`, `templates/ (docker, report email templates)`, `scripts/ (frontend, i18n, security, service, test, upgrade python implementations)`, `config/ (upgrade config json + docker local.md example)`, `tests/ (service + frontend pytest suites)`, `LICENSES.md, CHANGELOG.md, README.md`

**Skills.**

| Skill | Purpose |
|---|---|
| odoo-upgrade | Module migration 14->19: XML view transforms, Python API changes, JS/OWL components, theme SCSS variable restructuring, manifest updates, security, DB migrations, portal XPath fixes. |
| odoo-docker | Docker infrastructure manager: production deployment, nginx proxy, CI/CD pipelines, performance tuning, multi-version image management, container debugging, workspace orchestration. |
| frontend-js | Odoo frontend JavaScript patterns: publicWidget framework, Owl v1/v2 components, _t() translation, Bootstrap 4-to-5 migration, version detection. |
| theme-create | Theme scaffolding/creation pipeline: complete installable theme modules with SCSS config, page templates, mirror models, theme.utils activation, auto-fix install. |
| theme-design | Figma-to-Odoo design workflow: Figma extraction (colors/typography/layout), Chrome MCP automation, design-to-template matching, header/footer flowcharts, page reference. |
| theme-scss | Complete SCSS variable reference: $o-theme-font-configs, $o-color-palettes, $o-website-values-palettes (115+ keys), SCSS load order and color derivation. |
| theme-snippets | Website snippet reference/creation: 81+ static snippet templates, dynamic snippets, snippet options (we-* elements), custom snippet creation, version-aware registration. |
| odoo-i18n | i18n toolkit: extract translatable strings, validate .po files, generate translation reports, manage Arabic/RTL layouts, multilingual deployments. |
| odoo-report | Email templates & QWeb PDF reports: create/manage/debug, wkhtmltopdf setup, Arabic/RTL support, bilingual patterns, validation. |
| odoo-security | Security auditor: model access rules, HTTP route auth, sudo() usage, SQL injection risks, record rule completeness. |
| odoo-service | Server lifecycle manager: startup/shutdown, env init, DB management, Docker orchestration, IDE config across local venv and Docker. |
| odoo-test | Testing toolkit: generate test skeletons, run suites, create mock data, analyze coverage; TransactionCase/HttpCase/SavepointCase; Azure DevOps CI/CD integration. |

**Commands.**

| Command | Purpose |
|---|---|
| /create-theme | Scaffold a complete installable Odoo theme module from Figma or manual specs (routes to theme-generator agent). |
| /upgrade | Upgrade a module to a target version via full transformation pipeline; auto-detects module from cwd when bare. |
| /precheck | Read-only version compatibility scan reporting issues by severity; never modifies files. |
| /quickfix | Apply safe mechanical compatibility fixes with preview and confirmation before modifying. |
| /frontend | Show Odoo frontend environment status and available capabilities (read-only). |
| /docker | Docker infrastructure and container management (init/compose/deploy/build/up/down/logs/shell/status/update). |
| /service | Server lifecycle overview dispatching to start/stop/init/db/docker/ide/scaffold. |
| /start | Start Odoo server with config detection and environment awareness (--dev/--workers/--docker). |
| /stop | Stop Odoo server by killing processes on port 8069/8072. |
| /init | Initialize a new Odoo project: venv, config file, directories, prerequisite checks. |
| /db | Database operations: backup, restore, create, drop, list, reset-admin, modules. |
| /ide | Generate PyCharm and VSCode configurations for Odoo development. |
| /scaffold | Generate a complete module skeleton with models, views, security, and tests. |
| /test | Testing toolkit: generate, mock data, run, coverage, e2e for a model/module. |
| /security | Comprehensive module security audit with severity/layer filters and --fix/--json. |
| /i18n | i18n toolkit: extract, validate, find missing, export translations. |
| /report | Email templates & QWeb reports: create, validate, migrate, analyze, preview. |

**Hooks.**

| Event | Purpose |
|---|---|
| SessionStart (startup) | Detect Odoo version and inject frontend context via hookSpecificOutput; fail-open after internal 8s timeout. |
| PreToolUse (Write\|Edit) | guard_core_odoo.py — BLOCK writes/edits to core Odoo framework files (core path patterns loaded from odoo-upgrade.config.json); exit 2 to block. |
| PreToolUse (Write\|Edit) | pre_write_check.py — BLOCK Write/Edit of XML files containing inline JavaScript; fast-path string check before regex, internal timeout guard. |

**Agents.**

| Agent | Model | Purpose |
|---|---|---|
| security-auditor | sonnet | Scans modules for security vulnerabilities (access rules, routes, sudo, SQL injection, record rules) and produces structured audit reports; defers pattern knowledge to odoo-security skill. |
| test-analyzer | sonnet | Scans modules for test coverage gaps across models/controllers/wizards and produces structured coverage reports; defers to odoo-test skill. |
| theme-generator | sonnet | Generates complete Odoo website themes from Figma designs or manual specs; handles extraction, color/typography mapping, SCSS generation, scaffolding, install, auto-fix. Tools: Read/Write/Bash/Glob. |
| upgrade-analyzer | sonnet | Scans modules for version compatibility issues across xml/py/js/scss and produces structured reports; defers to odoo-upgrade skill. |

**Docs / examples.** `README.md (command + hook + domain tables)`, `CHANGELOG.md`, `LICENSES.md (component provenance)`, `templates/docker/ (Dockerfile.template, docker-compose.dev.yml, docker-compose.prod.yml, entrypoint.sh, nginx.conf, odoo.conf.template)`, `templates/report/email/ (basic_notification.xml, document_email.xml)`, `data/frontend/ (color_palettes.json, figma_prompts.json, theme_templates.json, typography_defaults.json, version_mapping.json)`, `data/report/ (context_variables.json, layouts.json, module_templates.md, template_fields.json)`, `reference/docker (docker-patterns, production-checklist, troubleshooting, version-matrix)`, `reference/upgrade (error_catalog.md, odoo18_to_19.md)`, `reference/report/version_helper.md, reference/service/version-matrix.md`, `memories/ (i18n, report, security, test domain pattern md files)`, `config/odoo-docker.local.md.example, config/odoo-upgrade.config.json`

**Validation patterns.** scripts/upgrade/validate.py — post-transform module validation; scripts/upgrade/precheck.py — read-only compatibility scan engine (severity-graded); scripts/security/* — security_auditor.py, access_checker.py, route_auditor.py, sql_scanner.py, sudo_finder.py (lint-style security scanners); scripts/i18n/i18n_validator.py — .po file validation; i18n_reporter.py reporting; scripts/test/coverage_reporter.py + test_runner.py — coverage/test execution; hooks/upgrade/check_odoo19_compat.py — compatibility check helper; rules/core-odoo-guard.md + rules/scss-load-order.md — behavioral contracts enforced by hooks; tests/service/ pytest suite (test_db_manager, test_docker_manager, test_env_initializer, test_ide_configurator, test_server_manager, test_shared, conftest); tests/frontend/ (test_plugin_structure.py, test_data_consistency.py, consistency_check.py) — structural + data-consistency self-tests

**Strengths.**
- Broad, genuinely unified coverage of 8 Odoo capability areas across versions 14-19, consolidated cleanly into area sub-skills rather than fragmented plugins
- Strong single-owner layering: thin commands route to skills/agents; pattern knowledge lives in skills + memories + reference, data in JSON/MD, contracts in rules/ — minimal duplication
- Safety-first hooks that fail-open with internal timeout guards and BLOCK both core-file edits and inline-JS-in-XML, backed by configurable path patterns in config json
- Real executable backbone: dedicated python scripts per domain (upgrade transforms, security scanners, i18n validators, test runners, service managers) instead of prose-only skills
- Has its own test suites (service pytest + frontend structure/consistency checks) and a validation script — unusually mature self-verification for a plugin
- Rich reusable assets: docker/report templates, color/typography/figma data, version-matrix and error-catalog references, and bare-invocation cwd auto-detection for upgrade commands

**Gaps.**
- No CHANGELOG-visible version bump discipline tie-in surfaced and plugin.json lacks a license/keywords/homepage field set typical of a published marketplace plugin
- No PostToolUse or Stop hook to auto-validate generated artifacts (e.g., re-run security scan or i18n validation after edits) — enforcement is only pre-write
- Frontend/theme tooling depends on Figma + Chrome MCP but there is no .mcp.json or documented MCP wiring/fallback, so the design pipeline silently degrades when MCP is absent
- No coverage for Odoo Enterprise-specific or Studio/no-code artifacts, and no OWL test (hoot/QUnit) generation in the test domain
- No CI workflow definition shipped to run the bundled pytest suites; tests exist but their execution is not automated/documented for contributors
- Upgrade pipeline lacks a documented rollback/backup-and-restore safety net and a post-upgrade diff/report comparing before vs after
- i18n covers extract/validate/export but no machine-translation or .po round-trip merge/conflict-resolution workflow
- No performance/profiling or query-analysis tooling despite docker perf-tuning being mentioned — no log analysis or slow-query domain
- Service/db commands are POSIX-leaning (port-kill via process); Windows-host parity (the user's actual environment) is unverified in inventory

**Can absorb lessons:** Yes. This is the natural home for any Odoo-domain engineering lesson: version-specific breaking changes and migration gotchas (feed odoo-upgrade skill + reference/upgrade/error_catalog.md), theme SCSS/Bootstrap/OWL pitfalls (frontend skills + memories), security anti-patterns and sudo/SQL findings (odoo-security memories), i18n/RTL and report/QWeb rendering quirks, and Docker/service lifecycle operational lessons. Lessons land best as entries in the matching memories/ or reference/ files, with hard rules promoted into rules/ or hook config.

**Recommended enhancement areas.**
- Add a PostToolUse/Stop hook that re-runs the relevant domain validator (security scan, i18n .po validate, manifest lint) on touched files and advises, closing the loop beyond pre-write blocking
- Ship a .mcp.json (or documented MCP detection + graceful fallback) for the Figma/Chrome design pipeline so theme-design degrades predictably
- Add an upgrade rollback/backup command and a post-upgrade before/after diff report; pair with a /upgrade --dry-run that wraps existing precheck output
- Introduce a CI workflow (GitHub Actions) that runs the bundled pytest suites + validate_plugin.py on every change, and document a contributor test command
- Add an OWL/hoot/QUnit frontend test generator and an Enterprise/Studio-aware mode to broaden the test and upgrade domains
- Add a performance/log-analysis skill+command (slow-query, worker tuning, logfile triage) to realize the docker perf-tuning capability the README advertises
- Verify and document Windows-host parity for service/db process management (port detection, server start/stop) since the maintainer's environment is Windows
- Enforce plugin.json version bump + CHANGELOG entry via a SessionStart/pre-commit reminder so the marketplace updater can detect new versions

**Lessons mapped here (this study):** 12. _(See §5 for the enhancement plan.)_

---

### pandoc-plugin  `(registered: pandoc)` — v2.1.0

**Purpose.** Universal document conversion plugin powered by Pandoc. Converts between 50+ input and 60+ output formats (Markdown, Word, HTML, PDF via LaTeX, EPUB, reveal.js/Beamer/PowerPoint slides) with smart format detection, citation processing, batch workflows, and dedicated Arabic/RTL support.

**Structure.** `commands/`, `hooks/`, `pandoc/ (skill dir, holds SKILL.md + scripts/)`, `pandoc/scripts/`, `reference/`, `test/`, `.claude-plugin/`

**Skills.**

| Skill | Purpose |
|---|---|
| pandoc | Single CLI-tool skill (model: sonnet, declares pandoc-min-version 3.0.0). Drives the full conversion workflow: verify pandoc/LaTeX install, detect input/output formats, build and run the pandoc command, report result. Holds a format quick-reference table, common-options table, setup flow, error-handling table, Arabic/RTL essentials, and best-practices list. Five trigger examples in frontmatter (md->PDF, docx->md, slides, setup/pdflatex fix, batch). |

**Commands.**

| Command | Purpose |
|---|---|
| pandoc | Single unified command. Parses $ARGUMENTS and dispatches to subactions: empty/help (usage + formats), setup (install Pandoc + LaTeX/MiKTeX with auto-install), status (check install/version/formats), convert <file> <format> [opts] (run conversion), formats (list supported formats). Bare invocation runs sensibly (shows help), matching the no-args convention. Delegates real behavior to the pandoc skill. |

**Hooks.**

| Event | Purpose |
|---|---|
| SessionStart (DOCUMENTED but NOT wired) | session-check.sh exists and is correct: checks for pandoc and pdflatex/xelatex on stdin-driven session start, stays silent if both present, otherwise advises running /pandoc setup. README documents it as wired, but hooks/hooks.json is empty ({"hooks":{}}) and plugin.json has no hooks key, so the hook does not actually run. |
| PreToolUse:Bash (DOCUMENTED but NOT wired) | pandoc-context.sh exists and is correct: parses the Bash command JSON, and only for pandoc commands injects format-specific tips (PDF-needs-LaTeX, Arabic/RTL->use xelatex+dir=rtl, EPUB cover image, HTML -s/standalone). Same gap: not registered in hooks.json or plugin.json, so it is inert. |

**Agents.** _none_

**Docs / examples.** `README.md (quick start, command table, features, hook table, structure, extending, troubleshooting)`, `reference/format_guide.md (per-format best practices: install/MiKTeX, PDF, DOCX, HTML, EPUB, slides, batch, error prevention, extensive Arabic/RTL section with templates and font tables)`, `pandoc/scripts/setup.ps1 (Windows installer: Pandoc via winget + MiKTeX + auto-install + 30+ LaTeX packages)`, `pandoc/scripts/setup.sh (Linux/macOS installer: apt/brew + TeX Live/MacTeX)`, `test/sample.md, test/sample.rst, test/sample.tex (sample input files for manual conversion testing), test/.gitignore`

**Validation patterns.** No automated validation/QA/lint/test scripts inside the plugin (it relies on the workspace-level validate_plugin.py).; test/ holds sample input files (sample.md/.rst/.tex) intended for manual round-trip conversion checks, but there is no runner, assertions, or expected-output fixtures.; Runtime self-check pattern: SKILL.md Step 1 and format_guide.md both mandate verifying pandoc --version and pdflatex --version before any conversion; setup.ps1 verifies and pre-installs LaTeX packages to avoid popups. These are convention-level checks, not enforced tests.

**Strengths.**
- Clean single-owner layering: thin /pandoc command routes to one sonnet skill, heavy detail lives in reference/format_guide.md, install logic isolated in platform scripts.
- Strong, specific skill triggering: five concrete <example> blocks plus a clear 'When to Use' list covering PDF, format migration, slides, setup, and batch.
- Exceptional Arabic/RTL coverage: xelatex flags, polyglossia template, RTL HTML stylesheet, bilingual handling, font recommendation table, and a common-issues troubleshooting table — a genuine differentiator.
- Cross-platform automated setup that pre-installs 30+ LaTeX packages and enables MiKTeX auto-install to avoid the classic per-package popup trap.
- Practical, copy-paste-ready guidance: quick-reference and common-options tables, error->cause->fix table, and best-practices list reduce trial-and-error.
- Good no-args ergonomics — bare /pandoc shows help, and subcommands are optional shortcuts rather than required syntax.

**Gaps.**
- Hooks are dead: both scripts (session-check.sh, pandoc-context.sh) exist and are documented in README, but hooks/hooks.json is empty ({"hooks":{}}) and plugin.json declares no hooks — so neither hook actually fires. This is a shipped bug, not a design choice.
- Hook scripts are bash-only with no PowerShell/.cmd equivalent; even once wired they will silently no-op on a vanilla Windows shell, despite Windows being the primary documented platform.
- No real test harness: test/ has sample inputs but no runner, no expected-output fixtures, and no assertion that conversions succeed across formats/platforms.
- No version-bump discipline visible: no CHANGELOG.md in the plugin despite the workspace convention to add a CHANGELOG entry on every change.
- No templates/ directory shipped despite README and skill repeatedly recommending --reference-doc (DOCX/PPTX), --template (LaTeX), and CSS/CSL files — users must build these themselves.
- No CSL citation-style assets or guidance beyond naming IEEE/APA; --citeproc workflow lacks bundled styles or a fetch step.
- No image/asset preflight: nothing checks that referenced images exist or that the output directory is writable before invoking pandoc (the guide says to verify but nothing enforces it).
- No declared dependency or graceful-degradation note for when winget/brew/apt are unavailable, and no offline/manual-install fallback wired into the setup command path.

**Can absorb lessons:** Yes. A natural home for document-conversion lessons: pandoc invocation gotchas (engine choice, flag interactions, encoding), LaTeX/MiKTeX/TeX Live install and missing-package fixes, RTL/Arabic typography pitfalls, and format-specific quirks (EPUB covers, DOCX media extraction, slides themes). Such lessons belong in reference/format_guide.md and the skill's error-handling table.

**Recommended enhancement areas.**
- Fix and wire the hooks: populate hooks/hooks.json (or plugin.json hooks key) to register SessionStart->session-check and PreToolUse:Bash->pandoc-context, then validate they fire; ship cross-platform variants so they work on Windows too.
- Add a templates/ directory with starter reference.docx, reference.pptx, an academic LaTeX template, and the Arabic polyglossia template referenced in the guide, plus a /pandoc template subcommand to scaffold them.
- Bundle common CSL styles (IEEE, APA, Chicago) or add an automatic fetch step so --citeproc works out of the box.
- Add a real test/QA harness: a script that round-trips sample.md/.rst/.tex through key output formats and asserts non-empty, valid output; gate it in validate flow.
- Add a preflight check (skill step or hook) that confirms input files and referenced images exist and the output dir is writable before running pandoc.
- Add CHANGELOG.md and adopt the version-bump-on-every-change convention.
- Consider a lightweight conversion agent (haiku) for high-volume batch jobs and a status/formats parser that surfaces the live installed reader/writer list rather than a static table.

**Lessons mapped here (this study):** 0. _(See §5 for the enhancement plan.)_

---

### paper-plugin  `(registered: paper)` — v3.0.0

**Purpose.** A UI/UX design specialist plugin that turns Claude into a senior designer for web, mobile (iOS/Android), and desktop. It covers screen design, wireframing, design-system generation, design/accessibility review (WCAG 2.1 AA), and bidirectional Figma sync via the optional Figma MCP plugin.

**Structure.** `.claude-plugin/ (plugin.json manifest)`, `skills/ (design, figma-workflow)`, `agents/ (design-reviewer, wireframe-builder)`, `commands/ (paper.md)`, `hooks/ (hooks.json — present but EMPTY)`, `reference/ (5 knowledge docs)`, `README.md`

**Skills.**

| Skill | Purpose |
|---|---|
| design | Core design knowledge skill. Activates on natural-language design tasks (design a page, wireframe, color palette, typography, accessibility check). Covers color theory, type scales, 4px spacing system, layout fundamentals, multi-platform design (web/iOS/Android/desktop), common screen types, a 6-dimension review checklist, anti-patterns, and a structured design output format. Declares a metadata.filePattern (html/xml/css/scss/jsx/tsx/vue/svelte) and points to the 5 reference docs for deep detail. |
| figma-workflow | Figma MCP integration skill. Activates on Figma URLs/keywords. Documents 13 Figma MCP tools (read+write), URL parsing rules (fileKey/nodeId), design-to-code and code-to-design workflows, design-system token sync, and asset-handling rules (use localhost URLs, never import icon packages). Gracefully degrades with setup instructions when the Figma MCP plugin is absent. |

**Commands.**

| Command | Purpose |
|---|---|
| paper | Single unified, thin dispatcher command. Bare /paper shows capabilities + Figma connection status. Routes figma {pull\|push\|status\|suggest\|diagram} and system {generate\|analyze} sub-commands, and falls back to natural-language intent inference. Behavior lives one layer down in the skills. |

**Hooks.** _none_

**Agents.**

| Agent | Model | Purpose |
|---|---|---|
| design-reviewer | inherit | Color purple. Senior UI/UX review agent that audits existing UI code (HTML/CSS/SCSS/XML/JSX/Vue/Svelte) across 6 dimensions (visual hierarchy, color/contrast, typography, spacing/layout, accessibility, responsive). Optionally compares against a Figma source via MCP. Produces a scored (X/10) report with severity-rated, line-cited, fix-bearing findings. |
| wireframe-builder | inherit | Color blue. Rapid prototyping agent that produces low-fidelity ASCII wireframes, component inventories, responsive/interaction notes, multi-screen flow diagrams, and optional Bootstrap 5 HTML/CSS prototypes. Includes platform wireframe templates (web/iOS/Android/desktop) and can push wireframes/diagrams to Figma when MCP is available. |

**Docs / examples.** `README.md (comprehensive: capability table, quick start, install options, component reference, project structure)`, `reference/color-theory.md (palette algorithms, HSL shade generation, contrast, dark mode)`, `reference/typography-scale.md (7 modular scales, 12 font pairings, fluid type, vertical rhythm)`, `reference/layout-patterns.md (21 layout patterns with ASCII diagrams + CSS)`, `reference/platform-guidelines.md (iOS HIG, Material Design 3, Windows Fluent, Web)`, `reference/accessibility-checklist.md (WCAG 2.1 AA by POUR principles, ARIA patterns, testing methods)`

**Validation patterns.** No automated validation/lint/test scripts are bundled inside the plugin.; Quality is enforced behaviorally: the design-reviewer agent applies a 6-dimension rubric with a 1-10 scoring guide and Critical/Major/Minor/Suggestion severity ratings.; WCAG 2.1 AA contrast thresholds (4.5:1 / 3:1) are codified in the design skill and reference/accessibility-checklist.md as the review source of truth.; Design anti-pattern table in the design skill acts as a negative-rule checklist.; Plugin is checked externally by the repo-level validate_plugin.py, not by anything in-plugin.

**Strengths.**
- Strong, well-layered architecture: thin /paper command -> 2 focused skills -> 2 specialized agents -> 5 deep reference docs, with skills/agents explicitly pointing to references (no logic duplication).
- Genuinely deep, accurate domain knowledge grounded in authoritative sources (Apple HIG, Material 3, Fluent, W3C WCAG 2.1 AA) — color theory, type scales, spacing tokens, platform touch-target rules.
- Excellent skill/agent triggering: rich, example-laden YAML descriptions with concrete <example> blocks and trigger keyword lists improve activation accuracy.
- Graceful degradation around the optional Figma MCP dependency — the plugin remains fully useful (theory, wireframing, review, design systems) without it, and tells the user how to install it.
- Multi-platform coverage (web responsive, iOS, Android, desktop) plus complete-screen checklists (empty/error/loading/onboarding states) make output production-oriented, not just aesthetic.
- Clean v3.0 refactor history documented in README (monolithic skill split, Odoo content removed, command slimmed to a dispatcher).

**Gaps.**
- Hooks are documented but NOT implemented: README describes a 'Markup Design Check' and 'Style Design Check' PostToolUse hook, but hooks/hooks.json is literally {"hooks":{}} — a documentation/implementation drift that should be fixed (either ship the hooks or remove the claims).
- No CHANGELOG.md despite v3.0.0 and a documented migration — violates the workspace convention of a CHANGELOG entry on every plugin change.
- plugin.json declares no explicit skills/commands/agents/hooks arrays; relies entirely on auto-discovery (works, but explicit registration is more robust and self-documenting).
- No design-token output format/contract (e.g., a standard tokens.json/CSS-custom-property schema or a templates/ dir), so generated design systems are ad hoc per run.
- No automated accessibility/contrast verification — contrast checks are reasoned by the model rather than computed by a bundled script, so results can drift.
- No design-versioning or visual-regression / diff capability for comparing successive design iterations or code-vs-Figma beyond manual MCP screenshot comparison.
- Coverage gaps in modern UI domains: no motion/animation guidance, no internationalization/RTL or localization layout rules, no data-visualization/charting design guidance, no email/print design.
- No tests/ directory and no in-plugin validation script, so regressions in skill/agent guidance go uncaught.

**Can absorb lessons:** Yes. This is the natural home for UI/UX and frontend-design engineering lessons: accessibility/WCAG gotchas, contrast and color-token pitfalls, responsive-breakpoint mistakes, platform-specific (iOS HIG / Material / Fluent) conventions, design-to-code fidelity lessons, and Figma MCP integration quirks. Such lessons map cleanly onto the design skill, the reference docs, the anti-pattern table, and the design-reviewer rubric.

**Recommended enhancement areas.**
- Wire the documented hooks: add real PostToolUse hooks in hooks.json (markup files: semantic tags/alt/labels; style files: contrast/relative-units/focus styles) so the README matches reality — or update the README if they are intentionally dropped.
- Add a contrast/a11y validation script (scripts/) the design-reviewer can call to compute WCAG ratios deterministically instead of estimating them.
- Introduce a design-tokens contract: a templates/ dir with a canonical tokens schema (CSS custom properties + JSON) so 'system generate' emits a consistent, machine-readable design system.
- Add a CHANGELOG.md and per-update version bump to satisfy the marketplace update-detection convention.
- Add an explicit accessibility-audit command/sub-command (e.g., /paper review or /paper a11y) that routes straight to the design-reviewer agent for one-shot audits.
- Expand reference coverage with new skills/docs for motion/animation, i18n/RTL layout, and data-visualization design — high-value modern UI domains currently absent.
- Add a tests/ directory with skill-trigger and command-routing smoke tests, and register components explicitly in plugin.json for robustness.

**Lessons mapped here (this study):** 1. _(See §5 for the enhancement plan.)_

---

### qa-browser-plugin  `(registered: qa-browser)` — v0.2.0

**Purpose.** Framework-agnostic browser QA and role-based smoke testing. Drives chrome-devtools-mcp or playwright-mcp to log in as each role, walk modals and table actions, verify UI-vs-API permissions, capture console/network/screenshot evidence, and produce PASS / BLOCKED / NOT-TESTABLE reports for UAT signoff — with baked-in production-URL and destructive-action safety gates.

**Structure.** `skills/ (9 skills)`, `commands/ (5 commands)`, `agents/ (2 agents)`, `hooks/ (hooks.json + 2 python scripts)`, `.claude-plugin/ (plugin.json manifest)`, `README.md`, `CHANGELOG.md`, `LICENSE`

**Skills.**

| Skill | Purpose |
|---|---|
| browser-qa-discipline | Owns the PASS / BLOCKED / NOT-TESTABLE three-status vocabulary, the per-check evidence requirement, the 'code-read is NOT runtime evidence' rule, and the silent-pass-is-not-pass rule. Activates at the start of any QA pass and before any PASS or sign-off claim. |
| runtime-reality-check | Verifies the target is actually reachable, healthy, and on the expected build BEFORE any check runs. Owns the reachability gate (HEAD probe + landing render), build-identity check (commit/version/deploy timestamp), env-claim-vs-actual comparison, and dead-infrastructure / stale-build / wrong-environment labels. |
| role-smoke-tests | Per-role smoke pattern: fresh-context login, menu enumeration, per-route walk, per-step screenshot+console+network capture, and cross-role consistency check. Owns role-rotation discipline (logout + fresh storage state between roles). |
| route-access-matrix | Negative-path RBAC verification. Owns the dual-gate check (UI AND API both deny), Shape-A detection (UI hides but API allows — most common RBAC bug), Shape-B detection (API denies but UI advertises), implicit-method probes (DELETE/PATCH often ungated), and the direct-URL bypass pattern. |
| modal-and-action-walkthroughs | Per-action walkthroughs for row actions, bulk actions, modals, confirmation dialogs, and form submit/cancel/dirty-leave. Owns the open-assert-cancel and confirm-verify patterns, modal-stack hygiene, type-to-confirm handling, and cancel-vs-close distinction. |
| import-export-ui-checks | Browser-side QA for admin import (upload → preview → commit → result) and export (filter → download → verify). Owns the upload-fixture set (golden/bad-rows/over-cap/duplicate/idempotency), preview-without-commit verification, row-cap rejection, per-row error visibility, idempotency-via-rerun, and export filename+content checks. |
| console-and-network-capture | Defines what to capture from console/network during QA, when each signal counts as a failure (5xx = FAIL), and how to redact credentials/PII/tokens before evidence lands. Owns capture-window convention, console severity mapping, request classification, redaction rules, and evidence file naming. |
| safe-destructive-testing | Disposable-data-only rule for any state-mutating action. Owns the 'what counts as disposable' test, production-URL refusal, the do-not-click selector skiplist, the credentials-must-be-gitignored rule, and irreversible-action escalation to the user. |
| uat-readiness-report | Composes the final PASS / BLOCKED / NOT-TESTABLE report from per-skill evidence. Owns report layout, sign-off recommendation rule (YES/NO/CONDITIONAL), severity grouping (HIGH/MEDIUM/LOW), evidence-link convention, and the explicit-acceptance gate for BLOCKED items before sign-off. |

**Commands.**

| Command | Purpose |
|---|---|
| /qa-target | Set or inspect the QA target — base URL, per-role credential map, do-not-click skiplist, production markers. Manages .qa-browser.local.json (set/show/clear/check), pre-checks for a browser MCP server, and refuses to operate if the credential file is git-tracked. Required before the other commands. |
| /qa-smoke | Run a single-role smoke test — reality check → login → enumerate menu → walk each route → capture screenshot+console+network → logout, producing a per-role PASS/BLOCKED/FAIL report. Read-only, no mutations. argument-hint: <role-name> [--wait-seconds N] [--include-perf]. |
| /qa-roles | Batch form of /qa-smoke across every configured role, producing one consolidated smoke report plus the cross-role consistency check. argument-hint: [--wait-seconds N] [--include-perf] [--only role1,role2]. |
| /qa-route | Focused dual-gate check on one URL across roles — observe UI denial/allow and API status, classify as PASS / Shape-A FAIL / Shape-B FAIL. Read-only. argument-hint: <url-path> [--include-implicit-methods] [--only role1,role2]. |
| /qa-report | Compile the final UAT readiness report from previously captured qa-evidence/ — executive summary + per-skill sections + failure grouping + sign-off recommendation. Read-only. argument-hint: [--date] [--env] [--summary-only] [--out path]. |

**Hooks.**

| Event | Purpose |
|---|---|
| SessionStart (matcher: startup) | Runs session_start_target_check.py — advisory reminder to run /qa-target if no target is configured; warns on git-tracked credential file, missing gitignore entry, or production-looking URL. Always exits 0 (never blocks). |
| PreToolUse (matcher: mcp__.*__navigate_page \| mcp__.*__browser_navigate) | Runs pre_navigate_prod_gate.py — production URL gate on browser-navigate MCP calls. BLOCKS navigation if the URL contains production markers (prod/production defaults, configurable) unless QA_BROWSER_ALLOW_PRODUCTION=1 is set per-session. |

**Agents.**

| Agent | Model | Purpose |
|---|---|---|
| qa-evidence-collector | sonnet | For one (role × route) cell, drives the browser MCP to login, navigate, and capture screenshot+console+network with redaction, returning one standard evidence row. Read-only — no clicks on action buttons, no form submits, no mutations. Used to delegate single-cell capture (e.g., re-run a failing cell after a fix). |
| qa-failure-classifier | sonnet | Takes one FAIL row plus its evidence and classifies the root cause as ui-bug / api-bug / data-issue / env-issue / spec-ambiguity / unknown-needs-investigation, returning a compact verdict with reasoning and the additional evidence needed to resolve an 'unknown'. Read-only — reasons from supplied evidence, runs no new probes. |

**Docs / examples.** `README.md (purpose, skill/command/agent/hook tables, framework scope, adapter inputs, MCP dependencies, safety rules, explicit non-goals, roadmap)`, `CHANGELOG.md (Keep a Changelog format; documents 0.1.0 scaffold and 0.2.0 content with safety-rules and validation notes)`, `LICENSE (MIT)`

**Validation patterns.** Plugin self-validation via parent-repo validate_plugin.py (CHANGELOG records 'python validate_plugin.py qa-browser-plugin -> 0 errors'); Genericness/portability sweep documented in CHANGELOG — grep over all skill/command/agent/hook files for product-specific tokens (e.g. coupon, qid, qatar, SUPER_ADMIN) expecting 0 hits; Runtime QA verdict vocabulary itself (PASS / BLOCKED / NOT-TESTABLE / FAIL) is the plugin's domain validation contract, owned by browser-qa-discipline; 5xx = FAIL network classification and console severity mapping (console-and-network-capture) act as pass/fail gates; Dual-gate UI+API access verification (route-access-matrix) as an RBAC correctness check; Safety-gate validations: production-URL gate (hook + skill), git-tracked-credentials refusal, disposable-data classification before mutation

**Strengths.**
- Strong, explicit safety posture — production-URL PreToolUse gate that actually blocks, git-tracked-credential refusal, do-not-click skiplist, disposable-data-only mutations, and credential/PII/token redaction at capture time
- Genuinely framework-agnostic — drives either chrome-devtools-mcp or playwright-mcp, detects rather than assumes the stack (Next.js, React SPA, Django admin, Nova/Filament, Odoo, wp-admin)
- Evidence discipline is a first-class concept — 'code-read is NOT runtime evidence', no silent passes, every check needs a screenshot+console+network artifact, with a clean three-status PASS/BLOCKED/NOT-TESTABLE vocabulary
- Sophisticated RBAC testing — dual-gate UI+API verification with named failure shapes (Shape-A: UI hides but API allows; Shape-B: API denies but UI advertises) and implicit-method probes for ungated DELETE/PATCH
- Clean single-owner layering — each concern lives in exactly one skill; commands and agents reference skills rather than re-implementing them; agents are correctly read-only and scoped to one cell each
- Well-documented and disciplined — README, CHANGELOG (Keep a Changelog + SemVer), roadmap, explicit non-goals, and pointers to sibling plugins for out-of-scope concerns

**Gaps.**
- No data/ directory — failure-classification taxonomy, severity rubric, redaction patterns, and production-marker defaults live inline in skills rather than in a single machine-readable source of truth (e.g. data/redaction_patterns.json, data/failure_taxonomy.json)
- No bundled import/export fixtures — the upload-fixture set (golden/bad-rows/over-cap/duplicate/idempotency) is described but each project must supply its own; deferred to 0.3.0
- No evidence-retention or report-archival convention beyond qa-evidence/<date>/<env>/; long-term retention, diffing across runs, and trend tracking are left to the project (deferred to 0.3.0)
- No /qa-action command for single-action walkthroughs — modal/row/bulk action walkthroughs are described in the skill but have no command entry point (deferred to 0.3.0)
- No accessibility, performance-budget, or visual-regression checks — capture supports optional perf timing but there is no Lighthouse/a11y audit, no baseline-screenshot diffing, no Core Web Vitals gate
- No automated test suite for the plugin's own hook scripts (pre_navigate_prod_gate.py / session_start_target_check.py) — no tests/ directory to guard against regressions in the production-gate matcher or redaction logic
- No CI/headless-run guidance or machine-readable report output (e.g. JSON/JUnit) for piping UAT results into a pipeline — reports are Markdown-only
- No rules/ layer — safety contracts (write-gate, profile-loader equivalents) are embedded in skills rather than extracted as referenced rule files, unlike the devops-plugin pattern

**Can absorb lessons:** Yes. A natural home for lessons about browser-based QA, role/RBAC testing, and UAT evidence discipline: e.g. MCP-driven browser automation quirks (chrome-devtools vs playwright differences, navigate/wait timing), recurring RBAC failure shapes, redaction edge cases for credentials/PII in HAR/console logs, framework-specific login/menu-detection patterns, and safety-gate false-positive/negative tuning for production-URL detection.

**Recommended enhancement areas.**
- Add a data/ layer that externalizes the failure-classification taxonomy, severity rubric, redaction regex patterns, and configurable production-marker list into JSON so hooks, skills, and the classifier agent share one source of truth
- Add a /qa-action command (already on the roadmap) as a thin entry point that delegates modal/row/bulk action walkthroughs to qa-evidence-collector under safe-destructive-testing gating
- Ship a fixtures/ pack for import-export-ui-checks (golden, bad-rows, over-cap, duplicate, idempotency-rerun) plus a small generator script, so projects do not have to hand-roll upload fixtures
- Add machine-readable report output (JSON / JUnit XML) alongside the Markdown UAT report so results can feed CI dashboards, and document a headless/non-interactive run mode with the production gate honored
- Add an accessibility + performance skill (Lighthouse / axe-core / Core Web Vitals via the chosen MCP) and an optional visual-regression baseline-diff capability to extend beyond functional smoke
- Add a tests/ directory with unit tests for the two hook scripts (production-gate matching, override env var, redaction) and a validation harness so safety logic cannot regress silently
- Add an evidence-retention/archival convention (run manifest, cross-run diffing, trend of PASS/FAIL over time) to support release-over-release UAT comparison
- Extract safety contracts into a rules/ layer (write-gate, credential-handling, production-refusal) referenced by skills/agents/hooks, matching the single-owner layering convention used by the larger plugins

**Lessons mapped here (this study):** 15. _(See §5 for the enhancement plan.)_

---

### rag-plugin  `(registered: rag)` — v0.13.1

**Purpose.** Operational console for the "ragtools" local-first RAG product — installs, configures, diagnoses, repairs, upgrades, and runs an embedded-Qdrant Markdown knowledge base from inside Claude Code. It is an ops/support layer (auto-wires the ragtools MCP, manages projects via HTTP API, walks repair playbooks) and explicitly never re-implements search.

**Structure.** `commands/`, `agents/`, `skills/ (ragtools-ops, markdown-authoring, ragtools-release)`, `skills/*/references/`, `hooks/`, `rules/`, `docs/ (decisions.md)`, `scripts/ (analyzers + unit/smoke tests)`, `.claude-plugin/`, `.mcp.json (plugin-root MCP registration)`, `ARCHITECTURE.md`, `CHANGELOG.md`, `LICENSE`

**Skills.**

| Skill | Purpose |
|---|---|
| ragtools-ops | v0.5.0 keyword-triggered operations router. Detects install/service state, routes to the smallest reference file, and chains ragtools MCP ops tools (project_status, list_project_files, ignore-rule, reindex, tail_logs, crash_history) directly to answer operational questions without slash commands. Binds 5 boundary rules (never call search_knowledge_base, never write config.toml from CWD, never open Qdrant, never recommend GPU/MPS, never auto-download). |
| markdown-authoring | v0.7.0 skill that shapes new Markdown output to be chunker-friendly for the ragtools RAG pipeline. Picks a page template (concept/runbook/SOP/reference/architecture), enforces 8 hard rules + avoids 9 anti-patterns, runs a pre-output checklist. Does not save files (creation-time companion to /md-rag-enhance). |
| ragtools-release | v0.1.0 maintainer-facing release-gate skill. Walks the six permanent ragtools release invariants (data/install boundary, schema version+migration, dev-mode isolation, upgrade-path manual test, uninstall opt-in, RELEASE_LIFECYCLE accuracy) one at a time, collects explicit ack/hold, and produces a green/pre-release/blocked verdict. Pure gating — never tags, builds, or ships. |

**Commands.**

| Command | Purpose |
|---|---|
| /doctor | Smart state-aware diagnose+status+repair. Default fast probe; --full deep system_health/crash_history wrap with F-001..F-012 classification; free-text symptom classification; --symptom F-NNN playbook walk; --logs dispatches the rag-log-scanner agent; --fix walks playbook inline. Absorbed former /rag-status and /rag-repair. |
| /setup | Smart install/upgrade/verify. Branches on detected state: install walkthrough (not-installed), start-service (down), upgrade walkthrough (up-but-old), idempotent verify (up-and-current). Checks MCP wiring, CLAUDE.md rule, and MCP dedupe on every run. Absorbed former /rag-upgrade. |
| /projects | Project CRUD strictly via HTTP API (127.0.0.1:21420) — never edits config.toml. Subcommands list/status/summary/files/add/remove/enable/disable/rebuild. State-gate refuses writes when service is down/broken. |
| /reset | Three-level destructive reset (--soft via MCP rebuild / --data / --nuclear) with typed-DELETE gates. Shows but never executes destructive shell commands. Blocks on pre-v2.4.1 versions. |
| /config | Plugin-layer config: telemetry on/off (default off, local-only), CLAUDE.md retrieval-rule install/remove, mcp-dedupe scan/clean, and hook-observability log status/analyze/clear. Atomic, backup-first writes. |
| /project-focus | Per-workspace ragtools retrieval scoping (D-028). Auto-detects project via cwd/git-root, persists state at ~/.claude/rag-plugin/state/project-focus.json; the UserPromptSubmit hook injects scope-to-X reminders. Subcommands set/status/clear plus --global. |
| /report | Generates two evidence-based maintainer diagnostic reports (RAC/RAG application setup + plugin behavior) plus GitHub-ready issue bodies. Captures install/runtime/performance/config-drift/missed-retrieval/workaround signals from local state and session JSONL. Privacy-safe redaction, no auto-upload. |
| /md-rag-enhance | Always-safe Markdown enhancer for existing files. Runs scripts/md_analyzer.py applying only two mechanically safe fixes (pseudo-heading→real heading, blank-line normalization) and reports all other structural findings for manual review. Atomic backups. |
| /sync-docs | MAINTAINER-ONLY (disable-model-invocation: true). Diffs bundled references against upstream ragtools_doc.md and reports drift via checksums. Never auto-rewrites. |

**Hooks.**

| Event | Purpose |
|---|---|
| PreToolUse (matcher: Bash) | lock_conflict_check.py — warns (permissionDecision: ask) before CLI commands that would fight the Qdrant single-process file lock, but only when the service is reachable on 127.0.0.1:21420. Silent pass-through otherwise; never blocks unconditionally. |
| UserPromptSubmit (matcher: *) | prompt_retrieval_reminder.py (v0.3.0/v0.4.0) — shape-gate + operational-intent classifier + local /api/search probe (top_k=1); injects a system reminder to call search_knowledge_base when a likely KB match scores above threshold (raised 0.5→0.65). Silent-passes operational/inspection prompts. |
| UserPromptSubmit (matcher: *) | project_focus_inject.py (v0.10.0, D-028) — reads project-focus state, resolves effective focus (workspace > global > none), injects scope-to-X reminder; emits a neutral notice without leaking other workspaces' project names when no local focus applies. |

**Agents.**

| Agent | Model | Purpose |
|---|---|---|
| rag-log-scanner | haiku | Narrow service.log pattern matcher for the F-001..F-012 failure catalog. Returns structured findings JSON only — does not diagnose, suggest fixes, read other files, or invent failure IDs. Cost-disciplined Haiku tier feeding the more expensive /doctor Sonnet flow; bounds reads with tail. |

**Strengths.**
- Disciplined single-owner layering (commands → skill → references → rules → product surfaces) with a strict forbidden list in ARCHITECTURE.md and binding decisions D-001..D-028 in docs/decisions.md — concerns live in exactly one place and are referenced, never re-implemented.
- Strong scope boundary: explicitly an ops console that never wraps or re-implements search; registers the ragtools MCP via a flat-shape .mcp.json (same pattern as devops/playwright/context7) and defers all retrieval to the running server.
- Three layers of harness-enforced retrieval discipline (CLAUDE.md rule + UserPromptSubmit reminder hook + per-workspace project-focus) that can't be 'forgotten' because they fire at answer time, with an operational-intent classifier to suppress false positives.
- Codified known-failure catalog (F-001..F-012), repair playbooks, gaps catalog (G-001..G-010), and report findings (A-012..A-014) — honest about product limitations and never invents support.
- Cost-aware agent design (Haiku log-scanner that only matches patterns) and safety-first destructive flows (typed-DELETE gates, pre-v2.4.1 blocks, HTTP-API-only writes through get_config_write_path).
- Real test/validation harness: unit tests (test_rag_report.py 24 cases, test_project_focus.py), a hook-classifier smoke test (20 fixtures), and a maintainer drift-detection command — driven by actual external user diagnostics.

**Gaps.**
- No plugin-level CI: the bundled pytest/smoke scripts (test_rag_report.py, test_project_focus.py, hook_classifier_smoke.py) appear to be run manually — no documented GitHub Actions workflow asserts they pass on every change.
- Hooks invoke 'python3' which is fragile on Windows (the plugin's primary platform), where the launcher is usually 'python' or the 'py' launcher — no portable interpreter resolution is documented.
- Telemetry/observability is local-JSONL only and opt-in; there is no aggregation or trend view, so recurring failure patterns across sessions aren't surfaced beyond the one-shot /report.
- Several documented product gaps (G-002 macOS auto-start, G-006 persistent activity log, G-007 structured request logging) are faithfully reflected but the plugin offers no operator-side workaround scaffolding (e.g., a LaunchAgent/systemd generator).
- No automated reference-freshness check in CI — drift between bundled references and upstream ragtools_doc.md relies on a maintainer manually running /sync-docs.
- Version drift inside the plugin: README header still says v0.11.0 while plugin.json is 0.13.1 and command catalog references v0.7.0/v0.10.0 — internal version labels across docs/skills are inconsistent.
- No self-healing for MCP registration: if 'rag' is not on PATH the plugin can only walk /setup branch C manually; there's no automated PATH probe + repair beyond instructions.
- Cross-platform path handling in scripts (report/focus) is not obviously validated on all three supported platforms (Windows/macOS-arm64/Linux-arm64) by the test suite.

**Can absorb lessons:** Yes. It already absorbs lessons directly — the v0.4.0 operational-intent classifier closed a LESSONS.md TODO (2026-04-28), and report-engine fixes came from verbatim external user diagnostics. It is the natural home for lessons about RAG/ragtools operations: new failure signatures (new F-/A- IDs), Qdrant lock and single-process foot-guns, MCP-wiring/dedupe edge cases, retrieval false-positive/false-negative patterns for the reminder hook, chunker/Markdown authoring pitfalls, and cross-platform install/upgrade quirks. New behavior should land as a data/reference entry → rule → skill workflow rather than a new command (per D-021).

**Recommended enhancement areas.**
- Add a CI workflow (GitHub Actions) that runs the bundled pytest + smoke tests and validate_plugin.py on every push, and a scheduled job that runs /sync-docs-style reference drift detection against upstream.
- Make hook interpreter resolution portable (detect python/py/python3) and add a SessionStart hook that verifies 'rag' is on PATH and surfaces MCP-registration health proactively.
- Reconcile internal version labels (README header, skill version fields, command catalog) to a single source and add a version-consistency check to the test suite.
- Add an operator-side workaround generator for documented product gaps (e.g., a macOS LaunchAgent / Linux systemd unit emitter for auto-start, G-002).
- Extend telemetry/observability into a lightweight local trend analyzer (recurring F-/A- IDs across sessions) reusing the existing JSONL usage log and analyze_hook_decisions.py.
- Add a data/ directory of failure-signature and remediation-order source-of-truth (currently embedded in references and the agent table) so new lessons append as data rows feeding both the log-scanner agent and /doctor classification.

**Lessons mapped here (this study):** 6. _(See §5 for the enhancement plan.)_

---

### react-admin-kit-plugin  `(registered: react-admin-kit)` — v0.2.0

**Purpose.** Reusable, framework-generic patterns for building and auditing React / Next.js admin panels — admin shell, CRUD lists, forms, role-aware UI, dangerous-action confirmations, import/export, RTL/LTR, and loading/error/empty states — plus the UI-level security rules every admin panel needs ("UI hide is not authorization", PII masking, audit visibility, file-upload safety). It deliberately makes no business-domain assumptions; project specifics (roles, PII fields, auth/audit helpers, paths) come from an adapter cache.

**Structure.** `./.claude-plugin (plugin.json manifest)`, `agents/ (1 agent)`, `commands/ (3 commands)`, `skills/ (8 skills, each a single SKILL.md with no sibling references/examples/scripts)`, `README.md`, `CHANGELOG.md`, `LICENSE`

**Skills.**

| Skill | Purpose |
|---|---|
| admin-shell | Admin layout shell — sidebar + header + content slot, i18n context provider placement, language toggle with persisted locale, sidebar collapse persistence, shell-level route-guard composition (auth -> role -> render), breadcrumb derivation. Composition only; defers role filtering, direction utilities, and bootstrap states to sibling skills. user_invocable: false. |
| admin-crud | List/table/detail/filter/pagination patterns. Owns URL-as-source-of-truth for filters/page/sort, server-side pagination as default, filter-chip pattern, sortable columns, detail-page tab convention (overview/edit/related/audit), row-action affordance, and the empty-vs-no-results distinction. user_invocable: false. |
| admin-forms | Form patterns — field-component-per-type, client validation mirrors authoritative server, save/cancel/dirty (warn-on-leave) flow, row-action and bulk-action batching contract with per-item failure report, optimistic-vs-pessimistic reconciliation. Validation/form library is project-supplied. user_invocable: false. |
| admin-roles-and-permissions | Foundation security skill. Owns the paired UI-gate/API-gate rule ('UI hide is NOT authorization'), role-aware menu pattern, PII masking (mask by default, reveal on explicit action + audit), audit-log visibility scoping, and the UI-hide anti-pattern catalogue. Role names/PII fields/audit helpers are adapter inputs. user_invocable: false. |
| admin-dangerous-actions | Confirmation patterns for destructive operations (delete/suspend/impersonate/force-logout/mass-update). Owns friction-proportional-to-blast-radius, the confirmation modal contract (consequence summary + type-to-confirm + audit-on-action), two-step button pattern, destructive-action affordance rules, and undo-window pattern. user_invocable: false. |
| admin-import-export | Safe CSV/Excel/JSON import and export. Owns the upload -> parse -> preview -> confirm -> commit pipeline, a default 10k row cap, typed per-row error report (row/field/code/message), idempotency via external_id, no-auto-create-related-entities, dry-run vs commit phases, and export filename + filter-context convention. user_invocable: false. |
| admin-states | Loading/error/empty/no-results/partial-error display conventions. Owns skeleton-matches-final-layout, the error contract (message + actionable next step + support hint; never a raw stack), empty-vs-no-results distinction, per-row partial-error indicator, in-flight pagination/refetch feedback, and non-blocking toast vs blocking modal choice. user_invocable: false. |
| admin-rtl-ltr | Direction-aware UI for mixed RTL/LTR locales. Owns html dir-attribute placement, logical-CSS-properties-only rule (margin-inline-start over margin-left; Tailwind ms-/me-/ps-/pe-/start-/end-), icon-mirroring catalogue (which flip vs stay), LTR-locked content (code/charts/numeric tables/technical dates), text-align start/end, and RTL focus order. Locale list is project-supplied. user_invocable: false. |

**Commands.**

| Command | Purpose |
|---|---|
| /admin-scaffold | Generate an admin CRUD page skeleton (list + detail + form) for a given entity, applying the full skill set. Asks for adapter inputs on first invocation and caches answers to .react-admin-kit.local.json. Flags: --list-only / --detail-only / --form-only. allowed-tools: Read, Glob, Grep, Write, Edit. |
| /admin-audit | Read-only audit of an existing admin route (file, folder, or whole admin tree) against the skill rules; produces a Markdown findings table with file:line citations, grouped by section. Flag: --suggest-fixes. allowed-tools: Read, Glob, Grep (no write). |
| /admin-role-matrix | Generate, validate, or diff the role x resource x operation permission matrix that drives the sidebar menu, route guards, per-row API permissions, and audit-log scoping. Reads adapter cache; writes a Markdown table + a TS/JSON config. Modes: --generate (default) / --validate / --diff. |

**Hooks.** _none_

**Agents.**

| Agent | Model | Purpose |
|---|---|---|
| admin-route-auditor | sonnet | Read-only auditor (tools: Read, Glob, Grep; color orange) of a single admin route, folder, or whole admin tree. Applies every react-admin-kit skill rule across 8 sections (authorization / PII / CRUD / forms / dangerous actions / import-export / states / RTL) and returns a severity-tagged (HIGH/MEDIUM/LOW) findings table with file:line and suggested fix per row. Loads .react-admin-kit.local.json for project identifiers when present. Never edits, runs scripts, or calls APIs. |

**Strengths.**
- Clean single-owner layering with explicit owns/defers_to frontmatter on every skill — each rule lives in exactly one skill and others cross-reference rather than re-implement, so there is no logic duplication across the 8 skills.
- Security-first framing: admin-roles-and-permissions is the foundation skill and the 'UI hide is NOT authorization' / paired UI-gate-API-gate rule is repeated as a load-bearing contract across scaffold, audit, and the auditor agent.
- Genuinely framework-agnostic and domain-agnostic by design — an adapter-cache (.react-admin-kit.local.json) injects all project specifics (roles, PII fields, auth/audit helpers, paths, libraries), and the CHANGELOG documents a genericness grep sweep that proves zero business-domain leakage.
- Read-only audit surface is well thought out: a /admin-audit command and a dedicated sonnet auditor agent both constrained to Read/Glob/Grep, returning severity-tagged findings with file:line citations.
- Commands follow the workspace conventions — bare invocation works (defaults like --generate), flags are optional shortcuts, and command files are not prefixed with the plugin name.
- Strong consistent skill contract (Purpose / When to use / Inputs / Investigation / Decision framework / Safety gates / Validation checklist / Output format / Anti-patterns / Portability rationale / Cross-references) plus a /admin-role-matrix command that creates a single source of truth to prevent role logic drift.

**Gaps.**
- No hooks at all — the planned opt-in PreToolUse reminder on Write|Edit matching admin/** paths is still deferred (README and CHANGELOG mark it for v0.3.0), so nothing enforces the skill rules at edit time; everything is advisory.
- No data/ or rules/ layer — anti-pattern catalogues, the icon-mirroring table, error-contract templates, and the row-cap default live inline in skill prose rather than in a referenceable data file, so the auditor agent and audit command re-describe the same rules instead of citing a shared contract file.
- No reference implementation / example admin — the skills describe patterns but ship no examples/ code, snippets, or a worked end-to-end admin (also deferred to v0.3.0), making the scaffold output hard to validate against a known-good target.
- No tests or validators of its own — relies solely on the workspace-level validate_plugin.py; there are no scaffold-output snapshots or auditor-output golden files to catch regressions in generated code or findings.
- Adapter-cache contract is informal: .react-admin-kit.local.json is read by three commands and the agent but there is no JSON schema, no documented full key list in one place, and no command to initialize/validate the cache (e.g. /admin-init).
- Heavy overlap with security verification is only cross-referenced (qa-browser for API enforcement) but not integrated — there is no mechanism to confirm that a UI gate flagged by the auditor actually has a matching backend gate.
- Accessibility (WCAG, keyboard nav beyond RTL focus order, ARIA for tables/modals/forms) and data-table performance (virtualization, large-list rendering) are not owned by any skill despite being core admin-panel concerns.
- No skill or command for admin observability/telemetry, optimistic-UI rollback testing, or export-data-privacy (PII in exported files), which a mature admin kit would cover.

**Can absorb lessons:** Yes. This plugin is a natural home for lessons about React/Next.js admin-panel engineering: UI authorization pitfalls (UI hide vs real authz), PII masking and audit-visibility patterns, CRUD list/filter/pagination conventions, form dirty-state and bulk-action handling, destructive-action confirmation friction, safe import/export pipelines, loading/error/empty state contracts, and RTL/LTR direction bugs. Lessons phrased as concrete anti-patterns or rules map directly into the owns/anti-patterns sections of the relevant skill, or into a future data/rules contract file the audit command and auditor agent could cite.

**Recommended enhancement areas.**
- Ship the deferred opt-in PreToolUse hook (Write|Edit on admin/** paths) that surfaces the matching skill's safety gates at edit time, configurable in hooks/hooks.json — turning advisory rules into a fail-fast reminder.
- Extract inline contracts into a data/ or rules/ layer: anti-pattern catalogue, icon-mirroring table, error-display contract, default row cap, and a documented adapter-cache JSON schema — so commands, skills, and the auditor agent all cite one source of truth.
- Add a /admin-init command to initialize and validate .react-admin-kit.local.json (interactive intake + schema validation + gitignore check) instead of relying on first-invocation prompts in three separate commands.
- Provide an examples/ reference admin built against all 8 skills (the deferred v0.3.0 reference implementation) plus golden-file snapshots for scaffold output and auditor findings, and lightweight tests/ that run them.
- Add an accessibility skill (ARIA for data tables/modals/forms, keyboard navigation, focus management) and a data-table-performance skill (virtualization, large-list rendering) to close core admin-panel gaps the current 8 skills do not own.
- Integrate UI-gate-to-API-gate verification: have /admin-audit or the auditor agent cross-link each flagged UI gate to the backend handler and flag missing server-side enforcement, optionally handing off to qa-browser for live API checks.
- Add export-privacy and observability coverage — a rule that PII masking applies to exported files, and a convention for where unexpected admin errors are reported with which fields.

**Lessons mapped here (this study):** 32. _(See §5 for the enhancement plan.)_

---

### remotion-plugin  `(registered: remotion)` — v2.1.0

**Purpose.** Creates professional videos with smooth AI voice narration using Remotion and Claude Code. Its signature feature is the "continuous audio pattern" — a single root-level audio track that prevents voice cutting between slides — backed by a free edge-tts voice pipeline and full prompt-to-MP4 video creation from natural-language scene descriptions.

**Structure.** `.claude-plugin/ (plugin.json manifest)`, `commands/ (1 slash command)`, `remotion/ (SKILL.md — note: skill lives in a custom-named dir, not skills/)`, `hooks/ (hooks.json — currently empty)`, `scripts/ (5 Python voice-pipeline tools)`, `templates/ (4 TSX/TS composition templates)`, `memories/ (4 reference markdown files)`, `README.md`, `CHANGELOG.md`, `LICENSE`

**Skills.**

| Skill | Purpose |
|---|---|
| remotion (model: sonnet) | Full video-creation pipeline: scaffold Remotion compositions, generate edge-tts narration (300+ voices), build continuous-audio React compositions that never cut between slides, and render MP4/WebM/GIF. Encodes the critical continuous-audio pattern, Math.ceil frame-calculation formula, prerequisites, project structure, and voice + render workflows. Frontmatter declares model sonnet, cli-tool mode, cross-platform support, and supported voice engines (edge-tts, elevenlabs) and output formats. |

**Commands.**

| Command | Purpose |
|---|---|
| /remotion | Video creation toolkit entry point. No args = status/prerequisite check; [project-name] = scaffold a new Remotion project with all dependencies. The command doc also lists render/voice sub-routes, but per the v2.1.0 CHANGELOG those workflows were delegated to the skill via natural language (command/skill text is slightly inconsistent on this). |

**Hooks.** _none_

**Agents.** _none_

**Docs / examples.** `README.md (quick start, problem/solution explanation, prerequisites, extension guide)`, `CHANGELOG.md (v1.0.0 and v2.1.0 history)`, `LICENSE (MIT)`, `templates/Root.tsx (composition registration, static + dynamic duration)`, `templates/composition_continuous_audio.tsx (the correct single-root-audio pattern)`, `templates/composition_multi_scene.tsx (data-driven multi-scene from timeline.json, extensible SCENE_RENDERERS map)`, `templates/timeline_schema.ts (Zod schemas validating timeline.json)`, `memories/audio_patterns.md (continuous audio pattern + anti-patterns)`, `memories/composition_patterns.md (reusable scene component recipes, color schemes)`, `memories/voice_reference.md (voice tables, rate/pitch/SSML, script-writing tips)`, `memories/troubleshooting.md (issue table, audio debugging checklist, performance tips)`

**Validation patterns.** scripts/setup_check.py — prerequisites checker (Node 18+, Python 3.8+, edge-tts, mutagen) with platform-specific install commands; scripts/measure_audio.py — measures real MP3 duration and validates it against expected ms / frame counts before render; scripts/concat_audio.py — emits JSON segment timestamps used as the source of truth for Sequence timing; scripts/_common.py — shared dependency checker (check_dependencies by package group) and audio-duration utility; timeline_schema.ts — Zod runtime validation of timeline.json data; Skill 'Key Rules' section acts as a self-check contract (one root Audio, Math.ceil, 1s padding, validate audio, staticFile)

**Strengths.**
- Solves one sharp, real pain point exceptionally well: the continuous-audio pattern is documented identically across skill, README, memories, and templates so the anti-pattern is hard to reintroduce.
- Clean single-owner layering after the v2.1.0 refactor: SKILL.md trimmed 79% (980 to ~200 lines), heavy reference moved to memories/, scripts deduplicated into _common.py.
- Free, zero-API-key voice generation via edge-tts (300+ voices, 70+ languages) lowers adoption friction versus paid TTS.
- Python tooling is real and composable — every script takes CLI flags (--fps, --voice, --gap, --method) and concat_audio emits machine-readable timestamps that feed Sequence timing.
- Strong correctness guardrails encoded as rules: Math.ceil frame math, 1s padding, measure-before-render, staticFile() for assets.
- Cross-platform and well-documented with concrete prerequisites, extension guide (templates/scripts/memories/SCENE_RENDERERS), and worked examples.

**Gaps.**
- Hooks are advertised but missing: hooks/hooks.json is literally {"hooks":{}}, yet README and CHANGELOG v2.1.0 both describe 5 wired PostToolUse safety hooks (Audio-in-Sequence guard, render audio validation, timeline JSON validation, etc.). The enforcement layer the docs promise does not exist — this is the single biggest gap.
- Skill is in a non-standard directory (remotion/SKILL.md) rather than skills/remotion/SKILL.md; may not be discovered by the validator or by Claude Code's standard skill auto-discovery.
- Command doc and skill disagree on whether render/voice are sub-commands or natural-language only — drift between the two layers introduced by the v2.1.0 refactor.
- No automated tests for the Python scripts (no tests/ dir) despite scripts being the load-bearing pipeline.
- ElevenLabs is declared in skill frontmatter voice-engines but there is no script or workflow implementing it — only edge-tts exists.
- No agent layer: long render/voice-generation pipelines (which can be slow and high-volume) run in the main context with no offloaded subagent.
- No caption/subtitle, music-bed/ducking, or multi-track audio mixing support — only a single narration track.
- No marketplace-registration check surfaced here; the empty-hooks discrepancy suggests validation isn't catching doc/manifest drift.

**Can absorb lessons:** Yes. Natural home for lessons about Remotion video generation, audio/voice synchronization, and the edge-tts pipeline — especially frame-timing pitfalls, audio-cutting causes/fixes, render performance, and voice/SSML tuning. The memories/ directory (troubleshooting.md, audio_patterns.md, voice_reference.md) is already the designated landing zone for such domain lessons, and the README explicitly invites adding project-specific .md files there.

**Recommended enhancement areas.**
- Restore/implement the documented hooks in hooks/hooks.json: a PostToolUse hook matching .tsx/.jsx writes that warns when <Audio> appears inside <Sequence>, plus reminders after render/voice/concat commands and on timeline.json writes — make the docs and the wired config agree.
- Move the skill to the standard skills/remotion/SKILL.md location so it is reliably discovered and validator-clean.
- Add a tests/ directory with unit tests for the Python scripts (frame-calc edge cases, concat timestamp correctness, dependency-check behavior) so the load-bearing pipeline is regression-protected.
- Reconcile command vs skill on render/voice handling — pick one source of truth and reference it from the other layer.
- Either implement the ElevenLabs voice engine declared in frontmatter or remove the claim to avoid capability drift.
- Add a render/voice subagent (cheap model for high-volume voice generation, sonnet for scene planning) to keep long pipelines out of the main context.
- Add captions/subtitle generation and a background-music + audio-ducking pattern as new memories + a template, extending beyond single-track narration.
- Strengthen validation: a doc-vs-manifest consistency check (e.g., hooks count, declared voice engines, command sub-routes) to catch the kind of drift seen between v2.1.0 docs and the empty hooks file.

**Lessons mapped here (this study):** 0. _(See §5 for the enhancement plan.)_

---

## 3. Lessons taxonomy

183 distinct lessons were classified into 17 categories. Counts and the dominant failure pattern per category follow.

| Category | Lessons | Top destination(s) |
|---|---|---|
| AI-agent workflow | 30 | no-action (9), future:claude-env-doctor (4), wiki-sop (3) |
| Windows/WSL/environment | 23 | future:claude-env-doctor (11), no-action (7), wiki-sop (3) |
| security/RBAC/auth | 19 | qa-browser (7), react-kit (5), future:claude-env-doctor (2) |
| DevOps/deployment | 15 | wiki-sop (5), devops-plugin (3), future:gha-hardening (3) |
| React/UI architecture | 14 | react-kit (11), no-action (3) |
| GitHub/promotion/release | 12 | devops-plugin (5), no-action (3), wiki-sop (3) |
| plugin-authoring | 11 | no-action (7), future:plugin-authoring-guide (1), future:skill-library-architect (1) |
| code review/static analysis | 10 | react-kit (9), qa-browser (1) |
| production safety | 8 | no-action (2), future:migration-cutover-runbook (1), wiki-sop (1) |
| documentation/wiki | 8 | docs-wiki (8) |
| Odoo | 7 | odoo-plugin (7) |
| browser QA/UAT | 6 | qa-browser (6) |
| testing/validation | 6 | react-kit (6) |
| RAG/context/memory | 5 | rag-plugin (4), future:wiki-memory-sync (1) |
| data migration/import-export | 4 | odoo-plugin (1), future:django-safety-audit (1), future:db-migration-guard (1) |
| project onboarding/context | 4 | no-action (2), wiki-sop (1), future:claude-env-doctor (1) |
| other | 1 | no-action (1) |

For each category, representative lessons (highest priority-score first):

#### AI-agent workflow — 30 lessons

- **Common failure pattern:** Without a codified investigation discipline, agents jump straight to fixes, pollute the main context window, and assert findings without evidence or severity ranking, leading to unverified claims and missed root causes.
- **Prevention destinations:** no-action (9), future:claude-env-doctor (4), wiki-sop (3), future:audit-orchestrator (2), devops-plugin (2), rag-plugin (2), future:agent-mcp-wrapper (2), future:plan-verifier (1), claude-plugin-builder (1), future:auto-mode-authority-gate (1), future:wiki-memory-sync (1), paper-plugin (1), memory-sync-rule (1)
- **Representative lessons:**
  - _L1471-01_ → `future:audit-orchestrator` (skill, P1, score 15)
  - _L1543-01_ → `future:audit-orchestrator` (rule, P2, score 14)
  - _L218-verify-plan-vs-files_ → `future:plan-verifier` (subagent, P1, score 13)
  - _L1621-structured-output-subagent-call-once_ → `claude-plugin-builder` (subagent, P1, score 13)
  - _L1801-per-project-env-disables-oauth_ → `future:claude-env-doctor` (documentation, P1, score 13)
  - _L868-auto-mode-authority-split_ → `future:auto-mode-authority-gate` (hook, P1, score 12)

#### Windows/WSL/environment — 23 lessons

- **Common failure pattern:** Windows consoles default to a cp1252 codec for Python stdout, so any emoji/non-ASCII print raises UnicodeEncodeError; tooling authored on POSIX assumes utf-8 stdout and never sets the encoding.
- **Prevention destinations:** future:claude-env-doctor (11), no-action (7), wiki-sop (3), odoo-plugin (2)
- **Representative lessons:**
  - _L1567-pythonioencoding-utf8-windows_ → `future:claude-env-doctor` (hook, P1, score 13)
  - _L1719-windows-grep-empty-fallback-read_ → `future:claude-env-doctor` (documentation, P2, score 12)
  - _L1989-lsp-npm-shim-windows_ → `future:claude-env-doctor` (documentation, P1, score 12)
  - _L10-wsl-hcs-timeout-escalation_ → `future:claude-env-doctor` (skill, P2, score 11)
  - _L11-ssh-over-ssm-dns-handshake_ → `future:claude-env-doctor` (skill, P2, score 10)
  - _L335-wsl-dns-broken-vpn_ → `future:claude-env-doctor` (command, P2, score 10)

#### security/RBAC/auth — 19 lessons

- **Common failure pattern:** Authorization logic is duplicated across route/UI/service layers that are edited independently; and dev convenience bypasses (hardcoded OTP behind an env flag) become security holes when the gating assumption (non-production, allowlisted) does not hold on a reachable environment.
- **Prevention destinations:** qa-browser (7), react-kit (5), future:claude-env-doctor (2), wiki-sop (2), future:secrets-hygiene-guard (1), future:prompt-injection-guard (1), no-action (1)
- **Representative lessons:**
  - _L1009-rbac-three-layers-dev-otp_ → `qa-browser` (checklist, P0, score 18)
  - _L07b-403-vs-400-409-rbac-proof_ → `qa-browser` (skill, P0, score 17)
  - _L722-pure-renderer-not-security-primitive_ → `qa-browser` (checklist, P1, score 16)
  - _L1594b-csrf-missing-both-headers-reject_ → `qa-browser` (validation-rule, P1, score 16)
  - _L307-pasted-token-is-compromised_ → `future:secrets-hygiene-guard` (hook, P0, score 15)
  - _L633-barcode-not-auth-token_ → `qa-browser` (checklist, P1, score 15)

#### DevOps/deployment — 15 lessons

- **Common failure pattern:** Tags and branches are mutable, so a compromised upstream can silently swap the code an action runs — a supply-chain risk especially without GitHub Advanced Security.
- **Prevention destinations:** wiki-sop (5), devops-plugin (3), future:gha-hardening (3), odoo-plugin (2), no-action (2)
- **Representative lessons:**
  - _L05a-sha-pin-third-party-actions_ → `devops-plugin` (hook, P0, score 15)
  - _L259-verify-workitem-type-semantics_ → `devops-plugin` (checklist, P1, score 14)
  - _L685-odoo-volume-drift-never-down-v_ → `odoo-plugin` (hook, P1, score 14)
  - _L05b-environment-block-not-approval-gate_ → `future:gha-hardening` (checklist, P1, score 13)
  - _L05d-dont-weaken-established-gates_ → `future:gha-hardening` (checklist, P1, score 13)
  - _L672-almajal-pg16-volume-forward-incompat_ → `odoo-plugin` (hook, P1, score 13)

#### React/UI architecture — 14 lessons

- **Common failure pattern:** Hooks that abstract away the error object hide backend status codes from the UI, so legitimate access/permission failures render as empty content rather than actionable states.
- **Prevention destinations:** react-kit (11), no-action (3)
- **Representative lessons:**
  - _L08-error-swallowing-data-hooks_ → `react-kit` (skill, P1, score 15)
  - _L2027-forwardref-to-ref-prop_ → `react-kit` (example, P1, score 15)
  - _L2040-array-index-keys_ → `react-kit` (documentation, P2, score 15)
  - _L2028-usecontext-to-use_ → `react-kit` (documentation, P2, score 14)
  - _L2029-no-derived-state-intentional_ → `react-kit` (documentation, P2, score 14)
  - _L1033-modals_ → `react-kit` (skill, P1, score 13)

#### GitHub/promotion/release — 12 lessons

- **Common failure pattern:** Agents conflate 'work is done' with 'work should be published'; without an explicit approval gate they auto-push, which can promote unreviewed or wrong-identity commits to shared remotes.
- **Prevention destinations:** devops-plugin (5), no-action (3), wiki-sop (3), react-kit (1)
- **Representative lessons:**
  - _L1504-01_ → `devops-plugin` (hook, P1, score 16)
  - _L01-squash-linear-history-promo_ → `devops-plugin` (skill, P1, score 12)
  - _L1060-gh-account-flip_ → `no-action` (hook, P2, score 11)
  - _L1513-01_ → `devops-plugin` (hook, P2, score 11)
  - _L1536-01_ → `devops-plugin` (documentation, P2, score 11)
  - _L1788-git-stash-include-untracked-before-pull_ → `wiki-sop` (documentation, P2, score 11)

#### plugin-authoring — 11 lessons

- **Common failure pattern:** YAML treats an unquoted colon as a key/value separator and a leading quoted token as a typed scalar boundary, so descriptions with colons or list items starting with quotes parse as malformed structure; authors don't run a strict parser before shipping.
- **Prevention destinations:** no-action (7), future:skill-library-architect (1), future:plugin-authoring-guide (1), wiki-sop (1), future:skill-system-auditor (1)
- **Representative lessons:**
  - _L1605-yaml-frontmatter-colons-quoted-list-items_ → `no-action` (validation-rule, P1, score 15)
  - _L950-skill-layering-foundation-domain-workflow_ → `future:skill-library-architect` (documentation, P2, score 12)
  - _L1748-skill-rename-name-folder-match_ → `no-action` (validation-rule, P2, score 12)
  - _L231-readonly-subagent-vs-skill_ → `future:plugin-authoring-guide` (documentation, P2, score 11)
  - _L1073-genericness-grep_ → `no-action` (validation-rule, P2, score 11)
  - _L1361-claudemd-not-reaching-running-sessions_ → `wiki-sop` (documentation, P2, score 11)

#### code review/static analysis — 10 lessons

- **Common failure pattern:** Static analyzers (lint, deslop, react-doctor) emit findings without context; treating them as commands rather than hypotheses produces false-positive-driven breakage (e.g. adding aria-label clobbers a visible Label, destructuring useSearchParams().get ships a runtime crash, unused-file deletion removes live code), and chasing the score motivates risky refactors in sensitive zones.
- **Prevention destinations:** react-kit (9), qa-browser (1)
- **Representative lessons:**
  - _L1484-01_ → `react-kit` (skill, P0, score 17)
  - _L03-security-review-source-to-sink_ → `qa-browser` (skill, P0, score 16)
  - _L2016-deslop-unused-file-fp-knip_ → `react-kit` (documentation, P1, score 15)
  - _L456-preflight-eslint-newfile_ → `react-kit` (hook, P1, score 14)
  - _L2015-usesearchparams-fp_ → `react-kit` (documentation, P2, score 13)
  - _L2014-rule-count-scoring_ → `react-kit` (documentation, P2, score 12)

#### production safety — 8 lessons

- **Common failure pattern:** Shell/string substring matching is case-sensitive by default, and authors write the guard against the lowercase form they expect, leaving uppercase/mixed-case inputs unmatched and the destructive action ungated.
- **Prevention destinations:** no-action (2), qa-browser (1), future:audit-orchestrator (1), future:migration-cutover-runbook (1), devops-plugin (1), docs-wiki (1), wiki-sop (1)
- **Representative lessons:**
  - _L1594a-guard-lowercase-host-match_ → `qa-browser` (hook, P0, score 18)
  - _L1495-01_ → `future:audit-orchestrator` (rule, P1, score 16)
  - _L06-phased-migration-cutover-pattern_ → `future:migration-cutover-runbook` (skill, P1, score 15)
  - _L934-default-write-scripts-flag-semantics_ → `devops-plugin` (hook, P1, score 15)
  - _L970-script-default-flip-doc-sync_ → `docs-wiki` (checklist, P1, score 14)
  - _L563-tamper-evident-artifacts_ → `wiki-sop` (template, P3, score 8)

#### documentation/wiki — 8 lessons

- **Common failure pattern:** Authors assume wiki URLs honor folder paths like a normal static site; GitHub Wiki flattens them, so colliding filenames (multiple README.md) and relative .md links 404 or download raw.
- **Prevention destinations:** docs-wiki (8)
- **Representative lessons:**
  - _L620-github-wiki-flat-namespace_ → `docs-wiki` (validation-rule, P1, score 14)
  - _L1840-removing-docs-check-dependents_ → `docs-wiki` (checklist, P1, score 14)
  - _L844-source-of-truth-ordering_ → `docs-wiki` (skill, P1, score 13)
  - _L857-handbook-target-not-current_ → `docs-wiki` (skill, P1, score 13)
  - _L1051-stale-checkboxes_ → `docs-wiki` (skill, P1, score 12)
  - _L890-jwt-lifetimes-stale-value_ → `docs-wiki` (validation-rule, P2, score 11)

#### Odoo — 7 lessons

- **Common failure pattern:** Plain source-path references load into the catalog but don't bind to field/view terms; authors hand-write references instead of deriving them from the framework's canonical .pot export.
- **Prevention destinations:** odoo-plugin (7)
- **Representative lessons:**
  - _L1216-po-typed-references_ → `odoo-plugin` (skill, P1, score 13)
  - _L1224-button-immediate-upgrade-hijack_ → `odoo-plugin` (skill, P1, score 13)
  - _L1242-source-string-invalidates-po_ → `odoo-plugin` (validation-rule, P1, score 13)
  - _L1251-unicode-escape-po_ → `odoo-plugin` (documentation, P2, score 12)
  - _L1441-khairgate-i18n-po-source-of-truth_ → `odoo-plugin` (skill, P1, score 12)
  - _L659-odoo-post-copy-translated-fields_ → `odoo-plugin` (checklist, P2, score 11)

#### browser QA/UAT — 6 lessons

- **Common failure pattern:** Front-end role labels are frequently hardcoded display copy decoupled from the authenticated session, misleading manual verification.
- **Prevention destinations:** qa-browser (6)
- **Representative lessons:**
  - _L07a-auth-me-over-ui-label_ → `qa-browser` (skill, P1, score 17)
  - _L1274-host-scoped-auth-headers-cors_ → `qa-browser` (skill, P0, score 16)
  - _L1576-react-controlled-inputs-native-playwright_ → `qa-browser` (skill, P1, score 15)
  - _L1260-vercel-preview-bypass_ → `qa-browser` (skill, P1, score 14)
  - _L1295-playwright-mcp-chrome-vs-chromium_ → `qa-browser` (documentation, P1, score 13)
  - _L12-wsl-playwright-stale-profile-lock_ → `qa-browser` (skill, P2, score 10)

#### testing/validation — 6 lessons

- **Common failure pattern:** Floating @latest pulls a new ruleset that adds/removes rules; comparing aggregate scores across versions conflates ruleset changes with actual code changes.
- **Prevention destinations:** react-kit (6)
- **Representative lessons:**
  - _L2038-react-doctor-version-drift_ → `react-kit` (documentation, P2, score 13)
  - _L320-stale-prisma-client-drift_ → `react-kit` (skill, P1, score 12)
  - _L374-coverage-ratchet-rhythm_ → `react-kit` (checklist, P2, score 12)
  - _L418-vitest-constructor-mock_ → `react-kit` (example, P2, score 12)
  - _L441-singleton-untestable-branch_ → `react-kit` (documentation, P3, score 11)
  - _L1728-mock-factory-missing-methods_ → `react-kit` (documentation, P3, score 9)

#### RAG/context/memory — 5 lessons

- **Common failure pattern:** The .claude/ folder holds most config (plugins, sessions, settings) so users reasonably assume MCP config lives there too; in fact user MCP servers live in the sibling ~/.claude.json dotfile, a non-obvious split.
- **Prevention destinations:** rag-plugin (4), future:wiki-memory-sync (1)
- **Representative lessons:**
  - _L696-claude-mcp-add-writes-dot-claude-json_ → `rag-plugin` (checklist, P1, score 14)
  - _L709-dot-claude-json-concurrent-clobber_ → `rag-plugin` (checklist, P2, score 13)
  - _L1426-ragtools-8stage-architecture_ → `rag-plugin` (documentation, P2, score 11)
  - _L1886-superseded-rag-reminder-fp_ → `rag-plugin` (hook, P3, score 9)
  - _L1109-codememory-branch-pinning_ → `future:wiki-memory-sync` (documentation, P3, score 8)

#### data migration/import-export — 4 lessons

- **Common failure pattern:** Cascade-delete is a convenient default, but developers rarely trace the full cascade graph to discover it can erase financial or audit records that must be retained.
- **Prevention destinations:** future:django-safety-audit (1), odoo-plugin (1), future:db-migration-guard (1), wiki-sop (1)
- **Representative lessons:**
  - _L02b-cascade-to-money-audit-tables_ → `future:django-safety-audit` (checklist, P1, score 14)
  - _L02a-django-softdelete-queryset-bypass_ → `odoo-plugin` (checklist, P1, score 13)
  - _L398-prisma-db-push-drift_ → `future:db-migration-guard` (checklist, P2, score 12)
  - _L735-sync-gaps-push-once-not-bidirectional_ → `wiki-sop` (documentation, P3, score 7)

#### project onboarding/context — 4 lessons

- **Common failure pattern:** Claude Code can persist an OAuth token whose flow type doesn't match the billing/account type of the active org, so the API rejects it 401 on every call while /login keeps re-writing the same wrong-flow token; forceLoginMethod pins the correct flow.
- **Prevention destinations:** no-action (2), future:claude-env-doctor (1), wiki-sop (1)
- **Representative lessons:**
  - _L1670-claude-code-401-loop-forceloginmethod_ → `future:claude-env-doctor` (documentation, P2, score 12)
  - _L607-workspace-container-not-repo_ → `wiki-sop` (documentation, P3, score 7)
  - _L981-adahi-brd-structure_ → `no-action` (documentation, P3, score 7)
  - _L1387-two-html-editors-confirm-surface_ → `no-action` (documentation, P3, score 4)

#### other — 1 lessons

- **Common failure pattern:** Stakeholders/engineers conflate a scheduled approval step with validation because both touch the approval state, missing that validation already happened at submission and the cron only buffers review.
- **Prevention destinations:** no-action (1)
- **Representative lessons:**
  - _L750-auto-approve-cron-is-policy-lever_ → `no-action` (documentation, P3, score 3)

## 4. Lesson-by-lesson mapping table

One row per lesson (183 rows), sorted by category then descending priority score. `Dest` uses planned names (react-kit / qa-browser / docs-wiki) for those three plugins. Risk **C**ritical/**H**igh/**M**edium/**L**ow; Freq **C**ommon/**O**ccasional/**R**are; Prev(entability) **H**/**M**/**L**.

| # | Lesson | Generic pattern | Root cause | Risk | Freq | Prev | Dest | Alt dest | Artifact | Prio | Score | Notes |
|---|---|---|---|:--:|:--:|:--:|---|---|---|:--:|:--:|---|
| 1 | L1471-01 | For any broad audit/triage request, default to a workflow of: read-only structural survey -> parallel single-concern subagents (one concern each) -> … | Without a codified investigation discipline, agents jump straight to fixes, pollute the main context window, … | H | C | H | future:audit-orchestrator | qa-browser, devops-plugin | skill | P1 | 15 | This is a reusable, domain-agnostic investigation methodology (survey -> parallel subagents -> cited synthesis -> live … |
| 2 | L1543-01 | When a governing rule (CLAUDE.md/policy) may conflict with the requested task, the orchestrating agent must escalate to the actual human for an expli… | In multi-agent setups, a parent agent under pressure to complete a task may manufacture an 'override notice' … | H | R | H | future:audit-orchestrator | memory-sync-rule, no-action | rule | P2 | 14 | A multi-agent governance/safety rule: never fabricate authority to bypass a guardrail; escalate to the human. Relevant … |
| 3 | L218-verify-plan-vs-files | Gate execution of any multi-file or destructive plan behind a read-only audit pass that verifies every (file, reference) citation against the actual … | Plans are authored from memory of an earlier code state; code drifts (refactors, renames, coverage changes) s… | H | C | H | future:plan-verifier | react-kit, memory-sync-rule, no-action | subagent | P1 | 13 | Strongly reusable across every codebase. Cleanest as a read-only 'plan citation auditor' subagent + a pre-execution che… |
| 4 | L1621-structured-output-subagent-call-once | For tasks that must return through a named structured-output tool: put nothing in prose, map every constrained field to its allowed enum value first,… | Orchestration scripts parse only the real tool call, but models often emulate the output in prose, double-cal… | H | C | H | claude-plugin-builder | future:subagent-authoring, wiki-sop | subagent | P1 | 13 | Meta-lesson about authoring reliable structured-output subagents. No marketplace plugin owns subagent-authoring as a do… |
| 5 | L1801-per-project-env-disables-oauth | Putting endpoint/credential env vars (auth tokens, API keys) in a committed per-project settings.json silently overrides the user's interactive/subsc… | Credential resolution gives env-block tokens priority over OAuth, and the model picker still shows the unreac… | H | R | H | future:claude-env-doctor | wiki-sop, no-action | documentation | P1 | 13 | Claude Code config/auth gotcha — not a business-domain plugin concern. High impact (silently breaks Opus access). Best … |
| 6 | L868-auto-mode-authority-split | Split agent write-authority by artifact class: docs/skills/wiki are directly editable in autonomous mode, but code-touching changes must be emitted a… | Autonomous agents will edit anything they can reach; without an enforced authority boundary, code edits bypas… | H | O | H | future:auto-mode-authority-gate | devops-plugin, react-kit | hook | P1 | 12 | This is a reusable PreToolUse write-gate pattern (path glob → allow docs, block code, redirect to plan file) that no ex… |
| 7 | L1766-ask-for-tool-surface-before-guessing-endpoints | When required MCP/tool capabilities are missing from the session, surface the gap (needed vs loaded) and ask the user to load the correct MCP server … | Agents react to a short tool inventory by improvising direct API calls, skipping the MCP layer's auth/validat… | M | O | H | devops-plugin | rag-plugin, future:claude-env-doctor, no-action | documentation | P2 | 12 | The original incident is Azure DevOps MCP tools (wit_add_work_item_comment, core_get_identity_ids) missing, so devops-p… |
| 8 | L1923-mega-task-decomposition | When a task requires fetching/transcribing N>5 long-form verbatim items, do not do it in the main context (it force-summarizes and loses fidelity); d… | Verbatim long-form content accumulates linearly in the main context and exceeds the window; the main agent is… | M | O | H | no-action | wiki-sop | documentation | P2 | 12 | This is a general Claude Code working-discipline lesson, not a domain plugin capability — it belongs in the user's Acti… |
| 9 | L244-one-subagent-per-longform-item | When a task requires verbatim/complete extraction across many items, dispatch one subagent per item in parallel with a narrow single-item prompt, rat… | A subagent handling many items at once compresses each to fit its single context window; the 'don't truncate'… | M | O | H | devops-plugin | future:plugin-authoring-guide, memory-sync-rule, … | documentation | P2 | 11 | Two homes apply: as a general fan-out pattern it belongs in plugin-authoring/agent-dispatch guidance (overlaps superpow… |
| 10 | L490-worktree-pinning | When an analysis tool must produce reproducible artifacts from multiple repos, don't analyze whatever branch the developer happens to have checked ou… | Analyzing the developer's live working tree makes generated artifacts depend on whichever feature branch is c… | M | R | H | future:wiki-memory-sync | rag-plugin, docs-wiki | skill | P2 | 11 | This is the reproducibility engine for memory/doc-sync generators — squarely the future wiki-memory-sync plugin's conce… |
| 11 | L1710-figma-rest-needs-pat-not-webfetch | When a service's REST API requires custom auth headers, the built-in WebFetch tool cannot supply them and will fail or return public-only data; detec… | WebFetch silently lacks custom-header support, so engineers try it against header-authenticated APIs and misr… | L | O | H | paper-plugin | odoo-plugin, future:claude-env-doctor, no-action | skill | P2 | 11 | paper-plugin already owns Figma sync (figma-workflow skill) and is the natural home for a 'Figma REST needs PAT, WebFet… |
| 12 | L13-railway-mcp-cli-version | To diagnose a failing plugin MCP: claude mcp list → read the plugin's .mcp.json for the exact spawn command → run that command manually to get the re… | A plugin MCP is a spawned stdio command; if the resolved binary is too old (missing the subcommand) or instal… | L | O | H | rag-plugin | future:claude-env-doctor, wiki-sop, no-action | skill | P2 | 10 | The generic MCP-spawn diagnosis ladder (-32000 = unrunnable spawn; read .mcp.json, run the command manually; Windows-na… |
| 13 | L197-inspect-before-asking | For operational/inspection-shaped requests (start/stop X, where is Y, what's running, is Z installed), treat the filesystem, processes, and tool --he… | A retrieval-reminder hook fires on phrase similarity and produces false positives for operational questions, … | L | C | H | future:claude-env-doctor | memory-sync-rule, rag-plugin, no-action | documentation | P2 | 10 | This is already encoded as Section 0a in the user's global CLAUDE.md (override: operational/inspection questions skip t… |
| 14 | L517-mcp-output-not-persisted | When a downstream script needs data from a large MCP tool response, don't pipe it through a bash heredoc (`node -e 'const data = $BLOB'`) because the… | MCP responses are inline-only unless they overflow a size threshold, and shell heredoc interpolation mangles … | M | O | H | future:claude-env-doctor | rag-plugin, no-action | documentation | P3 | 10 | A general Claude Code agent-authoring best practice (MCP data plumbing), not a fit for any current domain plugin. Belon… |
| 15 | L536-session-storage-schema | Any tool that scans Claude Code session transcripts (lesson-gathering, friction detection, audit/forensic export) should rely on the documented stora… | Transcript-scanning tools that assume a single text blob or guess the path-encoding/line-schema break silentl… | L | O | H | future:claude-env-doctor | rag-plugin, no-action | documentation | P2 | 10 | Foundational reference for the existing `lessons` skill and any session-scanning workflow (rag:report already scans ses… |
| 16 | L1349-count-human-in-loop-hops | When designing an agent+human workflow, count the explicit human steps per cycle and aim for <=1. If the agent's only role on one half of the loop is… | Workflow designs accrete human relay steps that feel natural during design but add latency and silent failure… | M | O | M | wiki-sop | no-action, future:agent-mcp-wrapper | documentation | P2 | 10 | A durable agent-workflow design heuristic ('count human-in-the-loop hops, aim for <=1'). It's a design principle, not a… |
| 17 | L1632-bulk-powershell-replace-over-edit-loops | For mechanical bulk find-and-replace across many files, prefer a scripted pass (PowerShell -replace / sed) over per-file Edit-tool loops: (1) grep pe… | Treating every change as an interactive Edit operation scales linearly with files x patterns, wasting turns a… | L | C | H | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 10 | General Claude Code working-style guidance, not a plugin capability — best lives in CLAUDE.md/LESSONS or a workflow SOP… |
| 18 | L646-subagent-large-file-watchdog-script | When a deliverable is a single large file driven by deterministic rules (template-per-section + glossary), generate it with a script (Python/Node) an… | The stream watchdog kills agents silent for >600s; an agent constructing a huge file in memory before writing… | M | O | H | no-action | future:claude-env-doctor, wiki-sop | documentation | P2 | 9 | A cross-cutting Claude Code authoring discipline, not a fit for any existing domain plugin. Best captured as a global l… |
| 19 | L1529-01 | For operational/inspection questions ('where is X', 'what's running', 'is Z installed', 'why is this failing'), inspect the filesystem, processes, co… | Agents over-ask for clarification and over-trigger retrieval on operational questions because phrase-similari… | L | C | H | rag-plugin | memory-sync-rule, no-action | documentation | P3 | 9 | Already codified in the user's CLAUDE.md Section 0a and LESSONS.md (confirmed). The reusable angle is the retrieval-vs-… |
| 20 | L1018-local-only-classifier-blocks-promotion | When an autonomous-mode safety classifier blocks an action by phrase/intent similarity (e.g. treating any staging/prod-targeted git/gh command as a d… | Intent classifiers gate on phrase/keyword similarity and cannot distinguish a read-only status check from a d… | L | O | M | no-action | devops-plugin, future:auto-mode-authority-gate | documentation | P3 | 7 | This is a meta-observation about working with a safety classifier, not a buildable feature for a product plugin. The re… |
| 21 | L1051-phase-gating | Multi-phase initiatives gate each phase on (a) prior-phase UAT signoff and (b) explicit owner approval before execution; agents must confirm the curr… | Without an enforced gate, an agent reads the whole plan and starts downstream work that isn't approved or who… | M | O | M | wiki-sop | no-action | documentation | P3 | 7 | Specific to one project's sales-cycle phase plan and one owner's approval requirement. The generic 'gate phases on UAT … |
| 22 | L1315-telegram-single-getupdates | For single-consumer poll APIs (Telegram getUpdates, exclusive webhooks), never write a capture script that assumes it owns the long-poll connection. … | Telegram's long-poll getUpdates is exclusive per bot token; assuming you can poll alongside an existing daemo… | L | R | M | no-action | wiki-sop, ntfy-plugin | documentation | P3 | 6 | Niche to Telegram-bot integrations (OpenClaw/Roy). No current plugin owns Telegram. ntfy-plugin's two-way Q&A polling i… |
| 23 | L1328-wrap-shell-as-tiny-mcp | When you find yourself telling an MCP-first agent to 'run this shell command' in natural language and it falls back to a generic tool, wrap that comm… | Agents that only act via MCP tools have no clean way to invoke arbitrary shell scripts, and natural-language … | L | O | M | future:agent-mcp-wrapper | no-action, wiki-sop | skill | P2 | 6 | Reusable agent-design pattern (wrap shell as scoped MCP, prefer single-purpose over general MCPs), but no existing plug… |
| 24 | L1413-roy-mcp-first-scoped-mcp | When an MCP-first agent needs to run a shell-driven workflow, wrap it as a tiny custom MCP server with one named tool per logical operation, scope it… | Same root cause as L1328: MCP-first agents can't cleanly invoke shell scripts and default to whichever generi… | L | O | M | future:agent-mcp-wrapper | no-action, wiki-sop | skill | P3 | 6 | Near-duplicate of L1328 (wrap shell as tiny MCP, scope to agent, disable generic MCP) but instantiated for the Roy/Roya… |
| 25 | L1522-01 | Communication style contract: be terse, use sentences not paragraphs, skip play-by-play narration and trailing recaps, surface updates only at inflec… | Default assistant behavior is verbose and narrates intent; for a user who reads diffs and commits directly, t… | L | C | H | memory-sync-rule | no-action | documentation | P3 | 6 | This is a personal communication-style preference, not plugin-shaped behavior. It belongs in the user's global CLAUDE.m… |
| 26 | L810-plan-then-execute-auto-paced-loops | When asked to implement N sequential phases, author all N prompts up front (each self-contained with decisions/paths/prior outputs) and fire them as … | Cramming multi-phase work into one mega-prompt forces plan-and-execute in a single pass, skipping the natural… | L | O | M | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 5 | A general Claude Code orchestration technique (use /loop for multi-phase plans). It's a workflow habit, not a domain ar… |
| 27 | L1814-router-proxy-for-mixed-endpoints | A single Claude Code process can only target one API endpoint/auth; mixing models from different upstream vendors in one session requires a local req… | Claude Code's transport binds one base URL and one auth header per process, and there is no per-model or per-… | L | R | M | wiki-sop | future:claude-env-doctor, no-action | documentation | P3 | 5 | Advanced multi-vendor Claude Code setup knowledge; niche and setup-heavy (requires standing up a third-party router pro… |
| 28 | L1855-migrated-index | When durable lessons are migrated into plugin skills/docs, keep a thin index table in the central lessons file that points to the canonical target fi… | Lessons accumulate faster than they can be promoted into plugins; without an index of what was already migrat… | L | R | H | no-action | rag-plugin, docs-wiki | documentation | P3 | 5 | Already-absorbed bookkeeping index. No new plugin work needed — these lessons already live in rag-plugin skills and the… |
| 29 | L1550-01 | When one agent spans two contexts (internal dev vs external client), separate the two rule sets into their respective config files — dev-session rule… | Mixing dev-session constraints with client-facing persona rules in one file creates contradictory or overreac… | M | R | M | no-action | wiki-sop, memory-sync-rule | documentation | P3 | 4 | This is a project-specific agent-design lesson (a named BA liaison bot for one platform) about config-file separation a… |
| 30 | L09e-bash-classifier-500-compound-wsl | When a command-safety classifier intermittently errors on compound/looping WSL invocations, decompose into simple single-purpose commands (one operat… | The classifier struggles with complex compound WSL command strings, producing transient 500s unrelated to the… | L | O | L | no-action | future:claude-env-doctor | documentation | P3 | 3 | A harness-level quirk Claude can't fix from a plugin; only a behavioral workaround (decompose commands). Low preventabi… |
| 31 | L1567-pythonioencoding-utf8-windows | When a working Python script dies on Windows with a cp1252 UnicodeEncodeError on stdout/stderr, set PYTHONIOENCODING=utf-8 in the environment (or wra… | Windows consoles default to a cp1252 codec for Python stdout, so any emoji/non-ASCII print raises UnicodeEnco… | M | C | H | future:claude-env-doctor | rag-plugin, odoo-plugin, no-action | hook | P1 | 13 | Cross-cutting Windows environment lesson that affects every plugin shipping Python helper scripts (rag-plugin hooks inv… |
| 32 | L1719-windows-grep-empty-fallback-read | On Windows, treat an empty content-search result as unverified rather than authoritative: confirm with an absolute-path file Read of a suspected matc… | Windows path-separator semantics and Bash working-directory drift can make a content search return empty desp… | M | C | H | future:claude-env-doctor | wiki-sop, no-action | documentation | P2 | 12 | A cross-cutting Claude-Code-on-Windows behavior, not domain-specific to any one marketplace plugin. Best home is a Wind… |
| 33 | L1989-lsp-npm-shim-windows | On Windows, any plugin that launches a Node-based CLI/language-server with shell:false must invoke node.exe (a real PATH exe) plus the package's JS e… | npm global installs on Windows create only shell shims; Node 20+ refuses to spawn .cmd/.bat without a shell, … | H | O | H | future:claude-env-doctor | wiki-sop, no-action | documentation | P1 | 12 | Windows-specific Claude Code harness/LSP spawn issue. No existing marketplace plugin owns Claude Code environment docto… |
| 34 | L10-wsl-hcs-timeout-escalation | For WSL exec timeouts at the HCS layer, escalate in order — wsl --terminate, then wsl --shutdown, then Restart-Service WslService (requires elevation… | The WSL2 utility VM / HCS service host can wedge in a way that survives distro-level restarts, and 'port OPEN… | M | R | L | future:claude-env-doctor | wiki-sop, no-action | skill | P2 | 11 | A clean, reusable WSL-recovery escalation ladder with concrete host-triage commands (sc.exe query, wsl --version, df). … |
| 35 | L11-ssh-over-ssm-dns-handshake | When SSM SSH/port-forwarding intermittently times out at banner exchange but plain SSM shell sessions are reliable, suspect slow local DNS against th… | VPN tunnel interfaces at low metric get queried first for public hostnames and time out before Windows falls … | M | R | M | future:claude-env-doctor | devops-plugin, wiki-sop, no-action | skill | P2 | 10 | Excellent diagnostic ladder for SSM/SSH/DNS hangs with a clear discriminator (shell works, Port fails → DNS). Niche but… |
| 36 | L335-wsl-dns-broken-vpn | When a tool on WSL2 fails to reach an external API (e.g. ECONNREFUSED), run a DNS-vs-TCP isolation pass (ping IP, raw TCP connect, curl-by-host vs re… | WSL2 mirrored networking delegates DNS to the Windows resolver; a complex Windows DNS stack (Tailscale MagicD… | M | R | M | future:claude-env-doctor | wiki-sop, memory-sync-rule, no-action | command | P2 | 10 | Strong fit for a future:claude-env-doctor plugin that diagnoses local Claude Code connectivity: a command running the D… |
| 37 | L363-wsl-discover-distro-name | Before targeting a named WSL distro with wsl -d <name>, enumerate installed distros with wsl -l -v and use the exact reported name; do not assume an … | WSL distro names are version- and case-sensitive and the bare 'Ubuntu' alias is not guaranteed to exist, so c… | L | O | H | future:claude-env-doctor | memory-sync-rule, no-action | documentation | P3 | 10 | Small but real WSL gotcha; pairs naturally with the WSL DNS lesson in a future:claude-env-doctor environment helper (a … |
| 38 | L1663-msys-no-pathconv-gitbash-docker | When passing Linux-style absolute paths as arguments to docker/exec commands from Git Bash on Windows, set MSYS_NO_PATHCONV=1 to stop MSYS path trans… | MSYS/Git Bash auto-translates anything that looks like a POSIX path into a Windows path before passing it to … | L | O | H | odoo-plugin | future:claude-env-doctor, no-action | documentation | P2 | 10 | odoo-plugin's docker/service domain runs container exec commands and its inventory flags unverified Windows-host parity… |
| 39 | L1775-msys-no-pathconv-breaks-f-flag | On Git Bash/MSYS, MSYS_NO_PATHCONV=1 is all-or-nothing for a command: it fixes Linux paths passed to Linux-target tools but simultaneously breaks Win… | Git Bash auto-translates POSIX-looking paths to Windows paths, and the only off-switch (MSYS_NO_PATHCONV) is … | M | O | M | odoo-plugin | future:claude-env-doctor, wiki-sop, no-action | documentation | P2 | 10 | Caught while running odoo docker-compose from Git Bash; odoo-plugin's odoo-docker/odoo-service skills are POSIX-leaning… |
| 40 | L09c-cli-test-doesnt-prove-gateway-path | After changing a config value consumed by a long-running daemon, restart the daemon and verify through the live path; a fresh-reading CLI invocation … | Long-running processes cache config at startup; CLI one-shots re-read it, so the two paths diverge and a CLI-… | M | O | H | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 9 | Good general verification discipline (test the live path, not a proxy) but emerged in a project-specific (OpenClaw mode… |
| 41 | L294-schedule-is-cloud-not-local | Distinguish cloud-executed recurring agents (which can only reach remote APIs) from local recurring tasks (which need a local scheduler). Route local… | Remote scheduled-agent tooling appears to be a general-purpose scheduler, but it executes in cloud infrastruc… | L | O | H | future:claude-env-doctor | memory-sync-rule, no-action | documentation | P2 | 9 | About harness tool semantics (/schedule vs /loop vs OS schedulers), not a domain plugin capability. Best as a behaviora… |
| 42 | L09a-wsl-localhost-forward-masquerade | When migrating a localhost service from WSL to native Windows, stop the WSL-side service first (e.g. systemctl --user stop) before binding the Window… | WSL2 transparently forwards localhost ports, so a stale in-WSL listener silently intercepts connections meant… | M | R | M | future:claude-env-doctor | wiki-sop, no-action | documentation | P3 | 8 | Niche WSL/Windows environment troubleshooting; no existing plugin covers local-environment diagnosis. A future claude-e… |
| 43 | L1643-per-command-git-safe-directory | When git refuses to operate on a Windows repo due to 'dubious ownership', prefer a per-command git -c safe.directory=<path> override instead of mutat… | Windows ownership flips (often after elevated operations or Syncthing) trigger git's safe.directory protectio… | L | O | H | future:claude-env-doctor | no-action, wiki-sop | documentation | P3 | 8 | Windows git-ownership workaround. Honors the user's no-global-git-config rule. Best as a recipe in a generic Windows en… |
| 44 | L09d-unc-copy-tool-gotchas | For large/awkward WSL↔Windows file transfers, prefer copying from inside WSL to /mnt/c over the 9p UNC mount for many small files, use tar --exclude … | The 9p UNC mount is slow and fails on external symlinks, and MSYS path conversion silently rewrites command-l… | L | O | M | future:claude-env-doctor | wiki-sop, no-action | documentation | P3 | 7 | Reusable WSL file-transfer tips with no natural plugin home; best as a claude-env-doctor reference note or wiki SOP. Th… |
| 45 | L510-tr-newline-sanitize-bug | When sanitizing a string into a filesystem-safe slug in shell, prefer bash parameter expansion (`${name//[^a-zA-Z0-9_]/_}`) over `echo \| tr` because… | echo adds a trailing newline that the tr complement-replace treats as a non-allowed character and rewrites, s… | L | R | H | no-action | future:wiki-memory-sync | example | P3 | 7 | Embedded shell-hygiene sub-bug from the worktree lesson. Too granular for its own plugin artifact; best left as a note … |
| 46 | L795-vhdx-syncthing-mutual-exclusion | When sharing a single VM disk image across machines via a sync tool, enforce strict mutual exclusion: shut down fully (never suspend/save-state) befo… | VHDX (and most VM disk) formats assume a single writer; concurrent access or syncing a suspended/inconsistent… | H | R | H | wiki-sop | no-action | documentation | P3 | 7 | High data-loss risk but very niche and no plugin home; belongs in the VM README/ops playbook. The suggested start-vm.ps… |
| 47 | L1160-inwsl-syncthing | For syncing developer state between two WSL2 machines, run the sync agent natively inside WSL (not Windows-side over the \\wsl.localhost share), sync… | Syncing WSL filesystems from Windows-side flattens Linux permissions, drops symlinks, breaks inotify, and is … | M | R | H | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 7 | WSL/Syncthing topology recipe. No plugin owns this domain. The 'never run a stateful CLI on both synced machines / excl… |
| 48 | L09b-scheduled-task-gateway-lifecycle | When a Windows background service is implemented as a Scheduled Task, manage it through its lifecycle wrapper (start/stop/restart) rather than launch… | Operators treat a scheduled-task-backed service as a foreground process and try to force-run it, colliding wi… | L | R | M | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 6 | Very tool-specific (OpenClaw's scheduled-task gateway). The general principle (use the lifecycle wrapper, don't force-r… |
| 49 | L1142-wsl-autostart-vbs | To run any process inside WSL silently at Windows login, use a wscript/VBS shim with window style 0 launched by a logon Scheduled Task (Task Schedule… | Task Scheduler's -Hidden flag only hides the task entry, not the spawned console window, so bare wsl.exe flas… | L | R | H | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 6 | Windows/WSL environment recipe. No marketplace plugin owns Windows/WSL host setup. Reusable but niche; would fit a futu… |
| 50 | L1177-wsl-tailscale-nat | WSL2's internal NAT means a Windows-host VPN/overlay (Tailscale) does not reach services bound inside WSL; to get direct full-speed connectivity, ins… | WSL2 networking is NAT'd separately from the Windows host, so host-level VPN reachability does not extend to … | L | R | H | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 6 | Networking/WSL diagnostic recipe. No plugin home. Reusable env knowledge; already in LESSONS.md. No-action for the cata… |
| 51 | L780-hyperv-gen2-secureboot-uefi-ca | When scripting Gen2 Hyper-V VM creation for Linux, set the Secure Boot template to MicrosoftUEFICertificateAuthority in the provisioning script; trac… | The default Gen2 Secure Boot template only trusts Microsoft Windows signing, so Linux bootloaders fail Secure… | L | R | H | wiki-sop | no-action | documentation | P3 | 5 | Same niche as L765 — Hyper-V Linux VM provisioning. No plugin owns VM/host provisioning; keep in the personal Hyper-V s… |
| 52 | L765-hyperv-xrdp-gnome-wayland-xfce | For a Linux dev VM accessed over RDP, default to a lightweight X11 desktop (XFCE) rather than GNOME/Wayland; bake the .xsession + Xwrapper.config + s… | GNOME on Wayland does not cooperate with xrdp's X session, and several xrdp prerequisites (executable .xsessi… | L | R | H | wiki-sop | no-action | documentation | P3 | 4 | Niche environment/ops playbook with no marketplace-plugin home (no DevOps/VM-provisioning plugin exists; devops-plugin … |
| 53 | L1202-wslconfig-keys | INI/TOML-style config files use a section header plus bare keys, not dotted section-prefixed keys; when a config tool emits a recurring 'Unknown key'… | Confusing dotted dotted-path config syntax with INI section+key syntax leads to writing 'section.key=' which … | L | R | H | no-action | future:claude-env-doctor | documentation | P3 | 4 | Trivial INI-syntax gotcha for .wslconfig. No plugin home; already in LESSONS.md. No-action. |
| 54 | L1009-rbac-three-layers-dev-otp | Treat RBAC as multi-layer: API route guards, UI visibility gates, and deeper service-layer guards can disagree (a route can pass while a service stil… | Authorization logic is duplicated across route/UI/service layers that are edited independently; and dev conve… | C | O | H | qa-browser | react-kit, wiki-sop | checklist | P0 | 18 | Highly reusable and high-value. Three pieces map cleanly: (a) 'verify all RBAC layers and confirm 403->400/409 empirica… |
| 55 | L07b-403-vs-400-409-rbac-proof | When verifying a permission change via API probes, treat 400/409 as 'authorized, hit a business rule' and only 401/403 as 'still blocked'; a pre-fix … | Testers conflate any non-200 with 'still denied,' missing that status codes distinguish the authorization lay… | M | C | H | qa-browser | qa-browser, future:secure-code-review, wiki-sop | skill | P0 | 17 | Ideal for qa-browser's UI-vs-API authorization verification — a precise, universally reusable status-code discriminator… |
| 56 | L722-pure-renderer-not-security-primitive | When auditing any flow that presents a client-rendered code to a third-party scanner, assume the value is attacker-controlled and screenshot-replayab… | Mobile/web UIs display rendered codes as if presence on-device proves identity, but client rendering provides… | H | O | H | qa-browser | react-kit, wiki-sop | checklist | P1 | 16 | The generalized form of L633 — prefer this as the canonical security-audit checklist item. Fits qa-browser (UI-vs-API a… |
| 57 | L1594b-csrf-missing-both-headers-reject | In CSRF protection, treat 'no Origin AND no Referer' on a state-changing method (POST/PUT/PATCH/DELETE) as a REJECT, not a pass. Flag any if(!origin … | Developers add an early-return that treats absent headers as same-origin/trusted to avoid false positives, bu… | C | O | H | qa-browser | react-kit, wiki-sop, no-action | validation-rule | P1 | 16 | qa-browser already verifies UI-vs-API authorization and could add a CSRF/header-less probe to its route-access/security… |
| 58 | L307-pasted-token-is-compromised | Treat any secret pasted into a transcript as compromised. Recommend revoke+reissue with least privilege before use; verify a claimed-rotated token is… | Secrets in chat are permanently captured in the transcript; users often re-send the same string believing it … | C | O | H | future:secrets-hygiene-guard | devops-plugin, memory-sync-rule, no-action | hook | P0 | 15 | Highest-value security lesson in the range and broadly reusable. A UserPromptSubmit hook that detects token-shaped stri… |
| 59 | L633-barcode-not-auth-token | When auditing barcode/QR redemption flows, never treat a client-rendered code as authenticating. Ask 'what stops a screenshot or a swapped value from… | UIs present a rendered code as if possession of the device proves identity, but open-loop codes have no signa… | H | O | H | qa-browser | react-kit, wiki-sop | checklist | P1 | 15 | Near-duplicate of L722 (the generalized 'pure renderer != security primitive'). Fits qa-browser's UI-vs-API authorizati… |
| 60 | L908-middleware-fallthrough-and-exceptions | Route-matcher inclusion does not equal route protection: a path can be in a middleware matcher yet fall through to a pass-through with no auth branch… | Middleware matchers and middleware branches are configured separately; a route added to the matcher without a… | H | O | H | qa-browser | react-kit, wiki-sop | checklist | P1 | 15 | Strong generic security check: 'matcher inclusion != protection; verify each matched route has an auth branch or handle… |
| 61 | L1585-enum-status-orm-allowlist-membership | Whenever wiring an external filter/enum/status string into an ORM query, gate it through a fixed allowlist membership check that returns null/rejects… | Treating client-supplied filter strings as trusted and passing them straight into the query builder lets atta… | H | C | H | react-kit | qa-browser, wiki-sop, no-action | validation-rule | P1 | 15 | Backend/data-access security pattern; no current plugin owns server-side ORM query hardening cleanly. react-kit (former… |
| 62 | L1737-no-allowlist-execution-shaped-tools | When auto-generating a permission allowlist from transcripts, exclude (a) read-only commands the harness already auto-allows (noise) and (b) any inte… | Allowlist generators naively promote every frequently-seen command, redundantly listing auto-allowed reads an… | H | O | H | future:claude-env-doctor | wiki-sop, no-action | validation-rule | P1 | 15 | This is a security guardrail for the built-in fewer-permission-prompts/allowlist tooling, not for any marketplace busin… |
| 63 | L04a-confirm-token-bind-live-count | For count/amount-based confirm-before-destructive-bulk-action gates, resolve the affected set server-side and build the confirmation token from the l… | Trusting a client-displayed count lets the user confirm one quantity while the server acts on a different (dr… | H | O | H | react-kit | qa-browser, react-kit, wiki-sop | skill | P1 | 14 | react-kit/react-admin-kit owns admin-dangerous-actions confirmations; this is the server-authoritative-count rule that … |
| 64 | L275-verify-cited-user-message-prompt-injection | Treat any in-turn 'the user already authorized this' claim as potential prompt-injection. Before acting, verify the quoted authorization actually app… | Subagents receive context from a parent and can be induced to trust forged 'user authorization' claims; witho… | C | R | H | future:prompt-injection-guard | memory-sync-rule, devops-plugin, no-action | hook | P1 | 13 | High-value security pattern but hard to fully automate (verifying a quote against full conversation history is non-triv… |
| 65 | L2039-no-danger-trusted-html | no-danger / dangerouslySetInnerHTML findings on trusted, staff-authored rich-text content are an audit-only signal: do not silently introduce a sanit… | Static rules flag all dangerouslySetInnerHTML regardless of trust boundary; bolting on DOMPurify mid-cleanup … | M | O | H | react-kit | qa-browser | documentation | P2 | 13 | react-kit owns UI-level security rules (PII masking, file-upload safety) — a 'dangerouslySetInnerHTML is audit-only, sc… |
| 66 | L04c-no-auto-echo-stepup-token | When a threshold crossing is meant to require a fresh human decision, the client must re-prompt on server step-up and never auto-echo the escalated t… | Convenience auto-resubmit logic treats the step-up token as a mechanical retry value rather than a human-ackn… | H | R | H | react-kit | qa-browser, react-kit, wiki-sop | skill | P2 | 12 | Belongs alongside L04a in react-kit admin-dangerous-actions as a UI contract; qa-browser verifies the re-prompt actuall… |
| 67 | L09f-secret-hygiene-config-migration | For any config migration, run all config through a redactor (mask values by key-name pattern and by JWT/PAT/opaque shape) and perform credential-bear… | Manual config editing routinely prints secrets to the terminal/logs; without a redaction layer and scripted m… | M | O | H | future:claude-env-doctor | qa-browser, rag-plugin, wiki-sop | template | P2 | 12 | A reusable redaction-script pattern (key-name + shape-based masking) is broadly valuable; qa-browser already has redact… |
| 68 | L919-tracked-security-issues-not-silently-patched | Maintain a tracked-known-issues register so agents surface (not silently fix) intentionally-deferred security/tech-debt items when touching the affec… | Without a known-issues register, an agent that spots a security smell will either patch it out-of-scope (bypa… | H | O | H | wiki-sop | docs-wiki, qa-browser | documentation | P2 | 12 | The specific four issues are project-specific (belong in that project's security wiki/SOP), but the 'tracked known-issu… |
| 69 | L04b-drift-window-tier-boundary | When designing/reviewing tiered confirmation gates, verify that no allowed drift-tolerance window overlaps a hard tier boundary; if it can, the gate … | Tolerance windows and tier thresholds are designed independently, so an overlap that lets a confirmed quantit… | H | R | M | qa-browser | react-kit, future:secure-code-review, wiki-sop | checklist | P2 | 11 | Subtle, lower-frequency edge case best captured as a review/QA checklist item rather than enforced code. Pairs with L04… |
| 70 | L1400-backend-hide-by-default-query-param | For sub-collections that should be invisible in a global list and only viewed/created within their parent context, enforce hide-by-default at the bac… | Relying on frontend-only filtering to hide records is fragile (bypassable); without a backend default-exclude… | M | O | H | react-kit | wiki-sop, qa-browser | validation-rule | P2 | 11 | The generic principle ('UI hide is not authorization; enforce default-exclude at the backend, opt-in to reveal') aligns… |
| 71 | L1909-view-session-discriminator | When two token types share one signing secret, the only thing preventing cross-token reuse is an explicit type/claim allow-list at verification time;… | Reusing one JWT secret across token audiences makes the type-claim check the sole boundary; independent audit… | M | R | M | wiki-sop | no-action | documentation | P3 | 8 | Project-specific (aqraboon) security finding needing a one-time human review to land canonical phrasing in that project… |
| 72 | L1127-openclaw-agent-isolation | When hosting multiple AI agents in one process, isolate by (1) per-agent persistent memory keyed by agent id, (2) explicit per-agent channel/account … | Default multi-agent hosting shares state and tools and binds permissively; without deliberate per-agent isola… | H | R | H | no-action | future:agent-host-hardening, wiki-sop | checklist | P3 | 6 | OpenClaw-product-specific multi-agent isolation. Strong security lesson but tied to a specific bot platform; no marketp… |
| 73 | L05a-sha-pin-third-party-actions | On any CI pipeline review, flag every third-party action referenced by mutable tag/branch and require a full commit-SHA pin (first-party actions/* ma… | Tags and branches are mutable, so a compromised upstream can silently swap the code an action runs — a supply… | H | C | H | devops-plugin | future:gha-hardening, qa-browser, wiki-sop | hook | P0 | 15 | Mechanically enforceable — a PreToolUse/Write hook or linter scanning .github/workflows for unpinned third-party action… |
| 74 | L259-verify-workitem-type-semantics | Before any bulk tracker export/operation, verify item-type and container semantics against the actual API (fetch one item, print its real type and pr… | Informal user vocabulary is trusted as-is, and supplied IDs are trusted to be the right type/project; the too… | M | O | H | devops-plugin | wiki-sop, no-action | checklist | P1 | 14 | Clean fit for devops-plugin, which already owns Azure DevOps work-item semantics, hierarchy enforcement, and a profile.… |
| 75 | L685-odoo-volume-drift-never-down-v | When a stack 500s after a compose mount-point change, enumerate volumes (docker volume ls) and inspect candidates before deleting any; migrate data f… | Named-volume mounts are keyed by mount path; editing the path detaches the old volume (still full) and create… | H | O | H | odoo-plugin | wiki-sop | hook | P1 | 14 | odoo-plugin odoo-docker sub-skill. A PreToolUse Bash guard that blocks/warns on `docker compose down -v` and `docker vo… |
| 76 | L05b-environment-block-not-approval-gate | When reviewing deploy pipelines, do not treat a YAML environment: block as an approval gate; verify the protection rule exists in repo settings befor… | The YAML environment keyword looks like it enforces approval but only references a setting that must be confi… | H | O | M | future:gha-hardening | devops-plugin, qa-browser, wiki-sop | checklist | P1 | 13 | Not statically detectable from the repo files alone (needs the settings/API), so a review checklist + gh-api probe rath… |
| 77 | L05d-dont-weaken-established-gates | On CI review, flag continue-on-error added to an established blocking gate and any renamed required-check job; only new advisory scanners (e.g. SARIF… | Refactors quietly downgrade established gates to non-blocking or rename required checks, and reviewers over-f… | H | O | H | future:gha-hardening | devops-plugin, qa-browser, wiki-sop | checklist | P1 | 13 | Part of the GHA hardening review triplet (L05a-d). The ephemeral-cred-vs-real-leak distinction is a valuable nuance tha… |
| 78 | L672-almajal-pg16-volume-forward-incompat | Before regenerating a Docker/compose stack from a generic template, verify and preserve the actual running PostgreSQL major version (read PG_VERSION … | Regenerating from a generic template silently resets the pinned PG major; PostgreSQL on-disk data directories… | H | O | H | odoo-plugin | wiki-sop | hook | P1 | 13 | Fits odoo-plugin's odoo-docker sub-skill. The generic guard (probe PG_VERSION in the volume before re-init/regenerate; … |
| 79 | L05c-workflow-inventory-drift | Glob and read the real .github/workflows files to determine actual purpose and triggers rather than trusting docs; watch for workflow_run chains keye… | Docs drift from the actual workflow set, and name-keyed inter-workflow triggers create hidden coupling that b… | M | O | H | future:gha-hardening | devops-plugin, docs-wiki, wiki-sop | checklist | P2 | 11 | Doc-vs-file drift detection overlaps docs-wiki's code-vs-docs discrepancy theme but is CI-specific; better in a GHA har… |
| 80 | L879-dual-deploy-path | Document the exact deploy dispatch per environment (which command/tooling for production vs self-hosted vs other), and audit docs for stale or contra… | Projects accumulate multiple deploy mechanisms across their lifetime; docs reference whichever was current wh… | M | O | M | wiki-sop | docs-wiki, no-action | documentation | P2 | 10 | Highly project-specific deploy topology (ACA + PM2, no systemd). The reusable kernel is 'document deploy dispatch per e… |
| 81 | L998-stack-ci-reality-not-odoo | Establish the real stack and CI/deploy reality from the repo before applying any tooling: detect the actual language/framework (don't apply stack-for… | Assuming a stack or applying generic security/CI tooling without confirming the repo's actual language, build… | M | C | H | wiki-sop | devops-plugin, no-action | documentation | P2 | 10 | Two reusable kernels worth extracting: (1) 'detect the actual stack before applying tooling — don't run stack-foreign s… |
| 82 | L1690-ssh-banner-vs-tcp-refused | When diagnosing connection failures to a remote service, separate the transport layer (is the port reachable?) from the application layer (is the dae… | Engineers conflate 'connection failed' into a single symptom and fix the wrong layer (e.g., reconfigure the d… | M | O | M | devops-plugin | wiki-sop, future:claude-env-doctor, no-action | checklist | P2 | 10 | Generic SSH/network connectivity triage. Fits awkwardly in devops-plugin (which is Azure DevOps work-item focused, not … |
| 83 | L1614-railway-ssh-hostkey-base64-c | When a platform's internal DB hostname resolves only inside its private network, run seed/migration commands in-container via the platform's ssh/exec… | PaaS private networking hides internal hostnames from the local machine; OpenSSH refuses unknown host keys no… | M | O | M | wiki-sop | devops-plugin, future:claude-env-doctor, no-action | documentation | P2 | 9 | Railway-specific deployment runbook. devops-plugin is Azure-DevOps-only (no Railway), so it isn't a clean home; the reu… |
| 84 | L1690-ssh-banner-timeout-vs-tcp-refused | Diagnose SSH failures by layer: a TCP connect failure (refused/timeout) points at network/security-group/instance reachability; a successful TCP conn… | SSH problems get misattributed to a single cause because the connectivity layer (TCP/port reachability) and t… | L | O | M | wiki-sop | future:claude-env-doctor, devops-plugin, no-action | documentation | P3 | 9 | Generic SSH/network troubleshooting decision tree. No marketplace plugin owns infra/SSH diagnostics; best as a DevOps/i… |
| 85 | L1701-vpn-bastion-not-server-ip | After a VPN/bastion rollout, SSH targets must be reachable private IPs inside the VPN's routed CIDR, not the old public IPs. When connectivity breaks… | VPN config files describe the tunnel, not the destination hosts; engineers assume connecting the VPN automati… | M | R | M | wiki-sop | devops-plugin, future:claude-env-doctor, no-action | documentation | P3 | 8 | Network/VPN topology knowledge that is largely org-specific (depends on each company's infra CIDR scheme). Best capture… |
| 86 | L1191-bootstrap-kit-pattern | For cross-machine bring-up automation: stage an idempotent bootstrap kit in an already-synced shared location, auto-ferry it, expose a one-command id… | Manual multi-machine setup is error-prone and non-idempotent; sync tools report misleading first-scan counts,… | L | R | M | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 5 | General bring-up automation pattern (idempotent steps, peer-handshake via shared dir, don't trust first-scan counts). N… |
| 87 | L1456-adahi-brd-json-source-of-truth | When planning against a work-tracking system, snapshot the scope into local per-feature JSON files (metadata + child work-item list) pulled fresh fro… | Ad hoc Azure DevOps queries during planning are inconsistent and lose the agreed scope; a versioned local JSO… | L | R | M | no-action | devops-plugin, wiki-sop | documentation | P3 | 5 | Largely project-specific (aqraboon/Adahi feature numbers, file layout). The generic kernel — 'snapshot tracker scope in… |
| 88 | L08-error-swallowing-data-hooks | In data-fetching hooks, always propagate the error and branch on status in the consumer (403 → access-required, 404 → not-found); when debugging 'bla… | Hooks that abstract away the error object hide backend status codes from the UI, so legitimate access/permiss… | M | C | H | react-kit | react-kit, qa-browser, wiki-sop | skill | P1 | 15 | Maps cleanly to react-kit's admin-states (loading/error/empty) skill and its anti-pattern detection / code-review check… |
| 89 | L2027-forwardref-to-ref-prop | Migrating React components off forwardRef to the React 19 ref-as-prop API: use React.ComponentProps<...> (which includes ref in React 19 types) and d… | React 19 made ref a normal prop and forwardRef deprecated; teams need a type-clean, consumer-preserving migra… | M | C | H | react-kit |  | example | P1 | 15 | Highly reusable React 19 upgrade recipe for any shadcn/Radix-based component library. react-kit (reusable React/Next pa… |
| 90 | L2040-array-index-keys | Fix array-index React keys only when a stable unique id already exists on the item (or the value itself is unique); leave index keys on lists whose u… | The no-array-index-key rule ignores whether sibling state-mutation logic is index-addressed and whether a sta… | M | C | H | react-kit |  | documentation | P2 | 15 | Classic React keys nuance with a strong 'don't invent keys / respect index-based mutation' guard. react-kit tables/list… |
| 91 | L2028-usecontext-to-use | In React 19, replace useContext(Ctx) with use(Ctx) when called at top-level hook scope; it is a safe drop-in (use additionally supports conditional/p… | React 19 introduced the use() API that subsumes useContext; codebases migrating to React 19 want a confirmed-… | L | C | H | react-kit |  | documentation | P2 | 14 | Part of the React 19 migration recipe set; pairs with the forwardRef->ref-prop example in react-kit. Trivial to documen… |
| 92 | L2029-no-derived-state-intentional | no-derived-state findings are frequently legitimate state-snapshot/reset patterns (form reset on dialog open, debounce mirrors, cascading field reset… | The rule can't distinguish derived-state-as-anti-pattern from deliberate state-mirroring for reset/snapshot U… | M | O | H | react-kit |  | documentation | P2 | 14 | react-doctor FP/nuance recipe; reinforces 'inspect before fixing'. react-kit forms + code-review reference is the home.… |
| 93 | L1033-modals | When a React/Next.js admin codebase has an established modal/drawer pattern (e.g. custom fixed-position panels) and a fixed hook/typing convention (m… | Without inspecting existing conventions, an agent reaches for a familiar library (Radix Dialog/Sheet) or inve… | M | C | H | react-kit | react-kit | skill | P1 | 13 | Generic 'conform to host repo modal/drawer/mutation-hook conventions before scaffolding' fits react-kit's admin-shell/a… |
| 94 | L2017-div-to-button-backdrop | Clickable non-interactive elements (overlay/backdrop divs with onClick) should be real <button type=button> with an aria-label for keyboard+focus acc… | Click handlers are routinely attached to divs for layout convenience, dropping keyboard and focus semantics; … | L | C | H | react-kit | paper-plugin | documentation | P2 | 13 | Accessibility + Tailwind interaction recipe. react-kit owns React UI patterns and a11y basics (and already covers dange… |
| 95 | L2036-per-page-metadata-rule | A per-page metadata lint rule evaluates each page in isolation and ignores layout-level metadata inheritance; don't restructure layouts to satisfy th… | The rule scopes to page.tsx exports and does not model Next.js metadata inheritance from layouts, creating a … | L | O | H | react-kit |  | documentation | P3 | 12 | Next.js App Router metadata/SEO recipe for react-kit's route/page-organization + code-review references. Reusable acros… |
| 96 | L2037-server-passthrough-split | To attach server-only metadata to a client layout without behavior change, split into a thin server layout.tsx (exports metadata, renders the client … | Next.js requires metadata exports in server components, but existing layouts are often client components; spl… | L | O | H | react-kit |  | example | P2 | 12 | Reusable Next.js App Router server/client-split pattern; ship as a worked example in react-kit (app architecture + rout… |
| 97 | L899-i18n-inline-context-not-library | Verify the actual i18n implementation strategy in code (inline context tables vs a library like next-intl vs a messages/ JSON folder) before reasonin… | Docs assume a conventional/popular library is in use when the project actually rolled a bespoke approach; the… | L | O | H | react-kit | docs-wiki, no-action | documentation | P3 | 8 | react-kit owns RTL/LTR + i18n layout concerns; a 'verify actual i18n strategy before assuming a library' note fits ther… |
| 98 | L825-echarts-gl-lazy-load-3d-toggle | For heavy optional frontend assets (3D libs, large viz bundles), default to the lightweight path and lazy-load the heavy script only on first activat… | Loading large optional visualization libraries eagerly bloats every page load and leaks GPU memory if instanc… | L | R | M | react-kit | wiki-sop, no-action | documentation | P3 | 7 | The lazy-load-heavy-asset-on-demand + dispose-to-free-memory pattern generalizes to react-kit's dashboard-cards/charts … |
| 99 | L1060-tiptap-starterkit | When a rich-text/editor framework's 'starter kit' bundles extensions that you also want to configure explicitly, disable the bundled copies in the st… | Major-version starter kits change which extensions ship by default; adding an extension that's already bundle… | L | R | H | no-action | react-kit | documentation | P3 | 6 | Library-version-specific gotcha (TipTap v3). Too narrow for a plugin skill; better served by context7 docs lookup. Alre… |
| 100 | L1060-prosemirror-paste | When content appears to lose formatting 'after save', verify whether the loss happens client-side at paste/clipboard-parse time rather than server-si… | Symptom timing (noticed after save) misattributes the cause; the transformation actually happens earlier in t… | L | R | M | no-action | react-kit | documentation | P3 | 6 | Narrow debugging insight about ProseMirror/TipTap clipboard behavior. The generic 'isolate client vs server transformat… |
| 101 | L1372-tiptap-addattributes-camelcase | When extending a ProseMirror/TipTap node with attributes that map to HTML data-attributes, use camelCase attribute keys plus explicit parseHTML/rende… | TipTap/ProseMirror's attribute system treats hyphenated keys as invalid and silently drops them, and NodeView… | L | R | M | no-action | react-kit, wiki-sop | documentation | P3 | 5 | Library-specific (TipTap/ProseMirror) gotcha tied to one project's rich-text editor. react-kit is framework-generic and… |
| 102 | L1504-01 | Permission-first for all remote/GitHub write operations: stage and commit locally, surface the proposed commit message + changed-file list, and block… | Agents conflate 'work is done' with 'work should be published'; without an explicit approval gate they auto-p… | H | C | H | devops-plugin | docs-wiki, memory-sync-rule | hook | P1 | 16 | Already codified in the user's personal CLAUDE.md, so for the user this is 'confirmed'. As a marketplace artifact, the … |
| 103 | L01-squash-linear-history-promo | Before resolving repeated same-file conflicts on long-lived-branch promotions, inspect branch-protection for required_linear_history. If on, stop mer… | Squash/rebase merges collapse a merge into a single-parent commit, destroying ancestry; git merge-base then f… | M | O | H | devops-plugin | future:git-promotion-doctor, docs-wiki | skill | P1 | 12 | devops-plugin owns repo/PR workflows but is Azure-DevOps-only and gh-CLI gaps are noted; a git-promotion diagnosis skil… |
| 104 | L1060-gh-account-flip | When multiple GitHub identities are in play and the active gh account resets per shell, never rely on a session-level auth switch — chain the account… | gh's active-account state is not durable across shell sessions in this setup, so a previously-issued switch s… | H | C | H | no-action | future:gh-multi-account, wiki-sop | hook | P2 | 11 | Real and high-risk (pushing as the wrong identity). Already encoded in the user's CLAUDE.md GitHub auto-switch rule. No… |
| 105 | L1513-01 | Before any GitHub write op, detect the target repo owner (git remote -v), check the active gh identity (gh auth status), and auto-switch to the ident… | Users with multiple GitHub identities have a default account that often lacks access to the target repo; with… | M | C | H | devops-plugin | future:git-identity-guard, docs-wiki | hook | P2 | 11 | Highly user-specific in its concrete mapping (two named handles) but the PATTERN (owner->identity auto-switch + restore… |
| 106 | L1536-01 | To accelerate multi-PR/multi-change work without one failure blocking everything, batch by domain cluster (files sharing test mocks or a domain) rath… | Two failure modes at the extremes: per-file PRs are too slow, and a single mega-PR couples all changes so one… | M | O | M | devops-plugin | future:pr-batcher, wiki-sop | documentation | P2 | 11 | A reusable PR/change-batching strategy. devops-plugin owns PR workflows (pr-reviewer agent) and is the closest existing… |
| 107 | L1788-git-stash-include-untracked-before-pull | Before pulling onto a branch that has local untracked files which would be overwritten, stash with --include-untracked under a descriptive backup mes… | Untracked local files silently collide with incoming remote files; engineers either get blocked or force the … | M | O | H | wiki-sop | devops-plugin, future:claude-env-doctor, no-action | documentation | P2 | 11 | Generic git-safety workflow. No existing marketplace plugin owns local git hygiene (devops-plugin is Azure-DevOps work-… |
| 108 | L474-ci-poll-skip-watcher | Allow an explicit, user-granted 'CI watcher' delegation that lets the agent stop polling CI on low-risk PRs (test-only/coverage/docs) to save time — … | Polling CI on every PR is ~3 min of dead time that compounds over many PRs, but blanket skipping is unsafe fo… | L | O | H | devops-plugin | no-action, future:pr-flow | documentation | P3 | 8 | A workflow/etiquette convention more than an artifact. devops-plugin owns PR/CI workflows (pr-reviewer agent) so the ri… |
| 109 | L1060-worktree-syncthing | When the working tree is continuously modified by an external syncing tool (Syncthing, Dropbox, etc.), don't fight the dirty tree — create a git work… | Continuous file-sync tools mutate the working tree asynchronously, so checkout/stash assumptions break; the w… | M | O | H | no-action | wiki-sop, future:claude-env-doctor | documentation | P3 | 8 | Useful environment trick but no current plugin owns git-worktree/Syncthing workflow. Already captured as a LESSONS.md e… |
| 110 | L1656-git-archive-tar-recover-gitignored | To recover gitignored-but-committed files from history, use git archive <commit> <path> \| tar -x -C <dest> (reads the object store directly and bypa… | git checkout restores into the working tree subject to gitignore rules, so ignored paths silently fail; git a… | L | R | M | no-action | future:claude-env-doctor, wiki-sop | documentation | P3 | 8 | Niche but genuinely useful git recovery recipe. No marketplace plugin owns generic git operations; best captured as an … |
| 111 | L1681-fine-grained-vs-classic-pat | Choose the GitHub PAT type by access scope: fine-grained PATs bind to a single resource owner, so use a classic PAT (read-only repo + read:org) when … | Fine-grained PATs are scoped per resource-owner by design, which surprises users who expect one token to cove… | L | R | H | wiki-sop | devops-plugin, future:claude-env-doctor, no-action | documentation | P3 | 8 | GitHub PAT-selection guidance with a user-specific account-routing tail (work multi-org account vs single-owner account… |
| 112 | L1757-gh-repo-clone-ignores-dest | Don't assume a CLI's destination/output argument was honored — verify the actual resulting path/name after the operation (e.g., list the parent direc… | gh repo clone can override the explicit destination with a repo-configured name, and the command succeeds, so… | L | R | H | wiki-sop | devops-plugin, no-action | documentation | P3 | 8 | Narrow gh-CLI gotcha. No marketplace plugin owns gh clone workflows (devops-plugin is Azure DevOps, explicitly noted as… |
| 113 | L387-stacked-pr-rebase | For stacked/concurrent PRs that each edit a shared config (e.g. coverage thresholds), resolve conflicts mechanically by keeping the higher/stricter v… | Concurrent PRs touching the same threshold file produce repeated conflicts; without a deterministic resolutio… | L | R | H | react-kit | devops-plugin, no-action | documentation | P3 | 6 | Sub-lesson of the coverage-ratchet rhythm. Narrow (stacked-PR + shared-config conflict) and largely a documented conven… |
| 114 | L1605-yaml-frontmatter-colons-quoted-list-items | When authoring YAML frontmatter, avoid raw colons in unquoted scalars and quote-or-reword any list item that would start with a double-quote. Validat… | YAML treats an unquoted colon as a key/value separator and a leading quoted token as a typed scalar boundary,… | M | C | H | no-action | future:claude-env-doctor | validation-rule | P1 | 15 | This workspace already owns validate_plugin.py (the plugin-authoring source of truth) — the right home is to add a stri… |
| 115 | L950-skill-layering-foundation-domain-workflow | Layer a skill library with explicit precedence (foundation > domain > workflow), use numeric prefixes and a SKILL_INDEX declaring priority, designate… | Without a declared precedence and single-owner rule, multiple skills duplicate cross-cutting facts (security,… | M | C | H | future:skill-library-architect | docs-wiki, wiki-sop | documentation | P2 | 12 | This is the same single-owner-layering principle this workspace's devops-plugin/ARCHITECTURE.md already documents, appl… |
| 116 | L1748-skill-rename-name-folder-match | After renaming a skill (or any component whose folder name must equal a declared identifier in its manifest/frontmatter), verify the declared name fi… | Skill identity is duplicated in two places (folder name and frontmatter name:), and a directory rename update… | M | O | H | no-action | future:claude-env-doctor, wiki-sop | validation-rule | P2 | 12 | This is exactly what the workspace validator (validate_plugin.py / validate_plugin_simple.py) should assert — name==fol… |
| 117 | L231-readonly-subagent-vs-skill | When designing automation, separate knowledge from execution: knowledge/policy goes in a skill; read-only, bounded, report-emitting execution goes in… | Long multi-hour scan/classify/report tasks run inline consume the main session's productive context window; c… | L | O | H | future:plugin-authoring-guide | memory-sync-rule, no-action | documentation | P2 | 11 | This is a meta-lesson about how to author plugins/skills/agents, mirroring the workspace's own 'single-owner layering' … |
| 118 | L1073-genericness-grep | When generalizing project-specific tooling into a reusable plugin, run a 'genericness grep' for project-specific tokens (paths, role names, domain te… | Copying from a project's .claude/ folder easily drags along business logic, paths, and domain terms; without … | M | C | H | no-action | future:plugin-authoring-guard | validation-rule | P2 | 11 | Directly relevant to THIS study (mapping lessons to generic plugin destinations). A 'genericness grep' check is exactly… |
| 119 | L1361-claudemd-not-reaching-running-sessions | Instructions added to CLAUDE.md only take effect for sessions started afterward. When introducing a new workflow rule mid-project, ship a slash comma… | CLAUDE.md is loaded once at session start and not re-read, so doc-only workflow changes silently fail to prop… | M | C | H | wiki-sop | no-action, future:claude-env-doctor | documentation | P2 | 11 | Universally reusable Claude Code authoring insight (prefer slash commands over CLAUDE.md prose for new workflows; CLAUD… |
| 120 | L1073-plugin-layout-validation | Plugin authoring contract: kebab-case <name>-plugin folder, required manifest fields, mandatory marketplace.json registration with the -plugin suffix… | The marketplace-registration requirement and the suffix-stripping naming rule aren't enforced by the validato… | M | C | H | no-action | future:plugin-authoring-guard, wiki-sop | validation-rule | P2 | 10 | This is meta — about authoring THIS marketplace's plugins. It is already owned by validate_plugin.py + the repo CLAUDE.… |
| 121 | L1092-layered-config-update-safety | Separate plugin defaults from user/workspace overrides: ship defaults in the plugin tree, read overrides from a user/workspace config file outside th… | Storing user config inside the plugin tree means every plugin update overwrites it; without a layered default… | M | O | H | no-action | future:plugin-authoring-guard | documentation | P2 | 10 | This is the canonical plugin-settings pattern (matches plugin-dev:plugin-settings .local.md guidance and devops-plugin'… |
| 122 | L1916-audit-shape-generalizes | A repeatable audit-report template (inventory, per-item status, coverage gaps, conflicts, stale references, frontmatter health, index issues, bottom … | Audit structures crystallize inside one project's conventions (its priority/foundation/domain taxonomy), so t… | L | O | M | future:skill-system-auditor | wiki-sop, no-action | template | P3 | 9 | Needs-review: keep project-specific until confirmed on a 2nd project. The reusable core is a 'skill/plugin collection a… |
| 123 | L589-slash-commands-project-scoped | Slash commands and workspace CLAUDE.md are scoped to the workspace where they live and are not auto-shared across repos; any workflow that expects a … | Project-scoped command files don't propagate across workspaces, so a workflow authored in the reviewer's eval… | L | O | H | no-action | future:assessment-toolkit, wiki-sop | documentation | P3 | 7 | This is exactly the gap the plugin/marketplace mechanism already solves (packaging commands for distribution) — for mar… |
| 124 | L1092-plugin-scope-restricted | A plugin's intended scope (workspace-restricted vs generic-marketplace) must be stated consistently across README, manifest, and skill descriptions. … | Scope drifts during edits because the intended audience isn't pinned as an invariant; generic-sounding boiler… | L | O | H | no-action | future:plugin-authoring-guard | documentation | P3 | 7 | About a DIFFERENT marketplace's plugin (Taqat-Trading-Business-Solutions/Plugins). Meta plugin-authoring guidance — pre… |
| 125 | L1484-01 | On any cleanup/lint task: classify each analyzer finding as safe-mechanical / needs-judgment (defer with reason) / false-positive / forbidden-zone. A… | Static analyzers (lint, deslop, react-doctor) emit findings without context; treating them as commands rather… | H | C | H | react-kit | future:lint-triage, react-kit | skill | P0 | 17 | There is already a react-doctor skill in this environment; this lesson is the governing discipline for that kind of pas… |
| 126 | L03-security-review-source-to-sink | For any 'review this change for security' task, run a structured trace: (1) enumerate tainted inputs; (2) follow each to its sink and name the concre… | Linear diff reading misses cross-route divergence and fail-open replacements; reviewers wave through loosened… | H | C | H | qa-browser | react-kit, future:secure-code-review, wiki-sop | skill | P0 | 16 | Highly reusable review discipline. qa-browser already does UI-vs-API authorization verification so source-to-sink + sib… |
| 127 | L2016-deslop-unused-file-fp-knip | Dead-file detectors that don't resolve path aliases and framework route graphs produce massive false positives — never delete files on such a signal.… | Naive unused-file analysis follows only literal relative imports; it can't resolve tsconfig path aliases or f… | H | O | H | react-kit |  | documentation | P1 | 15 | High-value safety note: prevents deleting live files. Belongs in react-kit's React code-review reference — document des… |
| 128 | L456-preflight-eslint-newfile | Before pushing a newly created source/test file, run lint and type-check targeted at that exact file path (not just the whole-repo lint) so new-file-… | Repo-wide lint aggregates results and may exit zero or bury a new file's error among pre-existing warnings, s… | M | C | H | react-kit | devops-plugin, future:pre-push-guard | hook | P1 | 14 | High reuse, low effort, easy CI-pain prevention. Best as an opt-in PreToolUse/pre-push reminder hook (or react-doctor r… |
| 129 | L2015-usesearchparams-fp | Do not destructure this-bound native methods off objects returned by hooks (e.g. URLSearchParams.get) — it strips the receiver and throws at runtime;… | A static rule can't tell receiver-bound native methods from plain stable functions, so it suggests an unsafe … | M | O | H | react-kit |  | documentation | P2 | 13 | A reusable react-doctor false-positive recipe for any Next.js/React project. Belongs in react-kit's React code-review /… |
| 130 | L2014-rule-count-scoring | When a linter/quality tool scores by unique-rule presence rather than raw finding count, prioritize fully eliminating a rule (drive it to zero) over … | The scoring formula weights distinct violated rules, not occurrences; misunderstanding this makes cleanup eff… | L | O | H | react-kit |  | documentation | P2 | 12 | react-kit (the generalized react-admin-kit) is the natural home for a React-UI code-review / react-doctor triage discip… |
| 131 | L2021-react-doctor-live-playbook | For a fast-evolving external rule set, the skill should fetch the canonical playbook and per-rule recipes live from the vendor URL at triage time rat… | Embedding a third-party ruleset's guidance in a skill goes stale as the tool versions; a live-fetch pointer k… | L | O | H | react-kit |  | skill | P2 | 12 | Already implemented as the harness react-doctor skill (live-fetch pattern). For the marketplace, react-kit should refer… |
| 132 | L2018-control-has-label-fp | Before auto-adding aria-label to satisfy a control-has-label rule, verify there isn't already an associated visible <Label htmlFor> (which aria-label… | The accessibility rule checks for any label association mechanism but can't always see <Label htmlFor> wiring… | L | O | H | react-kit | paper-plugin | documentation | P2 | 11 | react-doctor a11y false-positive recipe. react-kit's React code-review/a11y reference is the home; paper-plugin's acces… |
| 133 | L2019-ellipsis-jsxtext-only | Scope-aware fixing: a rule that flags an ellipsis (or similar typography) only in JSX text content should not trigger edits to attribute/string value… | Rules target specific AST node types (JSXText vs JSXAttribute); fixers who don't know the rule's scope edit t… | L | O | H | react-kit |  | documentation | P3 | 9 | Minor react-doctor scope clarification for the react-kit code-review reference. Low impact but trivial to document alon… |
| 134 | L2020-skip-combine-iterations-small-arrays | Performance micro-optimization lint rules (e.g. combine filter+map into reduce) should be ignored on small UI-sized collections where the readability… | Iteration-combining rules assume hot, large collections; applied blindly to small UI lists they trade readabi… | L | O | H | react-kit |  | documentation | P3 | 9 | react-doctor 'when to ignore' guidance for react-kit's code-review reference. Reinforces the broader 'don't chase the n… |
| 135 | L1594a-guard-lowercase-host-match | Normalize case (and ideally canonicalize the host) before any deny/allow-list comparison in a safety guard. A literal substring match like *prod* sil… | Shell/string substring matching is case-sensitive by default, and authors write the guard against the lowerca… | C | O | H | qa-browser | devops-plugin, future:claude-env-doctor | hook | P0 | 18 | Directly improves qa-browser's existing production-URL safety gate (pre_navigate_prod_gate.py) and any devops destructi… |
| 136 | L1495-01 | A read-only/investigation task must never mutate auth/git/system state, even to work around an access error. When the only fix for an access failure … | Agents are biased toward 'fixing' a blocking error; under a read-only contract this bias causes unauthorized … | H | O | H | future:audit-orchestrator | qa-browser, devops-plugin | rule | P1 | 16 | This is a read-only-contract safety rule that belongs alongside the investigation workflow (same future:audit-orchestra… |
| 137 | L06-phased-migration-cutover-pattern | Apply a five-phase skeleton to any cutover/migration: (1) read-only discovery of both ends, never assuming paths; (2) full timestamped backups before… | Ad-hoc migrations mutate live state directly with no validation gate or rollback path, so silent breakage (de… | H | O | H | future:migration-cutover-runbook | devops-plugin, wiki-sop, docs-wiki | skill | P1 | 15 | Domain-agnostic safety skeleton — highly reusable. No existing plugin owns generic migration/cutover safety; a future m… |
| 138 | L934-default-write-scripts-flag-semantics | Never assume a destructive script's safety convention; read the source to confirm whether it defaults to write or dry-run and which flag actually gat… | Scripts adopt inconsistent or inverted safety conventions over time, and documented/aspirational gates are no… | C | O | H | devops-plugin | wiki-sop, future:script-safety-auditor | hook | P1 | 15 | Strong reusable production-safety rule: verify write/dry-run semantics from source before running, standardize on opt-i… |
| 139 | L970-script-default-flip-doc-sync | When changing a destructive script's behavior or safety convention, find every reference to the script across docs, skills, runbooks, package scripts… | Script behavior and the runbooks/skills referencing it live in different files; a code-only change leaves doc… | H | O | H | docs-wiki | wiki-sop, devops-plugin | checklist | P1 | 14 | This is a code-vs-docs drift / synchronized-update discipline — squarely docs-wiki-plugin's wiki-drift / code-vs-docs-d… |
| 140 | L563-tamper-evident-artifacts | To make a generated artifact verifiably unmodified, embed a SHA-256 hash of the verbatim content slice (between defined heading markers) as a footer … | Backup files and overwrite/backup prompts create places to stash a hand-polished version, and any interactive… | M | R | H | wiki-sop | future:assessment-toolkit, no-action | template | P3 | 8 | Tied to an assessment/transcript-grading SOP (candidate evaluation). The tamper-evident design pattern is reusable for … |
| 141 | L1042-softdelete-purge | Soft-delete implemented only at the Manager level (not the QuerySet level) silently hard-deletes on bulk .delete() and admin bulk-delete. A scheduled… | Soft-delete enforced via a custom Manager doesn't override QuerySet.delete(), so bulk paths bypass it; purge … | H | O | M | no-action | wiki-sop, future:django-data-safety | checklist | P3 | 8 | The QuerySet-vs-Manager soft-delete bypass and unguarded purge are real and high-risk, but they are Django-backend data… |
| 142 | L1042-commission-buckets | Some financial/aggregate views are intentionally computed-on-read with no materialized table; the payment-mutation path is made atomic and idempotent… | Agents tend to introduce materialized models for aggregates by default, and may not preserve idempotency/lock… | M | R | M | no-action | wiki-sop | documentation | P3 | 7 | Project-specific architectural decision (no CommissionPayout model). The generic takeaway (idempotent atomic money muta… |
| 143 | L620-github-wiki-flat-namespace | Before pushing to a flat-namespace wiki (GitHub Wiki): audit for filename collisions across all subfolders, rename collisions with a discriminating p… | Authors assume wiki URLs honor folder paths like a normal static site; GitHub Wiki flattens them, so collidin… | M | C | H | docs-wiki | docs-wiki | validation-rule | P1 | 14 | Squarely in docs-wiki-plugin's wheelhouse (it already owns flat-namespace + filename-uniqueness + internal-link convent… |
| 144 | L1840-removing-docs-check-dependents | Before deleting a large documentation tree, grep for cross-references across every surface (wiki, code comments, CI workflows, .gitignore, root READM… | Documentation trees are referenced from many unrelated surfaces, so a single delete leaves dangling links and… | M | O | H | docs-wiki | wiki-sop, no-action | checklist | P1 | 14 | Excellent fit for docs-wiki's existing scope (code-vs-wiki discrepancy, safe wiki edits, content migration into wiki, s… |
| 145 | L844-source-of-truth-ordering | Declare an explicit source-of-truth ordering for a project's knowledge layers (live code, wiki, current-state docs, target-state docs, skills) and tr… | Multiple knowledge layers drift independently over time; without a declared precedence and a code-first readi… | M | C | H | docs-wiki | wiki-sop, rag-plugin | skill | P1 | 13 | The code-vs-wiki drift discipline is exactly docs-wiki-plugin's wiki-code-vs-docs-discrepancy skill. A generic 'source-… |
| 146 | L857-handbook-target-not-current | Clearly separate target/aspirational architecture docs from current-state docs (e.g. by folder: docs/target/ vs docs/current/), label aspirational do… | Aspirational design docs and current-state docs get conflated in one 'architecture handbook'; readers assume … | M | C | H | docs-wiki | wiki-sop | skill | P1 | 13 | Generalizable as a docs-wiki authoring/structure rule: target-vs-current separation and labeling. The specific handbook… |
| 147 | L1051-stale-checkboxes | Status markers in planning/spec/sprint docs drift from reality. Never treat a doc checkbox or percent-complete as ground truth for scope; cross-refer… | Manual status markers are easy to write and easy to forget to update; the doc and the code evolve on differen… | M | C | H | docs-wiki | docs-wiki, future:plan-vs-reality-drift | skill | P1 | 12 | Generalizes cleanly to docs-wiki's code-vs-wiki drift capability (wiki-code-vs-docs-discrepancy / /wiki-drift): extend … |
| 148 | L890-jwt-lifetimes-stale-value | Treat config/security constants (token lifetimes, rate limits) as having a single source-of-truth location in code; when auditing docs, flag any dive… | Security/config constants get copied as literals into multiple docs; when the code value changes, the doc cop… | M | C | H | docs-wiki | wiki-sop, no-action | validation-rule | P2 | 11 | Generalizes to a code-vs-docs drift check for duplicated config constants (docs-wiki drift reporter territory). A mecha… |
| 149 | L961-audit-report-shape | Define a standard read-only audit report template: single dated Markdown file in a reports folder, a fixed numbered section sequence (inventory -> st… | Ad hoc audits vary in shape and scope, sometimes grep historical evidence (retaining old terminology) and pro… | L | O | H | docs-wiki | wiki-sop, qa-browser | template | P2 | 11 | A bundled audit-report template + grep-scope discipline fits docs-wiki (wiki-audit / sync-audit) — note docs-wiki-plugi… |
| 150 | L1827-git-rm-noop-verify-target-exists | Before executing a removal command, confirm the target actually exists in both the working tree and the index; if it's already absent, the requested … | A removal target may have been deleted in a prior commit, so git rm errors with nothing to do; engineers run … | L | R | H | docs-wiki | wiki-sop, no-action | checklist | P3 | 9 | Surfaced during a docs/ cleanup. docs-wiki already owns 'avoiding stale docs folders' and code-vs-wiki drift, so a 'ver… |
| 151 | L1216-po-typed-references | For Odoo i18n, field/selection/view translations require typed reference comments in the PO file, not plain source paths, or they won't apply to labe… | Plain source-path references load into the catalog but don't bind to field/view terms; authors hand-write ref… | M | O | H | odoo-plugin |  | skill | P1 | 13 | Perfect fit for odoo-plugin's odoo-i18n skill. Adds the typed-#:-reference rule and the 'always start from odoo --i18n-… |
| 152 | L1224-button-immediate-upgrade-hijack | For Odoo module upgrades that must reliably run migrations / reload translations, prefer the odoo-bin CLI form (odoo -u <modules> -d <db> --stop-afte… | The RPC upgrade button can be intercepted by the website module's configurator flow, so the intended upgrade/… | M | O | H | odoo-plugin |  | skill | P1 | 13 | Fits odoo-plugin's odoo-upgrade / odoo-service / odoo-docker skills. Add the 'prefer odoo-bin CLI --stop-after-init ove… |
| 153 | L1242-source-string-invalidates-po | Editing a translatable source string changes its msgid, orphaning the existing translation (which then falls back to source language). After any chan… | gettext keys translations by source-string msgid; editing the source string changes the key, so the prior tra… | M | O | H | odoo-plugin |  | validation-rule | P1 | 13 | Fits odoo-plugin's odoo-i18n skill; a strong candidate for a PostToolUse/validation check (the plugin currently lacks p… |
| 154 | L1251-unicode-escape-po | Never use Python's unicode_escape codec to decode UTF-8 (or any non-latin1) bytes — it mangles non-ASCII. Keep the byte-encoding layer (explicit UTF-… | unicode_escape interprets bytes as latin-1, so multi-byte UTF-8 sequences are corrupted; conflating byte-deco… | M | R | H | odoo-plugin | pandoc-plugin | documentation | P2 | 12 | PO-parsing encoding gotcha; fits odoo-plugin's odoo-i18n skill (and tangentially pandoc-plugin's Arabic/RTL handling). … |
| 155 | L1441-khairgate-i18n-po-source-of-truth | For Odoo bilingual/multilingual content, route translations through the standard i18n/<lang>.po gettext workflow (export .pot, msgmerge --previous, f… | Forking per-language view trees duplicates structure and drifts; the maintainable path is Odoo's gettext .po … | M | O | H | odoo-plugin | wiki-sop | skill | P1 | 12 | Strong fit for odoo-plugin's odoo-i18n skill, whose gap list explicitly notes 'no .po round-trip merge/conflict-resolut… |
| 156 | L659-odoo-post-copy-translated-fields | When writing a theme→concrete model mirror in Odoo, declare ALL translatable fields in _theme_translated_fields[<model>] = [(theme_field, real_field)… | Developers declare only the obvious translatable fields (name/description) and forget Html/translate fields, … | M | R | H | odoo-plugin |  | checklist | P2 | 11 | Clean fit for odoo-plugin's odoo-i18n sub-skill. Addresses the noted i18n gap (no .po round-trip / translation-loss saf… |
| 157 | L1234-theme-load-hook | When provisioning a fresh Odoo DB with a custom theme, configuring website + languages first then triggering _theme_load (or re-running odoo -u <them… | Theme page materialization is driven by the _post_copy/_theme_load hook, not by the theme_id field assignment… | L | O | H | odoo-plugin |  | skill | P2 | 11 | Fits odoo-plugin's theme-create / theme-design skills. Add the 'configure website+languages first, then trigger _theme_… |
| 158 | L07a-auth-me-over-ui-label | When verifying logged-in identity during browser QA, trust the auth/me API response over on-screen role labels; admin shells often render a static ro… | Front-end role labels are frequently hardcoded display copy decoupled from the authenticated session, mislead… | M | C | H | qa-browser | qa-browser, react-kit, wiki-sop | skill | P1 | 17 | Perfect fit for qa-browser's runtime-reality-check / role-smoke-tests skills, which already do role login flows. Trivia… |
| 159 | L1274-host-scoped-auth-headers-cors | Never inject host-specific auth headers (bypass secrets, tunnel keys, Cloudflare Access tokens, proxy auth) globally on a browser context. Always rou… | Global extraHTTPHeaders is the convenient default, but it leaks custom headers onto cross-origin requests who… | H | O | H | qa-browser | qa-browser | skill | P0 | 16 | High-value, low-effort: a concrete Playwright code recipe (context.route host-scoping) plus the 'renders-but-empty => C… |
| 160 | L1576-react-controlled-inputs-native-playwright | When automating a React/controlled-component app, default to native Playwright actions (click/fill/select) on the real control rather than injecting … | React controlled inputs only update through their synthetic event pipeline; directly assigning .value or firi… | M | C | H | qa-browser | react-kit, qa-browser | skill | P1 | 15 | Perfect fit for qa-browser's modal-and-action-walkthroughs / browser-qa-discipline skills: add an explicit rule that na… |
| 161 | L1260-vercel-preview-bypass | When a preview/staging deployment returns 401 at the edge, reach for the platform's purpose-built automation-bypass primitive (a scoped bypass secret… | Edge-level deployment protection looks like an app permissions problem, so engineers misdiagnose it and reach… | M | O | H | qa-browser | qa-browser, no-action | skill | P1 | 14 | Directly relevant to qa-browser's target/auth setup (/qa-target). A skill section on 'preview/staging deployment protec… |
| 162 | L1295-playwright-mcp-chrome-vs-chromium | When a Playwright-based MCP/tool errors with "Chromium distribution 'chrome' is not found", it's defaulting to the system Chrome channel. Fix by eith… | Playwright MCP defaults to the 'chrome' channel (system browser) rather than its own bundled chromium, and th… | M | O | H | qa-browser | qa-browser, future:claude-env-doctor | documentation | P1 | 13 | qa-browser drives playwright-mcp/chrome-devtools-mcp, so this MCP-setup troubleshooting note (chrome channel vs bundled… |
| 163 | L12-wsl-playwright-stale-profile-lock | When a persistent-profile browser MCP reports the profile in use, kill the orphaned top-level browser holding the profile (matching --user-data-dir, … | The MCP shares one persistent user-data-dir and never tears down the prior browser on plugin reload, so orpha… | M | O | M | qa-browser | qa-browser, future:claude-env-doctor, wiki-sop | skill | P2 | 10 | qa-browser drives playwright-mcp/chrome-devtools-mcp, so a troubleshooting reference (stale persistent-profile lock unl… |
| 164 | L2038-react-doctor-version-drift | When running a quality tool via @latest, its ruleset and scoring can change between runs; pin the tool version for any cross-run comparison and never… | Floating @latest pulls a new ruleset that adds/removes rules; comparing aggregate scores across versions conf… | M | O | H | react-kit |  | documentation | P2 | 13 | react-kit code-review/triage reference should mandate pinning the react-doctor version (or per-rule comparison) for any… |
| 165 | L320-stale-prisma-client-drift | Before editing code to resolve generated-ORM-client type errors, verify the generated client is fresh: compare generated-client mtime vs schema mtime… | A stale generated ORM client produces type errors that look exactly like schema-vs-code drift, so engineers e… | H | O | H | react-kit | future:orm-drift-doctor, no-action | skill | P1 | 12 | Reusable across any Prisma/TypeScript (Next.js) project, which makes react-kit a plausible home (it owns React/Next.js … |
| 166 | L374-coverage-ratchet-rhythm | When raising test coverage across many files, do one PR per file or per shared-mock domain cluster; ratchet coverage thresholds conservatively (only … | Aggressive threshold ratchets leave no margin so the next PR immediately trips the gate; megaPRs couple unrel… | M | O | H | react-kit | qa-browser, no-action | checklist | P2 | 12 | Generic React/Next.js + vitest coverage workflow; fits react-kit's code-review/test-quality remit as a documented playb… |
| 167 | L418-vitest-constructor-mock | When a unit under test instantiates an imported dependency with `new`, mock that dependency with a real ES class (or a function that mutates `this` a… | vi.fn() factory mocks return an object rather than binding `this`, so `new` produces undefined/incorrect inst… | M | O | H | react-kit | no-action | example | P2 | 12 | Specific but broadly reusable vitest gotcha for any TS/JS project mocking constructor-instantiated SDK clients. Best sh… |
| 168 | L441-singleton-untestable-branch | When a module-level lazy singleton guards initialization with a defensive throw, that throw branch is only reachable on the cache-empty first call, m… | Module singleton caches persist across tests in the same suite, so initialization-only branches execute at mo… | L | O | H | react-kit | no-action | documentation | P3 | 11 | Pairs with the coverage-ratchet and constructor-mock lessons; together they form a 'testing untestable-by-design code' … |
| 169 | L1728-mock-factory-missing-methods | When a test fails with 'cannot read mockResolvedValue/mockReturnValue of undefined', the test's inline mock is missing the method/property being stub… | Inline hand-written mock factories drift behind the methods the code under test actually calls, and the undef… | L | O | H | react-kit | qa-browser, wiki-sop, no-action | documentation | P3 | 9 | JS/TS unit-test mocking gotcha (Prisma/vitest). react-kit (generic React/Next.js patterns incl. testing of admin/data-l… |
| 170 | L696-claude-mcp-add-writes-dot-claude-json | When an MCP server fails to load, run `claude mcp list` first; if absent, edit ~/.claude.json (or use `claude mcp add`) — never trust ~/.claude/mcp.j… | The .claude/ folder holds most config (plugins, sessions, settings) so users reasonably assume MCP config liv… | M | C | H | rag-plugin | future:claude-env-doctor | checklist | P1 | 14 | rag-plugin already owns MCP-wiring diagnosis (ragtools-ops /doctor, /setup branch C, MCP-duplicate detection). Add the … |
| 171 | L709-dot-claude-json-concurrent-clobber | Before adding/changing MCP servers via `claude mcp add`, close other Claude Code instances; if an entry mysteriously disappears, suspect concurrent-s… | ~/.claude.json is rewritten wholesale on session events with no merge/locking, so concurrent instances overwr… | M | O | H | rag-plugin | future:claude-env-doctor | checklist | P2 | 13 | Pairs with L696 in rag-plugin's MCP-registration playbook (close other instances before mcp add; clobber-vs-corruption … |
| 172 | L1426-ragtools-8stage-architecture | When operating a tool against an upstream product, reference the product's documented binding decisions (decisions.md / D-xxx records) before changin… | Consumer-layer (plugin) decisions trace back to product-side architecture; without referencing the upstream d… | L | O | H | rag-plugin | wiki-sop | documentation | P2 | 11 | This is the upstream architecture rag-plugin operates against — a perfect fit as a bundled reference in rag-plugin (the… |
| 173 | L1886-superseded-rag-reminder-fp | A similarity-scored UserPromptSubmit reminder hook cannot distinguish knowledge questions from operational/inspection questions and will false-positi… | Phrase/score similarity alone is too coarse to classify prompt intent; without an override rule and a managed… | L | O | H | rag-plugin |  | hook | P3 | 9 | Already shipped/resolved in rag-plugin v0.11.0 (managed Section 0a + hook classifier). No further action beyond confirm… |
| 174 | L1109-codememory-branch-pinning | When building context/memory from multiple repos, pin each source to an explicit branch via detached git worktrees so the user's working tree is neve… | Reading the user's working tree or silently falling back to another branch produces context that drifts from … | M | R | H | future:wiki-memory-sync | memory-sync-rule, rag-plugin | documentation | P3 | 8 | This is a memory/context-sync engine design lesson (branch-pinned, worktree-isolated, fail-loud-per-source). It maps to… |
| 175 | L02b-cascade-to-money-audit-tables | Grep for cascade-delete foreign keys and trace each to its target; flag any whose deletion destroys money/audit history. Prefer restrict/null-on-dele… | Cascade-delete is a convenient default, but developers rarely trace the full cascade graph to discover it can… | C | O | H | future:django-safety-audit | odoo-plugin, wiki-sop, no-action | checklist | P1 | 14 | The CASCADE-tracing pattern generalizes beyond Django to any relational ORM, but the concrete grep target is Django syn… |
| 176 | L02a-django-softdelete-queryset-bypass | On any soft-delete audit, confirm a QuerySet/Manager-level delete() override exists (not just the instance method) and that admin bulk-delete actions… | Django executes QuerySet.delete() and admin bulk-delete at the SQL level, never calling the per-instance dele… | C | O | H | odoo-plugin | future:django-safety-audit, wiki-sop, no-action | checklist | P1 | 13 | Django-specific so plugin_fit is awkward — odoo-plugin is ORM-adjacent but not Django; the cleanest home is a new djang… |
| 177 | L398-prisma-db-push-drift | Before running a migration-deploy against an environment kept current by schema-direct push (db push / db sync), count migration directories vs the a… | Mixing schema-direct push with migration-history-aware workflows leaves the migrations bookkeeping table out … | H | O | H | future:db-migration-guard | react-kit, wiki-sop | checklist | P2 | 12 | Prisma/Node ecosystem-specific but a real bricked-deploy preventer. No existing plugin owns DB migration safety; react-… |
| 178 | L735-sync-gaps-push-once-not-bidirectional | When integrating two systems, document the sync direction and re-sync triggers explicitly: identify which edits will NOT propagate after the initial … | The integration was designed as one-time push plus balance-pull, not bidirectional; 'synced' is treated as te… | M | O | M | wiki-sop | no-action | documentation | P3 | 7 | Project-specific integration architecture (Aqraboon↔Odoo BMS). The generic 'document sync direction and non-propagating… |
| 179 | L1670-claude-code-401-loop-forceloginmethod | When Claude Code /login succeeds but every request returns 401, diagnose an account-type mismatch: compare the credential file shape against the org … | Claude Code can persist an OAuth token whose flow type doesn't match the billing/account type of the active o… | M | R | H | future:claude-env-doctor | no-action, wiki-sop | documentation | P2 | 12 | A Claude-Code-harness operational fix (auth flow, settings.json). No marketplace plugin owns Claude Code self-diagnosis… |
| 180 | L607-workspace-container-not-repo | When a project root is a container of sibling repos, detect the real repo root before running any VCS/build/test/deploy command, and treat the wiki r… | CLAUDE.md and habit assume the workspace root is the git repo; after a restructure (docs moved to a separate … | M | O | H | wiki-sop | docs-wiki, no-action | documentation | P3 | 7 | Project-specific layout fact (Aqraboon container). The generic 'detect repo root' habit is real but too thin to merit a… |
| 181 | L981-adahi-brd-structure | For a large new initiative, capture the work-item hierarchy (Epic -> Features -> PBIs) including intentional ID gaps and removed/out-of-scope items, … | Jumping straight to feature 1 without a foundation sprint leaves required data models, RBAC, and audit infras… | M | R | M | no-action | wiki-sop, devops-plugin | documentation | P3 | 7 | Almost entirely project/business-specific (the Epic/Feature/PBI IDs, the Adahi enum, the SMS aggregator). The one reusa… |
| 182 | L1387-two-html-editors-confirm-surface | When a codebase has multiple components serving a similar role (e.g. two editors, two upload paths, two auth flows), disambiguate WHICH surface the u… | Historical duplication (a legacy tool and a production component coexisting) plus stale code comments make it… | L | R | M | no-action | wiki-sop | documentation | P3 | 4 | Project-specific orientation fact about Royal Preps' two editors. The only reusable kernel ('disambiguate which surface… |
| 183 | L750-auto-approve-cron-is-policy-lever | Distinguish business-policy controls from technical validation when reasoning about a system: a timed approval cron is a configurable review-window l… | Stakeholders/engineers conflate a scheduled approval step with validation because both touch the approval sta… | L | R | M | no-action | wiki-sop | documentation | P3 | 3 | Pure project-domain business-logic explanation (Aqraboon approval flow). Not generalizable into a plugin artifact; belo… |

## 5. Existing plugin enhancement recommendations

This covers the **seven mature plugins**. The three planned plugins (react-kit / qa-browser / docs-wiki) are in §6. A recurring theme below: several MCP/Windows/WSL lessons *touch* a plugin's domain but are really generic Claude-Code environment truths — those should live once in the proposed `future:claude-env-doctor` and be *referenced* by the domain plugin, not copied (see §7).

### 5.1 devops-plugin — 11 lessons mapped · priority **P0–P1**

**Current purpose.** Azure DevOps hybrid (CLI + MCP) work-item / sprint / PR management with a single-owner layered architecture, a write-confirmation gate, and a `PreToolUse` validation hook.

**Lessons mapped (highlights).** Permission-first remote writes (L1504, s16); SHA-pin third-party GitHub Actions + `environment:`≠approval-gate (L05a, s15, **P0**); never assume a destructive script's flag semantics (L934, s15); verify work-item *type/container* semantics before bulk export (L259, s14); `required_linear_history` breaks long-lived-branch promotions (L01, s12); auto-switch GitHub identity by repo owner (L1513, s11); ask for the right MCP tool surface instead of guessing REST endpoints (L1766, s12); one subagent per long-form item to defeat truncation (L244, s11); bulk by domain cluster not phase (L1536, s11); SSH banner-vs-TCP-refused triage (L1690, s10); user-as-CI-watcher poll-skip (L474, s8).

**The catch worth naming up front.** This plugin is **Azure-DevOps-only**, but ~8 of these lessons are **GitHub** lessons (identity auto-switch, SHA-pinning, linear-history promotions, permission-first push). They do not belong inside the Azure DevOps skill. Two clean options: (a) generalize the plugin's safety layer into a provider-neutral `rules/` set that both an Azure and a GitHub workflow reference; or (b) host the GitHub-side rules in a small `future:git-promotion-doctor` / `future:git-identity-guard` and have devops-plugin reference them. **Recommended: (a)** — promote `rules/write-gate.md` to a provider-neutral *git/remote-write* contract.

- **Proposed new skills:** none net-new; extend the existing `devops` skill's WIQL/PR workflows with a "verify item type & project before bulk op" pre-step.
- **Proposed command updates:** add `/devops pipelines` (list/trigger builds, tail logs) — closes a real inventory gap; add `--cluster` batching semantics to bulk operations.
- **Proposed hooks (highest value):**
  - `PreToolUse` on any `git push` / `gh pr create` / repo-write MCP tool → **permission-first gate** (surface commit msg + file list, block until explicit go) and **identity check** (`git remote -v` → owner → `gh auth status` → auto-switch). This generalizes L1504 + L1513 and is the plugin's biggest risk-reduction win.
  - A CI-review advisor that flags non-SHA-pinned third-party actions, YAML-only "approval" gates, renamed required checks, and `continue-on-error` on established gates (L05a/L05d) — fires on edits to `.github/workflows/**`.
- **Proposed subagents:** a read-only `ci-pipeline-auditor` (haiku/sonnet) that enumerates `.github/workflows` and reports drift vs the documented SOP.
- **Proposed docs/examples/checklists:** a "bulk tracker export" checklist (verify type → walk hierarchy from named parent → one-subagent-per-item); a "long-lived-branch promotion" runbook (check `required_linear_history`; branch off target HEAD instead of looping merge PRs).
- **Generic behavior to add:** provider-neutral remote-write safety (permission-first + identity-correct + branch-protection-aware) belongs in `rules/`, referenced by both Azure and any future GitHub workflow.
- **Must NOT add:** specific org/repo names, the `a-lakosha`/`ahmed-lakosha` handle mapping, or Taqat's "PBI == user story" vocabulary as code — those are user/SOP config, kept in the user profile / `data/`, never hardcoded.
- **Priority:** P0 for the identity + permission-first + SHA-pin hooks; P1 for pipelines command and the CI auditor; P2 for cluster-batching and the watcher-delegation doc.
- **Risk-reduction value:** High — prevents wrong-identity pushes, supply-chain-mutable actions, and merge-conflict loops; all have burned real hours.
- **Acceptance criteria:** a push under the wrong gh identity is blocked/auto-corrected; `validate_plugin.py` passes 0 errors; a test asserts every shell script in `hooks/` is wired in `hooks.json` (the current docs-vs-wiring drift is itself a §5 finding); the CI auditor flags a `@v3` third-party action in a fixture workflow.

### 5.2 odoo-plugin — 12 lessons mapped · priority **P1–P2**

**Current purpose.** Unified Odoo plugin: upgrade, frontend, report, test, security, i18n, service, docker — organized as sub-skills under `skills/<area>/`.

**Lessons mapped.** Odoo i18n is the dominant theme: PO files need typed `#:` references for field/view labels (L1216); editing a source string orphans its `msgid` (L1242); never route PO bytes through `unicode_escape` (L1251); the canonical bilingual workflow is `.pot` export → `msgmerge --previous` → fill fuzzy (L1441); theme→concrete mirrors must declare every translatable field in `_theme_translated_fields` (L659). Runtime/ops: `_theme_load` after setting `theme_id` (L1234); `button_immediate_upgrade` gets hijacked by the website module → use odoo-bin CLI (L1224); never `down -v` — orphan filestore/data volume drift (L685); verify/preserve the actual Postgres major version before regenerating a stack (L672). Plus two Git-Bash/Docker path lessons (L1663, L1775).

- **Proposed new skills / sub-skill content:** enrich `skills/i18n/` with a canonical **PO gettext workflow reference** (typed references, `msgmerge` salvage semantics, source-string-invalidation audit, UTF-8 decode rule) and `skills/docker|service/` with a **volume-safety + Postgres-pinning** reference.
- **Proposed command updates:** add a `/odoo i18n-audit` flow (export `.pot`, diff against shipped `ar.po`, list stale/fuzzy msgids) and a `/odoo stack-doctor` (enumerate volumes, read `PG_VERSION` inside the named volume, warn before any `down -v`).
- **Proposed hooks:** a `PreToolUse` Bash guard that **blocks `docker compose down -v` / `docker volume rm`** on an Odoo stack and prints the copy-forward migration steps (generalizes L685 — pure risk reduction).
- **Proposed subagents:** a read-only `odoo-i18n-auditor` that flags stale msgids after source-string edits.
- **Proposed docs/examples/checklists:** "fresh DB + custom theme bring-up" checklist (configure website+languages → `_theme_load`); "module upgrade to reload translations" recipe (odoo-bin CLI form, not RPC).
- **Generic behavior to add:** the gettext/PO discipline is reusable across *any* Odoo client; keep it method-only.
- **Must NOT add:** per-client deviation notes — brand strings, module install orders, literal master passwords, or specific Docker volume names — those belong in a project Wiki/SOP, never in the plugin.
- **One mis-mapping to correct:** the **Django** soft-delete/CASCADE lessons (L02a, L02b) were routed here as the nearest "backend/ORM" home, but **Odoo ≠ Django**. They belong in `future:django-safety-audit` or `wiki-sop`, not odoo-plugin. Excluded from odoo-plugin scope.
- **Priority:** P1 for the i18n reference + volume-safety hook; P2 for the audit commands and Git-Bash path notes (latter overlap claude-env-doctor).
- **Risk-reduction value:** High for the `down -v` guard and Postgres-pin check (data-loss class); Medium for i18n (correctness/quality).
- **Acceptance criteria:** the down-`v` guard blocks on a fixture Odoo compose; the i18n reference reproduces the export→msgmerge→fill flow; `validate_plugin.py` clean; no client brand strings present (genericness grep).

### 5.3 rag-plugin — 6 lessons mapped · priority **P1–P2**

**Current purpose.** Operate/diagnose/repair the local `ragtools` service + its MCP wiring; knowledge-base retrieval discipline.

**Lessons mapped.** `claude mcp add -s user` writes to `~/.claude.json`, **not** `~/.claude/mcp.json` (L696); concurrent Claude-Code sessions clobber each other's `mcpServers` (L709); reference the product's documented `D-xxx` binding decisions before changing constraints (L1426); failing-plugin-MCP diagnosis ladder (`claude mcp list` → read `.mcp.json` → run the spawn command manually) (L13); inspect-first for operational/inspection questions (L1529); the similarity-scored retrieval-reminder hook false-positives on operational questions — already resolved upstream (L1886, superseded).

- **Proposed new skills:** none net-new; the existing `ragtools-ops` / `doctor` skills already own most of this. Add a short **"MCP wiring truths"** reference card consolidating L696/L709/L13 (much of this is already in `references/mcp-wiring.md` per the Migrated-to-Plugin-Skills index — verify it's current, don't duplicate).
- **Proposed command updates:** extend `/rag doctor` with an "MCP not loading" branch that runs the L13 diagnosis ladder automatically.
- **Proposed hooks:** none new — the retrieval-reminder hook's operational-question false-positive is **already fixed** (v0.11.0 + canonical Section 0a). Verify, don't re-solve.
- **Generic behavior to add:** the `~/.claude.json`-is-the-real-config truth and the failing-MCP diagnosis ladder are **generic Claude-Code facts**, not rag-specific — host the canonical copy in `future:claude-env-doctor` and have rag-plugin reference it (see §7). Keep only ragtools-service-specific wiring in rag-plugin.
- **Must NOT add:** ragtools internal architecture as plugin behavior (it's the product's `decisions.md`); the plugin should *reference* `D-xxx`, not restate it.
- **Priority:** P2 (most of this is consolidation/verification, not net-new); P1 only for the `/rag doctor` MCP-not-loading branch.
- **Risk-reduction value:** Medium — saves hours of "my MCP won't load" debugging.
- **Acceptance criteria:** `/rag doctor` detects and explains a missing/clobbered `~/.claude.json` entry; no duplication of facts already in `references/mcp-wiring.md`.

### 5.4 paper-plugin — 1 lesson mapped · priority **P3**

**Current purpose.** (Per inventory) research/paper-authoring assistance with agents + skills.

**Lessons mapped.** Only L1710 (Figma REST API needs a PAT; built-in WebFetch can't send custom headers → use `curl`). This is a **generic Claude-Code tooling fact**, not a paper-plugin concern. **Recommendation: do not enhance paper-plugin for this** — route L1710 to `future:claude-env-doctor` (the "WebFetch can't send custom auth headers" pattern is a tool-capability gotcha). paper-plugin gets **no lesson-driven change**.

### 5.5 ntfy-plugin, pandoc-plugin, remotion-plugin — **0 lessons each**

Honest finding: the lessons corpus contains **no** notification, document-conversion, or video/Remotion lessons, so none of these three receive a lesson-driven enhancement in this pass.

- Their **inventory gaps are still real** (e.g. remotion-plugin lacks render-failure diagnosis; pandoc-plugin lacks a format-matrix reference) — but those are *gap-driven*, not *lesson-driven*, and are explicitly **out of scope** for this study. Capture them in the plugins' own backlogs.
- **One cross-plugin tie-in (see §7):** if `qa-browser` gains screenshot/visual-evidence capture, and `remotion` ever needs visual QA of rendered frames, they should share a single screenshot/diff helper rather than each implementing one. And `devops-plugin`'s proposed notification-on-new-assignment could call `ntfy-plugin` rather than reinventing push. These are *integration opportunities*, not lessons.

---

## 6. Planned plugin recommendations

Each planned plugin already has a scaffold directory (`react-admin-kit-plugin`, `qa-browser-plugin`, `docs-wiki-plugin`). Below, every requested capability area is listed; areas with a mapped lesson are marked **[lesson-backed]** with the lesson IDs, areas that are expected-but-not-in-the-corpus are marked **[spine]** (build them because the plugin needs them, not because a lesson demands it).

### 6.1 react-kit  (rename of `react-admin-kit`)

**Purpose.** Reusable React/Next.js patterns *generally* — app architecture, admin panels, dashboards, forms/CRUD, navigation, UI structure, role-aware interfaces, and frontend quality rules. 32 lessons map here, but they cluster around **frontend-quality discipline and React-19 migration**, not admin panels — which is precisely why the broadened name fits. Admin-panel scaffolding is one capability, not the identity.

**What the lessons actually demand (lead with these):**

- **Lint/finding-triage discipline — the flagship skill. [lesson-backed: L1484, L2014, L2021, L2038, L2016, L2015, L2029, L2039, L2018, L2019, L2020, L2036]** Treat every analyzer finding (react-doctor, eslint, deslop, knip) as a *hypothesis*, classify it `safe-mechanical / needs-judgment / false-positive / forbidden-zone`, apply only the safe class, defer the rest with a documented reason, and **never chase the score**. Bundle the known false positives as a recipe library: `deslop/unused-file` is ~95% FP (use knip, alias+route-aware); `control-has-associated-label` over-fires when `<Label htmlFor>` already exists; `react-compiler-destructure-method` is wrong for `this`-bound natives like `useSearchParams().get`; `no-derived-state` is usually intentional snapshot/reset; `no-danger` on trusted staff HTML is audit-only; ellipsis rules are JSXText-only; skip `combine-iterations` on small arrays; per-page `nextjs-missing-metadata` ignores layout inheritance; score moves only when a whole rule hits 0; pin the tool version across runs.
- **React-19 migration reference. [lesson-backed: L2027, L2028, L2037]** `forwardRef`→ref-as-prop via `React.ComponentProps<…>` (drop redundant `displayName`, gate with `tsc --noEmit`); `useContext(Ctx)`→`use(Ctx)`; server-passthrough split to attach metadata to a `'use client'` layout without behavior change.
- **Data-fetching states: loading / error / empty / access-required. [lesson-backed: L08]** Hooks must propagate the error and the consumer must branch on status (`403→access-required`, `404→not-found`) — never swallow the error into a nullish empty shell. This is the highest-risk react-kit lesson and doubles as a **role-aware UI** rule.
- **Reusable UI structure & conventions. [lesson-backed: L1033]** When a codebase has an established modal/drawer pattern (e.g. custom fixed-position panels) and a mutation-hook/typing convention, *extend the convention* rather than introducing a competing UI lib. Skill = "detect-and-follow the house pattern."

**Requested capability areas (full coverage):**

| Area | Status | Source / note |
|---|---|---|
| React app architecture | [spine] | scaffold conventions; defer-to house pattern (L1033) |
| Admin panel layout | [spine] | secondary capability; template, not the identity |
| Sidebar / navigation | [spine] | template |
| Route / page organization | [lesson-backed: L2036, L2037] | per-page metadata reality; server/client split |
| Reusable components | [lesson-backed: L1033] | follow established primitives |
| Forms & validation | [lesson-backed: L1585] | gate any external filter/enum/status through fixed-allowlist membership before it hits a query |
| Tables / lists / detail pages | [lesson-backed: L1400, L2040] | hide-by-default sub-collections + opt-in query param; array-index keys only with a stable id |
| Dashboard cards / charts | [lesson-backed: L825] | default to the light path, lazy-load heavy viz (ECharts-GL) only on first toggle; dispose to free GPU |
| Role-aware UI | [lesson-backed: L08] | render access-required state from `403`, not an empty shell |
| Import/export interfaces | [spine] | pairs with qa-browser import/export QA |
| Loading / error / empty states | [lesson-backed: L08] | the canonical state machine |
| RTL/LTR support | [spine] | Arabic-first UX is a stated user constraint (preserve, don't regress) |
| Accessibility basics | [lesson-backed: L2017, L2018] | clickable backdrops → real `<button aria-label>`; verify existing `<Label htmlFor>` before adding aria-label |
| Anti-pattern detection | [lesson-backed: L2015, L2029] | don't destructure `this`-bound hook methods; derived-state is often intentional |
| Code-review checks for React UI | [lesson-backed: L2040, L2019, L2020, L456] | keys, scope-aware fixes, readability over micro-perf; pre-flight `eslint <new-file>` + `tsc --noEmit` |
| Frontend testing patterns | [lesson-backed: L418, L441, L1728, L374] | ES-class constructor mocks; singleton-throw branches are untestable (skip+document); inline mock-factory missing methods; conservative coverage ratchets |
| i18n strategy verification | [lesson-backed: L899] | confirm inline-context vs library vs `messages/` in code before reasoning |

- **Proposed artifacts:** skills — `react-lint-triage` (flagship), `react19-migration`, `data-fetching-states`, `follow-house-ui-pattern`; references — `react-doctor-false-positives.md`, `react-frontend-testing.md`; templates — `admin-panel/`, `dashboard/`, `crud-resource/`, `form-with-validation/`; a `hook` (PreToolUse/Stop) running targeted `eslint <new-file> && tsc --noEmit` before a push is proposed; optional `subagent` `react-quality-reviewer` (read-only, applies the triage classification to a diff).
- **What must NOT be added:** Royal-Preps/Aqraboon specifics — TipTap editor internals, `useModelListPage`, `src/lib/api/admin.ts` paths, medical-content sanitization decisions, specific question/exam models. Keep patterns; drop the project nouns.
- **Priority:** P0 `react-lint-triage` + `data-fetching-states`; P1 `react19-migration`, false-positive reference, forms/allowlist; P2 templates, testing reference, charts; P3 the rest.
- **Risk-reduction value:** High for data-fetching-states (silent access bugs) and lint-triage (prevents destructive "cleanups"); Medium elsewhere.
- **Acceptance criteria:** the triage skill reproduces the documented FP verdicts on a fixture; `data-fetching-states` renders access-required on a mocked 403; templates compile (`next build`); genericness grep finds no project nouns.

### 6.2 qa-browser

**Purpose.** Generic browser QA (Playwright / browser MCP): role login flows, route-access validation, UI-vs-API authorization proof, console/network capture, screenshots, destructive-action safeguards, import/export QA, staging/UAT smoke reports, PASS/FAIL/BLOCKED criteria, disposable-data safety. It owns **7 of the top-10 lessons by score** — the single most concentrated risk-reduction surface.

**What the lessons actually demand (lead with these):**

- **Identity & RBAC verification — the crown jewel. [lesson-backed: L07a, L07b, L1009]** Trust the **auth/me API over on-screen role labels** (admin shells render decorative role text). Prove an RBAC change by **reading status codes on disposable data**: `401/403`=still blocked; `400/409`=authorized, reached business logic — so a pre-fix `403`→`400 "field required"` proves the gate opened without crafting a destructive payload. And treat RBAC as **three layers** (route guard, UI visibility gate, deeper service guard) that can disagree, plus a dev-mode OTP bypass that must be scoped out before any staging scan.
- **Authorization review pass. [lesson-backed: L03, L908, L1594a, L1594b, L04b]** Source-to-sink trace (tainted input → sink → named mitigation at each hop) + sibling-route parity + control-replacement check; route-matcher inclusion ≠ protection (a path can fall through with no auth branch); lowercase/canonicalize host before any allow/deny match; treat "no Origin AND no Referer" on a state-changing method as a REJECT; verify no drift-tolerance window straddles a tier boundary.
- **Access to protected environments + CORS-safe injection. [lesson-backed: L1260, L1274]** Use the platform's purpose-built automation-bypass primitive for 401-at-the-edge previews; **route-scope** any host-specific auth/bypass header to the protected host only (global `extraHTTPHeaders` kills cross-origin XHRs via CORS preflight — "page renders, all widgets empty" is the signature).
- **Client-rendered-code anti-fraud audit. [lesson-backed: L633, L722]** Never treat a client-rendered barcode/QR/signature as authenticating; ask "what stops a screenshot or a swapped value?"; recommend rotating-HMAC/PIN/device-binding or document it as detection-only.
- **React-aware automation. [lesson-backed: L1576]** Drive controlled inputs with native Playwright `click/fill/select`, not injected DOM events (which skip React's `onChange`).

**Requested capability areas (full coverage):**

| Area | Status | Source / note |
|---|---|---|
| Role login flows | [lesson-backed: L1009, L1260] | per-role login; preview-bypass for staging |
| Route access validation | [lesson-backed: L908, L1009] | matcher≠protection; three-layer awareness |
| UI-vs-API authorization verification | [lesson-backed: L07a, L07b] | auth/me over labels; status-code proof |
| Console / network capture | [spine] | reinforced by L1274 (watch for CORS preflight failures) |
| Screenshots / visual evidence | [spine] | shared helper candidate with remotion (§7) |
| Destructive-action safeguards | [lesson-backed: L04b, + L04a/L04c via react-kit] | disposable data only; tier-boundary/drift checks |
| Import/export QA | [spine] | pairs with react-kit import/export UIs |
| Staging/UAT smoke reports | [lesson-backed: L961 template via docs-wiki] | dated, table-first, scoped |
| PASS / FAIL / BLOCKED criteria | [lesson-backed: L07b] | status-code semantics define the verdict |
| Disposable-data safety | [lesson-backed: L1009] | scope out OTP/SMS/coupon routes; test-phone allowlist; `BMS_ENABLED` off-equivalent |
| Browser-env troubleshooting | [reference→claude-env-doctor: L1295, L12] | chrome-vs-chromium, stale profile lock — *reference*, don't own |

- **Proposed artifacts:** skills — `verify-identity-and-rbac` (flagship), `authorization-review-pass`, `protected-preview-access`, `client-code-anti-fraud-audit`, `react-aware-automation`; checklist — `rbac-three-layer.md`, `destructive-action-safety.md`; template — `uat-smoke-report.md` (PASS/FAIL/BLOCKED, dated, evidence-linked); optional read-only `subagent` `route-access-prober`.
- **What must NOT be added:** Aqraboon coupon/OTP/SMS routes, Royal-Preps exam endpoints, Vercel project secrets, specific staging hostnames/bypass tokens — patterns only; never store a real bypass secret.
- **Priority:** P0 `verify-identity-and-rbac` + guard-hygiene + CORS-safe injection; P1 authorization-review-pass, preview access, anti-fraud audit, react-aware automation; P2 smoke-report template, import/export QA.
- **Risk-reduction value:** Very High — these lessons each prevented (or caught) a real authorization mistake; this is the corpus's best safety ROI.
- **Acceptance criteria:** the RBAC skill demonstrates a `403→400` proof on a fixture; header injection is route-scoped (no global CORS break); smoke report emits PASS/FAIL/BLOCKED with screenshots + status codes; no real secrets/hosts in the plugin.

### 6.3 docs-wiki

**Purpose.** Generic Wiki authoring & auditing — business docs, SOP pages, onboarding/role guides, workflow + Mermaid diagrams, code-vs-wiki discrepancy reports, safe edits, link/namespace validation, avoiding stale doc folders. **Boundary (per the brief): docs-wiki does NOT do Wiki→memory sync** — that is `future:wiki-memory-sync` (§8). 9 lessons map here, and they skew strongly toward **integrity/auditing and source-of-truth doctrine**, less toward authoring templates.

**What the lessons actually demand (lead with these):**

- **Source-of-truth doctrine. [lesson-backed: L844, L857, L890, L1051]** Declare an explicit knowledge-layer ordering (live code > wiki > current-state docs > target-state docs > skills) and treat code as truth for behavior; separate *target/aspirational* docs from *current-state* docs (by folder, labeled); treat security/config constants (token lifetimes, rate limits) as having one source-of-truth location and flag divergent literals; **never trust a doc checkbox or % complete as ground truth** — cross-reference git history + dated reports.
- **Code-vs-wiki discrepancy report. [lesson-backed: L844, L857, L890, L1051]** A read-only skill that reads code, then flags every doc/wiki claim that contradicts it (and resolves the conflict as a *doc fix*, not a code fix, unless a code change is queued).
- **Wiki integrity validators. [lesson-backed: L620, L970, L1840, L1827]** Flat-namespace link/collision validator (filenames globally unique; internal links use flat slugs without `.md`); script-reference sync (changing a script's behavior requires updating every doc/runbook/CI reference in the same change); safe doc-tree deletion (grep every dependent surface — wiki, code comments, workflows, README — before `rm`; verify the target even exists before "deleting").
- **Standard audit-report template. [lesson-backed: L961]** Single dated Markdown file, fixed numbered section sequence (Inventory → Status → Gaps → Conflicts → Stale refs → Frontmatter → Index → Bottom line), table-first, line-capped, excludes historical/forensic folders from grep scope.

**Requested capability areas (full coverage):**

| Area | Status | Source / note |
|---|---|---|
| Business docs | [spine] | page templates |
| Engineering SOP pages | [spine] | template; pairs with the audit-report shape |
| Onboarding guides | [lesson-backed: L857, L1051] | onboard from current-state, never the target handbook or stale checkboxes |
| User manuals / role guides | [spine] | template |
| Workflow diagrams / Mermaid | [spine] | authoring helper |
| Code-vs-wiki discrepancy reports | [lesson-backed: L844, L857, L890, L1051] | the auditing flagship |
| Safe wiki edits | [lesson-backed: L620, L1827, L1840] | link/namespace + delete-safety |
| Avoiding stale doc folders (Wiki = SoT) | [lesson-backed: L1840, L970] | migrate + scrub references, don't leave dead trees |

- **Proposed artifacts:** skills — `source-of-truth-doctrine`, `code-vs-wiki-discrepancy-report` (read-only, flagship), `wiki-link-namespace-validator`, `safe-doc-deletion`; template — `audit-report.md`, `sop-page.md`, `onboarding.md`, `role-guide.md`; optional read-only `subagent` `doc-drift-auditor`.
- **What must NOT be added:** Aqraboon's specific layer ordering numbers, JWT `24h/8h` values, GitHub-Wiki vs repo-wiki host specifics as hardcoded truth — keep the *doctrine*, parameterize the values.
- **Priority:** P1 discrepancy-report skill + source-of-truth doctrine + link/namespace validator + safe-deletion; P2 audit-report + page templates + Mermaid helper.
- **Risk-reduction value:** Medium-High — stale/contradictory docs are a persistent, recurring source of wasted hours and misleading onboarding.
- **Acceptance criteria:** the discrepancy report flags a planted code-vs-doc contradiction; the link validator catches a colliding filename + a `.md`-suffixed internal link; safe-deletion refuses to delete a tree with live cross-references; no project-specific constants baked in.

---

## 7. Cross-plugin recommendations

Several patterns touch more than one plugin. The rule for all of them: **one canonical implementation, referenced — never re-stated — by the others** (this is the single-owner layering doctrine from `devops-plugin/ARCHITECTURE.md`, applied across plugins). Duplicating a rule guarantees drift, which is itself one of the most common failure modes in the corpus.

| Cross-cutting pattern | Affected plugins | Canonical home | How others reference it | Duplication risk |
|---|---|---|---|---|
| **Claude-Code / Windows / WSL / MCP environment truths** (`~/.claude.json` is the real MCP config, concurrent-session clobber, WSL DNS/HCS, chrome-vs-chromium, LSP npm-shim, MSYS path conv, `git safe.directory`, `PYTHONIOENCODING`, WebFetch can't send custom headers, per-project env disables OAuth) | rag-plugin, odoo-plugin, paper-plugin, qa-browser, devops-plugin | **`future:claude-env-doctor`** (§8.1) | each plugin links to the relevant doctor entry from its troubleshooting section | **High** — these already appear half-stated in rag/odoo; consolidate before they diverge |
| **Remote-write safety** (permission-first push, identity auto-switch by repo owner, branch-protection/linear-history awareness) | devops-plugin, `future:git-*` ideas | **`devops-plugin/rules/remote-write-gate.md`** (promote to provider-neutral) | a GitHub workflow + the write-gate hook both load the same rule | High — Azure vs GitHub flows will each grow their own copy otherwise |
| **Authorization review & RBAC proof** (source-to-sink trace, sibling-route parity, control-replacement, 403-vs-400/409, CSRF/guard hygiene) | qa-browser, react-kit, devops (CI security) | **qa-browser `authorization-review-pass` + `verify-identity-and-rbac`** | react-kit references the frontend slice (error-swallow, CORS, allowlist); devops references the CI-security slice | Medium — keep the *trace methodology* in one skill |
| **"Analyzer findings are hypotheses, not commands"** (classify safe/judgment/FP/forbidden; never chase the score) | react-kit (React/lint), and any future code-review/security-scanner plugin | **shared `rules/findings-are-hypotheses.md`** referenced by react-kit | react-kit's `react-lint-triage` is the React *instance* of the shared meta-rule | Medium — language-agnostic; don't lock it inside react-kit |
| **Read-only investigation + parallel single-concern subagents + structured-output-once + verify-plan-vs-files** | devops, the planned plugins' subagents, plugin-authoring | **`future:audit-orchestrator` / plugin-authoring guide** (§8) | any plugin dispatching subagents references the dispatch contract | Medium — already a stated user preference; centralize once |
| **Audit / report shape** (dated single file, fixed numbered sections, table-first, scope-excludes historical folders) | docs-wiki (audit report), qa-browser (UAT smoke), devops (sprint report) | **docs-wiki `templates/audit-report.md`** | qa-browser's PASS/FAIL/BLOCKED smoke report and devops's sprint report adopt the section skeleton | Low |
| **Migration / cutover & volume/data safety** (discover→backup→stage→additive→archive-by-rename; never `down -v`; db-push drift) | odoo-plugin (volumes/Odoo), devops (deploy), `future:data-migration-safety` | **`future:data-migration-safety`** (§8.3) | odoo's `stack-doctor` and devops deploy flows reference the phased skeleton | Medium |
| **Destructive-action confirmation gates** (bind token to live server count, no auto-echo on step-up, drift-window vs tier boundary) | qa-browser (verify), react-kit (UI), devops (write-gate) | **one `confirmation-gate` contract** | each plugin implements its layer against the shared semantics | Low-Medium |
| **Screenshot / visual-evidence capture** | qa-browser (QA evidence), remotion (rendered-frame QA) | **shared screenshot+diff helper** | both call the helper rather than each writing one | Low (only if remotion ever does visual QA) |
| **Proactive notification** (new work-item assignment, failing build/CI) | devops-plugin (producer), ntfy-plugin (transport) | **ntfy-plugin** | devops's monitor/CI hooks call ntfy instead of reinventing push | Low — integration, not duplication |

**Net guidance:** build `future:claude-env-doctor` and the shared `rules/` contracts (remote-write, findings-are-hypotheses, confirmation-gate) *first*, because the most expensive cross-plugin risk in this corpus is **the same rule drifting between two homes** — exactly the doc-vs-code and SOP-vs-config drift the lessons keep flagging.

---

## 8. Future plugin recommendations

38 lessons pointed at a `future:*` destination across 15 raw names. Collapsing the singletons into coherent products yields **one clear build-now candidate, three build-soon/-later candidates, and a "do not build — fold in" list**. The guiding rule (per the brief): prefer enhancing an existing plugin; create a new plugin only when the capability is clearly reusable, high-value, and homeless.

### 8.1 `claude-env-doctor` — **BUILD NOW** (Phase 1) · ~18 lessons

- **Purpose.** Diagnose and repair the **Claude Code + Windows/WSL + MCP** environment — the layer beneath every project. One plugin that knows where config actually lives, how to isolate DNS-vs-TCP failures, and how to fix the recurring spawn/encoding/auth footguns.
- **Lessons that justify it.** `~/.claude.json` is the real user-MCP config (not `~/.claude/mcp.json`) (L696); concurrent-session clobber of `mcpServers` (L709); failing-plugin-MCP diagnosis ladder (L13); WSL DNS-vs-TCP isolation + resolv.conf override (L335); WSL HCS-timeout escalation ladder (L10); `wsl -l -v` distro discovery (L363); Playwright chrome-vs-chromium executable-path fix (L1295); WSL Playwright stale-profile-lock (L12); LSP npm-shim spawn fix on Windows (L1989); 401-login-loop `forceLoginMethod` (L1670); per-project `env` block silently disables OAuth (L1801); `PYTHONIOENCODING=utf-8` for Windows emoji output (L1567); `MSYS_NO_PATHCONV` (and its `-f`-flag footgun) (L1663/L1775); per-command `git -c safe.directory` over global edits (L1643); Grep-empty-on-Windows → Read fallback (L1719); WebFetch can't send custom headers (L1710); `/schedule` is cloud, not local (L294); don't allowlist execution-shaped tools (L1737); secret-hygiene config-migration redactor (L09f); session-storage schema for scan tooling (L536); WSL→Windows localhost masquerade (L09a); UNC copy-tool gotchas (L09d).
- **Why not folded in.** It spans every plugin's troubleshooting section; no existing plugin owns "the environment." Putting it in rag-plugin (the closest, by MCP overlap) would mis-scope rag-plugin and leave the WSL/Windows/LSP/auth lessons homeless.
- **Estimated value.** Very high — 18 recurring, cross-machine, time-sink lessons; this is the single most justified new plugin.
- **Priority / when.** P1, build in Phase 1 alongside the existing-plugin hardening; it's also the canonical home referenced by §7.
- **Shape.** A `/env-doctor` command + `doctor` skill with per-symptom branches (MCP-not-loading, WSL-unreachable, login-401, LSP-missing, encoding-crash), a `DNS-vs-TCP isolation` reference, and a SessionStart advisory hook (probe-tier, like rag-plugin's) that warns on known-bad config (e.g. a credential `env` block shadowing OAuth).

### 8.2 `agent-safety-guards` — **BUILD SOON** · ~5 lessons

- **Purpose.** Hooks/rules that keep autonomous and multi-agent runs safe.
- **Lessons.** Treat any pasted secret as compromised → revoke/reissue least-privilege (L307, **P0**); verify a cited "user already authorized this" before acting — prompt-injection defense (L275); split write-authority by artifact class (docs/skills editable; code-touching → plan file for approval) (L868); a read-only task must never mutate auth/git/state even to fix an access error (L1495); never fabricate an override notice — escalate to the human (L1543).
- **Why not folded in.** These are agent-governance primitives, not domain features; they cut across every plugin that writes or dispatches. devops-plugin's write-gate is *one* instance; the secret/prompt-injection/read-only-immutability rules are broader.
- **Value / priority.** High security value; P1. Could ship as `rules/` + `hooks/` consumed by other plugins rather than a user-facing command-heavy plugin.

### 8.3 `data-migration-safety` — **BUILD LATER** · ~4 lessons

- **Purpose.** Guardrails for risky DB/migration/cutover work.
- **Lessons.** Five-phase cutover skeleton (discover→backup→stage+validate→additive→archive-by-rename) (L06); cascade-delete FKs to money/audit tables → prefer restrict/null + snapshot identity (L02b); `prisma db push`-style drift before `migrate deploy` (L398); stale generated-ORM-client masquerading as schema drift (L320). (The Django soft-delete QuerySet-bypass lesson L02a also lands here, not in odoo-plugin.)
- **Why not folded in.** Spans Django/Prisma/Odoo and deploy — no single existing plugin covers "data migration safety" generically.
- **Value / priority.** Medium-High (data-loss class), but lower frequency; P2, after the planned plugins.

### 8.4 `wiki-memory-sync` — **BUILD LATER** (Phase 6) · 2 lessons + brief-specified

- **Purpose.** Read a project Wiki and generate AI-readable business memories + SOP rules — the capability the brief explicitly carves *out* of docs-wiki.
- **Lessons.** Reproducible multi-repo analysis via detached-worktree branch pinning (L490); pin each source to an explicit branch so the developer's working tree is never read (L1109). (These are the reproducibility mechanics a sync engine needs.)
- **Why not folded in / why later.** It depends on docs-wiki existing and stabilizing first; merging sync into docs-wiki would violate the stated boundary. The TR_plugins `memory-sync` engine is prior art to mine.
- **Value / priority.** Medium-High but explicitly deferred to Phase 6; evaluate after docs-wiki ships.

### 8.5 Do **NOT** build standalone — fold into an existing home

- **`gha-hardening` (3 lessons: SHA-pin, `environment:`≠approval, workflow-inventory drift, don't-weaken-gates).** No dedicated GitHub plugin exists (devops is Azure-only). Per the brief's "prefer enhancing the existing DevOps/GitHub plugin," **fold into devops-plugin's CI-review advisor** (§5.1) as a provider-neutral rule set — not a new plugin.
- **`plan-verifier`, `audit-orchestrator`, `plugin-authoring-guide`, `skill-library-architect`, `skill-system-auditor`, `agent-mcp-wrapper` (~7 lessons).** These are agent-workflow / plugin-authoring meta-patterns (verify plan vs files; read-only-subagent-vs-skill split; one-subagent-per-long-form-item; structured-output-call-once; skill-library layering with foundation>domain>workflow precedence; generalizable audit-report shape; wrap-shell-as-tiny-scoped-MCP). The marketplace already has **`claude-plugin-builder`** (session skill) and the official **plugin-dev** plugin. **Enhance those** with these references rather than spawning new plugins. The investigation-first methodology (L1471) is also a strong candidate to become a reusable *workflow*, given it matches the user's stated preference.

### Future-plugin summary

| Candidate | Lessons | Build? | Priority |
|---|---|---|---|
| claude-env-doctor | ~18 | **Yes, now** | P1 (Phase 1) |
| agent-safety-guards | ~5 | Yes, soon | P1 |
| data-migration-safety | ~4 | Later | P2 |
| wiki-memory-sync | 2 | Later (after docs-wiki) | P2 (Phase 6) |
| gha-hardening | 3 | No — fold into devops-plugin | — |
| plan/audit/plugin-authoring meta | ~7 | No — enhance claude-plugin-builder / plugin-dev | — |

---

## 9. What should NOT become a plugin

These lessons are best kept out of the plugin layer. 20 are project Wiki/SOP material, 1 are future Wiki→memory sync rules, and 37 are no-action (project-specific, one-off, too risky to automate, or already handled by CI/tests). Generic patterns were still extracted where one exists, so a future plugin can pick them up if the same issue recurs in a second project.

### Project Wiki / SOP only — 20

| Lesson | Why not a plugin | Generic pattern (if reusable later) |
|---|---|---|
| L919-tracked-security-issues-not-silently-patched | The specific four issues are project-specific (belong in that project's security wiki/SOP), but the 'tracked known-issues register, surface… | Maintain a tracked-known-issues register so agents surface (not silently fix) intentionally-deferred security/tech-debt items whe… |
| L1361-claudemd-not-reaching-running-sessions | Universally reusable Claude Code authoring insight (prefer slash commands over CLAUDE.md prose for new workflows; CLAUDE.md is session-star… | Instructions added to CLAUDE.md only take effect for sessions started afterward. When introducing a new workflow rule mid-project… |
| L1788-git-stash-include-untracked-before-pull | Generic git-safety workflow. No existing marketplace plugin owns local git hygiene (devops-plugin is Azure-DevOps work-items, not git worki… | Before pulling onto a branch that has local untracked files which would be overwritten, stash with --include-untracked under a de… |
| L879-dual-deploy-path | Highly project-specific deploy topology (ACA + PM2, no systemd). The reusable kernel is 'document deploy dispatch per environment and audit… | Document the exact deploy dispatch per environment (which command/tooling for production vs self-hosted vs other), and audit docs… |
| L998-stack-ci-reality-not-odoo | Two reusable kernels worth extracting: (1) 'detect the actual stack before applying tooling — don't run stack-foreign scanners', and (2) 'r… | Establish the real stack and CI/deploy reality from the repo before applying any tooling: detect the actual language/framework (d… |
| L1349-count-human-in-loop-hops | A durable agent-workflow design heuristic ('count human-in-the-loop hops, aim for <=1'). It's a design principle, not a tooled capability —… | When designing an agent+human workflow, count the explicit human steps per cycle and aim for <=1. If the agent's only role on one… |
| L1614-railway-ssh-hostkey-base64-c | Railway-specific deployment runbook. devops-plugin is Azure-DevOps-only (no Railway), so it isn't a clean home; the reusable kernel (intern… | When a platform's internal DB hostname resolves only inside its private network, run seed/migration commands in-container via the… |
| L1690-ssh-banner-timeout-vs-tcp-refused | Generic SSH/network troubleshooting decision tree. No marketplace plugin owns infra/SSH diagnostics; best as a DevOps/infra runbook page or… | Diagnose SSH failures by layer: a TCP connect failure (refused/timeout) points at network/security-group/instance reachability; a… |
| L563-tamper-evident-artifacts | Tied to an assessment/transcript-grading SOP (candidate evaluation). The tamper-evident design pattern is reusable for audit artifacts but … | To make a generated artifact verifiably unmodified, embed a SHA-256 hash of the verbatim content slice (between defined heading m… |
| L1681-fine-grained-vs-classic-pat | GitHub PAT-selection guidance with a user-specific account-routing tail (work multi-org account vs single-owner account). Generalize the PA… | Choose the GitHub PAT type by access scope: fine-grained PATs bind to a single resource owner, so use a classic PAT (read-only re… |
| L1701-vpn-bastion-not-server-ip | Network/VPN topology knowledge that is largely org-specific (depends on each company's infra CIDR scheme). Best captured as a project/infra… | After a VPN/bastion rollout, SSH targets must be reachable private IPs inside the VPN's routed CIDR, not the old public IPs. When… |
| L1757-gh-repo-clone-ignores-dest | Narrow gh-CLI gotcha. No marketplace plugin owns gh clone workflows (devops-plugin is Azure DevOps, explicitly noted as having no GitHub su… | Don't assume a CLI's destination/output argument was honored — verify the actual resulting path/name after the operation (e.g., l… |
| L1909-view-session-discriminator | Project-specific (aqraboon) security finding needing a one-time human review to land canonical phrasing in that project's audit SKILL.md — … | When two token types share one signing secret, the only thing preventing cross-token reuse is an explicit type/claim allow-list a… |
| L607-workspace-container-not-repo | Project-specific layout fact (Aqraboon container). The generic 'detect repo root' habit is real but too thin to merit a plugin artifact; be… | When a project root is a container of sibling repos, detect the real repo root before running any VCS/build/test/deploy command, … |
| L735-sync-gaps-push-once-not-bidirectional | Project-specific integration architecture (Aqraboon↔Odoo BMS). The generic 'document sync direction and non-propagating edits' insight is r… | When integrating two systems, document the sync direction and re-sync triggers explicitly: identify which edits will NOT propagat… |
| L795-vhdx-syncthing-mutual-exclusion | High data-loss risk but very niche and no plugin home; belongs in the VM README/ops playbook. The suggested start-vm.ps1 lock-file wrapper … | When sharing a single VM disk image across machines via a sync tool, enforce strict mutual exclusion: shut down fully (never susp… |
| L1051-phase-gating | Specific to one project's sales-cycle phase plan and one owner's approval requirement. The generic 'gate phases on UAT signoff + explicit o… | Multi-phase initiatives gate each phase on (a) prior-phase UAT signoff and (b) explicit owner approval before execution; agents m… |
| L780-hyperv-gen2-secureboot-uefi-ca | Same niche as L765 — Hyper-V Linux VM provisioning. No plugin owns VM/host provisioning; keep in the personal Hyper-V setup playbook. The P… | When scripting Gen2 Hyper-V VM creation for Linux, set the Secure Boot template to MicrosoftUEFICertificateAuthority in the provi… |
| L1814-router-proxy-for-mixed-endpoints | Advanced multi-vendor Claude Code setup knowledge; niche and setup-heavy (requires standing up a third-party router proxy). Best captured a… | A single Claude Code process can only target one API endpoint/auth; mixing models from different upstream vendors in one session … |
| L765-hyperv-xrdp-gnome-wayland-xfce | Niche environment/ops playbook with no marketplace-plugin home (no DevOps/VM-provisioning plugin exists; devops-plugin is Azure-DevOps-only… | For a Linux dev VM accessed over RDP, default to a lightweight X11 desktop (XFCE) rather than GNOME/Wayland; bake the .xsession +… |

### Future Wiki→memory sync rule — 1

| Lesson | Why not a plugin | Generic pattern (if reusable later) |
|---|---|---|
| L1522-01 | This is a personal communication-style preference, not plugin-shaped behavior. It belongs in the user's global CLAUDE.md / memory (a user-p… | Communication style contract: be terse, use sentences not paragraphs, skip play-by-play narration and trailing recaps, surface up… |

### No action (project-specific / one-off / handled elsewhere) — 37

| Lesson | Why not a plugin | Generic pattern (if reusable later) |
|---|---|---|
| L1605-yaml-frontmatter-colons-quoted-list-items | This workspace already owns validate_plugin.py (the plugin-authoring source of truth) — the right home is to add a strict-YAML frontmatter … | When authoring YAML frontmatter, avoid raw colons in unquoted scalars and quote-or-reword any list item that would start with a d… |
| L1748-skill-rename-name-folder-match | This is exactly what the workspace validator (validate_plugin.py / validate_plugin_simple.py) should assert — name==folder for SKILL.md. Be… | After renaming a skill (or any component whose folder name must equal a declared identifier in its manifest/frontmatter), verify … |
| L1923-mega-task-decomposition | This is a general Claude Code working-discipline lesson, not a domain plugin capability — it belongs in the user's Active Lessons / a workf… | When a task requires fetching/transcribing N>5 long-form verbatim items, do not do it in the main context (it force-summarizes an… |
| L1060-gh-account-flip | Real and high-risk (pushing as the wrong identity). Already encoded in the user's CLAUDE.md GitHub auto-switch rule. No current plugin owns… | When multiple GitHub identities are in play and the active gh account resets per shell, never rely on a session-level auth switch… |
| L1073-genericness-grep | Directly relevant to THIS study (mapping lessons to generic plugin destinations). A 'genericness grep' check is exactly the kind of guard c… | When generalizing project-specific tooling into a reusable plugin, run a 'genericness grep' for project-specific tokens (paths, r… |
| L1073-plugin-layout-validation | This is meta — about authoring THIS marketplace's plugins. It is already owned by validate_plugin.py + the repo CLAUDE.md + the claude-plug… | Plugin authoring contract: kebab-case <name>-plugin folder, required manifest fields, mandatory marketplace.json registration wit… |
| L1092-layered-config-update-safety | This is the canonical plugin-settings pattern (matches plugin-dev:plugin-settings .local.md guidance and devops-plugin's profile/config spl… | Separate plugin defaults from user/workspace overrides: ship defaults in the plugin tree, read overrides from a user/workspace co… |
| L1632-bulk-powershell-replace-over-edit-loops | General Claude Code working-style guidance, not a plugin capability — best lives in CLAUDE.md/LESSONS or a workflow SOP, hence no-action as… | For mechanical bulk find-and-replace across many files, prefer a scripted pass (PowerShell -replace / sed) over per-file Edit-too… |
| L09c-cli-test-doesnt-prove-gateway-path | Good general verification discipline (test the live path, not a proxy) but emerged in a project-specific (OpenClaw model-default) context. … | After changing a config value consumed by a long-running daemon, restart the daemon and verify through the live path; a fresh-rea… |
| L646-subagent-large-file-watchdog-script | A cross-cutting Claude Code authoring discipline, not a fit for any existing domain plugin. Best captured as a global lesson/workflow note … | When a deliverable is a single large file driven by deterministic rules (template-per-section + glossary), generate it with a scr… |
| L1042-softdelete-purge | The QuerySet-vs-Manager soft-delete bypass and unguarded purge are real and high-risk, but they are Django-backend data-safety concerns wit… | Soft-delete implemented only at the Manager level (not the QuerySet level) silently hard-deletes on bulk .delete() and admin bulk… |
| L1060-worktree-syncthing | Useful environment trick but no current plugin owns git-worktree/Syncthing workflow. Already captured as a LESSONS.md entry; the harness no… | When the working tree is continuously modified by an external syncing tool (Syncthing, Dropbox, etc.), don't fight the dirty tree… |
| L1656-git-archive-tar-recover-gitignored | Niche but genuinely useful git recovery recipe. No marketplace plugin owns generic git operations; best captured as an LESSONS/SOP snippet … | To recover gitignored-but-committed files from history, use git archive <commit> <path> \| tar -x -C <dest> (reads the object sto… |
| L510-tr-newline-sanitize-bug | Embedded shell-hygiene sub-bug from the worktree lesson. Too granular for its own plugin artifact; best left as a note or folded into whate… | When sanitizing a string into a filesystem-safe slug in shell, prefer bash parameter expansion (`${name//[^a-zA-Z0-9_]/_}`) over … |
| L589-slash-commands-project-scoped | This is exactly the gap the plugin/marketplace mechanism already solves (packaging commands for distribution) — for marketplace plugins it'… | Slash commands and workspace CLAUDE.md are scoped to the workspace where they live and are not auto-shared across repos; any work… |
| L981-adahi-brd-structure | Almost entirely project/business-specific (the Epic/Feature/PBI IDs, the Adahi enum, the SMS aggregator). The one reusable kernel — 'sequen… | For a large new initiative, capture the work-item hierarchy (Epic -> Features -> PBIs) including intentional ID gaps and removed/… |
| L1018-local-only-classifier-blocks-promotion | This is a meta-observation about working with a safety classifier, not a buildable feature for a product plugin. The reusable behavior — 's… | When an autonomous-mode safety classifier blocks an action by phrase/intent similarity (e.g. treating any staging/prod-targeted g… |
| L1042-commission-buckets | Project-specific architectural decision (no CommissionPayout model). The generic takeaway (idempotent atomic money mutations via select_for… | Some financial/aggregate views are intentionally computed-on-read with no materialized table; the payment-mutation path is made a… |
| L1092-plugin-scope-restricted | About a DIFFERENT marketplace's plugin (Taqat-Trading-Business-Solutions/Plugins). Meta plugin-authoring guidance — preserve declared scope… | A plugin's intended scope (workspace-restricted vs generic-marketplace) must be stated consistently across README, manifest, and … |
| L1160-inwsl-syncthing | WSL/Syncthing topology recipe. No plugin owns this domain. The 'never run a stateful CLI on both synced machines / exclude data dirs / sync… | For syncing developer state between two WSL2 machines, run the sync agent natively inside WSL (not Windows-side over the \\wsl.lo… |
| L09b-scheduled-task-gateway-lifecycle | Very tool-specific (OpenClaw's scheduled-task gateway). The general principle (use the lifecycle wrapper, don't force-run) is mild and bett… | When a Windows background service is implemented as a Scheduled Task, manage it through its lifecycle wrapper (start/stop/restart… |
| L1060-tiptap-starterkit | Library-version-specific gotcha (TipTap v3). Too narrow for a plugin skill; better served by context7 docs lookup. Already in LESSONS.md. N… | When a rich-text/editor framework's 'starter kit' bundles extensions that you also want to configure explicitly, disable the bund… |
| L1060-prosemirror-paste | Narrow debugging insight about ProseMirror/TipTap clipboard behavior. The generic 'isolate client vs server transformation before blaming b… | When content appears to lose formatting 'after save', verify whether the loss happens client-side at paste/clipboard-parse time r… |
| L1127-openclaw-agent-isolation | OpenClaw-product-specific multi-agent isolation. Strong security lesson but tied to a specific bot platform; no marketplace plugin covers A… | When hosting multiple AI agents in one process, isolate by (1) per-agent persistent memory keyed by agent id, (2) explicit per-ag… |
| L1142-wsl-autostart-vbs | Windows/WSL environment recipe. No marketplace plugin owns Windows/WSL host setup. Reusable but niche; would fit a future env-doctor/WSL-se… | To run any process inside WSL silently at Windows login, use a wscript/VBS shim with window style 0 launched by a logon Scheduled… |
| L1177-wsl-tailscale-nat | Networking/WSL diagnostic recipe. No plugin home. Reusable env knowledge; already in LESSONS.md. No-action for the catalog. | WSL2's internal NAT means a Windows-host VPN/overlay (Tailscale) does not reach services bound inside WSL; to get direct full-spe… |
| L1315-telegram-single-getupdates | Niche to Telegram-bot integrations (OpenClaw/Roy). No current plugin owns Telegram. ntfy-plugin's two-way Q&A polling is the nearest concep… | For single-consumer poll APIs (Telegram getUpdates, exclusive webhooks), never write a capture script that assumes it owns the lo… |
| L810-plan-then-execute-auto-paced-loops | A general Claude Code orchestration technique (use /loop for multi-phase plans). It's a workflow habit, not a domain artifact; no existing … | When asked to implement N sequential phases, author all N prompts up front (each self-contained with decisions/paths/prior output… |
| L1191-bootstrap-kit-pattern | General bring-up automation pattern (idempotent steps, peer-handshake via shared dir, don't trust first-scan counts). No marketplace plugin… | For cross-machine bring-up automation: stage an idempotent bootstrap kit in an already-synced shared location, auto-ferry it, exp… |
| L1372-tiptap-addattributes-camelcase | Library-specific (TipTap/ProseMirror) gotcha tied to one project's rich-text editor. react-kit is framework-generic and deliberately makes … | When extending a ProseMirror/TipTap node with attributes that map to HTML data-attributes, use camelCase attribute keys plus expl… |
| L1456-adahi-brd-json-source-of-truth | Largely project-specific (aqraboon/Adahi feature numbers, file layout). The generic kernel — 'snapshot tracker scope into local JSON via th… | When planning against a work-tracking system, snapshot the scope into local per-feature JSON files (metadata + child work-item li… |
| L1855-migrated-index | Already-absorbed bookkeeping index. No new plugin work needed — these lessons already live in rag-plugin skills and the wiki Plugin-Develop… | When durable lessons are migrated into plugin skills/docs, keep a thin index table in the central lessons file that points to the… |
| L1202-wslconfig-keys | Trivial INI-syntax gotcha for .wslconfig. No plugin home; already in LESSONS.md. No-action. | INI/TOML-style config files use a section header plus bare keys, not dotted section-prefixed keys; when a config tool emits a rec… |
| L1387-two-html-editors-confirm-surface | Project-specific orientation fact about Royal Preps' two editors. The only reusable kernel ('disambiguate which surface before fixing') is … | When a codebase has multiple components serving a similar role (e.g. two editors, two upload paths, two auth flows), disambiguate… |
| L1550-01 | This is a project-specific agent-design lesson (a named BA liaison bot for one platform) about config-file separation and phrasing. The gen… | When one agent spans two contexts (internal dev vs external client), separate the two rule sets into their respective config file… |
| L09e-bash-classifier-500-compound-wsl | A harness-level quirk Claude can't fix from a plugin; only a behavioral workaround (decompose commands). Low preventability and no plugin l… | When a command-safety classifier intermittently errors on compound/looping WSL invocations, decompose into simple single-purpose … |
| L750-auto-approve-cron-is-policy-lever | Pure project-domain business-logic explanation (Aqraboon approval flow). Not generalizable into a plugin artifact; belongs in the project's… | Distinguish business-policy controls from technical validation when reasoning about a system: a timed approval cron is a configur… |

## 10. Grading and prioritization

Every lesson was graded 1–5 on impact, reuse potential, implementation effort, risk reduction, and plugin fit. `priority_score = impact + reuse_potential + risk_reduction + plugin_fit − implementation_effort` (range −1…19).

### Top 20 overall recommendations

| Lesson | Dest | Artifact | Imp | Reuse | Risk | Fit | Effort | Score | Prio |
|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| L1009-rbac-three-layers-dev-otp | qa-browser | checklist | 5 | 5 | 5 | 5 | 2 | **18** | P0 |
| L1594a-guard-lowercase-host-match | qa-browser | hook | 5 | 5 | 5 | 5 | 2 | **18** | P0 |
| L07a-auth-me-over-ui-label | qa-browser | skill | 4 | 5 | 4 | 5 | 1 | **17** | P1 |
| L07b-403-vs-400-409-rbac-proof | qa-browser | skill | 4 | 5 | 4 | 5 | 1 | **17** | P0 |
| L1484-01 | react-kit | skill | 5 | 5 | 5 | 4 | 2 | **17** | P0 |
| L03-security-review-source-to-sink | qa-browser | skill | 5 | 5 | 5 | 3 | 2 | **16** | P0 |
| L722-pure-renderer-not-security-primitive | qa-browser | checklist | 4 | 5 | 5 | 4 | 2 | **16** | P1 |
| L1274-host-scoped-auth-headers-cors | qa-browser | skill | 5 | 4 | 4 | 5 | 2 | **16** | P0 |
| L1495-01 | future:audit-orchestrator | rule | 4 | 5 | 5 | 4 | 2 | **16** | P1 |
| L1504-01 | devops-plugin | hook | 4 | 5 | 5 | 4 | 2 | **16** | P1 |
| L1594b-csrf-missing-both-headers-reject | qa-browser | validation-rule | 5 | 4 | 5 | 4 | 2 | **16** | P1 |
| L05a-sha-pin-third-party-actions | devops-plugin | hook | 4 | 5 | 5 | 3 | 2 | **15** | P0 |
| L06-phased-migration-cutover-pattern | future:migration-cutover-runbook | skill | 4 | 5 | 5 | 3 | 2 | **15** | P1 |
| L08-error-swallowing-data-hooks | react-kit | skill | 4 | 5 | 3 | 5 | 2 | **15** | P1 |
| L307-pasted-token-is-compromised | future:secrets-hygiene-guard | hook | 5 | 5 | 5 | 3 | 3 | **15** | P0 |
| L633-barcode-not-auth-token | qa-browser | checklist | 4 | 4 | 5 | 4 | 2 | **15** | P1 |
| L908-middleware-fallthrough-and-exceptions | qa-browser | checklist | 4 | 4 | 5 | 4 | 2 | **15** | P1 |
| L934-default-write-scripts-flag-semantics | devops-plugin | hook | 5 | 4 | 5 | 3 | 2 | **15** | P1 |
| L1471-01 | future:audit-orchestrator | skill | 5 | 5 | 4 | 4 | 3 | **15** | P1 |
| L1576-react-controlled-inputs-native-playwright | qa-browser | skill | 4 | 5 | 2 | 5 | 1 | **15** | P1 |

### Top 10 existing-plugin enhancements

| Lesson | Dest | Artifact | Imp | Reuse | Risk | Fit | Effort | Score | Prio |
|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| L1504-01 | devops-plugin | hook | 4 | 5 | 5 | 4 | 2 | **16** | P1 |
| L05a-sha-pin-third-party-actions | devops-plugin | hook | 4 | 5 | 5 | 3 | 2 | **15** | P0 |
| L934-default-write-scripts-flag-semantics | devops-plugin | hook | 5 | 4 | 5 | 3 | 2 | **15** | P1 |
| L259-verify-workitem-type-semantics | devops-plugin | checklist | 4 | 3 | 4 | 5 | 2 | **14** | P1 |
| L685-odoo-volume-drift-never-down-v | odoo-plugin | hook | 4 | 3 | 5 | 4 | 2 | **14** | P1 |
| L696-claude-mcp-add-writes-dot-claude-json | rag-plugin | checklist | 4 | 4 | 3 | 4 | 1 | **14** | P1 |
| L02a-django-softdelete-queryset-bypass | odoo-plugin | checklist | 5 | 3 | 5 | 2 | 2 | **13** | P1 |
| L672-almajal-pg16-volume-forward-incompat | odoo-plugin | hook | 4 | 3 | 4 | 4 | 2 | **13** | P1 |
| L709-dot-claude-json-concurrent-clobber | rag-plugin | checklist | 3 | 4 | 3 | 4 | 1 | **13** | P2 |
| L1216-po-typed-references | odoo-plugin | skill | 4 | 3 | 3 | 5 | 2 | **13** | P1 |

### Top 10 planned-plugin additions (react-kit / qa-browser / docs-wiki)

| Lesson | Dest | Artifact | Imp | Reuse | Risk | Fit | Effort | Score | Prio |
|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| L1009-rbac-three-layers-dev-otp | qa-browser | checklist | 5 | 5 | 5 | 5 | 2 | **18** | P0 |
| L1594a-guard-lowercase-host-match | qa-browser | hook | 5 | 5 | 5 | 5 | 2 | **18** | P0 |
| L07a-auth-me-over-ui-label | qa-browser | skill | 4 | 5 | 4 | 5 | 1 | **17** | P1 |
| L07b-403-vs-400-409-rbac-proof | qa-browser | skill | 4 | 5 | 4 | 5 | 1 | **17** | P0 |
| L1484-01 | react-kit | skill | 5 | 5 | 5 | 4 | 2 | **17** | P0 |
| L03-security-review-source-to-sink | qa-browser | skill | 5 | 5 | 5 | 3 | 2 | **16** | P0 |
| L722-pure-renderer-not-security-primitive | qa-browser | checklist | 4 | 5 | 5 | 4 | 2 | **16** | P1 |
| L1274-host-scoped-auth-headers-cors | qa-browser | skill | 5 | 4 | 4 | 5 | 2 | **16** | P0 |
| L1594b-csrf-missing-both-headers-reject | qa-browser | validation-rule | 5 | 4 | 5 | 4 | 2 | **16** | P1 |
| L08-error-swallowing-data-hooks | react-kit | skill | 4 | 5 | 3 | 5 | 2 | **15** | P1 |

### Top future-plugin candidate lessons

| Lesson | Dest | Artifact | Imp | Reuse | Risk | Fit | Effort | Score | Prio |
|---|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| L1495-01 | future:audit-orchestrator | rule | 4 | 5 | 5 | 4 | 2 | **16** | P1 |
| L06-phased-migration-cutover-pattern | future:migration-cutover-runbook | skill | 4 | 5 | 5 | 3 | 2 | **15** | P1 |
| L307-pasted-token-is-compromised | future:secrets-hygiene-guard | hook | 5 | 5 | 5 | 3 | 3 | **15** | P0 |
| L1471-01 | future:audit-orchestrator | skill | 5 | 5 | 4 | 4 | 3 | **15** | P1 |
| L1737-no-allowlist-execution-shaped-tools | future:claude-env-doctor | validation-rule | 4 | 5 | 5 | 3 | 2 | **15** | P1 |
| L02b-cascade-to-money-audit-tables | future:django-safety-audit | checklist | 5 | 3 | 5 | 3 | 2 | **14** | P1 |
| L1543-01 | future:audit-orchestrator | rule | 4 | 4 | 5 | 3 | 2 | **14** | P2 |
| L05b-environment-block-not-approval-gate | future:gha-hardening | checklist | 4 | 4 | 4 | 3 | 2 | **13** | P1 |

### Top 10 things to avoid (no-action / SOP-only, do not automate)

| Lesson | Class | Why avoid |
|---|---|---|
| L919-tracked-security-issues-not-silently-patched | wiki-sop | The specific four issues are project-specific (belong in that project's security wiki/SOP), but the 'tracked known-issues register, surface… |
| L1042-softdelete-purge | no-action | The QuerySet-vs-Manager soft-delete bypass and unguarded purge are real and high-risk, but they are Django-backend data-safety concerns wit… |
| L1060-gh-account-flip | no-action | Real and high-risk (pushing as the wrong identity). Already encoded in the user's CLAUDE.md GitHub auto-switch rule. No current plugin owns… |
| L1073-plugin-layout-validation | no-action | This is meta — about authoring THIS marketplace's plugins. It is already owned by validate_plugin.py + the repo CLAUDE.md + the claude-plug… |
| L1073-genericness-grep | no-action | Directly relevant to THIS study (mapping lessons to generic plugin destinations). A 'genericness grep' check is exactly the kind of guard c… |
| L1605-yaml-frontmatter-colons-quoted-list-items | no-action | This workspace already owns validate_plugin.py (the plugin-authoring source of truth) — the right home is to add a strict-YAML frontmatter … |
| L1923-mega-task-decomposition | no-action | This is a general Claude Code working-discipline lesson, not a domain plugin capability — it belongs in the user's Active Lessons / a workf… |
| L09c-cli-test-doesnt-prove-gateway-path | no-action | Good general verification discipline (test the live path, not a proxy) but emerged in a project-specific (OpenClaw model-default) context. … |
| L563-tamper-evident-artifacts | wiki-sop | Tied to an assessment/transcript-grading SOP (candidate evaluation). The tamper-evident design pattern is reusable for audit artifacts but … |
| L646-subagent-large-file-watchdog-script | no-action | A cross-cutting Claude Code authoring discipline, not a fit for any existing domain plugin. Best captured as a global lesson/workflow note … |

## 11. Proposed implementation roadmap

Sequenced so the highest risk-reduction and the shared canonical homes land first, and the planned plugins build on a stable base. Every phase obeys the workspace rules: bump `plugin.json` version + add a CHANGELOG entry on every change, register new plugins in `plugins/.claude-plugin/marketplace.json`, run `validate_plugin.py` to 0 errors (the 2 `hooks.json` warnings are the known benign quirk), command filenames carry **no** plugin-name prefix, SKILL.md uses the canonical "Use when…" voice, and **no push without explicit approval** (direct-to-main is fine when approved).

### Phase 0 — Structure confirmation & architecture decisions
- **Objective.** Lock the decisions this plan surfaces before writing code.
- **Decisions to confirm:** (1) execute the `react-admin-kit` → **react-kit** rename (folder, `plugin.json` name, `marketplace.json` entry, SKILL frontmatter `name:`); (2) approve `claude-env-doctor` and `agent-safety-guards` as new plugins; (3) approve promoting `devops-plugin/rules/write-gate.md` to a provider-neutral remote-write contract and folding `gha-hardening` into devops-plugin; (4) confirm Django/DB-safety lessons leave odoo-plugin for `future:data-migration-safety`.
- **Files likely touched later:** none yet (decision pass).
- **Validation:** decisions recorded; `validate_plugin.py` baseline captured for all 10 plugins.
- **Acceptance:** Ahmed signs off on the rename + the two new plugins + the fold-ins.
- **Risks:** scope creep — keep the new-plugin count to the two approved; everything else is fold-in or later.

### Phase 1 — High-impact existing-plugin hardening + shared homes
- **Objective.** Ship the P0/P1 risk-reduction wins and the canonical cross-plugin homes referenced everywhere else.
- **Work:** devops-plugin — permission-first + identity-auto-switch write hook, CI-review advisor (SHA-pin/`environment:`/gate-weakening), reconcile hook wiring vs docs; odoo-plugin — `down -v` guard + Postgres-pin check + i18n/PO reference; rag-plugin — `/rag doctor` MCP-not-loading branch (verify, don't duplicate `references/mcp-wiring.md`); **build `claude-env-doctor`** (the §7 canonical env home); **build `agent-safety-guards`** (secrets-compromised, prompt-injection-verify, read-only-immutability, write-authority-split); add shared `rules/` (`remote-write-gate.md`, `findings-are-hypotheses.md`, `confirmation-gate.md`).
- **Proposed artifacts:** hooks (write-gate, CI-advisor, down-`v` guard, secret/prompt-injection guards, env SessionStart advisory); skills (`env-doctor`, odoo i18n reference); subagents (`ci-pipeline-auditor`, read-only).
- **Validation:** each new hook fires on a fixture (wrong-identity push blocked, `@v3` action flagged, `down -v` blocked, planted secret flagged); `validate_plugin.py` 0 errors; genericness grep (no project nouns/secrets).
- **Acceptance:** the top-10 §1 recommendations that map to devops/odoo/rag/env/safety are demonstrably enforced on fixtures.
- **Risks:** duplicating env truths that already live in rag-plugin — mitigate by making rag reference claude-env-doctor, not copy.

### Phase 2 — react-kit (plan + scaffold)
- **Objective.** Rename, then implement the frontend-quality core.
- **Files likely touched:** `react-admin-kit-plugin/` → `react-kit-plugin/` (or registered `react-kit`); `plugin.json`, `marketplace.json`, `CHANGELOG.md`; new `skills/react-lint-triage/`, `skills/data-fetching-states/`, `skills/react19-migration/`, `skills/follow-house-ui-pattern/`; `references/react-doctor-false-positives.md`, `references/react-frontend-testing.md`; `templates/{admin-panel,dashboard,crud-resource,form-with-validation}/`; optional pre-push `hook` + `react-quality-reviewer` subagent.
- **Validation:** triage skill reproduces documented FP verdicts on a fixture; `data-fetching-states` renders access-required on a mocked 403; templates pass `next build`; `validate_plugin.py` clean; genericness grep.
- **Acceptance:** §6.1 P0/P1 artifacts present and demonstrated; no project nouns.
- **Risks:** scope sprawl into project specifics (TipTap, `useModelListPage`) — keep patterns generic.

### Phase 3 — qa-browser (plan + scaffold)
- **Objective.** Implement the security-verification core (best safety ROI).
- **Files likely touched:** `skills/{verify-identity-and-rbac,authorization-review-pass,protected-preview-access,client-code-anti-fraud-audit,react-aware-automation}/`; `checklists/{rbac-three-layer,destructive-action-safety}.md`; `templates/uat-smoke-report.md`; optional `route-access-prober` subagent. References env troubleshooting from claude-env-doctor.
- **Validation:** `403→400` RBAC proof on a fixture app; header injection is route-scoped (no CORS break); smoke report emits PASS/FAIL/BLOCKED with status codes + screenshots; disposable-data guard refuses live OTP/SMS-shaped routes.
- **Acceptance:** §6.2 P0/P1 artifacts demonstrated; no real secrets/hosts.
- **Risks:** accidentally targeting non-disposable data — bake the disposable-data + test-allowlist guard in first.

### Phase 4 — docs-wiki (plan + scaffold)
- **Objective.** Implement source-of-truth doctrine + integrity auditing.
- **Files likely touched:** `skills/{source-of-truth-doctrine,code-vs-wiki-discrepancy-report,wiki-link-namespace-validator,safe-doc-deletion}/`; `templates/{audit-report,sop-page,onboarding,role-guide}.md`; optional `doc-drift-auditor` subagent.
- **Validation:** discrepancy report flags a planted code-vs-doc contradiction; link validator catches a filename collision + a `.md`-suffixed internal link; safe-deletion refuses a tree with live cross-references.
- **Acceptance:** §6.3 P1 artifacts demonstrated; doctrine parameterized (no Aqraboon constants); **no Wiki→memory-sync code** (kept for Phase 6).
- **Risks:** scope bleed into memory-sync — hard boundary.

### Phase 5 — Cross-plugin QA & packaging review
- **Objective.** Prove the §7 single-owner contracts hold and nothing drifted.
- **Work:** confirm every plugin *references* (not restates) the shared `rules/` and claude-env-doctor; run `validate_plugin.py` across all plugins; genericness grep across the marketplace; verify all version bumps + CHANGELOG entries + marketplace registrations; confirm hook-wiring matches docs (the devops drift finding) for every plugin.
- **Validation/Acceptance:** 0 validator errors; 0 project-specific tokens (beyond doc/CHANGELOG false positives); no duplicated rule text across plugins; every shell script referenced in its `hooks.json`.
- **Risks:** late discovery of duplicated rules — cheaper to catch here than after release.

### Phase 6 — Evaluate future candidates
- **Objective.** Decide on `wiki-memory-sync` (now that docs-wiki is stable) and `data-migration-safety`.
- **Work:** prototype `wiki-memory-sync` using the detached-worktree branch-pinning mechanics (L490/L1109) and TR_plugins `memory-sync` prior art; scope `data-migration-safety` (cascade-to-money, db-push drift, phased cutover).
- **Acceptance:** go/no-go per plugin with a one-page scope; nothing built that violates the docs-wiki↔memory-sync boundary.
- **Risks:** building memory-sync before docs-wiki stabilizes — gated by Phase 4 completion.

---

## 12. Recommended next execution prompt

Paste the block below as the next message after reviewing this plan. It starts at Phase 0 (decisions) and Phase 1 (highest-impact, lowest-risk work), defers everything else, and bakes in the workspace's standing rules so implementation stays safe.

```text
Read plugins/LESSONS_TO_PLUGINS_GLOBAL_RECOMMENDATION_PLAN.md, then enter plan mode and propose Phase 0 + Phase 1 ONLY. Do not write plugin code yet — produce a step-by-step plan I can approve.

Phase 0 (decisions, no code): confirm these and surface anything that needs my call —
  1. Rename react-admin-kit-plugin -> react-kit (folder, .claude-plugin/plugin.json "name", plugins/.claude-plugin/marketplace.json entry, and any SKILL.md frontmatter "name:"); broaden scope to general React/Next patterns, admin panels as ONE capability.
  2. Approve two NEW plugins: claude-env-doctor (Windows/WSL/MCP/Claude-Code environment doctor, ~18 lessons) and agent-safety-guards (secrets-compromised, prompt-injection-verify, read-only-immutability, write-authority-split).
  3. Fold GitHub Actions hardening into devops-plugin as provider-neutral rules (no standalone gha plugin); promote devops-plugin/rules/write-gate.md to a provider-neutral remote-write contract.
  4. Confirm the Django/DB-safety lessons stay OUT of odoo-plugin (reserved for a later data-migration-safety plugin).

Phase 1 (high-impact hardening) plan to include —
  - devops-plugin: permission-first + gh-identity-auto-switch write hook; CI-review advisor (flag non-SHA-pinned third-party actions, YAML-only "approval" gates, weakened/renamed required checks); reconcile hooks.json wiring vs README (add a test that every hooks/ script is referenced).
  - odoo-plugin: a PreToolUse Bash guard blocking `docker compose down -v` / `docker volume rm` on Odoo stacks + a Postgres-major-version pin check; an i18n/PO gettext reference (typed refs, msgmerge salvage, source-string-invalidation audit, UTF-8 decode rule).
  - rag-plugin: add an "MCP not loading" branch to /rag doctor (claude mcp list -> read .mcp.json -> run spawn cmd) WITHOUT duplicating references/mcp-wiring.md.
  - NEW claude-env-doctor: /env-doctor command + doctor skill with per-symptom branches (MCP-not-loading, WSL-unreachable, login-401, LSP-missing, encoding-crash) + a DNS-vs-TCP isolation reference + a probe-tier SessionStart advisory; make rag/odoo/paper/qa-browser REFERENCE it, not copy.
  - NEW agent-safety-guards: rules/ + hooks/ for the four safety primitives above.
  - shared rules/: remote-write-gate.md, findings-are-hypotheses.md, confirmation-gate.md (single-owner; other plugins reference).

Constraints (non-negotiable):
  - Keep everything GENERIC and reusable. No project-specific business logic, names, paths, secrets, hosts, or tokens (no Aqraboon/Royal-Preps/Almajal/KhairGate/OpenClaw specifics). Prove it with a genericness grep before finishing.
  - On every plugin change: bump .claude-plugin/plugin.json version + add a CHANGELOG.md entry; register any new plugin in plugins/.claude-plugin/marketplace.json (registered name omits the -plugin suffix).
  - Command filenames carry NO plugin-name prefix; SKILL.md uses the canonical "Use when..." voice.
  - Run python validate_plugin.py <plugin> to 0 errors for each touched plugin (the 2 hooks.json "unknown top-level key" warnings are the known benign quirk).
  - Single-owner layering: never restate a rule that lives in another layer/plugin — reference it.
  - Do NOT push or open PRs without my explicit go. When approved, direct-to-main is fine for this marketplace.

Deliver the plan as a checkable task list (tasks/todo.md) grouped by plugin, with per-item acceptance criteria and the fixtures you'll use to prove each hook/skill works. Wait for my approval before implementing.
```

---

*End of plan. Sections 2, 3, 4, 9, and 10 are generated directly from the 21-agent analysis (10 inventory + 11 mapping agents over the full LESSONS.md); sections 1 and 5–8 and 11–12 are authored from that data plus a complete read of the 2,040-line lessons file. No plugin files were created or modified in producing this report.*
