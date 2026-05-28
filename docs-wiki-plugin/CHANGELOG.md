# Changelog

All notable changes to `docs-wiki-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [0.2.0] — 2026-05-28 — Phase 3 content

Skills, commands, agents, and safety hooks — the plugin is now functional, not just a scaffold.

### Added

- **Skills** — 7 skills covering the wiki authoring + audit surface:
  - `wiki-code-vs-docs-discrepancy` — the never-silently-choose rule; classification (doc-drift / code-drift / intentional gap / unknown); evidence-pinning convention. Generic; portable to any project with both docs and code.
  - `wiki-structure` — GitHub Wiki flat-namespace + filename-uniqueness + internal-link convention; Home / _Sidebar / _Footer authorship; sibling-clone path; no-numeric-prefix rule. Flavour-aware (github-wiki / gitlab-wiki / azure-devops-wiki / mkdocs-tree).
  - `wiki-mermaid` — TD direction default; fixed shape vocabulary (stadium / rectangle / diamond / cylinder / parallelogram / hexagon); four-class colour palette (ok / block / external / audit); label hygiene; code-path scrub.
  - `wiki-link-validation` — five scans: filename collisions, broken internal links, internal-link convention, visible numeric prefixes, orphan pages. Flavour-aware. Never auto-fixes.
  - `wiki-safe-updates` — diff-preview-before-write; push-approval gate; no-force-push; retired-folder awareness; one-purpose-per-commit; revert-based rollback.
  - `wiki-authoring` — template catalogue: SOP, runbook, role-guide, onboarding, release-handover, user-manual, workflow, architecture, decision-record. Universal conventions (audience header, last-reviewed line, one-paragraph summary).
  - `wiki-vs-stray-docs` — refuses new files in stray docs/ folders when a wiki exists; soft warning on edits to existing stray files; pass-through for retired folders + exceptions.
- **Commands** — 6 commands:
  - `/wiki-init` — initialise wiki structure (Home / _Sidebar / optional _Footer); collect adapter inputs into `.docs-wiki.local.json`.
  - `/wiki-audit` — run all read-only checks; produce severity-grouped findings table.
  - `/wiki-update <page>` — edit existing page with diff preview via Edit (preserves history).
  - `/wiki-new <Page-Name>` — create new page from one of the authoring templates.
  - `/wiki-drift` — code-vs-wiki discrepancy sweep; classification + evidence; never auto-resolves.
  - `/wiki-sync-audit` — composes `/wiki-audit` + `/wiki-drift` into one report.
- **Agents** — 3 agents:
  - `wiki-link-auditor` — read-only link validation pass; returns severity-tagged findings table.
  - `wiki-cleanup-validator` — pre-delete reference check; per-candidate GO / NO-GO / NEEDS-USER-DECISION.
  - `wiki-drift-reporter` — read-only drift sweep with per-block evidence and proposed direction (never applied).
- **Hooks** — 2 hooks:
  - `PreToolUse` on `Bash` — push-approval gate on `git push` against wiki repos. Detects wiki path via `.wiki` basename or adapter cache `wikiPath`. Requires `DOCS_WIKI_PUSH_APPROVED=1` per-session. Force-push always refused, even with approval.
  - `PreToolUse` on `Write|Edit` — stray-docs check. New file in docs/, doc/, documentation/, project-docs/ when a wiki is present → BLOCK. Edit to existing stray file → WARN (advisory). Retired folders + exceptions pass through. Override: `DOCS_WIKI_ALLOW_STRAY=1`.

### Skill contract

Every SKILL.md follows the standard contract: frontmatter (`name`, `description`, `version`, `last_reviewed`, `owns`, `defers_to`, `user_invocable`) + 10-section body.

### Explicit boundary (unchanged from scaffold)

**Wiki-to-memory sync remains out of scope.** This plugin only writes, organises, validates, and audits the wiki itself. Synchronising wiki content into long-term Claude memory is a separate future plugin.

### Safety rules baked in

1. Push-approval gate (hook) — refuses `git push` from a wiki repo without per-session approval.
2. Force-push refusal — always blocked, even with approval.
3. Diff-preview-before-write — every wiki file write surfaces the diff and waits for confirmation.
4. Stray-docs detection (hook) — refuses new files in stray docs/ folders when a wiki exists; warns on edits.
5. Filename-collision refusal (GitHub Wiki) — `/wiki-init` and `/wiki-new` refuse to create or populate colliding basenames.
6. No silent classification (drift) — every discrepancy ends at "Direction (NOT applied)".
7. Retired-folder awareness — folders the user has marked archived are never flagged as drift or stray.
8. Secret scan before write — proposed wiki content is scanned for tokens / PII before write; refused if detected.

### Adapter inputs (provided at `/wiki-init`, cached to `.docs-wiki.local.json`)

- `wikiPath` — absolute path to the wiki repo / folder.
- `wikiFlavour` — github-wiki | gitlab-wiki | azure-devops-wiki | mkdocs-tree.
- `owner` / `repo` — for GitHub Wiki URL construction.
- `sourceOfTruthRoots` — folders that authoritatively describe runtime behavior (used by drift sweep).
- `retiredFolders` — folders deliberately archived (default `_archived/`, `_legacy/`, `_deprecated/`, `historical/`).
- `exceptions` — paths legitimately allowed alongside the wiki (e.g., auto-generated API docs).
- `sidebarStyle` — explicit (default) or auto.

### Validation

- `python validate_plugin.py docs-wiki-plugin` → 0 errors.
- Genericness sweep — grep over all skill / command / agent / hook files for `aqraboon|beneficiar|coupon|qid|qatar|taqatfortechnology|AdminUser|AppConfig|HELPDESK|SUPER_ADMIN|alaqraboon|indogate`: 0 hits.

### Out of scope (deferred to 0.3.0 — and permanent)

Deferred to 0.3.0:

- Polished GitLab / Azure DevOps Wiki adapters (currently `github-wiki` is the most-tested path; the other flavours are documented but less battle-tested).
- ADR numbering helper (currently the user supplies the NN).
- A `/wiki-archive <page>` command for one-step archive-with-cleanup-validation.
- Mermaid syntax linting beyond the rules in `wiki-mermaid` (currently rules are documented; mechanical linting deferred).

Permanently out of scope:

- Wiki-to-memory sync. Will be a separate future plugin.

## [0.1.0] — 2026-05-28 — Scaffold

Initial scaffold. No skill, command, agent, or hook content yet — those land in `0.2.0` (Phase 3).

### Added

- `.claude-plugin/plugin.json` — plugin manifest at v0.1.0.
- `README.md` — plugin documentation: status, planned skills/commands/agents, explicit out-of-scope (memory sync), wiki flavours supported, safety rules, adapter inputs.
- `CHANGELOG.md` — this file.
- `LICENSE` — MIT.

### Validation

- `python validate_plugin.py docs-wiki-plugin` → 0 errors.

### Out of scope (deferred to 0.2.0 — Phase 3)

- `skills/wiki-structure/`, `skills/wiki-authoring/`, `skills/wiki-mermaid/`, `skills/wiki-link-validation/`, `skills/wiki-code-vs-docs-discrepancy/`, `skills/wiki-safe-updates/`, `skills/wiki-vs-stray-docs/`.
- `commands/wiki-init.md`, `commands/wiki-audit.md`, `commands/wiki-update.md`, `commands/wiki-new.md`, `commands/wiki-drift.md`, `commands/wiki-sync-audit.md`.
- `agents/wiki-link-auditor.md`, `agents/wiki-cleanup-validator.md`, `agents/wiki-drift-reporter.md`.
- `hooks/hooks.json` (push-approval gate + stray-docs warning).

### Permanently out of scope

- Wiki-to-memory sync. Will be a separate future plugin.
