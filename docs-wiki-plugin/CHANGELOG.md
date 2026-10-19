# Changelog

All notable changes to `docs-wiki-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [0.11.0] - 2026-10-19

### Changed
- **Commands use bare verbs** (ECO-18): `/docs-wiki:init`, `new`, `update`, `audit`, `drift`, `sync-audit`, `swimlane`. The `wiki-*` names stay for one minor version as deprecated stubs that point to the new command; they will be removed in 0.12.0. Dropped the stale per-command `author` / `version` frontmatter.
- **One write policy** (WIKI-P1-02, X-5): `wiki-safe-updates` now holds a single policy that every command, skill and agent points to. Publishing (wiki push, live REST/MCP write, attachment upload, work-item write) only on the user's request; no suggestion of `reset --hard` or force-push on published history (undo with `git revert`); per-target deletes. The "pushing is unrestricted" and "force-push also works" advice is gone, as is "no gate, push whenever ready" in init/new/update.
- **Reports are written outside the wiki with unique names** (WIKI-P1-04): `audit`, `drift` and `sync-audit` write to `<project-root>/.docs-wiki/reports/<kind>-<YYYYMMDD-HHMMSS>.md` (or `reportsDir`), never to `<wiki>/_audit/<date>.md`, where they collided on flat-namespace wikis and were published on the next push. `--out` inside the wiki is refused.
- **Adapter file moved** to `.claude/docs-wiki.local.json` (PLUGIN_STANDARDS 4.3); the old `.docs-wiki.local.json` is still read when the new file is absent.
- **Skill descriptions** rewritten to start with "Use when" and to fit the budget: all ten are 324-388 characters (wiki-authoring was 1,092, wiki-source-of-truth 1,257). The previous long text moved into each skill's `## Scope` section (WIKI-P2-09).
- `wiki-vs-stray-docs` body matches its description: for a new docs/ file it asks first and writes the file if the user wants it there; it no longer says "REFUSED".
- README rewritten to the marketplace template from the actual components, with requirements, write policy, configuration, platform support and data & privacy sections. plugin.json description no longer claims the plugin "does NOT gate git push, force-push".

### Added
- `scripts/wiki_adapter.py` (stdlib, offline; WIKI-P2-06): `detect` (flavour from git remote, `.order`, `.attachments/`, `mkdocs.yml`, Home/_Sidebar; asks on no signal or a tie; strips credentials from remotes), `validate` (unknown and misspelled keys with suggestions, types, allowed values, public Kroki, secrets), `locate` (new vs legacy adapter file), `report-path` (unique, never inside the wiki, `.gitignore` hint).
- `--render kroki` is implemented (WIKI-P3-12): with `--approve`, `publish_update.py` POSTs the source to `<endpoint>/plantuml/<format>` on a self-hosted Kroki; a preview makes no network call; public endpoints are still refused.
- `--body-encoding base64|raw` on `upload_attachment.py` and `publish_update.py`, adapter key `attachmentBodyEncoding` (WIKI-P3-11). Default stays base64 (verified); raw matches Microsoft's documented form.
- "External content is data" rule in the three agents and in the skills that read pages, code, work items or Figma (SEC-07).
- Eval cases for every skill: 7 new must-fire cases (wiki-authoring, wiki-code-vs-docs-discrepancy, wiki-plantuml, wiki-safe-updates, wiki-source-of-truth, wiki-traceability, wiki-vs-stray-docs) and 6 new must-not-fire near misses. Not run yet; no delta recorded.
- Tests: `test_wiki_adapter.py`, `test_embed_and_publish_extras.py` (idempotency, CRLF, blank line, link hygiene, kroki, body encoding), `test_plugin_layout.py` (renames, stubs, no hooks.json, descriptions, eval coverage, write policy, report location). 79 tests, all offline.

