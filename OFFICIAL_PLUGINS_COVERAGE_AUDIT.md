# Official Plugins Coverage Audit

> **Investigation + recommendation only.** No plugin was built, edited, or deleted. The official marketplace was updated with a safe fast-forward pull only. The single file written is this report.
>
> **Question answered:** *Are we about to build something the official Claude plugins already cover well?*
> **Short answer:** For **5 of 6** planned items — **no**, official plugins do not fully cover them (they cover adjacent slices). For **plugin-authoring** and **static/diff security review**, **yes** — official `plugin-dev` and `security-guidance` are production-grade and we should adopt them instead of building. The biggest course-correction vs. the prior plan: the **GitHub-side DevOps work and the plugin-authoring "future plugins" should be dropped in favor of official plugins**, and several future ideas shrink to thin layers on top of official tooling.
>
> **Inputs:** official marketplace at `C:\MY-WorkSpace\claude_plugins\claude-plugins-official` (204 marketplace entries; 19 relevant first-party/external plugins deep-inspected; 39 capability-relevant entries surfaced by a full-marketplace scan); local plugins at `C:\MY-WorkSpace\claude_plugins\plugins`; and the prior `LESSONS_TO_PLUGINS_GLOBAL_RECOMMENDATION_PLAN.md`.
> **Method:** safe git update, then a 20-agent read-only analysis workflow (1 marketplace scanner + 19 plugin inspectors), each scoring official→our-capability overlap as yes / partial / no with cited skills/commands/agents. The official inventory (§3) and the remote-entry table (§12) are script-generated from that data; decisions (§1, §5–§14) are authored.

---

## 1. Executive summary

- **Official repo update:** clean → fast-forward pull succeeded, `45896c8` → `3d368d2` (20+ commits). No dirty files; used a per-command `safe.directory` override (the repo is owned by `BUILTIN/Administrators`) rather than editing global git config.
- **Official plugins inspected:** 19 deep (16 first-party + 3 thin external MCP-pointer manifests); 39 of 204 marketplace entries flagged capability-relevant.
- **Local/custom plugins inspected:** 10 (carried from the prior audit + re-confirmed structurally).

**Capabilities already covered well by official plugins (adopt, don't build):**
- **plugin-authoring** → `plugin-dev` (7 skills: structure, command, agent, skill, hook, MCP, settings) is production-grade; `skill-creator`, `mcp-server-dev`, `hookify` cover the rest. *All our plugin-authoring "future" ideas are redundant.*
- **static + diff security review / secrets / injection** → `security-guidance` v2.0.0 (edit-time pattern warnings, Stop-time LLM diff review, agentic commit reviewer, 25+ vuln classes incl. hardcoded secrets) is a professional superset of most of our security-review idea.

**Capabilities only PARTIALLY covered (keep/build a thin layer on top of official):**
- **qa-browser** → `playwright` (+ remote `chrome-devtools-mcp`) supply the *browser engine and evidence capture* but **none** of the methodology (role-based smoke, RBAC status-code proof, UAT PASS/FAIL/BLOCKED, disposable-data safety, production-URL gates). Keep qa-browser as the methodology layer; depend on official MCP for transport.
- **react-kit** → `frontend-design` covers *visual/aesthetic* creation; `code-simplifier`/`pr-review-toolkit`/`typescript-lsp` touch code quality. **None** cover React lint/finding-*triage discipline*, React-19 migration, data-fetching error/empty/access states, or admin/CRUD/role-aware patterns. Keep react-kit, scope it complementary to frontend-design.
- **devops-enh (GitHub side)** → `code-review`, `pr-review-toolkit`, `commit-commands`, `github`, `gitlab`, `security-guidance` collectively cover PR review, commit/push/PR creation, the GitHub API surface, and CI-security review. **Adopt these; do not build GitHub features into the Azure-only `devops-plugin`.** Only Azure-specific work + identity-auto-switch + opinionated CI-hardening *rules* remain local.

**Capabilities NOT covered (build remains justified):**
- **claude-env-doctor** → nothing *diagnoses/repairs* the Windows/WSL/MCP/login/LSP environment. `claude-code-setup` is the *inverse* (it sets up, doesn't doctor); `session-report` only reads transcripts. **Strongly justified — build it.**
- **docs-wiki** → no official plugin authors a project Wiki / SOP pages / code-vs-wiki discrepancy reports (`gitlab` exposes a wiki MCP surface; `code-modernization` emits eng docs; remote `notion`/`atlassian`/`mintlify` are doc *surfaces*, not authoring/auditing methodology). **Keep.**
- **wiki-memory-sync** → `claude-md-management` generates AI project-memory and captures *session* learnings, and remote `remember` derives memory from *chat* — but **none** derive memory from a *Wiki* or separate business vs SOP/rule knowledge. **Defer, and align its memory format with `claude-md-management`** rather than reinventing.

**Local plugins worth keeping (tailored, low official overlap):** `qa-browser-plugin`, `react-admin-kit-plugin`(→react-kit), `docs-wiki-plugin`, `rag-plugin`, `odoo-plugin`. **Enhance rather than replace:** `devops-plugin` (lean on official GitHub plugins; keep Azure core), `ntfy-plugin` (no official equiv). **Possible duplication to watch:** none are outright replaced by an official plugin today; the risk is *building new overlap* (GitHub DevOps features, plugin-authoring helpers, a generic security reviewer).

**New plugins still recommended:** **claude-env-doctor** (only one that is both uncovered and high-value). **No longer recommended as standalone:** the plugin-authoring meta-plugins, a generic secrets/security plugin (use `security-guidance` + `hookify`), and the GitHub-hardening plugin (fold into devops or use `code-review`).

### Top 10 final decisions

| # | Item | Decision |
|---|---|---|
| 1 | **plugin-authoring future plugins** (plan-verifier, plugin-authoring-guide, skill-library-architect, agent-mcp-wrapper) | **DROP — use official** `plugin-dev` + `skill-creator` + `mcp-server-dev` + `hookify` |
| 2 | **claude-env-doctor** | **BUILD NEW** — genuinely uncovered; highest-value new plugin |
| 3 | **qa-browser** | **KEEP / ENHANCE** as a methodology layer; depend on official `playwright` MCP for transport (don't build automation) |
| 4 | **react-kit** (rename of react-admin-kit) | **KEEP / ENHANCE**; scope complementary to `frontend-design` (triage + React-19 + states + admin/CRUD), not aesthetics |
| 5 | **devops GitHub-side enhancements** | **USE OFFICIAL** `code-review` + `commit-commands` + `github`; keep only Azure core + identity-switch + CI-hardening rules local |
| 6 | **security-review / secrets-hygiene future** | **ADOPT** `security-guidance` (+`hookify`); keep only the unique nuances (live RBAC proof in qa-browser; pasted-token-revoke + prompt-injection-verify + read-only-immutability as small rules) |
| 7 | **docs-wiki** | **KEEP / BUILD** — uncovered project-Wiki authoring + discrepancy auditing |
| 8 | **wiki-memory-sync** | **DEFER**; design to align with `claude-md-management`'s memory format; do not merge into docs-wiki |
| 9 | **odoo / rag / ntfy / pandoc / remotion / paper local plugins** | **KEEP as-is** — no official overlap; lesson-driven enhancements only where the prior plan found them |
| 10 | **First action** | Adopt official `plugin-dev`, `security-guidance`, `playwright`, `code-review`, `commit-commands` now; then build `claude-env-doctor`; then enhance qa-browser/react-kit/docs-wiki on top of official transport |

**Is any new plugin still truly needed?** Yes — exactly one clear case: **claude-env-doctor**. The three planned plugins (react-kit, qa-browser, docs-wiki) remain justified but as *thin, opinionated layers* that consume official plugins, not as from-scratch builds. Everything else is "adopt official" or "defer."

---

## 2. Official repository update result

| Field | Value |
|---|---|
| Official repo path | `C:\MY-WorkSpace\claude_plugins\claude-plugins-official` |
| Branch | `main` |
| Remote | `origin → https://github.com/anthropics/claude-plugins-official.git` |
| Before commit | `45896c8` — *Make Scan Plugins a viable required check; auto-dispatch on bump PRs (#1815)* |
| After commit | `3d368d2` — *Merge pull request #2105 … fix-2098-output-config-format* |
| Update status | **updated** (fast-forward; 20+ commits) |
| Dirty files | none (`git status --short` empty) |
| Notes | Repo is owned by `BUILTIN/Administrators`, so a per-command `git -c safe.directory=…` override was used for every git call (lesson L1643 — never edit global git config). No force, no reset, no stash. The pull added/updated several plugins incl. `security-guidance` hook scripts; this report reflects post-pull state. |

---

## 3. Official plugin inventory

Only first-party plugins under `plugins/` (and the thin MCP-pointer manifests under `external_plugins/`) are deep-inspectable; remote/third-party marketplace entries are covered from their manifest description in §12. 19 relevant official plugins were inspected.

### frontend-design — vunversioned  `[useful-but-incomplete]`

**Purpose.** A single-skill plugin from Anthropic's official marketplace that guides Claude to generate distinctive, production-grade frontend UI/UX code (HTML/CSS/JS, React, Vue) with high design quality, steering away from generic "AI slop" aesthetics. It focuses entirely on the visual/aesthetic dimension: bold aesthetic direction, distinctive typography, cohesive color themes, high-impact motion/animations, unexpected spatial composition, and atmospheric backgrounds. The skill auto-triggers when a user asks to build web components, pages, or applications.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\frontend-design`

**Skills.** `frontend-design` — Drives creation of aesthetically distinctive, production-grade frontend interfaces. Prescribes a 'design thinking' pre-step (purpose/tone/constraints/differentiation), then aesthetic guidelines across typography, color/theme, motion, spatial composition, and backgrounds, with explicit anti-patterns (no Inter/Roboto/Arial, no purple-gradient-on-white cliches, no convergent choices). Pure prompt guidance — no scripts, templates, or reference files.

**Docs quality.** Minimal but clear: a 31-line README with concrete usage examples and a link to the external Frontend Aesthetics Cookbook, plus a well-written self-documenting SKILL.md; adequate for the plugin's tiny scope though there is no CHANGELOG or version metadata.

**Relevant capabilities.** react-kit

**Limitations.** Tiny plugin: exactly 4 files (plugin.json, LICENSE, README.md, one SKILL.md). No commands, agents, hooks, scripts, tests, templates, or reference material.; plugin.json has no 'version' field and there is no CHANGELOG, so version is unknown/unversioned.; Scope is strictly aesthetic/visual quality — typography, color, motion, layout, backgrounds. It contains zero guidance on application architecture, data flow, state management, CRUD/list/detail/form patterns, RBAC/role-aware UI, loading/error/empty states, accessibility, internationalization (RTL/LTR), linting, or framework-version migration.; Skill body (~42 lines) is prose-only guidance with no code examples, component conventions, or runnable assets; it relies on the linked external 'Frontend Aesthetics Cookbook' for depth.; Framework-agnostic by design — it does not encode Next.js, React-19, Tailwind, Radix, or any of our specific stack conventions.; Could subtly conflict with house style guides: it explicitly discourages 'system fonts' and Inter and pushes 'bold/maximalist' choices, which may clash with a constrained corporate/admin design system.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| react-kit | PARTIAL | Overlaps only on the aesthetic/visual-polish slice. The frontend-design skill covers typography, color theming (CSS variables), motion/micro-interactions, and layout composition f… |
| qa-browser | NO | No browser automation, Playwright, role-based smoke tests, RBAC/permission verification, or UAT reporting anywhere in the plugin. It only authors code; it does not test or validat… |
| docs-wiki | NO | No wiki authoring, SOP/role-guide generation, Mermaid diagrams, or docs-vs-code discrepancy tooling. The plugin produces UI code, not documentation. |
| wiki-memory-sync | NO | Unrelated. No wiki ingestion, memory extraction, or project-context-file generation. |
| claude-env-doctor | NO | Unrelated. No environment diagnosis/repair, MCP wiring, Windows/WSL, or Claude Code config concerns. |
| devops-enh | NO | Unrelated. No git/GitHub/GitLab, PR review, CI hardening, or identity-switch functionality. |
| plugin-authoring | NO | Unrelated. It is itself a minimal example of a single-skill plugin, but provides no guidance, validation, or tooling for building plugins/skills/hooks/MCP servers. |
| security-review | NO | Unrelated. No static/diff security review, RBAC/auth review, secrets hygiene, or prompt-injection defense. |

---

### code-review — v1.0.0  `[useful-but-incomplete]`

**Purpose.** Automated code review for an open GitHub pull request. A single /code-review command orchestrates a multi-agent pipeline (eligibility gate, CLAUDE.md gathering, PR summary, 5 parallel Sonnet reviewers covering CLAUDE.md adherence, shallow bug scan, git blame/history, prior-PR comments, and in-code comment compliance), then per-issue Haiku confidence scoring (0-100), filters below 80, and posts a single deduplicated gh PR comment with full-SHA line-anchored citations.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\code-review`

**Commands.** `/code-review` — Review an open GitHub PR via a Haiku/Sonnet multi-agent pipeline; gate eligibility (skip closed/draft/trivial/already-reviewed), gather CLAUDE.md guidance, summarize, run 5 parallel Sonnet reviewers, score each issue 0-100 for confidence, drop scores <80, re-check eligibility, and post one gh PR comment with full-SHA #L line links. No-arg by design (acts on current branch's PR).

**Scripts/tests/templates.** No scripts, no tests, no skills/agents/hooks directories. Only assets: .claude-plugin/plugin.json (manifest), commands/code-review.md (the entire logic, an inline agent-orchestration prompt), README.md, LICENSE. The PR-comment Markdown format and the 0-100 confidence rubric are embedded as inline templates inside commands/code-review.md (no separate template/data files).

**Docs quality.** README.md is thorough and user-friendly (usage, troubleshooting, config, scoring rubric) but is out of sync with the actual command (claims 4 review agents vs the 5 defined in commands/code-review.md) and overstates configurability.

**Relevant capabilities.** devops-enh; security-review

**Limitations.** Single command, zero skills/agents/hooks/scripts/tests; all behavior is one inline prompt in commands/code-review.md (no devops-plugin-style single-owner layering). Not declaratively configurable.; GitHub-only via gh CLI; no GitLab, no Azure DevOps, no local-diff-only review (the bundled /review and /code-review skills in this session's harness differ from this plugin).; allowed-tools restricts gh to issue/pr/search subcommands; it cannot push, create PRs, set branch protection, SHA-pin CI actions, or auto-switch GitHub identities.; Explicitly NOT a security tool: the prompt instructs agents to ignore 'general security issues' and lint/typecheck-catchable problems unless a CLAUDE.md calls them out. No secrets scanning, no auth/RBAC review, no prompt-injection defense, no diff-level taint analysis.; Doc/code drift: README says 4 review agents (#1 & #2 both CLAUDE.md, #3 bug, #4 history) while commands/code-review.md actually defines 5 agents (adds prior-PR-comment and in-code-comment reviewers); README also misspells unrelated to logic. plugin.json lacks a version field (1.0.0 only stated in README).; manifest.json has no version key, no commands/skills arrays, no keywords; relies entirely on directory auto-discovery.; No browser/UI testing, no docs/wiki authoring, no memory sync, no environment diagnosis, no React-specific knowledge, no plugin-authoring tooling.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| devops-enh | PARTIAL | Strong on the PR-review slice only: /code-review reads PR diff/blame/prior-PR comments via gh and posts a confidence-filtered review comment. But allowed-tools is read-only-ish (g… |
| security-review | NO | Despite being a 'review' tool, commands/code-review.md explicitly tells agents to treat 'general security issues' as false positives unless a CLAUDE.md mandates them, and to skip … |
| react-kit | NO | Language/framework-agnostic; no React/Next knowledge, no lint triage, no a11y, no component conventions. Any React-specific checking would only happen indirectly if a repo CLAUDE.… |
| qa-browser | NO | Static PR review only. No Playwright/browser-MCP, no route-access/RBAC proof via status codes, no UI walkthroughs, no UAT reports. The prompt even forbids running builds/tests. |
| docs-wiki | NO | No wiki/SOP/user-manual authoring or diagram generation. It consumes CLAUDE.md as review input but never writes documentation. |
| wiki-memory-sync | NO | No memory extraction or project-context file generation; reads CLAUDE.md guidance for compliance checks only, does not sync or synthesize memories. |
| claude-env-doctor | NO | No environment diagnosis/repair. Only runtime dependency is an installed/authenticated gh CLI, which it assumes rather than diagnoses. |
| plugin-authoring | NO | Not a plugin-building tool. It is itself a minimal example of a single-command plugin (manifest + one command md), so it can serve as a reference pattern, but it provides no autho… |

---

### pr-review-toolkit — vunversioned  `[production-ready]`

**Purpose.** A bundle of 6 specialized read-only review subagents plus one orchestrating slash command that perform multi-aspect pull-request / pre-commit code review: code-quality vs CLAUDE.md, code simplification, comment accuracy, test-coverage gaps, error-handling/silent-failure auditing, and type-design quality. Agents are advisory (report findings with confidence/severity scoring); only code-simplifier is described as applying changes.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\pr-review-toolkit`

**Commands.** `review-pr` — Orchestrates a comprehensive PR review by checking git diff/gh pr view, deciding which of the 6 agents apply (always code-reviewer; conditionally test/comment/error/type/simplify), launching them sequentially or in parallel via Task, then aggregating findings into Critical/Important/Suggestions/Strengths + an action plan. Runs with no args (defaults to 'all'); optional aspect args (comments|tests|errors|types|code|simplify|all) and 'parallel'.

**Agents.** `code-reviewer` — General code review against project guidelines (CLAUDE.md): style violations, bug detection (logic, null/undefined, race conditions, leaks, security, perf), duplication, missing error handling, a11y, test coverage. Scores issues 0-100, reports only >=80, groups Critical(90-100)/Important(80-89). Defaults to git diff scope. model: opus.; `code-simplifier` — Simplifies/refactors recently modified code while preserving exact functionality: reduces nesting/complexity, removes redundant abstractions, enforces project standards (ES modules, function keyword, explicit return types, React Props patterns, avoids nested ternaries). The only agent that actively modifies code. model: opus.; `comment-analyzer` — Audits code comments/docstrings for factual accuracy vs implementation, completeness, long-term value, and 'comment rot'; flags misleading/outdated comments and recommends removals. Advisory only (does not modify). model: inherit.; `pr-test-analyzer` — Reviews test coverage quality (behavioral, not line coverage): finds untested error paths, missing edge/negative cases, uncovered business-logic branches; rates each gap 1-10 and flags brittle implementation-coupled tests. model: inherit.; `silent-failure-hunter` — Audits error-handling code for silent failures: empty/broad catch blocks, unlogged errors, unjustified fallbacks, fallback-to-mock in prod, swallowed errors, retry-without-feedback. Rates CRITICAL/HIGH/MEDIUM and prescribes fixes. References project logging conventions (logError/Sentry error IDs). model: inherit.; `type-design-analyzer` — Evaluates type/data-model design quality on 4 axes rated 1-10 (encapsulation, invariant expression, invariant usefulness, invariant enforcement); flags anemic models, exposed mutable internals, doc-only invariants, missing constructor validation; favors making illegal states unrepresentable. model: inherit.

**Scripts/tests/templates.** None present. The plugin ships only: .claude-plugin/plugin.json, README.md, LICENSE (MIT), commands/review-pr.md, and 6 agents/*.md. No skills/, hooks/, scripts/, tests/, data/, or rules/ directories. No bundled scripts, test suites, or output templates (the report 'template' is inline markdown in review-pr.md).

**Docs quality.** Strong and self-contained: a thorough README (per-agent focus, triggers, usage patterns, recommended workflow, confidence-scoring summary, troubleshooting) plus a detailed command file, though the manifest lacks a version field and the README's 'Contributing' section references internal Anthropic paths.

**Relevant capabilities.** devops-enh (PR review aspect); security-review (general bug/security pass in code-reviewer); react-kit (React component conventions in code-simplifier; React lint/finding triage tangentially)

**Limitations.** No version field in plugin.json (manifest only has name/description/author) — our convention requires versioned plugin.json + CHANGELOG; this upstream plugin has neither.; No hooks: review is opt-in via the agent/command, never enforced as a gate. Nothing blocks commit/push on findings.; Agents are advisory-only except code-simplifier; they do not create PRs, post review comments to GitHub/GitLab, manage branches, or do identity auto-switch — review-pr only reads git diff / gh pr view.; No browser/runtime testing: zero Playwright/RBAC/route-access/UI-vs-API verification — all review is static against the diff.; No documentation/wiki authoring, no memory-sync, no environment diagnosis/repair, no plugin-authoring tooling.; Security coverage is incidental, not specialized: code-reviewer lists 'security vulnerabilities' as one bullet among many; there is no dedicated secrets-scanning, prompt-injection-defense, or auth/RBAC-review agent.; React relevance is shallow: code-simplifier mentions React Props/component patterns as examples of project standards, but there is no Next.js/admin-panel/CRUD/RTL/a11y/data-fetching/React-19 knowledge.; Examples in agent descriptions are hardcoded to an internal context ('Daisy', logForDebugging/logError/constants/errorIds.ts) — assumes a specific project's error-handling stack rather than being generic.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| react-kit | NO | Only code-simplifier name-drops React (explicit Props types, component patterns) as an example coding standard. No architecture, admin panels, dashboards, CRUD/list/detail/form, r… |
| qa-browser | NO | Entirely static, diff-based review. No Playwright/browser-MCP, no role-based smoke tests, no UI route-access or UI-vs-API permission checks, no 403-vs-400/409 RBAC proof, no conso… |
| docs-wiki | NO | comment-analyzer audits in-code comments/docstrings for accuracy and rot — that is the closest touchpoint, but it neither authors nor maintains a project Wiki, SOPs, role guides, … |
| wiki-memory-sync | NO | No wiki reading, no memory/context-file generation, no business-vs-SOP knowledge separation, no stale-memory detection. Nothing in the 6 agents or command relates to extracting or… |
| claude-env-doctor | NO | No environment diagnosis or repair whatsoever — no MCP wiring, ~/.claude.json/settings, Windows encoding, Playwright Chrome/Chromium, WSL DNS/VPN, npm-shim, 401 login loop, or LSP… |
| devops-enh | PARTIAL | Overlaps on the 'PR review' sub-area only: review-pr reads git status/diff and gh pr view, and the agents produce structured review findings. But it does NOT create/merge PRs, pos… |
| plugin-authoring | NO | This is a target of analysis, not a tool: it contains no plugin/skill/hook/MCP/agent-building guidance, no skill-library layering, no validation. It is itself a sample of the well… |
| security-review | PARTIAL | code-reviewer's bug-detection bullet includes 'security vulnerabilities', and silent-failure-hunter hardens error handling (a reliability/abuse-surface concern). But there is no d… |

---

### code-simplifier — v1.0.0  `[scaffold-sample]`

**Purpose.** A single-agent plugin that simplifies and refines recently-modified code for clarity, consistency, and maintainability while strictly preserving all functionality/behavior. The agent reads project coding standards from CLAUDE.md, prefers readable/explicit code over compact code (e.g., avoids nested ternaries), and operates autonomously/proactively after code is written. Opinionated toward JS/TS/React conventions.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\code-simplifier`

**Agents.** `code-simplifier` — Opus-tier subagent that refactors recently-touched code for elegance/readability without changing behavior. Applies CLAUDE.md coding standards (ES modules, function keyword over arrows, explicit return types, explicit React Props types, consistent naming), reduces nesting/redundancy, removes obvious comments, and explicitly avoids over-simplification (no nested ternaries, no dense one-liners). Scope limited to recently modified code unless told otherwise.

**Docs quality.** No README or CHANGELOG exists; documentation is limited to the one-line plugin.json description and the agent's own well-written system prompt, so end-user docs are essentially absent.

**Relevant capabilities.** Behavior-preserving code refactoring/simplification; Enforcing project coding standards from CLAUDE.md; JS/TS/React component convention cleanup; Readability/maintainability review of recently-modified code

**Limitations.** Extremely minimal: only a plugin.json manifest plus one agent .md file and a LICENSE; no README, CHANGELOG, skills, commands, hooks, scripts, tests, or templates.; No slash command or hook entry point — the agent is only invokable as a subagent, with no wiring to auto-trigger it (the prompt claims it operates 'autonomously and proactively' but nothing in the plugin enforces that).; Single-responsibility by design: it explicitly only changes HOW code reads, never WHAT it does — so it performs no bug-finding, no security analysis, no testing, no diagnostics, and no docs.; Coding-standard assumptions are hardcoded toward JS/TS/React (ES modules, function keyword, explicit return types, React Props) and a specific CLAUDE.md style; weak fit for Python/Django, Flutter, or non-JS stacks.; Uses the opus model for every invocation, which is expensive for routine cleanup work.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| react-kit | PARTIAL | The code-simplifier agent shares react-kit's 'elegance / component conventions' sub-area — it enforces React Props typing, naming consistency, ES-module import hygiene, and de-nes… |
| security-review | NO | Both review code, but code-simplifier's prime directive is 'never change what the code does' and it has zero security framing — no RBAC/auth review, no secrets hygiene, no diff-ba… |
| qa-browser | NO | No browser/Playwright/testing capability whatsoever; the agent does static refactoring only and never executes or validates the code. |
| docs-wiki | NO | No documentation authoring; it actively REMOVES comments that describe obvious code rather than producing docs/wiki pages. |
| wiki-memory-sync | NO | No wiki reading or memory-file generation; unrelated. |
| claude-env-doctor | NO | No environment diagnosis/repair, MCP wiring, or Windows/WSL/Claude-Code concerns; unrelated. |
| devops-enh | NO | No Git/GitHub/PR/CI/branch-protection or identity-switch functionality; it is purely a local code-quality subagent. |
| plugin-authoring | NO | It does not help build plugins/skills/hooks/MCP/agents; it is itself a minimal example of an agent-only plugin but offers no authoring tooling or validation. |

---

### code-modernization — vunversioned (no "version" field in .claude-plugin/plugin.json)  `[production-ready]`

**Purpose.** Structured workflow + specialist agents for modernizing legacy codebases (COBOL, legacy Java/C++, monolith web apps) into current stacks while preserving behavior. Enforces a sequence: assess -> map -> extract-rules -> brief -> reimagine|transform -> harden. Discovery commands emit artifacts under analysis/<system>/; build commands scaffold code under modernized/<system>/; harden produces a reviewed remediation patch without ever editing legacy/.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\code-modernization`

**Commands.** `modernize-assess` — Full discovery & inventory of a legacy system (languages, LOC, complexity, build system, integrations, debt, security posture, COCOMO effort). --portfolio sweeps a parent dir into a sequencing heat-map. Produces ASSESSMENT.md + ARCHITECTURE.mmd; spawns legacy-analyst x2 + security-auditor.; `modernize-map` — Dependency & topology mapping of the legacy system: call graph, data lineage, entry points, dead-end candidates, one traced critical-path flow. Writes re-runnable extraction script + topology.json/TOPOLOGY.html + call-graph/data-lineage/critical-path Mermaid diagrams.; `modernize-extract-rules` — Mines business rules (calculations, validations, eligibility, state transitions, policies) into Given/When/Then Rule Cards with file:line citations + confidence ratings. Spawns 3 business-rules-extractor agents in parallel. Produces BUSINESS_RULES.md + DATA_OBJECTS.md.; `modernize-brief` — Synthesizes discovery artifacts into a phased Modernization Brief (target architecture, strangler-fig phase plan, behavior contract, validation strategy, approval block). Stops if ASSESSMENT/TOPOLOGY/BUSINESS_RULES missing; enters plan mode as a human-in-the-loop gate.; `modernize-reimagine` — Greenfield rebuild from extracted intent: mines AI_NATIVE_SPEC.md, designs + adversarially reviews a target architecture, scaffolds services with executable acceptance tests under modernized/<system>-reimagined/, writes a CLAUDE.md handoff. Two HITL checkpoints; spawns business-rules-extractor, legacy-analyst x2, architecture-critic, scaffolding agents.; `modernize-transform` — Surgical single-module strangler-fig rewrite to a target stack. Plans (HITL), writes characterization tests via test-engineer, writes idiomatic target impl, proves equivalence by running tests, emits TRANSFORMATION_NOTES.md. Reviewed by architecture-critic.; `modernize-harden` — Security hardening pass on the legacy system: OWASP/CWE scan, dependency CVEs, secrets, injection. Produces SECURITY_FINDINGS.md (Critical/High/Medium/Low) + a security_remediation.patch reviewed by a second security-auditor pass. Never edits legacy/ — user applies the patch.

**Agents.** `legacy-analyst` — Deep-reads legacy code (COBOL/JCL/RPG/ASP/EJB2/Struts/servlets/Perl) for structural & behavioral understanding; cite-everything (file:line), distinguishes is vs appears-to-be. Tools: Read, Glob, Grep, Bash.; `business-rules-extractor` — Mines calculations/validations/eligibility/state-transitions/policies from procedural code into testable Given/When/Then specs with source citations; explicitly separates business rules from technology artifacts. Tools: Read, Glob, Grep, Bash.; `architecture-critic` — Adversarial principal-engineer reviewer of proposed target architectures and transformed code; flags microservices-for-the-resume, ceremonial error handling, one-impl abstractions, leaking legacy structure (JOBOL). Tools: Read, Glob, Grep, Bash.; `security-auditor` — Adversarial security reviewer — OWASP Top 10, CWE, dependency CVEs (npm audit/pip-audit), secrets, injection, access control (IDOR/ownership/ACLs), auth/session. Per-finding table: ID/CWE/severity/location/exploit/fix. Tools: Read, Glob, Grep, Bash.; `test-engineer` — Writes characterization/contract/equivalence tests pinning legacy behavior (legacy code is the oracle, literal in/out values, branch coverage) so a rewrite can be proven equivalent; flags assertion-free tests. Tools: Read, Write, Edit, Glob, Grep, Bash.

**Scripts/tests/templates.** No scripts/ or tests/ dirs and no bundled template files., Templates are inline in command markdown: each command defines the exact output-artifact structure (ASSESSMENT.md, ARCHITECTURE.mmd, topology.json/TOPOLOGY.html, BUSINESS_RULES.md, DATA_OBJECTS.md, MODERNIZATION_BRIEF.md, AI_NATIVE_SPEC.md, REIMAGINED_ARCHITECTURE.md, TRANSFORMATION_NOTES.md, SECURITY_FINDINGS.md, security_remediation.patch)., /modernize-map generates a re-runnable extraction script as an output artifact (not shipped in the plugin)., Optional external tooling referenced (graceful fallback): scc/cloc (LOC+complexity+COCOMO), lizard (cyclomatic complexity), find/wc fallback., README ships a recommended .claude/settings.json permission layout (deny Edit(legacy/**), scope Write to analysis/** and modernized/**).

**Docs quality.** Excellent — a thorough README with the full workflow rationale, per-command/per-agent descriptions, expected layout, optional-tooling notes, a recommended permission settings.json, and a typical-workflow walkthrough; the only gap is the missing version field in the manifest.

**Relevant capabilities.** Security debt scanning (OWASP/CWE/CVE/secrets/injection) with reviewed remediation patch; Access-control / RBAC review (IDOR, missing ownership checks, ACL/privilege escalation) inside security-auditor; Structured engineering-document generation (assessment, brief, business-rules, topology) with file:line citations; Mermaid diagram generation (call-graph, data-lineage, critical-path, architecture); Business-rule extraction and separation of domain logic from implementation; Adversarial architecture review and characterization/equivalence testing for safe rewrites; CLAUDE.md knowledge-handoff generation in reimagine (adjacent to AI memory/context files)

**Limitations.** No version field in plugin.json — cannot pin/track releases; relies on marketplace versioning.; No skills, no hooks, no scripts/tests — behavior lives entirely in command markdown + 5 agents; nothing enforced outside the model (the never-edit-legacy invariant is convention + a recommended user-supplied settings.json deny rule, not a hook).; Scoped to legacy modernization (COBOL/legacy Java/C++/monoliths). Not a general-purpose React/frontend, QA-browser, env-doctor, or wiki toolkit.; Security review is framed as scanning a legacy system (analysis/), not reviewing a PR diff or pending branch changes; no prompt-injection-defense coverage.; Assumes a specific workspace layout (legacy/<system>, analysis/, modernized/) — requires symlinking your code in; brittle if layout differs.; Diagrams/docs are emitted to analysis/ as standalone files, not into any project Wiki; no wiki link/namespace validation or code-vs-wiki discrepancy reporting.; Greenfield/transform scaffolding can target any stack via free-text vision/target-stack args but carries zero stack-specific scaffolding for React/Next or any framework.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| security-review | PARTIAL | Strong on static security: security-auditor agent + /modernize-harden cover OWASP Top 10, CWE, dependency CVEs (npm/pip-audit), secrets, injection, and RBAC/access-control (IDOR, … |
| react-kit | NO | Entirely legacy-modernization focused (COBOL, legacy Java/C++, monoliths). /modernize-reimagine and /modernize-transform can target a React/Next stack via a free-text target-stack… |
| qa-browser | NO | No browser automation, Playwright, or browser-MCP. test-engineer writes characterization/contract/equivalence tests (unit-level, legacy-as-oracle) to prove rewrite equivalence — n… |
| docs-wiki | PARTIAL | Generates structured engineering documents (ASSESSMENT.md, MODERNIZATION_BRIEF.md, BUSINESS_RULES.md, DATA_OBJECTS.md, TRANSFORMATION_NOTES.md) with file:line citations and Mermai… |
| wiki-memory-sync | PARTIAL | Conceptually adjacent: business-rules-extractor separates durable business knowledge from technology/implementation, and /modernize-reimagine writes a CLAUDE.md knowledge-handoff … |
| claude-env-doctor | NO | No environment diagnosis/repair. It only references external code-analysis tools (scc/cloc/lizard) with graceful fallback and recommends a project settings.json permission layout … |
| devops-enh | NO | Uses only read-only git (git diff/log/status in the recommended allowlist) and suggests a .claude/settings.json permission layout. No PR review/creation, commit/push workflow, CI … |
| plugin-authoring | NO | This is a consumer plugin (commands + agents only), not a plugin/skill/hook/MCP authoring toolkit. It is itself a useful reference example of the thin-command -> specialist-agent … |

---

### security-guidance — v2.0.0  `[production-ready]`

**Purpose.** A hooks-only security-review plugin (by David Dworken @ Anthropic) that reviews Claude-generated code in three layers: (1) instant regex pattern warnings on Edit/Write/MultiEdit/NotebookEdit for ~25 known-dangerous patterns, (2) an LLM-powered git-diff review on Stop that feeds high-severity findings back to Claude before the user sees the turn, and (3) an agentic SDK-driven commit/push reviewer (git commit / git push / Graphite gt) that reads related files via Read/Grep/Glob to trace cross-file data flow. Covers injection, XSS, SSRF, hardcoded secrets, IDOR, auth bypass, unsafe deserialization, path traversal, and 25+ other vulnerability classes.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\security-guidance`

**Hooks.** `SessionStart` — Runs ensure_agent_sdk.py to verify/bootstrap the Agent SDK dependency needed for the layer-3 agentic commit reviewer (180s timeout).; `UserPromptSubmit` — Runs security_reminder_hook.py to capture a git baseline SHA (via git stash create) so the Stop-hook diff review only sees changes Claude made this turn.; `PostToolUse (matcher: Edit|Write|MultiEdit|NotebookEdit)` — Layer 1 — fast regex pattern warnings injected as additionalContext on every file edit; no LLM call.; `PostToolUse (matcher: Bash, conditional)` — Layer 3 — agentic commit/push security review gated on git commit / git push / gt create|modify|submit, using asyncRewake to feed findings back to Claude in the background after the commit.; `Stop` — Layer 2 — LLM diff review (default Opus 4.7) of the session diff vs baseline; two-stage investigate-then-self-refute pipeline, asyncRewake re-prompts Claude to address or acknowledge findings.

**Scripts/tests/templates.** hooks/patterns.py — 25 regex/substring security pattern rules + RuleId enum + bitmask telemetry (the static-analysis source of truth), hooks/review_api.py — importable agentic-review surface: investigate system prompt, self-refute adversarial prompt, findings JSON schema, diff capping, diff-anchor tagging, severity filtering, finding rendering, hooks/extensibility.py — loads org-policy claude-security-guidance.md (user/project/local precedence) and custom security-patterns.{yaml,json}; ReDoS validation; prompt-injection-safe <project-security-guidance> wrapping, hooks/security_reminder_hook.py — main CC-hook entrypoint orchestrating all layers, hooks/llm.py, gitutil.py, diffstate.py, session_state.py, _base.py, ensure_agent_sdk.py — runtime engine (LLM calls, git baseline/diff, session state, debug logging, SDK bootstrap), hooks/sg-python.sh — Python-interpreter shim (python3/python/py -3), NO tests/ directory, NO commands/agents/skills/ directories, NO templates/ directory — claude-security-guidance.md org-policy file is the only template-like config pattern (documented in README, not shipped as a file)

**Docs quality.** Excellent — the README thoroughly documents all three layers, every env var toggle, model-id forms per provider, org-policy file precedence, a detailed privacy/data-handling section, limitations, and troubleshooting; in-code docstrings (security_reminder_hook.py, extensibility.py) further explain architecture, git-baseline mechanics, and the prompt-injection trust model.

**Relevant capabilities.** Static regex security scanning on every edit (25 rules: command injection, eval/new Function, XSS sinks innerHTML/outerHTML/insertAdjacentHTML/dangerouslySetInnerHTML/document.write, unsafe deserialization pickle/yaml/marshal/shelve/torch/joblib, XXE, weak crypto AES-ECB/createCipher, TLS verification disabled, subprocess shell=True, os.system, Go exec shell, GitHub Actions workflow injection, missing SRI); LLM diff review on Stop with two-stage investigate then adversarial self-refute pipeline, medium+ severity, diff-anchored to avoid flagging pre-existing code; Agentic cross-file commit/push review tracing data flow (entry points to sinks) for IDOR, auth bypass, cross-file SSRF, parser/validator differentials, fail-open state drift, over-broad grants, gate/action field mismatch; RBAC/authorization review: explicit sibling-path gate parity, gate/action field mismatch, over-broad grant detection, privilege-boundary reasoning (attacker vs victim) in the refute pass; Secrets hygiene: hardcoded-secret pattern warnings + sensitive-to-observability detection (credentials/PII reaching logs/traces/metrics); Prompt-injection defense: org-policy .md is wrapped in a provenance-tagged additive-only block that cannot suppress findings; custom regexes ReDoS-validated; explicit refute-pass rules that NEVER apply no-privilege-boundary to LLM-agent capability gates / hooks / bash allowlists; Org/project extensibility via claude-security-guidance.md and security-patterns.{yaml,json} with user/project/local precedence; CI/CD security: GitHub Actions workflow-injection pattern rule + agentic CI/CD-trust check (workflow_dispatch/pull_request_target without branch filter when secrets/write perms present), SRI on external scripts

**Limitations.** Hooks-only plugin — no slash commands, no agents, no skills, no on-demand /security-review entrypoint; it fires automatically on edit/stop/commit and cannot be invoked manually for an ad-hoc audit of arbitrary unchanged code.; Review scope is the session diff vs a git baseline (or commit/push diff) — it reviews only code Claude changed this turn, NOT whole-repo or pre-existing code; the diff-anchor logic explicitly down-weights off-diff findings.; Requires a working API path and outbound calls (api.anthropic.com or your gateway/Bedrock/Vertex) for layers 2 and 3; transmits diff hunks, changed file contents, and any files the agentic reviewer pulls in — a privacy/egress consideration the README flags.; Layer 3 (agentic commit review) does NOT read claude-security-guidance.md org policy; org rules only influence the Stop-hook LLM review (layer 2).; 8 KB combined org-policy prompt budget — project-local rules are truncated/dropped first; ~15 tool-call budget caps the agentic reviewer's exploration depth.; Best-effort assistive tool with no warranty; pattern rules are regex (multi-line calls false-positive/negative, e.g. torch.load and yaml.load across lines), and the LLM reviewer can miss findings and produce false positives.; Built-in pattern rules cannot be individually disabled (only the whole pattern layer); no per-rule kill switch in v1.; Python 3.8+ on PATH and Claude Code CLI >= 2.1.144 required.; No automated tests directory in this checkout; correctness is asserted via an import-time RuleId-sync assertion and (per docstrings) external eval coverage not present here.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| security-review | YES | This is a direct, professional-grade competitor/superset of our security-review capability. It does static (patterns.py, 25 rules) + diff (Stop-hook LLM, investigate+self-refute i… |
| devops-enh | PARTIAL | Touches the commit/push workflow: PostToolUse[Bash] hooks fire on git commit / git push / gt create\|modify\|submit and run an agentic review with asyncRewake feedback — overlaps … |
| react-kit | PARTIAL | Only the security slice of React/JS overlaps: dedicated JS/TS-gated rules for dangerouslySetInnerHTML, innerHTML/outerHTML/insertAdjacentHTML, document.write XSS, new Function/eva… |
| plugin-authoring | NO | Not a plugin-authoring tool. It is itself a well-structured example of a hooks-only plugin (clean hooks.json with asyncRewake/conditional Bash matchers, importable engine modules,… |
| qa-browser | NO | No browser, Playwright, or runtime testing whatsoever. It reviews source diffs statically/agentically. It reasons about RBAC at the code level (gate/action mismatch, privilege bou… |
| docs-wiki | NO | No wiki/docs authoring, SOP pages, diagrams, or code-vs-doc discrepancy reporting. Its only doc-adjacent artifact is the org-policy claude-security-guidance.md config file, which … |
| wiki-memory-sync | NO | No concept of reading a wiki, extracting memories, or generating AI-readable project context. The claude-security-guidance.md is a hand-authored policy file, not a synced/generate… |
| claude-env-doctor | NO | Not an environment diagnose/repair tool. It has a Python-interpreter shim (sg-python.sh) and a SessionStart ensure_agent_sdk.py bootstrap for its own dependency, plus a debug log … |

---

### claude-md-management — v1.0.0  `[production-ready]`

**Purpose.** Maintains and improves CLAUDE.md project-memory files. Two complementary tools: a skill that audits existing CLAUDE.md files against a 6-criterion quality rubric (commands, architecture, gotchas, conciseness, currency, actionability), scores them A-F, and proposes targeted diffs after a quality report; and a command that reflects on the current session to capture newly-discovered commands/patterns/gotchas into CLAUDE.md (or .claude.local.md). Both are approval-gated before writing.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\claude-md-management`

**Skills.** `claude-md-improver` — Discover all CLAUDE.md / .claude.local.md files, score each against a weighted quality rubric, emit a per-file quality report, then propose and (on approval) apply targeted improvements. Backed by three reference files: quality-criteria.md (scoring rubric + red flags), templates.md (per-project-type CLAUDE.md templates), update-guidelines.md (what to add vs not add, diff format).

**Commands.** `revise-claude-md` — End-of-session command (allowed-tools: Read, Edit, Glob) that reflects on the session for missing context — commands used, code-style patterns, testing approaches, env quirks, gotchas — locates CLAUDE.md files, drafts concise one-line-per-concept additions, shows diffs, and applies only with user approval.

**Scripts/tests/templates.** skills/claude-md-improver/references/quality-criteria.md — 6-criterion scoring rubric (20/20/15/15/15/15) plus red-flags list, skills/claude-md-improver/references/templates.md — section catalog + minimal/comprehensive/package/monorepo CLAUDE.md templates, skills/claude-md-improver/references/update-guidelines.md — what-to-add vs what-not-to-add catalog with diff format and validation checklist, claude-md-improver-example.png, revise-claude-md-example.png — README screenshots, No scripts, no tests directory

**Docs quality.** Concise and clear: a short README with a comparison table distinguishing the skill (codebase-alignment) from the command (session-capture), plus three well-structured reference docs and example screenshots — adequate for a small two-tool plugin.

**Relevant capabilities.** CLAUDE.md / AI project-memory file authoring and maintenance; Quality rubric + scoring for project context docs; Session-learning capture into project memory; Approval-gated, diff-based safe doc updates; Per-project-type doc templates (root, package, monorepo)

**Limitations.** Self-contained plugin (not a remote pointer) — full inventory possible; maturity is clear.; Scope is narrowly CLAUDE.md files only — no project Wiki, no business docs, no role/user manuals, no Mermaid diagrams.; No agents and no hooks — purely a skill + a command; no automation/enforcement layer.; No scripts and no tests; the discovery step uses a raw `find` shell command (POSIX-only, may misbehave on Windows PowerShell without the Bash tool).; Source of truth for the command is the live chat session, not any external doc/wiki — it cannot reconcile against a Wiki or codebase scan the way our wiki-memory-sync intends.; Audit currency check is heuristic/manual ('run documented commands mentally or actually') — no programmatic code-vs-doc discrepancy detection.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| wiki-memory-sync | PARTIAL | Closest overlap: CLAUDE.md IS an AI-readable project-memory/context file, and the claude-md-improver skill + revise-claude-md command both generate/update such memory and flag sta… |
| docs-wiki | NO | Only touches CLAUDE.md files. No wiki page authoring, no SOP/business/role/user-manual pages, no Mermaid diagrams, no wiki link/namespace validation. templates.md offers CLAUDE.md… |
| plugin-authoring | NO | Itself an example of a clean two-component plugin (skill + command, approval-gated writes, references/ layering) so it is a useful reference pattern, but it provides no skill/hook… |
| react-kit | NO | No React/Next content whatsoever. CLAUDE.md templates are stack-agnostic; the only intersection is that a documented CLAUDE.md could describe React conventions, which is incidenta… |
| security-review | NO | No security, RBAC/auth, secrets, or prompt-injection content. The update-guidelines.md JWT example is illustrative documentation, not a security review. |
| devops-enh | NO | No GitHub/GitLab, PR/commit/push, CI, branch-protection, or identity-switch logic. The command merely documents discovered commands into CLAUDE.md; it performs no VCS or CI operat… |
| qa-browser | NO | No browser/Playwright/MCP testing, no RBAC route-access checks, no PASS/FAIL UAT reports. Entirely unrelated domain. |
| claude-env-doctor | NO | No environment diagnosis/repair (MCP wiring, ~/.claude.json, Python encoding, WSL/Playwright/Node issues). It edits a project doc file; it does not inspect or fix the Claude Code … |

---

### claude-code-setup — v1.0.0  `[useful-but-incomplete]`

**Purpose.** A single-skill, strictly read-only advisory plugin from Anthropic. It scans a codebase (package.json, configs, dir structure, deps) to detect language/framework/tooling signals, then recommends the top 1-2 Claude Code automations per category: MCP servers, skills, hooks, subagents, plugins, and slash commands. It outputs a formatted recommendations report with rationale and where-to-place guidance, but never creates or modifies any files — the user (or a separate Claude session) implements the suggestions.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\claude-code-setup`

**Skills.** `claude-automation-recommender` — Read-only codebase analyzer that detects project signals and recommends tailored Claude Code automations (hooks, skills, MCP servers, subagents, plugins, slash commands), 1-2 per category, as a formatted report. Tools restricted to Read/Glob/Grep/Bash. Backed by four reference catalogs (mcp-servers, skills-reference, hooks-patterns, subagent-templates) and encourages web search to extend beyond the bundled lists.

**Scripts/tests/templates.** No scripts, no tests, no runnable templates., references/mcp-servers.md — catalog of ~25 MCP servers (context7, Playwright, Supabase, Convex, Postgres, GitHub, Linear, AWS, Cloudflare, Sentry, Docker, etc.) with detection signals., references/skills-reference.md — official-plugin skill list plus 8 copy-paste custom-skill examples (api-doc, create-migration, gen-test, new-component, pr-check, release-notes, project-conventions, setup-dev) with inline YAML/template/script snippets., references/hooks-patterns.md — PostToolUse format/lint/type-check/test hooks, PreToolUse protection hooks (.env, lock files), and Notification hook matchers with one JSON example., references/subagent-templates.md — 8 subagent archetypes (code-reviewer, security-reviewer, test-writer, api-documenter, performance-analyzer, ui-reviewer, dependency-updater, migration-helper) with model/tool guidance., automation-recommender-example.png — screenshot for the README; LICENSE; README.md.

**Docs quality.** Good for its narrow scope: a clear README, a well-structured SKILL.md with detection tables and a report template, and four substantive reference catalogs — but it is purely advisory documentation, with no executable code, validation, or tests.

**Relevant capabilities.** Meta-tooling: recommends WHICH Claude Code automations (hooks, skills, agents, MCP, slash commands, plugins) to add for a given codebase; Codebase signal detection (framework/ORM/DB/CI/test/issue-tracker) mapped to tool recommendations; Catalog of MCP servers, hooks patterns, and subagent archetypes useful as a reference when designing our own plugins; Recommendation-only posture (no file mutation) — an onboarding/'how to set up Claude Code' advisor

**Limitations.** Single skill, zero commands/agents/hooks/scripts/tests — it is an advisor, not an implementer. It never builds, validates, or runs anything.; No marketplace.json in this directory (it is the upstream anthropics repo, registered elsewhere); version pinned at 1.0.0 with no CHANGELOG.; All 'coverage' is advice about a domain, not execution of it: e.g. it recommends a security-reviewer subagent but performs no security review; recommends Playwright MCP but runs no browser QA; recommends frontend-design but writes no React.; Reference lists are static snapshots (it explicitly tells Claude to web-search for anything newer), so they will drift.; Detection is shallow (file-existence and dep-name grep) — no deep architecture, RBAC, or behavior analysis.; Bundled examples are macOS-flavored (afplay/osascript) and POSIX bash; no Windows/PowerShell guidance, unlike our Windows/WSL-focused work.; Directory present and fully readable — maturity is not 'unclear'; it is genuinely complete for its advisory scope but does no domain work.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| react-kit | NO | The skill only RECOMMENDS the frontend-design plugin / a ui-reviewer subagent / Playwright MCP when it detects React/Vue/Angular (skills-reference.md, subagent-templates.md ui-rev… |
| qa-browser | NO | mcp-servers.md recommends Playwright/Puppeteer MCP for UI testing and a ui-reviewer subagent, but the plugin performs no browser QA itself: no role-based smoke tests, no UI-vs-API… |
| docs-wiki | NO | Touches documentation only tangentially — recommends an api-documenter subagent / api-doc skill (OpenAPI) and Notion MCP. No project Wiki authoring, SOP/role-guide pages, Mermaid … |
| wiki-memory-sync | NO | Mentions Memory MCP (cross-session memory) and a project-conventions Claude-only skill as recommendations, but does nothing to read a Wiki, extract business vs SOP memories, gener… |
| claude-env-doctor | PARTIAL | Adjacent and the closest real overlap. It is the inverse of diagnosis: it sets UP a Claude Code project (recommend MCP servers, hooks, .claude/settings.json, --mcp-debug tip, perm… |
| devops-enh | NO | Recommends GitHub/GitLab/Linear MCP, a commit-commands plugin, a code-reviewer subagent, and headless `claude -p` in CI — but executes no GitHub/GitLab work, no PR review/creation… |
| plugin-authoring | PARTIAL | Real adjacency. The whole skill is meta-tooling: it recommends plugin-dev skills and shows copy-paste YAML for skills, hook JSON, and subagent frontmatter (model/tools). That help… |
| security-review | PARTIAL | subagent-templates.md defines a security-reviewer archetype (OWASP, auth/payment/PII detection signals, read-only tools) and hooks-patterns.md adds block-.env/secrets PreToolUse h… |

---

### session-report — vunversioned (no plugin.json; marketplace.json entry carries no version field — Anthropic-authored, source ./plugins/session-report)  `[useful-but-incomplete]`

**Purpose.** Generates a self-contained, explorable HTML report of Claude Code session usage from local ~/.claude/projects JSONL transcripts. Surfaces token usage (uncached/cache-create/cache-read), cache efficiency, wall-clock vs active hours, subagent activity by type, skill/slash-command invocations, cache breaks (>100k uncached input on a single call), most expensive prompts, and a per-day timeline. The skill drives a bundled Node analyzer to emit JSON, then fills an HTML template with the data plus 3-5 anomaly findings and 1-4 optimization suggestions. This is a cost/usage observability tool for the Claude Code user's own session history, not a software-engineering capability.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\session-report`

**Skills.** `session-report` — Orchestrates the report: run analyze-sessions.mjs --json --since 7d, read the JSON, copy template.html to cwd, edit in the data blob + anomaly/optimization narrative, report the saved path. Default window last 7 days; supports 24h/30d/all.

**Scripts/tests/templates.** C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\session-report\skills\session-report\analyze-sessions.mjs (Node ESM analyzer, ~876 lines: streams ~/.claude/projects/**/*.jsonl, dedupes by uuid/requestId, classifies main vs subagent vs workflow transcripts, attributes tokens to prompts/skills/subagent types, detects cache breaks, builds by_day timeline; --json/--dir/--since/--top/--cache-break flags), C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\session-report\skills\session-report\template.html (569-line self-contained HTML report template with embedded JS/CSS; renders hero total, sortable tables, block-char bars, drill-downs from an embedded JSON blob), C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\session-report\LICENSE, No tests; no plugin.json; no README/CHANGELOG in the plugin dir

**Docs quality.** Docs are limited to the SKILL.md (clear, precise step-by-step with exact markup) plus a verbose self-documenting analyzer header explaining the empirically-discovered JSONL structure; there is no README or CHANGELOG, and the plugin ships no plugin.json manifest.

**Relevant capabilities.** Claude Code session/usage analytics from local transcripts; Token + cache-efficiency accounting (uncached/cache-create/cache-read, % cached); Subagent activity and per-type token attribution; Skill / slash-command invocation tallying with token attribution; Cache-break detection (>100k uncached input per call); Most-expensive-prompt ranking with surrounding context; Per-project and per-day usage timeline; HTML report generation with anomaly + optimization narrative

**Limitations.** No plugin.json manifest and no version field in the marketplace entry — versioning is undefined; relies on git SHA of the official repo.; No commands, no hooks, no agents — the entire plugin is a single skill plus two bundled assets.; No tests of any kind for the ~876-line analyzer despite its acknowledged reliance on empirically-reverse-engineered JSONL structure (header notes structure was 'discovered empirically'); brittle to Claude Code transcript format changes.; Scope is strictly the user's own ~/.claude/projects usage telemetry. It does NOT touch application source code, repositories, CI, browsers, wikis, or environments.; Output is a static local HTML file the user must open manually; the skill explicitly does not open or render it. No upload/sharing/no dashboard.; Privacy note: top_prompts embeds up to 240 chars of raw human prompt text into the HTML report — no redaction of any secrets/tokens that may appear in prompts.; Cross-platform path note: SKILL.md hardcodes node <skill-dir>/analyze-sessions.mjs > /tmp/session-report.json and uses cp/date +%Y%m%d — POSIX-shell assumptions that need adaptation on Windows/PowerShell (our workspace is Windows-first).

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| react-kit | NO | Nothing React/Next.js. The skill never reads application source; it only parses Claude Code session transcripts. No component, admin-panel, CRUD, RTL, lint, or migration concern i… |
| qa-browser | NO | No browser, Playwright, RBAC, route-access, or UAT functionality. 'session' here means Claude Code chat sessions (~/.claude/projects JSONL), not web app sessions; the only artifac… |
| docs-wiki | NO | It generates one HTML usage report into cwd, not project wiki/SOP/user-manual pages. No Mermaid, no link/namespace validation, no code-vs-wiki discrepancy reporting. The only doc-… |
| wiki-memory-sync | NO | Reads transcripts to summarize token/cost telemetry, not to extract business/SOP memories into AI-readable context files. Different source (usage JSONL vs wiki) and different outp… |
| claude-env-doctor | PARTIAL | Adjacent only: both operate on the local Claude Code install. It reads ~/.claude/projects and can flag usage anomalies (cache-hit <85%, runaway subagents/skills, a prompt >2% of t… |
| devops-enh | NO | No GitHub/GitLab, PR, commit/push, CI, branch-protection, or identity-switch behavior. The plugin is read-only against local transcripts and writes a single HTML file; it never in… |
| plugin-authoring | PARTIAL | It is itself a minimalist reference example of a single-skill plugin that bundles a Node script + HTML template and drives them from SKILL.md (good pattern for script+template ski… |
| security-review | NO | No static/diff review, RBAC/auth review, or prompt-injection defense. Worth flagging the opposite risk: it embeds up to 240 chars of raw prompt text per top prompt into an HTML fi… |

---

### plugin-dev — v0.1.0  `[production-ready]`

**Purpose.** Anthropic's official toolkit for developing Claude Code plugins. Provides seven progressive-disclosure skills (plugin structure, manifest, command/agent/skill/hook authoring, MCP integration, plugin settings), three specialized agents (agent-creator, plugin-validator, skill-reviewer), one guided end-to-end /create-plugin workflow command, and bundled validation/test utility scripts. It is the meta-tooling for building, validating, and publishing plugins to a marketplace.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\plugin-dev`

**Skills.** `plugin-structure` — Plugin directory layout, plugin.json manifest fields, component auto-discovery, ${CLAUDE_PLUGIN_ROOT} usage, naming conventions; minimal/standard/advanced example layouts plus component-patterns and manifest-reference docs.; `command-development` — Slash-command authoring: YAML frontmatter (description, argument-hint, allowed-tools), dynamic $ARGUMENTS, bash-for-context, AskUserQuestion interactive patterns, namespacing; 10 example commands and references for advanced/interactive workflows and testing. (v0.2.0); `agent-development` — Subagent authoring: frontmatter (name, description, model, color, tools), <example>-block triggering descriptions, system-prompt design patterns (analysis/generation/validation/orchestration), AI-assisted generation; includes validate-agent.sh.; `skill-development` — Skill authoring with progressive disclosure, strong trigger descriptions, imperative/third-person style, references/examples/scripts organization; based on skill-creator methodology adapted for plugins.; `hook-development` — Hook authoring across all events (PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart/End, UserPromptSubmit, PreCompact, Notification), prompt-based vs command hooks, JSON output schemas, security/input validation; ships validate-hook-schema.sh, test-hook.sh, hook-linter.sh and 3 example hook scripts.; `mcp-integration` — MCP server integration: .mcp.json vs plugin.json, stdio/SSE/HTTP/WebSocket server types, env-var expansion, OAuth/token auth, tool naming/usage; 3 example server configs.; `plugin-settings` — User-configurable plugins via .claude/plugin-name.local.md (YAML frontmatter + body), bash parsing techniques, flag-file temporarily-active hooks, gitignore/lifecycle; ships validate-settings.sh and parse-frontmatter.sh.

**Commands.** `create-plugin` — Guided 8-phase end-to-end plugin creation workflow (discovery, component planning, detailed design, structure creation, implementation, validation, testing, documentation). Loads the relevant skills via the Skill tool and delegates to agent-creator/plugin-validator/skill-reviewer; uses TodoWrite, AskUserQuestion, Task. Notably advises that commands/ is legacy and new user-invoked commands should be skills.

**Agents.** `agent-creator` — Generates new subagent definitions (identifier, whenToUse with examples, system prompt) from a description. model: sonnet, tools: Write/Read.; `plugin-validator` — Comprehensive plugin validation: manifest, structure, naming, components, security; can trigger proactively after plugin changes. model: inherit, tools: Read/Grep/Glob/Bash.; `skill-reviewer` — Reviews skill quality: description/triggering effectiveness, progressive disclosure, writing style. model: inherit, tools: Read/Grep/Glob (read-only).

**Scripts/tests/templates.** skills/agent-development/scripts/validate-agent.sh, skills/hook-development/scripts/validate-hook-schema.sh, skills/hook-development/scripts/test-hook.sh, skills/hook-development/scripts/hook-linter.sh, skills/hook-development/examples/validate-write.sh, skills/hook-development/examples/validate-bash.sh, skills/hook-development/examples/load-context.sh, skills/plugin-settings/scripts/validate-settings.sh, skills/plugin-settings/scripts/parse-frontmatter.sh, skills/plugin-settings/examples/read-settings-hook.sh, skills/mcp-integration/examples/{stdio,sse,http}-server.json (config templates), skills/plugin-structure/examples/{minimal,standard,advanced}-plugin.md (layout templates), No tests/ directory; the bundled .sh scripts are validators/linters, not a test suite. No plugin-level version in plugin.json (only README states 0.1.0).

**Docs quality.** Excellent: a 400-line README documenting every skill's triggers/resources/word-counts, a full 8-phase workflow command, and each skill carries references/ + examples/; the canonical Anthropic reference our own CLAUDE.md points to.

**Relevant capabilities.** plugin-authoring

**Limitations.** plugin.json manifest is minimal (name/description/author only) and omits a version field; the only version (0.1.0) appears in the README, so an installed copy reports no semver.; No hooks/ directory and no hooks.json — the plugin itself ships zero runtime hooks; it only teaches hook authoring and provides validation scripts.; Bundled utilities are bash-only (.sh). On this Windows-first workspace they need Git Bash/WSL; validate-agent.sh / validate-hook-schema.sh / hook-linter.sh will not run under PowerShell directly.; Scope is strictly plugin meta-development. Nothing here touches application code, React, browser QA, documentation/wiki, environment diagnosis, CI/DevOps, or security review beyond generic 'security-first' authoring advice (HTTPS, no hardcoded creds, input validation in hooks).; It is the upstream READ-ONLY reference our workspace already mirrors; our local plugins/validate_plugin.py and claude-plugin-builder skill are the productized equivalents, so overlap with plugin-authoring is intentional duplication, not a gap.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| plugin-authoring | YES | Directly and professionally covers it. Seven skills cover plugin structure/manifest, command, agent, skill, hook, MCP, and settings authoring; plugin-validator agent + validate-ag… |
| security-review | NO | Only generic authoring-time security hygiene (hook input validation in hook-development, HTTPS/WSS + env-var credentials in mcp-integration). No static/diff review, no RBAC/auth r… |
| devops-enh | NO | create-plugin Phase 8 mentions adding a marketplace.json entry and the README mentions forking/PR to the marketplace, but there is no GitHub/GitLab tooling, PR review/creation, co… |
| react-kit | NO | No React/Next content whatsoever; scope is plugin meta-development only. |
| qa-browser | NO | No browser automation, Playwright, or RBAC/status-code testing. 'Testing' here (Phase 7, test-hook.sh) means validating plugin components, not exercising a running app's UI. |
| docs-wiki | NO | Produces plugin README/skill docs as a byproduct (Phase 8) but has no project-wiki authoring, SOP/role pages, Mermaid diagrams, or code-vs-wiki discrepancy reporting. |
| wiki-memory-sync | NO | plugin-settings stores per-project plugin config in .local.md files, which is unrelated to extracting business/SOP memories from a project wiki into AI-readable context files. |
| claude-env-doctor | NO | Authoring guidance only (e.g. ${CLAUDE_PLUGIN_ROOT} portability, mcp-integration config). No diagnosis/repair of MCP wiring, ~/.claude.json, Windows Python encoding, Playwright Ch… |

---

### skill-creator — vunversioned (no version field in plugin.json or marketplace.json; only a git SHA pins the upstream clone)  `[production-ready]`

**Purpose.** Official Anthropic plugin that helps create, improve, and quantitatively benchmark Claude Code Skills. It guides the full lifecycle: capture intent -> draft SKILL.md -> author realistic eval prompts -> run with-skill vs baseline subagents -> grade assertions -> aggregate a benchmark (mean/stddev/delta) -> launch an HTML eval viewer for human review -> iterate -> optimize the skill's frontmatter description for triggering accuracy -> package a .skill file. It is a meta-tool for skill authoring, not a domain-feature plugin.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\skill-creator`

**Skills.** `skill-creator` — Single, large (33KB / ~485-line) SKILL.md orchestrating the entire skill draft/eval/iterate/optimize/package loop. Covers Claude Code, Claude.ai (no-subagent), and Cowork (no-display) execution modes. Backed by agents/, references/schemas.md, assets/eval_review.html, eval-viewer/, and a scripts/ Python package.

**Agents.** `grader.md (sub-agent spec, not a plugin agents/ entry)` — Instructions for a grader subagent: evaluate assertions against transcript+outputs, extract/verify implicit claims, critique weak assertions, emit grading.json with exact text/passed/evidence fields the viewer depends on.; `comparator.md (sub-agent spec)` — Blind A/B comparison of two skill-version outputs without revealing which is which; emits comparison.json with rubric scores and a winner.; `analyzer.md (sub-agent spec)` — Post-hoc analysis of why one skill version beat another and benchmark-pattern detection (non-discriminating assertions, high-variance/flaky evals, time/token tradeoffs); emits analysis.json.

**Scripts/tests/templates.** scripts/run_loop.py (full eval+improve description-optimization loop with 60/40 train/test split), scripts/run_eval.py (run a trigger eval set, 3x per query for reliable trigger rate), scripts/improve_description.py (propose better SKILL.md description from failures), scripts/aggregate_benchmark.py (build benchmark.json/benchmark.md with mean/stddev/delta), scripts/generate_report.py (HTML report of optimization iterations), scripts/package_skill.py (zip skill folder into .skill), scripts/quick_validate.py (structural validation), scripts/utils.py, scripts/__init__.py, eval-viewer/generate_review.py + viewer.html (browser/static review UI), assets/eval_review.html (interactive trigger-eval-set review/editor template with __EVAL_DATA_PLACEHOLDER__ etc.), references/schemas.md (full JSON schemas: evals.json, history.json, grading.json, metrics.json, timing.json, benchmark.json, comparison.json, analysis.json), No tests/ directory present; no automated test suite shipped

**Docs quality.** Excellent and unusually thorough: a long, well-reasoned SKILL.md with explicit per-environment branches (Claude Code / Claude.ai / Cowork), exact JSON schemas, and explanatory rationale, though it is heavy reading and assumes the reader is authoring skills rather than seeking a quick reference.

**Relevant capabilities.** Skill authoring lifecycle (intent capture, SKILL.md drafting, progressive-disclosure structure guidance); Skill triggering-description optimization via automated train/test eval loop (scripts/run_loop.py, improve_description.py, run_eval.py using claude -p); Quantitative skill benchmarking with with-skill vs baseline subagents, assertion grading, mean/stddev/delta aggregation (scripts/aggregate_benchmark.py); HTML eval review viewer for human qualitative + quantitative review (eval-viewer/generate_review.py, viewer.html, assets/eval_review.html); Skill packaging into distributable .skill archive (scripts/package_skill.py); Skill structural quick-validation (scripts/quick_validate.py)

**Limitations.** Ships NO version field anywhere (plugin.json and marketplace entry both omit version); only the upstream git clone SHA distinguishes revisions, which complicates change-tracking and the team's own 'bump version on every change' convention.; Zero commands and zero hooks: there is no /slash entry point and no event automation; the entire plugin is one always-on skill plus scripts, so invocation depends on description triggering or explicit user request.; Single monolithic ~485-line SKILL.md; despite advising '<500 lines ideal', it sits near that limit and is dense.; Scripts are POSIX/Unix-oriented (nohup ... > /dev/null 2>&1 &, /tmp/ paths, open command for browsers) and would need adaptation on the team's native Windows/PowerShell environment; the description optimizer requires the claude CLI (claude -p) and subagents.; The agents/*.md are sub-agent instruction prompts referenced by the skill, NOT discoverable Claude Code agents under a plugin agents/ directory, so they only work when the skill spawns them.; Strictly a meta/authoring tool: it has no React, browser-QA, wiki/docs, environment-diagnosis, DevOps/PR, or security-review capability and does not attempt them.; No standalone validator equivalent to our validate_plugin.py for full plugin (manifest/marketplace) shape; quick_validate.py only checks skill structure.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| plugin-authoring | PARTIAL | Strong overlap on the SKILL.md half of plugin authoring: the skill-creator skill professionally covers drafting skills, progressive-disclosure structure, description/triggering op… |
| qa-browser | NO | No browser/Playwright/RBAC/route-access testing. The only 'eval/test' machinery (run_eval.py, grader.md, eval-viewer) tests whether a SKILL triggers and produces good outputs, not… |
| react-kit | NO | No React/Next/frontend content whatsoever; it is framework-agnostic skill authoring. assets/eval_review.html and viewer.html are internal review tooling, not generated app UI. |
| docs-wiki | NO | Produces SKILL.md and eval/benchmark JSON, not project wiki pages, SOPs, role guides, or Mermaid diagrams. references/schemas.md is internal doc, not a wiki-authoring capability. … |
| wiki-memory-sync | NO | history.json tracks skill version progression, not project business/SOP memory extraction from a wiki. No memory-sync concept. |
| claude-env-doctor | NO | No environment diagnosis/repair. It assumes a working claude CLI, Python, and browser; in fact its Unix-isms (nohup, /tmp, open) are the kind of Windows-incompatibility our env-do… |
| devops-enh | NO | No GitHub/GitLab/PR/CI/branch-protection/identity-switch features. Packaging a .skill is local-only; no remote VCS interaction. |
| security-review | NO | Only a brief 'Principle of Lack of Surprise' paragraph telling authors not to write malware/exploit skills. No static/diff scanning, no RBAC/secrets/prompt-injection review. Menti… |

---

### mcp-server-dev — vunversioned (plugin.json declares no version; each skill frontmatter is 0.1.0)  `[useful-but-incomplete]`

**Purpose.** Official Anthropic plugin that guides a developer through designing and building MCP servers that integrate well with Claude. It interrogates the use case, recommends a deployment model (remote streamable-HTTP, MCPB-bundled local, or local stdio), picks a tool-design pattern (one-tool-per-action vs search+execute), covers auth (OAuth/CIMD/DCR), and adds interactive in-chat UI widgets (the Apps SDK). It is authoring/builder guidance for producing MCP servers, not a runtime tool that diagnoses or operates existing MCP wiring.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\mcp-server-dev`

**Skills.** `build-mcp-server` — Entry-point skill. Phase-based discovery (what it connects to, who uses it, action-surface size, UI need, upstream auth), then recommends a deployment model and tool-design pattern, picks a framework (TS SDK or FastMCP 3.x), scaffolds remote-HTTP/stdio inline, or hands off to build-mcp-app / build-mcpb. References: remote-http-scaffold, deploy-cloudflare-workers, tool-design, auth, resources-and-prompts, elicitation, server-capabilities, versions.; `build-mcp-app` — Adds interactive UI widgets (forms, pickers, tables, confirm dialogs, progress, charts) rendered inline in chat via MCP UI resources (ui:// + RESOURCE_MIME_TYPE) and the @modelcontextprotocol/ext-apps App class. Covers widget-vs-elicitation routing, iframe/CSP sandbox constraints, host theming, testing loops, and connector-directory submission. References: iframe-sandbox, widget-templates, apps-sdk-messages, payload-budgeting, abuse-protection, directory-checklist.; `build-mcpb` — Packages a local stdio MCP server with its runtime as an .mcpb bundle (manifest.json, server/, node_modules) so users install without Node/Python. Covers manifest schema, user_config (directory picker, keychain secrets), Node/Python build pipelines, mcpb pack/validate/sign, and stresses that MCPB has NO sandbox so path/spawn security is the author's job. References: manifest-schema, local-security.

**Scripts/tests/templates.** No scripts/ directory, no tests/, no hooks.json, no commands/, no agents/ — the plugin is skills-only., Inline code scaffolds embedded directly in SKILL.md bodies (TS-SDK remote HTTP server, contact-picker widget HTML + Express server, MCPB stdio server, manifest.json, headless JSON-RPC test.jsonl loop) serve as copy-paste templates but are not standalone template files., 16 reference markdown files (under each skill's references/) act as deep-dive docs/templates: build-mcp-server/references/{remote-http-scaffold,deploy-cloudflare-workers,tool-design,auth,resources-and-prompts,elicitation,server-capabilities,versions}.md; build-mcp-app/references/{iframe-sandbox,widget-templates,apps-sdk-messages,payload-budgeting,abuse-protection,directory-checklist}.md; build-mcpb/references/{manifest-schema,local-security}.md

**Docs quality.** Excellent and current: a tight README with a build-path table, three well-triggered skills with decision matrices and runnable scaffolds, and 16 focused reference files; only gap is the missing top-level plugin version.

**Relevant capabilities.** plugin-authoring; claude-env-doctor; security-review

**Limitations.** No top-level version in plugin.json (only per-skill frontmatter 0.1.0), so the marketplace updater cannot detect new versions of this plugin.; Skills-only: zero commands, hooks, agents, scripts, or tests. No automated validation, no programmatic scaffolder — everything is model-driven prose plus copy-paste snippets the developer must wire up by hand.; Strictly an authoring/builder aid for NEW MCP servers. It does NOT diagnose, repair, or operate existing MCP wiring (no equivalent of inspecting ~/.claude.json mcpServers, fixing a broken connector, or debugging an MCP that won't spawn).; Server-author-side only: security guidance (MCPB local-security path-traversal/spawn-allowlist, abuse-protection egress CIDRs, prompt-injection review-criteria) is about hardening a server you ship, not reviewing an arbitrary repo's diff/RBAC/secrets.; Several claims are version-sensitive (elicitation host support Claude Code >=2.1.76, ext-apps API, MCPB manifest v0.4) and depend on fetching external Anthropic docs (claude.com/docs/llms-full.txt) at runtime — stale if offline.; No coverage at all of React/Next UI work, browser/Playwright QA, project wikis, memory sync, or GitHub/GitLab PR/CI workflows — those capabilities are entirely out of scope.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| plugin-authoring | PARTIAL | Strong, complementary overlap on the MCP-server sub-domain only. build-mcp-server/build-mcp-app/build-mcpb teach how to BUILD an MCP server (deployment model, tool design, auth, w… |
| claude-env-doctor | NO | Adjacent topic (MCP), opposite direction. Our claude-env-doctor DIAGNOSES/REPAIRS MCP wiring (~/.claude.json, npm-shim/Node CLI spawn, settings). This plugin only shows how to aut… |
| security-review | PARTIAL | Covers server-author security hardening only: build-mcpb stresses MCPB has no sandbox (mandatory local-security.md — path traversal, spawn allowlist, least privilege), build-mcp-a… |
| devops-enh | NO | No GitHub/GitLab, PR review/creation, commit/push, CI hardening, identity switch, or branch protection. The only deploy mention is 'cloudflare workers, two commands' to publish a … |
| react-kit | NO | The only UI it produces is sandboxed iframe widget HTML/JS via the ext-apps App class (build-mcp-app) — deliberately vanilla, single-purpose, no React/Next, no admin panels/CRUD/f… |
| qa-browser | NO | Testing guidance is JSON-RPC/stdio loops, MCP Inspector, and a browser 'widget-preview' shim for iterating on widget HTML — author-side functional testing of one's own server, not… |
| docs-wiki | NO | It contains excellent docs but produces MCP servers, not project wikis/SOPs/role guides/Mermaid diagrams. The directory-checklist is about connector-directory submission, not wiki… |
| wiki-memory-sync | NO | Nothing about reading a wiki, extracting business/SOP memories, or generating AI-readable memory files. No overlap. |

---

### hookify — vunversioned (plugin.json has no version field; SKILL.md frontmatter version: 0.1.0)  `[production-ready]`

**Purpose.** Lets users create Claude Code hooks without editing hooks.json: they write lightweight markdown rule files (.claude/hookify.{name}.local.md) with YAML frontmatter defining a regex pattern, an event type (bash/file/stop/prompt/all), and an action (warn or block). Four generic Python hook executors (PreToolUse, PostToolUse, Stop, UserPromptSubmit) dynamically load and evaluate those rules on every matching event, showing a warning message or denying the operation. The /hookify command can also analyze the recent conversation to auto-suggest rules from behaviors the user corrected or got frustrated by.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\hookify`

**Skills.** `writing-rules (frontmatter name: writing-hookify-rules)` — Reference skill documenting hookify rule-file syntax: frontmatter fields (name/enabled/event/pattern/action), single-pattern vs multi-condition format, all six operators (regex_match/contains/equals/not_contains/starts_with/ends_with), field reference per event type, Python-regex tips, file naming/gitignore conventions, and create/refine/disable workflow. Loaded first by every command.

**Commands.** `hookify` — Primary command. With arguments: builds a rule from an explicit instruction. Without arguments: launches conversation analysis to find unwanted behaviors, presents findings via AskUserQuestion, then writes .claude/hookify.*.local.md rule files. Active immediately, no restart.; `configure` — Interactively enable/disable existing rules by toggling enabled: true/false in their frontmatter via AskUserQuestion + Edit.; `list` — Globs .claude/hookify.*.local.md and renders a table of all rules (name, enabled, event, pattern, file) plus per-rule previews.; `help` — Static documentation command explaining how the hook system, config files, events, patterns, and commands work.

**Agents.** `conversation-analyzer` — Read/Grep-only sub-agent (model: inherit) that scans recent user messages for correction requests, frustration signals, and repeated mistakes, then emits structured findings (category, tool, regex pattern, severity, suggested rule) that /hookify turns into rule files. Note: the command body actually dispatches a general-purpose Task with an inline prompt rather than this named agent.

**Hooks.** `PreToolUse` — Maps tool_name to event (Bash->bash, Edit/Write/MultiEdit->file), loads matching rules, evaluates them; can deny the tool call (permissionDecision: deny) for action: block, or emit a systemMessage for warnings. Fails open (always exit 0).; `PostToolUse` — Runs the same rule engine after a tool executes (post-hoc warnings/checks).; `Stop` — Evaluates stop-event rules (e.g. require-tests) against the session transcript/reason; can block stopping with decision: block when a completion condition is unmet.; `UserPromptSubmit` — Evaluates prompt-event rules against the submitted user_prompt text (e.g. surface a deploy checklist when a prompt contains a trigger phrase).

**Scripts/tests/templates.** core/rule_engine.py — rule evaluation engine (LRU-cached IGNORECASE regex, multi-condition AND matching, block>warn precedence, per-event blocking JSON formats; has an inline __main__ self-test but no formal test suite), core/config_loader.py — loads/parses .claude/hookify.*.local.md frontmatter into Rule/Condition objects (referenced by all hooks; not opened but its API is exercised throughout), core/__init__.py, hooks/__init__.py, matchers/__init__.py, utils/__init__.py — package markers (matchers/ and utils/ contain only __init__.py — placeholders/empty), examples/ — 4 ready-to-use template rules: dangerous-rm.local.md (block), console-log-warning.local.md (warn), sensitive-files-warning.local.md (multi-condition warn on .env/credentials/secrets), require-tests-stop.local.md (stop-event block), No tests/ directory; no CHANGELOG; .gitignore and MIT LICENSE present

**Docs quality.** Excellent and self-contained: an 8KB README plus a dedicated help command and a thorough writing-rules skill cover syntax, every event/field/operator, regex tips, troubleshooting, and 4 worked example rule files.

**Relevant capabilities.** User-configurable PreToolUse/PostToolUse/Stop/UserPromptSubmit hooks driven by markdown rule files; Regex-based guardrails against dangerous bash commands (rm -rf, chmod 777, dd, sudo); Warn/block on edits to sensitive files (.env, credentials, secrets) and hardcoded secrets in code (multi-condition file_path + new_text); Block-on-stop completion gates (e.g. require tests in transcript before finishing); Conversation analysis to auto-derive prevention rules from user corrections; Fail-open hook architecture (errors never block the user); LRU-cached regex compilation for performance; Skill-as-reference + thin-command + generic-hook layering pattern (matches our plugin-authoring conventions)

**Limitations.** No version field in plugin.json and no CHANGELOG, so Claude Code's plugin updater cannot detect new versions (conflicts with our versioning convention).; Hooks invoke 'python3' literally; on Windows that shim is often absent (it's typically 'python' or the py launcher), so the hooks may silently fail to run on our Windows environment — README only lists Python 3.7+, no Windows note.; matchers/ and utils/ directories contain only empty __init__.py — dead scaffolding, no matcher abstraction actually implemented.; The /hookify command dispatches a general-purpose Task with an inline prompt instead of the bundled conversation-analyzer agent, so the named agent definition is effectively unused by the command path.; Guardrails are purely regex/substring on tool input — no semantic/AST understanding, so easily bypassed (obfuscated commands, base64, alternate flags) and prone to false positives; it advises, it does not truly secure.; Stop-event 'require tests' relies on grepping the transcript text for 'npm test\|pytest\|cargo test' — fragile and language-specific.; Conversation-analysis quality is non-deterministic (LLM judgement); no rule-testing harness or validation beyond a manual python3 -c regex check.; Rules are per-project (.claude/) and meant to be gitignored; no built-in sharing/library/sync mechanism (listed only as a 'future enhancement').

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| security-review | PARTIAL | Provides preventive runtime guardrails (block dangerous bash, warn on .env/credentials/secrets edits via sensitive-files example + multi-condition API_KEY-in-TypeScript rule), whi… |
| react-kit | PARTIAL | Only touches React via generic 'warn on console.log / debugger' file-event rules (console-log-warning.local.md) and a hardcoded-credential-in-.tsx example. It is a lint-style nag … |
| plugin-authoring | PARTIAL | hookify is itself an exemplary hook-authoring plugin and a strong reference for the thin-command -> writing-rules skill -> generic-Python-hook -> data(.local.md) layering we follo… |
| devops-enh | NO | No GitHub/GitLab, PR, commit/push, CI-hardening, identity-switch, or branch-protection functionality. The only adjacency is a stop-event rule that nags to run tests before finishi… |
| qa-browser | NO | No browser/Playwright automation, no role-based smoke tests, no UI route/RBAC validation, no console/network/screenshot evidence. Entirely unrelated; hookify operates on tool-call… |
| docs-wiki | NO | hookify authors hook rule files, not project Wiki/SOP/user-manual docs. Its strong README/skill docs are about itself, not a docs-authoring capability. No overlap. |
| wiki-memory-sync | NO | No Wiki reading or AI-memory generation. The conversation-analyzer extracts behaviors to prevent (regex rules), not business/SOP memories — conceptually distant from memory sync. … |
| claude-env-doctor | NO | No environment diagnosis/repair (MCP wiring, ~/.claude.json, Python encoding, Playwright, WSL/DNS, login loops). Ironically hookify's own 'python3' dependency is the kind of Windo… |

---

### agent-sdk-dev — v1.0.0  `[useful-but-incomplete]`

**Purpose.** Scaffolds and verifies Claude Agent SDK applications (Python and TypeScript). One interactive command creates a new Agent SDK project (interview the user, fetch latest SDK docs/versions, write starter files, .env.example/.gitignore, run typecheck), then hands off to a language-specific verifier agent that audits SDK installation, usage patterns, type safety, env/security, and documentation against the official docs.claude.com Agent SDK reference.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\agent-sdk-dev`

**Commands.** `/new-sdk-app` — Interactive scaffolder for a new Claude Agent SDK app: asks language/name/agent-type/starting-point/tooling one question at a time, WebFetches official SDK docs, checks/installs latest @anthropic-ai/claude-agent-sdk (npm) or claude-agent-sdk (PyPI), writes starter code + tsconfig/package.json or requirements.txt + .env.example/.gitignore, runs tsc --noEmit / syntax check, then launches the matching verifier agent.

**Agents.** `agent-sdk-verifier-py` — Sonnet agent that verifies a Python Agent SDK app: claude-agent-sdk install/version, requirements.txt/pyproject, correct claude_agent_sdk imports and init patterns, streaming-vs-single mode, MCP/subagent/permissions config, .env hygiene (no hardcoded keys, .env in .gitignore), error handling, docs. WebFetches the official Python SDK docs to compare. Emits PASS / PASS WITH WARNINGS / FAIL report.; `agent-sdk-verifier-ts` — Sonnet agent that verifies a TypeScript Agent SDK app: @anthropic-ai/claude-agent-sdk install/version, package.json type:module + scripts, tsconfig module resolution/target, correct SDK imports/usage, runs npx tsc --noEmit for type safety, MCP/subagent/permissions config, .env hygiene, docs. WebFetches the official TS SDK docs. Emits PASS / PASS WITH WARNINGS / FAIL report.

**Scripts/tests/templates.** None present. The plugin ships no scripts/, no tests/, and no templates/ directory; starter files are generated inline by the LLM following the /new-sdk-app prompt rather than from bundled template assets. Only .claude-plugin/plugin.json, commands/new-sdk-app.md, agents/agent-sdk-verifier-py.md, agents/agent-sdk-verifier-ts.md, README.md, and LICENSE exist.

**Docs quality.** Strong: a 209-line README with feature breakdown, end-to-end workflow walkthrough, best practices, troubleshooting, and official-doc links, matched by detailed self-documenting prompts in the command and both agents.

**Relevant capabilities.** Scaffolding new Claude Agent SDK (programmatic agent) apps in Python or TypeScript; Verifying Agent SDK app correctness against official SDK docs (sonnet verifier agents); TypeScript type-checking and Node ESM/tsconfig validation for SDK projects; Env/API-key hygiene checks (.env.example present, .env gitignored, no hardcoded keys); MCP server integration / custom tools / permissions / subagents configuration within Agent SDK apps; Live doc-grounding via WebFetch/WebSearch against docs.claude.com and npm/PyPI for latest versions

**Limitations.** Entirely scoped to building/verifying Claude Agent SDK applications (programmatic SDK agents) -- it does NOT author Claude Code plugins, skills, hooks, commands, or marketplace entries, so it does not substitute for our plugin-authoring capability despite the superficially similar name.; No skills and no hooks: zero passive/automatic enforcement; everything is on-demand via one command + two agents.; No bundled scripts/tests/templates -- starter code is LLM-generated each run, so output quality depends on the model and live doc fetches; reproducibility/validation is not asset-backed.; plugin.json has no version field (version 1.0.0 only stated in README) and no marketplace.json was inspected here; manifest is minimal (name/description/author only).; Security review is shallow and SDK-specific: only .env/key-hardcoding and basic error handling -- no static/diff scanning, no RBAC/auth review, no prompt-injection defense.; No React/frontend, browser-QA/Playwright, wiki/docs-site authoring, memory-sync, env-doctor/WSL repair, or git/CI/PR (devops) functionality of any kind.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| plugin-authoring | NO | Name collision only. agent-sdk-dev builds runtime Claude Agent SDK apps (claude_agent_sdk / @anthropic-ai/claude-agent-sdk programs), not Claude Code plugins. /new-sdk-app scaffol… |
| security-review | PARTIAL | Both verifier agents check a narrow security slice: .env.example presence, .env in .gitignore, no hardcoded ANTHROPIC_API_KEY, and basic error handling around API calls. No static… |
| devops-enh | NO | No GitHub/GitLab, PR review/creation, commit/push, CI hardening, identity switch, or branch protection. /new-sdk-app only writes a .gitignore as part of scaffolding -- no git oper… |
| react-kit | NO | TypeScript support here is Node/ESM Agent SDK apps (tsc --noEmit, tsconfig module resolution), not React/Next. No components, admin panels, dashboards, CRUD/forms, role-aware UI, … |
| qa-browser | NO | No browser automation, Playwright/browser-MCP, role-based smoke tests, route-access/RBAC proof, or UAT reports. Verification is static file inspection plus tsc type-checking only. |
| docs-wiki | NO | Does not author project wikis/SOPs/user manuals or Mermaid workflow diagrams. The verifiers merely check that a README/setup instructions exist in the scaffolded app; the plugin's… |
| wiki-memory-sync | NO | No wiki-to-memory extraction, AI-readable project memory generation, or stale-memory detection. Out of scope. |
| claude-env-doctor | NO | No Windows/WSL/Claude-Code environment diagnosis or repair. It does verify SDK install/version and Node/Python runtime requirements for the scaffolded app, but that is project-con… |

---

### commit-commands — v1.0.0  `[scaffold-sample]`

**Purpose.** Streamlines the git workflow with three thin slash commands: generate a commit message from the current diff and commit (/commit), do commit+push+open-PR in one shot (/commit-push-pr), and prune stale local branches whose remote is [gone] including their worktrees (/clean_gone). Pure prompt-driven git automation, no execution layer beyond Bash.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\commit-commands`

**Commands.** `/commit` — Reads git status/diff/branch/recent-log via command-context injection, then drafts and creates a single commit matching repo style in one tool batch. allowed-tools limited to git add/status/commit.; `/commit-push-pr` — End-to-end: branch off main if needed, commit, push to origin, and open a PR via gh pr create -- all required in a single message. allowed-tools include git checkout/add/status/push/commit and gh pr create.; `/clean_gone` — Lists branches, finds [gone] remote-deleted branches, removes any associated worktrees, then force-deletes the stale local branches via an inline bash pipeline (grep/sed/awk loop).

**Scripts/tests/templates.** No scripts/, tests/, templates/, agents/, skills/, or hooks/ directories exist., Only files: .claude-plugin/plugin.json (minimal manifest, no version/commands/hooks keys), README.md (usage + troubleshooting), LICENSE, and 3 command markdown files under commands/., The /clean_gone command embeds an inline POSIX bash pipeline (git branch -v \| grep '[gone]' \| sed \| awk \| while read) -- bash/grep/sed/awk dependency, not portable to a no-bash Windows-only shell.

**Docs quality.** README is solid for such a small plugin -- per-command what-it-does, usage, features, requirements, troubleshooting, and workflow examples -- but plugin.json is bare (no version, author email is generic support@anthropic.com, version only stated in README).

**Relevant capabilities.** git commit message generation from diff; commit + push + PR creation in one command (gh pr create); stale local branch cleanup including git worktree removal; secret-avoidance during staging (mentioned in README, NOT enforced by command prompt or hook); branch-off-main-if-needed behavior

**Limitations.** No version field in plugin.json (version 1.0.0 only appears in README prose); no commands array declared in manifest -- relies entirely on commands/ auto-discovery.; No skills, agents, or hooks -- zero enforcement layer. README claims /commit 'avoids committing files with secrets (.env, credentials.json)' but the actual commit.md prompt contains NO such instruction or guard, so this is aspirational, not implemented.; No GitHub identity auto-switch, no CI hardening, no branch-protection awareness, no SHA-pinning -- it is purely local commit/push/PR ergonomics, not a DevOps governance tool.; /commit-push-pr has no approval gate and no review step -- it commits, pushes, and opens a PR in a single forced tool batch with no human checkpoint, which conflicts with our 'permission before push' and 'no auto-push' conventions.; /clean_gone uses git branch -D (force delete) and git worktree remove --force with no dry-run/confirmation -- destructive by default.; Inline bash pipeline in /clean_gone (grep/sed/awk) is Unix-shell dependent; brittle on native Windows PowerShell-only setups.; No security review, no PR-review-quality analysis, no prompt-injection defense -- out of scope for this plugin.; Generic allowed-tools (e.g. Bash(git checkout --branch:*)) -- note the flag is actually --branch but git's create-branch checkout flag is -b/-B; the wildcard scoping looks slightly off and may not match real invocations.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| devops-enh | PARTIAL | Overlaps on the commit/push/PR ergonomics layer only. /commit (commit-message drafting from diff) and /commit-push-pr (push + gh pr create) cover the basic commit-and-open-PR work… |
| security-review | NO | README advertises secret-avoidance (.env, credentials.json) for /commit, but commit.md contains no such guard, no hook, and no static/diff scanning -- so even the one claimed secu… |
| plugin-authoring | NO | It IS a plugin and can serve as a minimal example of command-only structure with allowed-tools and !`...` context injection, but it provides no tooling, skills, or guidance for bu… |
| react-kit | NO | No frontend, React, UI, or component content whatsoever. Irrelevant. |
| qa-browser | NO | No browser/Playwright/RBAC/UAT testing. Irrelevant. |
| docs-wiki | NO | No wiki/SOP/documentation authoring features. Has its own README but does not author project docs. Irrelevant. |
| wiki-memory-sync | NO | No memory/wiki extraction or sync. Irrelevant. |
| claude-env-doctor | NO | No environment diagnosis/repair (MCP/WSL/Playwright/Node). Only requires git + gh; offers no diagnostics. Irrelevant. |

---

### typescript-lsp — v1.0.0  `[scaffold-sample]`

**Purpose.** Registers the community typescript-language-server (run as `typescript-language-server --stdio`) as a Language Server Protocol backend for Claude Code, giving the LSP tool code-intelligence over TypeScript/JavaScript files (go-to-definition, find-references, diagnostics/error checking, symbol lookup). It maps the extensions .ts/.tsx/.js/.jsx/.mts/.cts/.mjs/.cjs to LSP language IDs. It does NOT ship any prompts, skills, agents, commands, or hooks — it is pure infrastructure wiring that requires the user to `npm install -g typescript-language-server typescript` first.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\plugins\typescript-lsp`

**Docs quality.** A 25-line README that states the plugin's purpose, the eight supported extensions, and the global npm/yarn install command for the language server, plus links to upstream docs — adequate for such a thin plugin but offers zero usage guidance beyond installation.

**Relevant capabilities.** TypeScript/JavaScript LSP code-intelligence (go-to-definition, find-references, hover, diagnostics); Extension-to-language mapping for TS/JS variants (.ts/.tsx/.js/.jsx/.mts/.cts/.mjs/.cjs); Backs the Claude Code LSP/getDiagnostics tooling for TS/JS projects

**Limitations.** Contains no skills, commands, agents, or hooks — it is only an `lspServers` config block declared in the repo-root marketplace.json (no `.claude-plugin/plugin.json` exists inside the plugin dir, only README.md and LICENSE).; Requires the user to manually `npm install -g typescript-language-server typescript`; the plugin does not bundle, install, or verify the binary, and offers no diagnostics if the LSP spawn fails.; Provides raw LSP primitives only — no opinionated React/Next patterns, no lint/triage workflow, no migration guidance, no accessibility or component-convention layer.; `strict: false` and no version-pinning of the language server, so behavior depends entirely on whatever globally-installed version the user has.; Marketplace entry is version 1.0.0; the README has no CHANGELOG and no per-extension or framework-specific behavior beyond the language-ID map.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| react-kit | PARTIAL | Overlaps only at the mechanical layer: the LSP backend surfaces type errors, undefined symbols, unused imports, and find-references across .tsx/.jsx, which underpins React lint/fi… |
| claude-env-doctor | PARTIAL | Directly adjacent to the 'LSP spawn failures' diagnosis target: this plugin IS the thing that fails when typescript-language-server is not on PATH / not installed / wrong Node, so… |
| security-review | NO | No security tooling. Diagnostics are limited to TS/JS type-checking via tsserver; there is no static security analysis, RBAC/auth review, secrets scanning, prompt-injection defens… |
| qa-browser | NO | No browser/Playwright/MCP, no role-based smoke tests, no RBAC-via-status-code proof, no UAT reports. Completely unrelated domain — this is editor-time language tooling, not runtim… |
| docs-wiki | NO | No wiki/docs authoring, SOPs, role guides, Mermaid, or code-vs-wiki reports. Ships only its own README; does not generate or maintain project documentation. |
| wiki-memory-sync | NO | No memory extraction, wiki reading, or AI-context-file generation. Unrelated. |
| devops-enh | NO | No GitHub/GitLab, PR review, commit/push, CI hardening, identity switch, or branch protection. Unrelated. |
| plugin-authoring | PARTIAL | Useful only as a reference example of the minimalist 'lspServers'-only plugin shape (marketplace.json entry with command/args/extensionToLanguage, strict:false, no .claude-plugin/… |

---

### playwright — vnone declared (no version field in plugin.json; MCP pinned to @playwright/mcp@latest, i.e. floating not pinned)  `[scaffold-sample]`

**Purpose.** Thin official wrapper plugin that registers Microsoft's Playwright MCP server (@playwright/mcp@latest) so Claude can drive a real browser: navigate, click, fill forms, snapshot the accessibility tree, screenshot, read console/network, and run JS for browser automation and end-to-end testing.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\external_plugins\playwright`

**Scripts/tests/templates.** None. The plugin contains only two files: .claude-plugin/plugin.json (3-key manifest: name, description, author=Microsoft) and .mcp.json (registers server 'playwright' -> command 'npx', args ['@playwright/mcp@latest']). No skills/, commands/, agents/, hooks/, scripts/, tests/, templates/, README, or CHANGELOG exist in the directory.

**Docs quality.** Minimal: a single one-line description in plugin.json and the marketplace entry (category 'testing'); no README, no CHANGELOG, no usage docs, and the directory homepage URL points at a 'claude-plugins-public' repo path that differs from the actual 'claude-plugins-official' location.

**Relevant capabilities.** Provides the raw Playwright MCP browser-automation toolset (browser_navigate, browser_click, browser_fill_form, browser_type, browser_snapshot (accessibility tree), browser_take_screenshot, browser_console_messages, browser_network_requests, browser_evaluate, browser_wait_for, browser_tabs, browser_select_option, browser_handle_dialog, browser_file_upload) — the same engine our qa-browser capability would build on top of.; Accessibility-tree snapshots usable for basic a11y inspection (relevant to react-kit a11y basics and qa-browser evidence).; Console + network capture, useful as raw evidence material for QA reports.

**Limitations.** Pure MCP pointer plugin: zero skills, commands, agents, hooks, scripts, tests, or templates — it contributes only the MCP server registration and no opinionated workflow, prompt, or guardrail.; No version field in plugin.json and the MCP is pinned to @playwright/mcp@latest (floating), so behavior can drift across runs; not reproducible.; Requires npx/Node at runtime to fetch @playwright/mcp@latest on first use (network + Node dependency); no offline guarantee and no bundled binary.; No safety gates of any kind: no production-URL guard, no destructive-action gate, no host-scoping or auth-header handling, no role/RBAC test logic — all of that would have to be built around it.; Documentation is one sentence; homepage URL in the marketplace entry references a 'claude-plugins-public' path that does not match this checkout. Maturity assessed from files only (directory is present and inspectable, not a broken remote pointer).

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| qa-browser | PARTIAL | Supplies the underlying browser-driving engine (mcp__plugin_playwright_playwright__browser_* tools: navigate, click, fill_form, snapshot, screenshot, console_messages, network_req… |
| react-kit | NO | Contains no React/Next patterns, components, architecture guidance, lint/triage, or migration content. The browser tools could exercise a React app at runtime, but the plugin offe… |
| claude-env-doctor | NO | Does not diagnose or repair anything. It is itself an example of the Playwright-Chrome-vs-Chromium / npx-shim surface that claude-env-doctor would troubleshoot (it shells out to n… |
| security-review | NO | No static analysis, diff review, RBAC/auth review, secrets hygiene, or prompt-injection defense. browser_evaluate / browser_run_code_unsafe execute arbitrary JS in the page with n… |
| docs-wiki | NO | No documentation authoring capability; the plugin itself ships only a one-line description and no README/CHANGELOG. |
| wiki-memory-sync | NO | Unrelated; no wiki reading, memory extraction, or context-file generation. |
| devops-enh | NO | No Git/GitHub/GitLab, PR, CI, or identity-switch functionality; only browser automation. |
| plugin-authoring | NO | Not a plugin-building tool. It is a minimal reference example of an MCP-only pointer plugin (good to study for the .mcp.json + thin plugin.json pattern), but it provides no skill/… |

---

### github — vnone declared (no version field in plugin.json; marketplace entry uses local source "./external_plugins/github" with no ref/sha pin)  `[scaffold-sample]`

**Purpose.** Thin MCP-wrapper plugin that registers GitHub's official remote MCP server (HTTP) so Claude Code can drive the full GitHub API directly — create/manage issues, manage and review pull requests, search repositories/code, and interact with repository management endpoints. It ships no local logic; all capability comes from the remote server at https://api.githubcopilot.com/mcp/, authenticated with a GITHUB_PERSONAL_ACCESS_TOKEN bearer token.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\external_plugins\github`

**Scripts/tests/templates.** No scripts, tests, templates, README, or CHANGELOG present. Only two files: .claude-plugin/plugin.json (manifest: name/description/author, no version) and .mcp.json (single HTTP MCP server: url=https://api.githubcopilot.com/mcp/, Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}).

**Docs quality.** Minimal — a one-line manifest description and a marketplace blurb; no README, no CHANGELOG, no usage docs, and no documentation of which GitHub MCP tools/scopes are exposed or how to provision the PAT.

**Relevant capabilities.** GitHub issue create/manage (via remote MCP); Pull request create/manage/review (via remote MCP); Repository and code search (via remote MCP); General GitHub API access (via remote MCP); PAT-based GitHub authentication (single bearer token)

**Limitations.** Pure remote-MCP pointer: the entire plugin is plugin.json + .mcp.json. No skills, commands, agents, hooks, scripts, tests, or templates ship locally — it adds zero opinionated workflow, only raw tool access.; Capabilities are not introspectable from the directory: the actual tool surface lives behind the remote HTTP server (https://api.githubcopilot.com/mcp/) and cannot be enumerated from files. The list of operations is inferred from the description only.; No version anywhere (plugin.json omits version; marketplace entry pins no ref/sha), so the version-bump/update-detection convention we rely on does not apply.; Requires a GITHUB_PERSONAL_ACCESS_TOKEN env var that the plugin neither provisions, scopes, nor documents; security posture (token scope, least-privilege) is entirely on the user.; It is GitHub-only. No GitLab, no Azure DevOps. No identity auto-switch between multiple GitHub accounts (a workflow we need for taqat-techno vs ahmed-lakosha).; No safety/policy layer: no PreToolUse confirmation hooks, no branch-protection guardrails, no CI-hardening logic, no approval gates — destructive GitHub writes are unguarded.; Provides primitives, not process: PR review here means the API surface to fetch/comment on PRs, not a review methodology, rubric, or security/RBAC analysis.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| devops-enh | PARTIAL | Supplies the GitHub API primitives our devops work needs — issues, PR create/manage, PR review endpoints, repo/code search, commit/push-adjacent operations via the remote MCP. But… |
| security-review | NO | Despite advertising 'review code,' that means the API surface to read/comment on PRs, not security analysis. There is no static/diff scanning, no RBAC/auth review, no secrets-hygi… |
| plugin-authoring | NO | Offers no plugin/skill/hook/agent authoring or validation help. It is only interesting to plugin-authoring as a canonical minimal example of the .mcp.json remote-HTTP MCP wiring p… |
| react-kit | NO | No frontend, React/Next, or UI content whatsoever. Unrelated domain. |
| qa-browser | NO | No browser automation, Playwright, RBAC/route-access testing, or UAT reporting. Unrelated. |
| docs-wiki | NO | No wiki/SOP/doc authoring. It can touch GitHub-hosted markdown via the raw API, but provides no authoring workflow, diagram generation, discrepancy reporting, or link validation. |
| wiki-memory-sync | NO | No memory extraction, SOP/business-knowledge separation, or staleness detection. Unrelated. |
| claude-env-doctor | NO | No environment diagnosis/repair. The only adjacency is that misconfigured GITHUB_PERSONAL_ACCESS_TOKEN / MCP wiring for this plugin would be something claude-env-doctor diagnoses … |

---

### gitlab — vnone (no version field in plugin.json)  `[scaffold-sample]`

**Purpose.** GitLab DevOps platform integration delivered purely as a remote MCP-server pointer. The plugin contributes zero local components; it registers GitLab's hosted HTTP MCP server (https://gitlab.com/api/v4/mcp) so Claude can manage GitLab repositories, merge requests, CI/CD pipelines, issues, and wikis through whatever tools that server exposes at runtime.

**Path.** `C:\MY-WorkSpace\claude_plugins\claude-plugins-official\external_plugins\gitlab`

**Docs quality.** No README or CHANGELOG; the only documentation is the one-sentence description repeated in plugin.json and the marketplace entry, so behavior and the exact tool catalog are entirely undocumented from the checkout.

**Relevant capabilities.** devops-enh; docs-wiki

**Limitations.** This is a remote-pointer plugin: the directory contains only .claude-plugin/plugin.json and .mcp.json. There are no skills/, commands/, agents/, hooks/, scripts/, tests/, or templates/ directories to inventory.; plugin.json has no version field, so Claude Code's plugin updater cannot track versions (violates our own version-bump convention) and there is no way to pin behavior.; All capability lives behind a hosted HTTP MCP server (https://gitlab.com/api/v4/mcp). The tool catalog is not declared locally and was not introspectable from the checkout; the actual MR/CI/issue/wiki operations depend entirely on what GitLab exposes at runtime and on GitLab.com auth — it does not work for self-hosted GitLab without changing the URL.; No README/CHANGELOG, no examples, no auth/setup guidance. A user installing this gets a raw tool set with no workflow scaffolding, no opinionated review/CI-hardening behavior, and no identity-switch logic.; The plugin provides raw GitLab API access only; it embeds no review heuristics, CI-hardening rules (SHA-pinning, approval gates), branch-protection workflows, security-diff review, or RBAC/QA logic of its own — those would all have to come from our plugins layered on top.

**Overlap with our capabilities.**

| Our capability | Coverage | Note |
|---|:--:|---|
| devops-enh | PARTIAL | The MCP server gives raw GitLab primitives (repos, merge requests, CI/CD pipelines, issues per the description) so the API surface for MR creation, commit/push, and pipeline inspe… |
| docs-wiki | PARTIAL | The description explicitly lists 'wikis' among managed resources, so GitLab wiki pages can presumably be read/written via MCP tools. However there is no SOP/role-guide authoring g… |
| react-kit | NO | No frontend/React capability whatsoever; this is a DevOps-platform integration. |
| qa-browser | NO | No browser/Playwright/QA capability; the plugin only exposes GitLab API tools. |
| wiki-memory-sync | NO | Wikis are mentioned only as a CRUD target. There is no memory-extraction, business-vs-SOP separation, or stale-memory detection — none of the wiki-memory-sync pipeline. |
| claude-env-doctor | NO | No environment diagnosis/repair. Ironically it adds an MCP server but provides zero tooling to diagnose MCP/Windows/WSL wiring. |
| plugin-authoring | NO | Not a plugin-building tool; it is itself a minimal example of an MCP-pointer plugin but offers no authoring/validation capability. |
| security-review | NO | No static or diff security review, RBAC/auth review, secrets hygiene, or prompt-injection defense. It only proxies GitLab API calls. |

---

## 4. Local custom plugin inventory

Ten local plugins (versions/purpose per the prior audit's live inventory). Overlap is assessed against the official marketplace.

| Plugin | Path | Ver | Purpose | Official overlap | Verdict | Reason |
|---|---|---|---|---|---|---|
| **devops-plugin** | `plugins/devops-plugin` | 6.3.0 | Azure DevOps hybrid (work items, sprints, PRs) | **Partial** — `code-review`, `pr-review-toolkit`, `commit-commands`, `github`, `gitlab`, `security-guidance` cover the *GitHub/PR/commit/CI-security* slice | **Enhance** | Keep the Azure-DevOps core (no official equivalent); adopt official plugins for any GitHub-side work instead of building it here |
| **react-admin-kit-plugin** → **react-kit** | `plugins/react-admin-kit-plugin` | 0.2.0 | Admin CRUD scaffolding + admin-route audit | **Partial** — `frontend-design` (aesthetics only) | **Enhance + rename** | Broaden to general React/Next patterns; complementary to `frontend-design`; triage/React-19/states are uncovered |
| **qa-browser-plugin** | `plugins/qa-browser-plugin` | scaffold | Browser QA / Playwright-MCP testing | **Partial** — `playwright` MCP (raw engine), remote `chrome-devtools-mcp` | **Enhance** | Build the methodology layer (RBAC proof, UAT reports, disposable-data safety) on top of official transport |
| **docs-wiki-plugin** | `plugins/docs-wiki-plugin` | scaffold | Wiki authoring / SOP / discrepancy | **Partial** — `gitlab` wiki MCP, `code-modernization` eng-docs; remote `notion`/`atlassian`/`mintlify` are surfaces | **Keep / build** | No official plugin authors+audits a project Wiki with source-of-truth doctrine |
| **rag-plugin** | `plugins/rag-plugin` | — | ragtools service ops/diagnose/repair + retrieval | **None** for ragtools; remote `context7` is unrelated docs-MCP | **Keep** | Bespoke to the local ragtools product; no overlap |
| **odoo-plugin** | `plugins/odoo-plugin` | — | Unified Odoo (upgrade/i18n/docker/etc. sub-skills) | **None** | **Keep / enhance** | Odoo-specific; lesson-driven i18n + volume-safety enhancements only |
| **paper-plugin** | `plugins/paper-plugin` | — | Research/paper authoring | **None** | **Keep** | No official overlap; the one mapped lesson (WebFetch headers) routes to claude-env-doctor |
| **ntfy-plugin** | `plugins/ntfy-plugin` | — | ntfy push notifications | **None** | **Keep** | No official notification plugin; integration target for devops alerts |
| **pandoc-plugin** | `plugins/pandoc-plugin` | — | Document conversion via pandoc | **None** | **Keep** | No official equivalent |
| **remotion-plugin** | `plugins/remotion-plugin` | — | Programmatic video (Remotion) | **None** | **Keep** | No official media/video plugin |

**Net:** zero local plugins are *replaced* by an official plugin. One is *renamed* (react-admin-kit → react-kit). Two planned scaffolds (qa-browser, docs-wiki) survive as thin layers over official tooling. `devops-plugin` is the only one whose *planned enhancements* shift substantially to official plugins.

---

## 5. Capability coverage matrix

`Off` = official coverage, `Loc` = local coverage (Y/Part/N). Recommendation codes: **USE-OFF** (use official as-is), **FORK** (fork/adapt official), **ENH-LOC** (enhance local), **KEEP-LOC** (keep local — official insufficient), **BUILD** (build new), **DEFER**, **DROP**.

### react-kit capabilities

| Capability | Off | Best official | Loc | Best local | Remaining gap | Dup risk | Rec | Prio |
|---|:--:|---|:--:|---|---|:--:|---|:--:|
| React app architecture | N | feature-dev (generic) | Part | react-kit | opinionated Next/React structure patterns | Low | KEEP-LOC | P2 |
| Admin panel creation | N | — | Y | react-admin-kit | none (local already does it) | Low | ENH-LOC | P1 |
| Dashboard / cards / charts | N | frontend-design (visual) | Part | react-kit | data-viz lazy-load patterns | Low | ENH-LOC | P2 |
| CRUD / list / detail / form | N | — | Y | react-admin-kit | none | Low | ENH-LOC | P1 |
| Role-aware UI | N | — (auth0/workos remote, infra) | Part | react-kit | render-from-403 access states | Low | ENH-LOC | P1 |
| Loading / error / empty / access states | N | — | Part | react-kit | the canonical state machine | Low | ENH-LOC | **P0** |
| Import/export UI | N | — | N | react-kit | pairs with qa-browser import/export QA | Low | BUILD(in react-kit) | P2 |
| RTL/LTR | N | frontend-design (styling) | Part | react-kit | Arabic-first preserve rules | Low | ENH-LOC | P2 |
| React lint/finding **triage discipline** | N | code-simplifier (quality only) | Part | react-kit + react-doctor skill | classify safe/judgment/FP/forbidden; FP catalog | Med | ENH-LOC | **P0** |
| React-19 migration | N | code-modernization (legacy, not React19) | N | react-kit | forwardRef→ref, useContext→use, server-passthrough | Low | BUILD(in react-kit) | P1 |
| data-fetching hooks surfacing errors | N | — | Part | react-kit | propagate-error→access-required | Low | ENH-LOC | **P0** |
| Accessibility basics | Part | frontend-design (a11y mentions) | Part | react-kit | backdrop→button, label-htmlFor checks | Med | ENH-LOC | P2 |
| Component conventions | Part | code-simplifier, pr-review-toolkit(type-design) | Part | react-kit | follow-house-pattern | Med | ENH-LOC | P2 |

### qa-browser capabilities

| Capability | Off | Best official | Loc | Best local | Remaining gap | Dup risk | Rec | Prio |
|---|:--:|---|:--:|---|---|:--:|---|:--:|
| Browser automation engine | **Y** | **playwright** MCP (+chrome-devtools-mcp) | Part | qa-browser | none — *consume official* | **High** | USE-OFF | P0 |
| Console / network / screenshot evidence | Y | playwright / chrome-devtools-mcp | Part | qa-browser | none — consume official | High | USE-OFF | P1 |
| Role-based smoke testing | N | — | Part | qa-browser | per-role login flow methodology | Low | ENH-LOC | P1 |
| UI route-access validation | N | — | Part | qa-browser | matcher≠protection checks | Low | ENH-LOC | P1 |
| UI-vs-API permission proof (403 vs 400/409) | N | — | Part | qa-browser | the status-code proof method | Low | ENH-LOC | **P0** |
| Modal/row/bulk action walkthroughs | N | playwright (raw clicks) | Part | qa-browser | scripted walkthrough patterns | Low | ENH-LOC | P2 |
| Safe destructive testing (disposable data) | N | — | Part | qa-browser | disposable-data + test-allowlist guard | Low | ENH-LOC | **P0** |
| UAT readiness report (PASS/FAIL/BLOCKED) | N | session-report (usage only) | Part | qa-browser | the report template | Low | ENH-LOC | P1 |
| Host-scoped auth/bypass headers | N | playwright (can route, no guidance) | Part | qa-browser | CORS-safe injection recipe | Low | ENH-LOC | **P0** |
| Production-URL safety gates | N | security-guidance (bash prod guard, adjacent) | Part | qa-browser | lowercase/canonicalize host gate | Med | ENH-LOC | **P0** |

### docs-wiki capabilities

| Capability | Off | Best official | Loc | Best local | Remaining gap | Dup risk | Rec | Prio |
|---|:--:|---|:--:|---|---|:--:|---|:--:|
| Project Wiki creation/authoring | N | gitlab (wiki MCP surface) | Part | docs-wiki | flat-namespace authoring methodology | Low | KEEP-LOC | P1 |
| Engineering SOP / business docs / manuals | Part | code-modernization (eng docs) | Part | docs-wiki | SOP/role-guide templates | Low | ENH-LOC | P2 |
| Workflow / Mermaid diagrams | N | — | Part | docs-wiki | diagram authoring helper | Low | ENH-LOC | P2 |
| Code-vs-wiki discrepancy reports | N | — | Part | docs-wiki | source-of-truth discrepancy skill | Low | ENH-LOC | P1 |
| Wiki link/namespace validation | N | — | Part | docs-wiki | collision + `.md`-slug validator | Low | ENH-LOC | P1 |
| Safe wiki updates / no stray docs | N | — | Part | docs-wiki | delete-safety + verify-target | Low | ENH-LOC | P1 |

### wiki-memory-sync capabilities

| Capability | Off | Best official | Loc | Best local | Remaining gap | Dup risk | Rec | Prio |
|---|:--:|---|:--:|---|---|:--:|---|:--:|
| Generate AI-readable project memory | Part | **claude-md-management** (CLAUDE.md) | N | — | from-Wiki source, not sessions | **Med** | FORK/align | DEFER |
| Extract business vs SOP/rule memories | N | code-modernization (business-rules extractor, adjacent) | N | — | the business/SOP split | Low | DEFER | DEFER |
| Detect stale memories | Part | claude-md-management (keep current) | N | — | wiki-driven staleness | Med | align w/ official | DEFER |
| Read project Wiki as source | N | gitlab/notion/atlassian (surfaces) | N | — | wiki→memory extraction | Low | DEFER | DEFER |

### claude-env-doctor capabilities

| Capability | Off | Best official | Loc | Best local | Remaining gap | Dup risk | Rec | Prio |
|---|:--:|---|:--:|---|---|:--:|---|:--:|
| Windows/WSL env diagnosis | N | — (desktop-commander remote = terminal) | N | — | all of it | Low | **BUILD** | P1 |
| MCP wiring diagnosis | N | claude-code-setup (sets up, not diagnoses) | Part | rag-plugin (ragtools-specific) | generic MCP-not-loading ladder | Low | **BUILD** | P1 |
| `~/.claude.json` / settings diagnosis | N | — | Part | rag-plugin (mcp-wiring ref) | generic config-truth doctor | Low | **BUILD** | P1 |
| Python encoding (Windows) | N | — | N | — | PYTHONIOENCODING guard | Low | BUILD | P2 |
| Playwright Chrome-vs-Chromium | N | playwright (the failing tool) | Part | qa-browser (touches) | executable-path fix recipe | Low | BUILD | P2 |
| WSL DNS / VPN / HCS timeouts | N | — | N | — | DNS-vs-TCP isolation ladder | Low | BUILD | P1 |
| npm-shim / Node CLI spawn / LSP failures | N | typescript-lsp (the failing artifact) | N | — | node.exe+JS-entrypoint fix | Low | BUILD | P1 |
| Claude Code 401 login loop | N | — | N | — | forceLoginMethod diagnosis | Low | BUILD | P2 |

### Existing-local-plugin enhancement areas & cross-cutting

| Capability | Off | Best official | Loc | Best local | Remaining gap | Dup risk | Rec | Prio |
|---|:--:|---|:--:|---|---|:--:|---|:--:|
| Plugin/skill/hook/MCP authoring | **Y** | **plugin-dev**, skill-creator, mcp-server-dev, hookify | Part | claude-plugin-builder skill | none — use official | **High** | USE-OFF | P1 |
| Static + diff security review, secrets, injection | **Y** | **security-guidance** (+semgrep/sonarqube remote) | N | — | live RBAC proof (→qa-browser) | **High** | USE-OFF | P1 |
| PR review (multi-agent, confidence) | Part→Y | **code-review**, pr-review-toolkit | Part | devops-plugin (Azure) | GitHub PR review = use official | High | USE-OFF | P1 |
| Commit / push / PR creation | Part→Y | **commit-commands** | Part | devops-plugin | use official for GitHub | Med | USE-OFF | P2 |
| GitHub API surface | Y | **github** MCP | N | — | use official | Med | USE-OFF | P2 |
| CI hardening (SHA-pin, gates) | Part | security-guidance, code-review | N | — | opinionated CI-review rules | Low | ENH-LOC(devops) | P1 |
| Identity auto-switch by repo owner | N | — | Part | devops-plugin (rule) | git-remote→gh-auth hook | Low | ENH-LOC(devops) | P1 |
| Odoo i18n / volume safety | N | — | Part | odoo-plugin | lesson-driven references | Low | ENH-LOC(odoo) | P1 |
| Notifications (push) | N | — | Y | ntfy-plugin | none | Low | KEEP-LOC | P3 |
| Document conversion | N | — | Y | pandoc-plugin | none | Low | KEEP-LOC | P3 |
| Programmatic video | N | — | Y | remotion-plugin | none | Low | KEEP-LOC | P3 |

---

## 6. React-kit decision

- **Does an official plugin cover generic React/Next.js app patterns?** No. `frontend-design` (1 skill) covers *visual/aesthetic* quality (typography, color theming, motion) and explicitly "avoids generic AI aesthetics" — it is a *design* skill, not an architecture/admin/CRUD/role-aware-UI patterns library. `feature-dev` is generic feature scaffolding, not React-specific. Remote `expo` is React **Native** (mobile), not web Next.js.
- **Admin panel creation?** No official coverage. Our local `react-admin-kit-plugin` (v0.2.0) already does this better than anything official, with an adapter-cache for genericness.
- **React lint/finding triage?** No. `code-simplifier` refines recently-modified code for clarity, and `pr-review-toolkit` has type-design/quality agents, but neither implements the *triage discipline* (classify each finding safe-mechanical / needs-judgment / false-positive / forbidden-zone, never chase the score) or the react-doctor false-positive catalog. The session's `react-doctor` skill is the *tool*; react-kit owns the *discipline*.
- **React 19 migration?** No. `code-modernization` targets COBOL/legacy-Java/C++/monoliths — not `forwardRef`→ref-prop, `useContext`→`use`, or server-passthrough metadata splits.
- **Should we still rename react-admin-kit → react-kit?** **Yes.** The official gap is precisely the *general* React-quality/migration/state space, not admin panels specifically — the broadened name matches where the unique value is.
- **Build/enhance local, or use official?** **Enhance local react-kit**, scoped to be *complementary* to `frontend-design`: react-kit owns architecture, admin/CRUD/dashboard templates, role-aware UI, the loading/error/empty/access state machine, lint-triage discipline + FP catalog, and React-19 migration; `frontend-design` stays the tool for net-new visual design. Do **not** duplicate frontend-design's aesthetics.
- **Which capabilities remain local-only?** Lint/finding-triage discipline, React-19 migration recipes, data-fetching error/access states, admin/CRUD/list/detail/form templates, role-aware UI from 403, RTL-preserve rules, follow-house-pattern. None of these have an official home.

**Decision: ENHANCE LOCAL (react-kit), complementary to `frontend-design`.** Priority P0 for the lint-triage discipline + data-fetching-states; P1 for React-19 migration + admin/CRUD templates.

---

## 7. QA-browser decision

- **Does an official plugin cover browser QA / Playwright-MCP testing?** Partially — the **transport only**. The first-party `playwright` external plugin exposes the Microsoft Playwright MCP (`browser_navigate/click/fill_form/snapshot/screenshot/network/console/…`), and remote `chrome-devtools-mcp` adds perf traces + source-mapped console/network capture. These are *raw automation engines*. Neither ships any QA *methodology*.
- **Role-based smoke testing?** No. The official engines can log in and click, but there is no per-role smoke-flow methodology.
- **UI-vs-API permission verification?** No. The 403-vs-400/409 status-code proof (and trusting the auth/me API over UI role labels) is entirely uncovered — and it is our single highest-value QA capability.
- **Safe destructive testing?** No. No disposable-data guard, test-phone allowlist, or "scope out OTP/SMS/coupon routes" discipline exists officially.
- **UAT readiness reports?** No. `session-report` produces a token/usage HTML report — unrelated. The PASS/FAIL/BLOCKED, evidence-linked UAT report is uncovered.
- **Production-URL safety gates?** Only adjacent — `security-guidance` has a bash production-safety guard pattern, but the lowercase/canonicalize-host gate for browser targets is uncovered.
- **Should local qa-browser still exist?** **Yes.** It is a methodology layer with no official equivalent.
- **Enhanced, replaced, or merged?** **Enhanced — and re-architected to *depend on* the official `playwright` MCP for transport** rather than implementing browser automation itself. This avoids duplicating Microsoft's engine and lets qa-browser focus 100% on RBAC proof, route-access validation, disposable-data safety, evidence capture conventions, and UAT reporting. Optionally support `chrome-devtools-mcp` as an alternate engine for perf/a11y evidence.

**Decision: ENHANCE LOCAL (qa-browser) as a methodology layer over official `playwright`/`chrome-devtools-mcp`.** Do **not** build a browser engine. Priority P0 for RBAC-proof + disposable-data-safety + host-scoped header injection + production-URL gate; P1 for role smoke flows + UAT report template. Note: the *static* security-review slice (injection/XSS/secrets) is better served by official `security-guidance`; qa-browser owns only the **live** authorization proof that static review cannot do.

---

## 8. Docs-wiki decision

- **Does an official plugin cover Wiki authoring?** No first-party plugin authors a project Wiki. `gitlab` exposes a wiki MCP *surface* (read/write GitLab wiki pages via API) but no authoring methodology; `code-modernization` *generates* structured engineering docs (ASSESSMENT/BRIEF/BUSINESS_RULES md) as a side effect of modernization, not as a Wiki tool. Remote `mintlify` (MDX doc sites), `notion`, and `atlassian`/Confluence are doc *surfaces/integrations*, not Wiki-authoring-with-doctrine plugins.
- **GitHub Wiki structure / flat namespace?** No. The flat-filename collision rule and `.md`-less internal-slug linking are uncovered (the prior audit's L620).
- **SOP / business docs / user manuals?** Only `code-modernization` partially (engineering docs from legacy analysis). No SOP/role-guide/manual templates officially.
- **Code-vs-wiki discrepancy?** No. The "read code, flag every contradicting doc claim, resolve as a doc fix" skill is uncovered.
- **Safe wiki updates?** No. Delete-safety (grep dependents before `rm`), verify-target-exists, and stale-folder avoidance are uncovered.
- **Should local docs-wiki still exist?** **Yes** — the authoring + integrity-auditing methodology is genuinely uncovered.
- **Should it remain separate from wiki-memory-sync?** **Yes** (per the brief). docs-wiki = human-facing Wiki authoring/auditing; wiki-memory-sync = machine-facing memory extraction. The official landscape does not provide an architecture that argues for merging them; if anything, `claude-md-management` (a *separate* memory plugin) reinforces keeping memory generation in its own plugin.

**Decision: KEEP / BUILD docs-wiki.** Priority P1 for code-vs-wiki discrepancy + source-of-truth doctrine + link/namespace validator + safe-deletion; P2 for SOP/manual/role-guide templates + Mermaid helper. If the target Wiki lives on GitLab, *consume* the official `gitlab` MCP for read/write rather than reimplementing API access.

---

## 9. Wiki-memory-sync decision

- **Does any official plugin convert Wiki/docs into AI memory/context?** No, not from a *Wiki*. `claude-md-management` generates and maintains `CLAUDE.md` (which *is* an AI-readable project-memory file) and "captures session learnings" — but its source is **sessions**, not a Wiki. Remote `remember` derives tiered memory from **conversation history**, again not docs. `code-modernization`'s business-rules-extractor separates durable business knowledge from implementation, which is conceptually adjacent but is a modernization step, not a docs→memory sync.
- **Does any official plugin manage project memories from docs?** No. The "read the Wiki/SOP pages → emit business-knowledge memories + rule memories, detect stale ones" loop is unimplemented anywhere official.
- **Is a new wiki-memory-sync plugin still needed?** **Yes, eventually** — the Wiki-as-source path is uncovered. But it is **not urgent**, and it should not be built before docs-wiki stabilizes.
- **Could it be an enhancement to an official plugin?** Partially — the *output* (an AI-memory file) should **align with `claude-md-management`'s memory/CLAUDE.md format** so the two don't produce competing memory artifacts. Treat `claude-md-management` as the memory-format authority and make wiki-memory-sync a *source adapter* (Wiki → that format), reusing its staleness model.
- **Could it be an enhancement to local docs-wiki?** **No** — keep it separate (per the brief). The official split (`claude-md-management` is its own plugin, distinct from any doc tool) supports separation: authoring docs and synthesizing memory are different concerns with different consumers.
- **Defer?** **Yes — defer to a later phase** (after docs-wiki). Mine the local TR_plugins `memory-sync` engine (detached-worktree branch pinning, L490/L1109) as prior art, and the official `claude-md-management` for the memory format.

**Decision: DEFER. Design as a source-adapter that emits `claude-md-management`-compatible memory; keep separate from docs-wiki.**

---

## 10. Claude-env-doctor decision

- **Do official plugins cover Windows/WSL/Claude-Code environment diagnosis?** No. `claude-code-setup` is the **inverse** — it analyzes a codebase and *recommends* automations (MCP servers, hooks, skills, subagents) to set up; it does not diagnose or repair a broken environment. `session-report` only reads `~/.claude/projects` transcripts for usage/cost. Remote `desktop-commander` provides terminal/process control (a *capability* a doctor could use) but no diagnosis logic. `microsoft-docs` is just Windows/Azure doc lookup.
- **MCP wiring diagnosis?** No generic coverage. `claude-code-setup` recommends MCP setup; our local `rag-plugin` diagnoses *ragtools-specific* MCP wiring. The generic "MCP not loading → `claude mcp list` → read `.mcp.json` → run the spawn command" ladder is uncovered.
- **`~/.claude.json` / settings diagnosis?** No. The truth that user-MCP config lives in `~/.claude.json` (not `~/.claude/mcp.json`), the concurrent-session clobber, and the per-project `env`-block-disables-OAuth trap are uncovered.
- **Python encoding / npm-shim / Node CLI spawn?** No. `PYTHONIOENCODING` on Windows and the LSP npm-shim spawn fix are uncovered — ironically, the official `typescript-lsp`/`pyright-lsp` plugins are the very artifacts that *fail* with these issues.
- **Playwright Chrome-vs-Chromium setup?** No. The `playwright` plugin is the failing tool; the `--executable-path` fix is uncovered.
- **Is claude-env-doctor still needed?** **Yes — unambiguously.** It is the only planned item that is both completely uncovered by official plugins and high-value (≈18 lessons in the prior audit).
- **Build new, absorb, or drop?** **Build new.** It cannot be absorbed into any existing plugin without mis-scoping it (it spans MCP, WSL, login, LSP, encoding, browser-env). It should be the canonical home that rag-plugin, odoo-plugin, qa-browser, and paper-plugin *reference* for their environment-troubleshooting needs.

**Decision: BUILD NEW (claude-env-doctor).** It may *consume* `desktop-commander` (or plain Bash) for process inspection and *reference* the official LSP/playwright plugins as the artifacts it diagnoses. Priority P1.

---

## 11. Existing local plugin enhancement decisions

For each local plugin: the enhancement the prior audit recommended, official coverage of it, the final recommendation, priority, and the exact next action.

### devops-plugin
- **Originally recommended:** permission-first + gh-identity-auto-switch write hooks; CI-review advisor (SHA-pin, `environment:`≠approval, weakened-gate detection); pipelines command; bulk-ops; reconcile hook wiring.
- **Official coverage:** PR review → `code-review` + `pr-review-toolkit` (strong); commit/push/PR → `commit-commands`; GitHub API → `github`; CI-security → `security-guidance`. Identity-auto-switch and Azure core → **no** official coverage.
- **Final recommendation:** **Use official for the GitHub side; enhance local only for Azure core + identity-switch + opinionated CI rules.** Don't build GitHub PR/commit/review features into an Azure-only plugin.
- **Priority / next action:** P1 — add the gh-identity-auto-switch + permission-first hook (uncovered, high value) and a thin CI-rules reference; **adopt** `code-review`/`commit-commands`/`github` for GitHub workflows instead of building them.

### odoo-plugin
- **Originally recommended:** i18n/PO gettext reference, `_theme_load`/upgrade recipes, `down -v` volume guard + Postgres-pin check.
- **Official coverage:** none (Odoo-specific).
- **Final recommendation:** **Enhance local** — fully uncovered.
- **Priority / next action:** P1 — add the i18n reference + the volume-safety `PreToolUse` Bash guard.

### rag-plugin
- **Originally recommended:** consolidate `~/.claude.json` MCP-wiring truths; `/rag doctor` MCP-not-loading branch.
- **Official coverage:** none for ragtools; the *generic* MCP-config truths overlap the proposed `claude-env-doctor`.
- **Final recommendation:** **Keep local; move generic env/MCP truths to `claude-env-doctor` and reference them.** Keep only ragtools-service specifics in rag-plugin.
- **Priority / next action:** P2 — verify `references/mcp-wiring.md` is current; add the `/rag doctor` MCP branch that calls/links the env-doctor ladder.

### paper-plugin
- **Originally recommended:** nothing lesson-driven (only the Figma-PAT/WebFetch note, which is generic).
- **Official coverage:** none directly.
- **Final recommendation:** **Keep as-is.** Route the WebFetch-headers note to `claude-env-doctor`.
- **Priority / next action:** P3 — no change this cycle.

### ntfy-plugin
- **Originally recommended:** none (0 lessons).
- **Official coverage:** none (no official notification plugin).
- **Final recommendation:** **Keep.** Becomes the integration target for devops/CI alerts.
- **Priority / next action:** P3 — optionally expose a thin "notify" interface other plugins can call.

### pandoc-plugin
- **Originally recommended:** none.
- **Official coverage:** none.
- **Final recommendation:** **Keep as-is.**
- **Priority / next action:** P3 — none.

### remotion-plugin
- **Originally recommended:** none (0 lessons; gap-driven only).
- **Official coverage:** none (no official media/video plugin).
- **Final recommendation:** **Keep as-is.** If visual QA is ever needed, share a screenshot helper with qa-browser.
- **Priority / next action:** P3 — none this cycle.

### react-admin-kit → react-kit
- **Originally recommended:** rename + lint-triage skill, React-19 migration, data-fetching states, admin/CRUD templates.
- **Official coverage:** `frontend-design` (aesthetics only) — none of the above.
- **Final recommendation:** **Enhance local + rename**, complementary to `frontend-design`.
- **Priority / next action:** P0 — rename; build `react-lint-triage` + `data-fetching-states`; P1 React-19 migration + templates.

### qa-browser
- **Originally recommended:** RBAC verification, authorization-review, CORS-safe headers, anti-fraud audit, UAT report.
- **Official coverage:** `playwright`/`chrome-devtools-mcp` (transport + evidence only); `security-guidance` (static security, not live RBAC).
- **Final recommendation:** **Enhance local as a methodology layer over official transport.** Adopt `security-guidance` for static security; keep live RBAC proof here.
- **Priority / next action:** P0 — re-architect to depend on `playwright` MCP; build `verify-identity-and-rbac` + disposable-data safety + host-scoped injection.

### docs-wiki
- **Originally recommended:** source-of-truth doctrine, discrepancy report, link/namespace validator, safe deletion, templates.
- **Official coverage:** `gitlab` (wiki MCP surface), `code-modernization` (eng docs) — no authoring/auditing methodology.
- **Final recommendation:** **Keep / build.** Consume `gitlab` MCP if the Wiki is GitLab-hosted.
- **Priority / next action:** P1 — build discrepancy-report + doctrine + validator + safe-deletion skills.

---

## 12. Duplications and overlap warnings

**Where building from scratch would duplicate a professional official plugin — STOP and adopt:**
- **Plugin/skill/hook/MCP authoring** → `plugin-dev` (7 skills, production-grade), `skill-creator`, `mcp-server-dev`, `hookify`. Our planned `plugin-authoring-guide` / `skill-library-architect` / `agent-mcp-wrapper` / `plan-verifier` future plugins are **redundant** — consume these.
- **Static + diff security review, secrets, injection/XSS/SSRF** → `security-guidance` v2.0.0 (edit-time + Stop-time + agentic commit reviewer, 25+ classes). Our `secrets-hygiene-guard` / generic `secure-code-review` ambitions are **mostly redundant** — adopt it; add only the unique pasted-token-revoke workflow as a tiny rule.
- **Browser automation engine + evidence capture** → `playwright` (+`chrome-devtools-mcp`). qa-browser must **not** reimplement navigation/click/screenshot/network; it layers methodology on top.
- **PR review / commit / push / GitHub API** → `code-review`, `pr-review-toolkit`, `commit-commands`, `github`. The GitHub-side DevOps features must **not** be hand-built into `devops-plugin`.

**Where official plugins are better maintained / more professional than anything we'd build:**
- `plugin-dev`, `security-guidance`, `pr-review-toolkit`, `code-modernization`, `hookify` are production-ready with multiple agents/hooks/skills and CI — out-build-ing them is not worth it.

**Where local plugins are more tailored and should stay (official does not cover enough):**
- `qa-browser` (live RBAC proof / UAT methodology), `react-kit` (triage discipline / React-19 / state patterns / admin-CRUD), `docs-wiki` (project-Wiki authoring + discrepancy), `claude-env-doctor` (env diagnosis), `rag-plugin` (ragtools), `odoo-plugin` (Odoo), `ntfy`/`pandoc`/`remotion` (no official equivalent).

**Where forking/adapting an official plugin beats both using-as-is and building new:**
- **react-kit ← `code-simplifier` + `pr-review-toolkit`**: adapt their React/type-design review *recipes* into react-kit's triage catalog (don't fork the whole plugin).
- **wiki-memory-sync ← `claude-md-management`**: adopt its memory/CLAUDE.md *format and staleness model* as the output target; build only the Wiki→memory source adapter.
- **devops CI rules ← `code-review` + `security-guidance`**: reuse their diff-review patterns for the CI-hardening advisor.

**Where our local *lessons* should become patches/enhancements rather than new plugins:**
- The GitHub-hardening lessons → a `code-review`/devops CI-rules reference, not a `gha-hardening` plugin.
- The agent-safety lessons (prompt-injection-verify, read-only-immutability, auto-mode authority split) → small `rules/` + `hookify`-built hooks, not standalone plugins.
- The DB/migration lessons → an odoo/devops reference + (later) a `data-migration-safety` plugin only if it recurs cross-project.

**Net duplication risk verdict:** No *existing* local plugin duplicates an official one today. The real risk is **new** duplication — building GitHub DevOps features, a plugin-authoring helper, a generic security reviewer, or a browser engine that official plugins already provide. Avoid all four.

---

### Marketplace scan — remote/third-party entries that touch our capabilities

The full marketplace has 204 entries; 39 touch our capability areas. The remote (non-first-party) ones below are integrations we could *consume* but cannot fork/inspect here:

| Entry | Capability touch | Note |
|---|---|---|
| expo | react-kit | Remote (expo/skills). React Native, not web Next.js. Touches React patterns + data fetching + UI but mobile-targeted; little overlap with admin/dashb… |
| chrome-devtools-mcp | qa-browser, react-kit | Remote (ChromeDevTools/chrome-devtools-mcp). Overlaps qa-browser's console/network/screenshot evidence capture and a11y/perf inspection; alternative … |
| remember | wiki-memory-sync | Remote (Digital-Process-Tools/claude-remember). Conversation-derived memory, not Wiki-derived. Overlaps the memory-extraction concept of wiki-memory-… |
| semgrep | security-review | Remote (semgrep/mcp-marketplace). Static analysis / SAST — overlaps security-review's static-review half. Rule-engine based, not diff/RBAC/prompt-inj… |
| sonarqube | security-review, react-kit | Remote (SonarSource). Overlaps security-review (secrets scanning, security rules) and react-kit's lint/finding triage (quality rules across 40+ langs… |
| coderabbit | security-review, devops-enh | Remote (coderabbitai/skills). Overlaps both PR-review (devops-enh) and security-review (vuln detection). External AI service, not local methodology. |
| qodo-skills | security-review, qa-browser, devops-enh | Remote (qodo-ai). Broad overlap: security scanning (security-review), automated testing (qa-browser-adjacent), CI/CD quality (devops-enh). Generic, n… |
| 42crunch-api-security-testing | security-review, qa-browser | Remote (42Crunch). BOLA/BFLA = broken object/function-level authorization — directly relevant to qa-browser's UI-vs-API permission/RBAC proofs and se… |
| nightvision | security-review, qa-browser | Remote (nvsecurity). DAST against running web apps overlaps qa-browser's live-app testing and security-review's vuln surface. Pentest-oriented, not R… |
| auth0 | security-review, react-kit | Remote (auth0/agent-skills). Touches auth/protected-routes (security-review auth review; react-kit role-aware UI/protected routes) but is Auth0-SDK-s… |
| workos | security-review, react-kit | Remote (workos/skills). Explicit RBAC + auth + secrets(Vault) — adjacent to security-review's RBAC/auth review and react-kit's role-aware UI. Vendor-… |
| duende-skills | security-review | Remote (DuendeSoftware). AuthN/authZ + secure identity overlaps security-review's auth/RBAC review, but .NET/IdentityServer-specific implementation g… |
| mintlify | docs-wiki | Remote (mintlify). Doc-site authoring overlaps docs-wiki's page authoring, but targets Mintlify MDX sites, not a project Wiki with SOP/role-guide/Mer… |
| notion | docs-wiki, wiki-memory-sync | Remote (makenotion). Notion can serve as the 'Wiki/knowledge base' surface — overlaps docs-wiki authoring and wiki-memory-sync's read-Wiki-extract-me… |
| atlassian | docs-wiki, wiki-memory-sync, devops-enh | Remote (atlassian). Confluence = a Wiki/docs surface (docs-wiki authoring + wiki-memory-sync extraction source); Jira sprints touch devops-enh's work… |
| microsoft-docs | claude-env-doctor | Remote (MicrosoftDocs/mcp). Weak/tangential — Windows/Azure documentation lookup could aid claude-env-doctor's Windows/WSL diagnosis research. Not a … |
| desktop-commander | claude-env-doctor | Remote (DesktopCommanderMCP). Terminal + process management overlaps claude-env-doctor's need to inspect processes/run repair commands, but it is a g… |
| superpowers | plugin-authoring, devops-enh, qa-browser | Remote (obra/superpowers). Its skill-authoring/testing overlaps plugin-authoring; code-review overlaps devops-enh; TDD/systematic-debugging is testin… |

## 13. Final build / do-not-build table

| Item | Final decision | Reason | Target path / plugin | Prio | Next action |
|---|---|---|---|:--:|---|
| **claude-env-doctor** | **BUILD NEW** | No official env-diagnosis plugin; ~18 lessons; canonical home for cross-plugin env truths | new `plugins/claude-env-doctor` | P1 | Scaffold `/env-doctor` + doctor skill (MCP / WSL / login / LSP / encoding branches) |
| **react-kit** (rename of react-admin-kit) | **ENHANCE LOCAL + RENAME** | `frontend-design` covers only aesthetics; triage/React-19/states/admin uncovered | `plugins/react-admin-kit-plugin` → react-kit | P0 | Rename; build `react-lint-triage` + `data-fetching-states`; then React-19 + templates |
| **qa-browser** | **ENHANCE LOCAL (layer on official)** | `playwright` = transport only; RBAC-proof/UAT/disposable-data uncovered | `plugins/qa-browser-plugin` | P0 | Re-architect onto `playwright` MCP; build RBAC-proof + disposable-data + host-scoped injection |
| **docs-wiki** | **KEEP / BUILD** | No official project-Wiki authoring + discrepancy auditing | `plugins/docs-wiki-plugin` | P1 | Build discrepancy-report + source-of-truth doctrine + link validator + safe-deletion |
| **wiki-memory-sync** | **DEFER** | Uncovered from-Wiki, but align output with `claude-md-management`; build after docs-wiki | future plugin | P2 | Later: source-adapter Wiki → claude-md-management memory format |
| **devops GitHub enhancements** | **USE OFFICIAL** | `code-review`+`commit-commands`+`github` cover PR/commit/API; `security-guidance` covers CI security | adopt official | P1 | Enable official plugins; keep only Azure core + identity-switch hook + CI-rules ref local |
| **devops identity-switch + Azure core** | **ENHANCE LOCAL** | Uncovered by official | `plugins/devops-plugin` | P1 | Add gh-identity + permission-first write hook; reconcile hook wiring |
| **odoo enhancements** | **ENHANCE LOCAL** | Odoo-specific; uncovered | `plugins/odoo-plugin` | P1 | i18n/PO reference + `down -v` volume guard + Postgres-pin check |
| **rag enhancements** | **ENHANCE LOCAL (thin)** | Generic env truths move to claude-env-doctor | `plugins/rag-plugin` | P2 | `/rag doctor` MCP branch referencing env-doctor |
| **plugin-authoring future plugins** | **DROP — USE OFFICIAL** | `plugin-dev`/`skill-creator`/`mcp-server-dev`/`hookify` are production-grade | official | — | Adopt official; retire the future ideas |
| **secrets/security-review future plugin** | **DROP / ADOPT** | `security-guidance` is a professional superset | official `security-guidance` | P1 | Adopt; keep only live-RBAC (qa-browser) + tiny pasted-token-revoke rule |
| **agent-safety guards** (prompt-injection-verify, read-only-immutability, auto-mode authority) | **BUILD SMALL (rules/hooks)** | Niche but uncovered; not a full plugin | `rules/` + `hookify`-built hooks | P2 | Author 3 small rules; generate hooks via `hookify` |
| **gha-hardening** | **DO NOT BUILD** | Fold into devops CI-rules ref / `code-review` | devops-plugin | P2 | CI-rules reference only |
| **data-migration-safety** | **DEFER** | Cross-framework, lower frequency | future plugin | P2 | Revisit if it recurs in a 2nd project |
| **ntfy / pandoc / remotion / paper** | **KEEP AS-IS** | No official overlap; no lessons | local | P3 | No change this cycle |

---

## 14. Recommended next execution prompts

Five scenario prompts. **A** is the recommended first move; the others are scoped follow-ups.

### A. Adopt official plugins where they already cover the need (do this first)

```text
We audited official plugins vs our plan (plugins/OFFICIAL_PLUGINS_COVERAGE_AUDIT.md). For the capabilities official plugins already cover professionally, configure/adopt them instead of building:
- Enable and document usage of: plugin-dev (+ skill-creator, mcp-server-dev, hookify) for all future plugin/skill/hook/MCP authoring; security-guidance for static+diff security review and secrets/injection; code-review + pr-review-toolkit + commit-commands + github for GitHub PR/commit/review workflows; playwright (MCP) as the browser engine qa-browser will sit on top of.
- Do NOT build: a plugin-authoring helper, a generic security/secrets reviewer, GitHub PR/commit features inside devops-plugin, or a browser automation engine.
- Produce a short adoption note (which official plugin replaces which planned item) and confirm each is installed/enabled. Read-only + config only; no plugin code. Do not push without my go.
```

### B. Enhance local plugins with patterns from official plugins

```text
Enhance our local plugins using lessons + official patterns, per OFFICIAL_PLUGINS_COVERAGE_AUDIT.md §11/§13. Plan (don't build yet) per plugin, with acceptance criteria + fixtures:
- devops-plugin: gh-identity-auto-switch + permission-first write hook (uncovered); a CI-hardening rules reference adapting code-review/security-guidance patterns; reconcile hooks.json wiring vs README + add a test.
- odoo-plugin: i18n/PO gettext reference + a PreToolUse Bash guard blocking `docker compose down -v` + a Postgres-major-version pin check.
- rag-plugin: a /rag doctor "MCP not loading" branch that references claude-env-doctor's ladder (no duplication of references/mcp-wiring.md).
- react-kit: adapt code-simplifier + pr-review-toolkit React/type-design recipes into the lint-triage false-positive catalog.
Constraints: generic only (no project names/secrets); bump plugin.json version + CHANGELOG on each change; register in marketplace.json; validate_plugin.py to 0 errors; reference shared rules, never restate. No push without my go.
```

### C. Build claude-env-doctor (the one genuinely-needed new plugin)

```text
Build the claude-env-doctor plugin (justified in OFFICIAL_PLUGINS_COVERAGE_AUDIT.md §10 — no official env-diagnosis plugin exists). Enter plan mode first.
Scope: a /env-doctor command + a "doctor" skill with per-symptom branches: MCP-not-loading (claude mcp list -> read .mcp.json -> run spawn cmd; ~/.claude.json is the real config; concurrent-session clobber), WSL-unreachable (DNS-vs-TCP isolation ladder; HCS-timeout escalation; wsl -l -v distro discovery), login-401 (forceLoginMethod credential-shape diagnosis), LSP-missing (node.exe + JS-entrypoint spawn fix), encoding-crash (PYTHONIOENCODING on Windows), playwright chrome-vs-chromium (--executable-path). Add a DNS-vs-TCP isolation reference and a probe-tier SessionStart advisory hook. May consume desktop-commander/Bash for process inspection; reference (do not duplicate) rag-plugin's ragtools-specific MCP wiring.
Make it the canonical env home that rag/odoo/qa-browser/paper reference. Generic only, no secrets. Register in marketplace.json; validate to 0 errors. Plan with acceptance criteria + fixtures; wait for my approval; no push without my go.
```

### D. Continue react-kit as a local plugin (rename + scope)

```text
Rename react-admin-kit-plugin -> react-kit and scope it complementary to official frontend-design (per OFFICIAL_PLUGINS_COVERAGE_AUDIT.md §6). Plan mode first.
Rename: folder, .claude-plugin/plugin.json "name", plugins/.claude-plugin/marketplace.json entry, SKILL.md frontmatter "name:", any .react-admin-kit.local.json key references.
Build (P0): react-lint-triage skill (classify findings safe-mechanical/needs-judgment/false-positive/forbidden-zone; never chase the score; FP catalog adapted from react-doctor + code-simplifier + pr-review-toolkit) and data-fetching-states skill (propagate 403->access-required, 404->not-found, no empty shells). P1: react19-migration (forwardRef->ref, useContext->use, server-passthrough) + admin/CRUD/dashboard templates. Do NOT duplicate frontend-design aesthetics. Generic only; bump version + CHANGELOG; validate to 0 errors. Wait for approval; no push without my go.
```

### E. Plan wiki-memory-sync for later (deferred)

```text
Do NOT build yet. Produce a one-page design for a future wiki-memory-sync plugin per OFFICIAL_PLUGINS_COVERAGE_AUDIT.md §9: a SOURCE ADAPTER that reads a project Wiki and emits memory in claude-md-management's CLAUDE.md/memory format (align, don't reinvent), separating business-knowledge memories from SOP/rule memories, with stale-memory detection. Reuse TR_plugins memory-sync's detached-worktree branch-pinning for reproducibility. Keep it SEPARATE from docs-wiki. Output: scope, dependencies (docs-wiki must ship first), risks, and a go/no-go recommendation. Planning only — no code.
```

---

*End of audit. §3 (official inventory) and the §12 remote-entry table are generated from the 20-agent analysis (1 marketplace scan + 19 plugin inspections over the post-pull official repo); §1–§2 and §4–§14 narrative are authored from that data plus the prior LESSONS_TO_PLUGINS_GLOBAL_RECOMMENDATION_PLAN.md. The official marketplace was updated by fast-forward pull only; no plugin (official or local) was created or edited.*