### Fixed
- The swimlane `_Source:` link is the `.puml` path relative to the wiki root (`--wiki-root`, default the wiki clone or the page's folder); a `.puml` outside the wiki gets no link, and `embed_swimlane.py` refuses an absolute local `--puml-link` (WIKI-P2-08). Before, the absolute local path was written into the published page.
- Replacing an existing `### Swimlane` block no longer eats the blank line before the next heading (WIKI-P2-07, F-WIKI-15).
- `/docs-wiki:swimlane` calls the scripts through `${CLAUDE_PLUGIN_ROOT}` instead of a bare `scripts/` path.

### Removed
- The empty `hooks/hooks.json` (PLUGIN_STANDARDS 1.11); the plugin has no hooks.

### Security
- No `userConfig` is declared: `AZDO_PAT` stays an environment variable because its only consumer is a script Claude runs, which receives no plugin options, and passing it through a command would put the token in the conversation. `validate` flags any secret-looking key in the adapter file.

## [0.10.0] - 2026-10-19

### Changed
- **The PlantUML swimlane pipeline no longer needs PowerShell.** `render_puml.py` and `upload_attachment.py` (stdlib only) replace the `.ps1` helpers. Renderer discovery order: `--plantuml-jar`, `PLANTUML_JAR` (legacy `DOCS_WIKI_PLANTUML_JAR`), then `plantuml` on PATH. Java comes from `--java`, `DOCS_WIKI_JAVA`, `JAVA_HOME`, then PATH. If no renderer is found, the script prints install steps and exits 2 (audit WIKI-P1-05).
- The Azure attachment upload reads `AZDO_PAT` (never printed) and keeps the retry and verify-on-fail behaviour. The `--approve` gate is unchanged.
- README and SKILL.md document the requirements (Java 8+ and a PlantUML jar, or the plantuml CLI, or self-hosted Kroki) with Windows, macOS and Linux install steps.

## [0.9.0] - 2026-10-19

### Fixed
- **`publish_update.py` no longer acts before approval** (WIKI-P0-01). The
  Azure attachment upload, the GitHub image staging into the wiki clone and the
  page write (via `embed_swimlane.py`) all ran *before* the `--approve` check, so
  a "preview" had already published. The gate is now the first step after
  argument validation. Without `--approve` the run renders into a temp dir
  (deleted on exit), prints the page diff via `embed_swimlane.py --dry-run` and
  lists the pending actions — zero network calls, zero writes outside temp. With
  `--approve` it renders, uploads (azure) or stages (github), then writes the
  page. It still never commits or pushes.
- All argument checks (azure `--org/--project/--wiki-id`, github `--wiki-clone`,
  Kroki endpoint) now run before any command executes.
- README: removed the two PreToolUse hooks it documented (`hooks/hooks.json` has
  always been empty), command names now match the namespaced
  `/docs-wiki:wiki-*` form, `/docs-wiki:wiki-swimlane` describes the preview-first
  flow, `wiki-vs-stray-docs` is described as advisory (it never refuses a write),
  the version badge is current and the stale roadmap is replaced by the release
  history. Marketplace description: 10 skills + 7 commands (was "7 + 6") and no
  phantom push-gate / stray-docs hooks.

### Added
- `embed_swimlane.py --dry-run`: print the diff, write nothing.
- `tests/test_publish_update_gate.py` (offline, stdlib `unittest`): with every
  external command recorded and sockets patched to fail, a preview makes no
  upload, stages nothing and leaves the page byte-identical; an approved run
  uploads/stages and writes the page; invalid args fail before any command.
  Run with `python -m unittest discover -s tests -v`.

### Changed
- `publish_update.py` CLI behaviour: a run without `--approve` no longer leaves a
  rendered image next to the `.puml`, an uploaded attachment, a staged image or
  an edited page behind. Re-run with `--approve` to perform them.

## [0.8.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (3 must-fire cases + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-azure-wiki-broken-relative-link` targets `wiki-link-validation`
- `fires-on-github-wiki-filename-collision` targets `wiki-structure`
- `fires-on-render-complaint` targets `wiki-mermaid`
- `ignores-plain-markdown-question` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [0.8.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 10 skills (previously inert).

## [0.7.0] — 2026-06-22 — Build-any-wiki enhancement: hub-first IA, resolution-based links, single-master-swimlane, traceability

A single-owner enhancement across the wiki skills, distilled by a multi-agent analysis of a
real production Azure DevOps wiki session report. The goal: build any wiki with the best
structure and avoid the mistakes that session hit — above all the Azure link-resolution bug
where a path-existence audit false-passes while links are actually broken.

### Fixed (corrections)

- **`wiki-structure` (→ 0.4.0): Azure internal-link form was wrong.** The adapter told
  generators to use a relative `](/Page-Name)` link, but on Azure DevOps a dashed relative link
  to a **hyphen-titled** page resolves the hyphens as spaces and 404s **even though the API path
  exists**. Corrected to the **page-ID URL** form `.../_wiki/wikis/{WikiName}/{pageId}/{Slug}`
  (owner-confirmed), with "validate by resolution, not path existence."
- **`wiki-link-validation` (→ 0.4.0):** Scan 2 changed from "verify the target page exists" to
  "verify the target **resolves**"; Azure anchors are now validated with the declared Azure
  slug algorithm (no whitespace collapse) instead of reported `UNKNOWN`.
- **`wiki-safe-updates` (→ 1.1.0):** kept the GitHub-wiki git-push **advisory/unrestricted**
  posture; added only a **scoped** approval gate for live-wiki (REST/MCP) and Azure work-item
  writes, plus a per-target delete instruction.

### Added

- **`wiki-structure` (→ 0.4.0):** hub-first themed IA (parents are **real hub pages**, never
  empty folders; reader-facing section labels); a validated default structure template; Azure
  REST move/delete mechanics (`pagemoves` `newOrder` mandatory, REST-for-move/delete, tree omits
  page id, childless-delete, no auto-repoint on move).
- **`wiki-link-validation` (→ 0.4.0):** resolution-based verdict + `dashed-relative-on-hyphen-page`
  finding; a **read-failure gate** (never report "0 broken" over a partial scan); stale-reference
  and reachability/backlink scans; tree-namespace concept-collision; the Azure anchor-slug rule.
- **`wiki-mermaid` (→ 0.4.0):** the **single-master-swimlane** rule (one end-to-end swimlane, on
  the workflow hub, exactly once); the **diagram-altitude** rule (compact map on hubs / focused on
  journeys / full state machine on the owning spec page); reuse-the-project-palette; a
  no-business-meaning-change-via-diagram gate.
- **`wiki-authoring` (→ 0.4.0):** a **Hub-page** template and a **Workflow-journey-page** template
  (defers every rule to its owning spec page via an "authoritative detail" pointer); a
  recommended business/product page-set catalogue.
- **`wiki-source-of-truth` (→ 0.4.0):** the page-level single-source-of-truth rule
  (journey-view vs source-page separation), hub-is-not-authoritative, backlog-as-source-of-truth
  leakage detection, the navigation-only-traceability principle, and the
  reorganization-preserves-meaning stance.
- **`wiki-safe-updates` (→ 1.1.0):** plan-first/dry-run preview for multi-step restructures;
  deterministic content-preserving edits (fetch → targeted string-replace → re-fetch verify);
  governed safe move/rename/delete + link-repoint ordering (specific-child-first, bare-parent-last);
  pre-write validation of generated datasets; the Azure visible-heading idempotency rule.
- **NEW skill `wiki-traceability` (0.1.0):** the navigation-only bidirectional model linking
  backlog work items ↔ wiki workflow pages ↔ Figma design nodes ↔ spec pages, plus the central
  Epic→Feature Traceability Matrix. Owns the Figma node URL format + colon→dash conversion, the
  **harvest-don't-invent** rule, the `&t=` share-token omission (hard safety gate), exact/lane/pending
  coverage, visible-heading idempotency, and Description-only PBI patching.

### Architecture

- Single-owner layering preserved: cross-cutting facts (page-ID URL form, resolution-based audit,
  single-master-swimlane placement, navigation-only principle, plan-first governance) each have one
  owning skill; the others reference by name. `defers_to`/Cross-references updated across all seven.

## [0.6.1] — 2026-06-22 — wiki-plantuml fixes (post-review of #17)

Fixes from an independent code review of the 0.6.0 swimlane feature.

### Fixed

- **`upload_attachment.ps1` — verify-on-500 used a non-existent endpoint.** The Wiki
  Attachments API (7.1) is **Create-only (no GET-by-name)**, so the old `Test-AttachmentExists`
  GET always failed and would misreport a 500-but-succeeded upload as a hard failure. Now
  verifies by **re-PUTting the same name** (idempotent — a new ETag version, not an error).
- **`embed_swimlane.py` — silent CRLF→LF conversion.** Read with newline-translation but
  wrote with `newline=""`, converting a CRLF wiki page to LF on the first run (huge spurious
  diff on Windows clones). Now reads raw, preserves the page's line endings, and writes them
  back unchanged.
- **`render_puml.ps1` — colour lint false-positive.** The deprecated-prefix-colour check now
  requires a trailing `;` so `<style>` / skinparam hex lines don't trip it.

### Notes

- The Azure attachment **base64 body** is retained (the verified-working path on this org's
  instance per the prototype); the script documents the raw-octet-stream escape hatch for
  instances where base64 renders broken. The colour-syntax guidance is softened from a
  version-dated breaking-change claim to "the prefix form is unsupported in activity-beta —
  render-verify on your build."

## [0.6.0] — 2026-06-22 — PlantUML BPMN swimlanes (the diagram Mermaid can't draw)

Adds a peer to `wiki-mermaid` for **actor-lane / BPMN-pool swimlanes** — the one diagram
class no wiki renders natively from text and Mermaid has no primitive for. Backed by an
`ultracode` multi-agent research pass that compared PlantUML, D2, bpmn.io, Kroki, and
Mermaid across both GitHub and Azure DevOps wikis.

### Added

- **`skills/wiki-plantuml`** (skill 0.1.0) — BPMN-style swimlane authoring in **PlantUML
  activity-beta** (the `.puml` is the diffable source). Owns: the scope boundary (PlantUML
  = swimlanes only; Mermaid stays authoritative for flowchart/sequence/state), the
  `|Actor|`-lane + one-system-lane rules, the **end-of-line suffix-stereotype colour rule**
  (`:text; <<#RRGGBB>>`; the prefix `#color:` form is deprecated in 1.2026.x), the
  four-class palette, and the **per-flavour render → attach → embed pipeline**.
- **`commands/wiki-swimlane.md`** — `/wiki-swimlane <page> [--render local|kroki] [--format svg|png]`.
- **`skills/wiki-plantuml/scripts/`** — `render_puml.ps1` (pinned `1.2026.x` jar, lints the
  deprecated colour + unbalanced gateways, `PLANTUML_LIMIT_SIZE`), `upload_attachment.ps1`
  (Azure `/.attachments` REST; **PAT from `$env:AZDO_PAT`, never echoed; base64 body;
  verify-on-HTTP-500**), `embed_swimlane.py` (idempotent `### Swimlane` block), and
  `publish_update.py` (render → attach/stage → embed → diff-preview → `--approve` gate).

### Pipeline facts encoded (from the research)

- **PlantUML never renders natively** on GitHub Wiki or Azure DevOps Wiki → pre-render to an
  image and embed. **GitHub** = commit the image into the `OWNER/REPO.wiki.git` sibling repo,
  reference with a leading-slash wiki-link `[[/images/x.png|alt]]`. **Azure** = PUT to
  `/.attachments` (base64 body, `api-version=7.1`), reference root-relative
  `![alt](/.attachments/x.png)`. **GitLab/MkDocs** render the same `.puml` natively (fence /
  build-time) — no attach.
- **PNG is the safe default**, not SVG: GitHub strips inline `<svg>`/`data:` URIs and the
  Camo proxy blocks hotlinked SVG; Azure's supported attachment list is PNG/GIF/JPEG/ICO and
  it sanitizes SVG. SVG only where verified per-instance.
- **Maven "latest" trap:** the 2012 build `8059` numeric-sorts above the `1.20xx` date-scheme
  releases — pin a `1.2026.x` jar. activity-beta needs **no Graphviz**.
- Privacy: local-jar render is the default; **public `kroki.io` is refused** (paste-leak) —
  self-hosted Kroki only.

### Changed

- `skills/wiki-mermaid` (→ 0.4.0) — added a "skip → use `wiki-plantuml`" rule for swimlanes
  and a cross-reference; `wiki-authoring`, `wiki-safe-updates`, `wiki-structure` cross-linked
  to the new skill (diagram-order guidance, governed publish, artifact placement).
- `plugin.json` 0.5.0 → 0.6.0; keywords add `azure-devops-wiki`, `plantuml`, `swimlane`, `bpmn`.

## [0.5.0] — 2026-06-20 — Remove all restrictions: non-blocking GitHub-wiki helper

The plugin no longer blocks, gates, or restricts any git/file operation. It is now a
purely advisory helper for working on a wiki. Wiki-quality safeguards that prevent a
*broken/unrenderable* wiki (basename-collision and PII checks) are kept as help, not gates.

### Removed

- **Both blocking hooks.** `hooks/hooks.json` is now empty (`{"hooks":{}}`). Deleted
  `hooks/pre_wiki_push_gate.py` (the wiki `git push` approval gate, incl. force-push
  refusal) and `hooks/pre_stray_docs_check.py` (the Write/Edit stray-docs block). No
  hook fires; `DOCS_WIKI_PUSH_APPROVED` / `DOCS_WIKI_ALLOW_STRAY` are no longer needed.
- The whole env-var-set → restart → push → unset approval dance is gone.

### Changed

- `skills/wiki-safe-updates` rewritten as **optional, non-blocking tips** (diff preview
  for big overwrites, revert-over-reset rollback, one-purpose commits, retired-folder
  awareness, optional pre-deletion reference check). Removed the push-approval gate,
  the "no force-push ever" rule, the diff-preview-non-negotiable mandate, and the
  pre-deletion gate. `git push` / force-push are explicitly unrestricted. (skill 1.0.0)
- `skills/wiki-vs-stray-docs` description reframed from "Refuse to create stray docs" to
  advisory surfacing only (it already only surfaced; the framing now matches).
- `plugin.json`, `README.md`, and `commands/{wiki-init,wiki-new,wiki-update,wiki-audit}.md`
  updated to drop "push-approval gate applies" / "block push" / "mandatory" wording.

### Kept (help, not restriction)

- Filename-uniqueness (basename-collision) and PII/secret checks — these prevent a wiki
  GitHub cannot render or a leak, and never block your push.
- Link-validation and code-vs-wiki drift audits remain advisory reports.

### Validation

- `python validate_plugin.py docs-wiki-plugin` → exit 0, 0 errors.
- `python -m json.tool hooks/hooks.json` → valid (empty hooks).

## [0.4.0] — 2026-06-13 — Anchor rules + safe doc deletion + neutralization discipline

### Added

- `wiki-link-validation` — heading-ANCHOR slug rules (lowercase; drop punctuation outside `a-z 0-9` space hyphen; spaces → hyphens uncollapsed; trim leading/trailing hyphens, keep internal multi-hyphens; de-dup suffix) plus a sixth scan that detects broken section-anchor links. New rule: a link anchor never starts with a hyphen.
- `wiki-safe-updates` — safe-doc-deletion gate: before removing a docs tree / page / section, a capture-check (every named final decision genuinely captured in the source-of-truth wiki; scattered-but-unnamed = migration gap = NOT captured) and a cross-reference sweep (wiki pages, code comments, CI workflows, root README / instruction files, build/coverage artifacts) categorizing every hit as rewrite / accept-stale / delete-with-target. New `references/safe-doc-deletion.md`.
- `wiki-authoring` + `wiki-source-of-truth` — tenant/client neutralization discipline: classify each name hit as active-target prose (neutralize to a deterministic placeholder), legacy reference / provenance (preserve byte-identical), or operator/platform context (preserve) — never a blind global find/replace. New `references/neutralization-discipline.md` (under `wiki-authoring`); `wiki-source-of-truth` supplies the current-state-vs-provenance judgement.

### Validation

- `python validate_plugin.py docs-wiki-plugin` -> 0 errors.
- Genericness sweep: 0 project-specific tokens; example name `AcmeCorp` used only as a labeled placeholder in neutralization examples.

## [0.3.0] — 2026-05-31 — Source-of-truth doctrine + page templates

### Added

- `wiki-source-of-truth` skill — declare a knowledge-layer order; separate current-state vs target docs; distrust stale checkboxes; flag config-constant drift; resolve code-vs-wiki conflicts as doc fixes.
- `templates/` — generic, placeholder-only Wiki page templates: sop, runbook, role-guide, user-manual, workflow (Mermaid), release-handover, onboarding.

### Validation

- `python validate_plugin.py docs-wiki-plugin` -> 0 errors.
- Genericness sweep: 0 project-specific tokens outside labeled examples.

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
- Genericness sweep — grep over all skill / command / agent / hook files for known client/project tokens: 0 hits.

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
