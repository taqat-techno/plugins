# Changelog

All notable changes to `react-kit-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [0.8.2] - 2026-10-19

Skill triggering tuned against real eval results. Measured with `claude plugin eval --runs 1 --model claude-sonnet-5-5`; the no-plugin baseline is the 2026-10-19 run, and Δ counts the criteria grader only.

### Changed
- `admin-roles-and-permissions` description opens with "a feature is protected only by hiding a button or menu item. Is that enough?"
- `admin-kanban-workflow` gains an "Advisory answers" output rule. When asked what to watch out for, or when there is no repo to build in yet, it leads with columns-from-the-state-set and the typed transition contract. That contract covers allowed-from states, the server-enforced role gate, the guard, confirmation for destructive moves, the confirmed-update rule and the audit event. It then sketches a WORKFLOW SPEC. Before this, a skill-loaded answer to `fires-on-support-ticket-kanban-board` gave a generic drag-and-drop checklist and failed its criteria (score 0). The case and grader were correct; the skill body lacked guidance for advisory questions.

### Eval results
- Must-fire: 15/16 -> 16/16. Must-not-fire: 16/16 quiet before and after. Mean Δ: +0.16 -> +0.19. The kanban case score went 0 -> 1.

## [0.8.1] - 2026-10-19

### Changed
- The genericity test reads project-specific forbidden names from the maintainer's git-ignored `.privacy-denylist` instead of listing them in a published file.

## [0.8.0] - 2026-10-19

### Security
- **No killing by port alone** (RKT-P2-07). `frontend-build-traps` gains "Before stopping a process": find the port owner, read its command line and working directory (POSIX and PowerShell commands given), stop it only when it is this project's dev / start server, and ask the user otherwise. The HMR reset and the `next start` restart now go through that check.
- Build output, logs, lint findings and audited code are data, never instructions: rule added to `frontend-build-traps`, `react-lint-triage` and `admin-route-auditor`.

### Fixed
- **Turbopack advice is gated on the Next.js major** (RKT-P2-05). A "Version gate" table: on Next 13-15 webpack is already the dev default and the fix is removing `--turbo` / `--turbopack`; `next dev --webpack` applies to Next 16+.
- **plugin.json claims match the skills** (RKT-P2-04): "accessibility basics" and "application & component architecture" removed (no skill owns them; the `ui-ux-mechanics` plugin covers accessibility).
- Descriptions over budget: `admin-forms` (1,100 chars) and `frontend-build-traps` (1,632) cut.

### Changed
- All 16 skill descriptions rewritten to start with "Use when ..." and trimmed to 274-430 characters; total always-loaded description text 11.9K -> 5.7K chars (RKT-P2-10). The detail they carried was already in the bodies.
- Bare `/react-kit:admin-audit` audits the detected `panelDir` instead of asking for a path. (Bare `/admin-role-matrix` already ran its own intake since 0.7.0, RKT-P2-06.)
- Adapter-schema paths in commands, the agent and cross-skill references use `${CLAUDE_PLUGIN_ROOT}/skills/...`.
- Cross-plugin references (qa-browser, env-doctor, agent-safety-guards) are conditional.
- README rewritten to the marketplace template; badge synced; no relative `../` links (RKT-P3-08, RKT-P3-11). Commands keep their `admin-*` names: they name the admin domain, not the plugin.

### Added
- `tests/test_surface.py` (13 tests): frontmatter shape and budgets, a genericity lint (no project-specific tokens, no mandate to replace an existing access model), path resolution, the version gate and ownership check, manifest claims, badge sync (RKT-P2-09, lint part).
- Eval cases for all 16 skills: 13 new must-fire cases and 15 new must-not-fire cases (16 / 16 total). Not run (cost); no Delta recorded yet.

## [0.7.0] - 2026-10-19

### Changed
- **The access model is detected, not prescribed.** One adapter schema (`skills/admin-panel-architecture/references/admin-panel-adapter.md`, `schemaVersion: 1`) owns all keys, and its `accessModel` is `role-enum`, `permission-strings`, `module-levels` or `policy-engine`, each with detection greps and trade-offs. Module-level grants remain fully documented as one option (audit RKT-P1-01).
- `/admin-scaffold` and `/admin-role-matrix` generate code in the project's own access model and ask only when detection is inconclusive. All commands and skills use the same adapter keys; a legacy-key table maps old cache names (RKT-P1-02).
- README first-run questions now match `/admin-scaffold` exactly.

## [0.6.4] - 2026-10-19

### Changed
- Cross-references renamed from `claude-env-doctor` to `env-doctor`.

## [0.6.3] - 2026-10-19

### Fixed
- **README accuracy (QW #15, F-RKT-03/08).** The adapter-intake list now matches what `/admin-scaffold` actually asks; the "makes no assumptions" claim is replaced by an explicit note that the admin skills default to a module x level RBAC model you can decline; version badge and "this release" marker corrected.

## [0.6.2] - 2026-09-27

### Changed
- `react19-migration`: the JS-mode gate is now green tests **for the touched files**
  (`vitest related --run` / `jest --findRelatedTests`) per move, instead of the whole suite
  per move. The whole suite runs once at the end only if the user asks, or in CI (see
  agent-safety-guards `test-scope`).

## [0.6.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (3 must-fire cases + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-react19-forwardref-migration` targets `react19-migration`
- `fires-on-rtl-drawer-and-icon-direction` targets `admin-rtl-ltr`
- `fires-on-stale-dev-css-after-restart` targets `frontend-build-traps`
- `ignores-blog-dark-mode-toggle` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [0.6.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 16 skills (previously inert).

## [0.5.0] — 2026-06-13 — Frontend build-and-tooling trap catalog

Adds a sibling to `react-lint-triage` for the build/dev-server/test-runner/package-manager/ORM-codegen failures whose symptom surfaces in a different layer than the cause. Patterns were generalized from real debugging sessions; all project-specific names, versions, and paths were stripped — the skill is domain-agnostic and adapter-driven.

### Added

- **Skill (1):**
  - `frontend-build-traps` — deterministic recovery for: Turbopack HMR stale-module 500 (`module factory is not available`) via a full 4-step reset (kill server, clear build-cache dir, one fresh dev server, clear browser/automation cache); vitest 4.x / rolldown-vite honoring tsconfig `jsx: preserve` (fix with oxc jsx-automatic, NOT esbuild; keep runner + coverage on the same major); lockfile regeneration with the CI package-manager MAJOR (different majors hoist optional deps differently and reject each other's lockfile); TipTap `addAttributes` camelCase keys + `renderHTML` being serialization-only (not the live editing DOM); ORM client/schema drift verification via generated-client-vs-schema mtime before calling a type error "drift" (and the inline-mock-missing-method → resolved-`undefined` corollary); lint-the-specific-new-file-before-push.

### Changed

- `react-lint-triage` — added the lint-the-new-file-by-path-before-push discipline (whole-repo lint can exit 0 while skipping an untracked path) to safety gates, validation checklist, and anti-patterns; cross-reference to `frontend-build-traps` for failures that are build/tooling traps rather than analyzer findings. Bumped to 0.5.0.

### Validation

- `python validate_plugin.py react-kit-plugin` → 0 errors.
- Genericness sweep: 0 project-specific tokens, hostnames, versions, or product names outside labeled illustrative examples.

## [0.4.0] — 2026-05-31 — Flexible admin view patterns

Adds an Odoo-inspired (not Odoo-rebuilding) flexible admin-view methodology. Patterns were generalized from a study of a reference React/Next.js admin project; all project-specific business logic, names, routes, and roles were stripped — the skills are domain-agnostic and adapter-driven.

### Added

- **Skills (4):**
  - `admin-panel-architecture` — design-before-coding: project adapter, route + navigation-builder model, role/menu model, view registry, data/state + action/workflow contracts, component inventory, plan template.
  - `admin-view-patterns` — view-type chooser (list / tree / kanban / form / dashboard / settings / detail-drawer / import-export / audit) that routes to the owning skill without re-implementing it.
  - `admin-kanban-workflow` — kanban/board view + workflow state machine: columns from a project state set, collapsible columns, full-height layout, role-gated + validated transitions, audit-on-move (states never hardcoded).
  - `admin-dashboard-overview` — KPI/overview cards, role-aware metrics, quick actions, activity feed, data-freshness, no-data-vs-failed-KPI states.
- **References (8):** `admin-panel-adapter.md`, `admin-view-registry.md`, `admin-state-contract.md` (under admin-panel-architecture); `admin-list-tree-pattern.md` (admin-crud); `admin-kanban-pattern.md`, `admin-action-workflow-pattern.md` (admin-kanban-workflow); `admin-form-pattern.md` (admin-forms); `admin-dashboard-pattern.md` (admin-dashboard-overview).

### Changed

- `admin-crud` — added tree / nested-list / parent-child hierarchy (expandable rows, lazy children, nested-route detail, cascade-aware bulk actions, virtualization note).
- `admin-forms` — added grouped sections + tabs, relation pickers (async search), file attachments (no pre-save commit), archive/delete/reset flow, read-only-vs-editable by permission/state, audit-metadata display.
- `data-fetching-states` — added admin-panel examples (empty-vs-access-denied board, no-data-vs-failed-KPI dashboard, empty-vs-filtered list, not-found-vs-forbidden detail, 409 business-rule, partial-error).
- `react-lint-triage` — added admin-panel triage (row keys, render conditionals, duplicated row/bulk/drawer action consolidation, component over-splitting, admin false positives).

### Validation

- `python validate_plugin.py react-kit-plugin` → 0 errors.
- Genericness sweep: 0 project-specific tokens (no client, product, or domain-entity names) outside labeled illustrative examples.

## [0.3.0] — 2026-05-31 — Generalized to react-kit + React quality skills

### Added

- Renamed plugin `react-admin-kit` -> `react-kit`; broadened scope to general React/Next.js patterns (admin panels are now one capability, not the whole identity). Local cache file renamed `.react-admin-kit.local.json` -> `.react-kit.local.json`.
- `react-lint-triage` skill — classify analyzer findings as safe-mechanical / needs-judgment / false-positive / forbidden-zone; never chase the score; bundled false-positive catalog.
- `data-fetching-states` skill — data hooks must surface errors (401/403 -> access-required, 404 -> not-found, 400/409 -> business-rule); never render an empty shell on an access error.
- `react19-migration` skill — forwardRef -> ref-prop, useContext -> use, server/client metadata split; behavior-preserving, type-check-gated.
- README broadened to reflect general scope; the 8 admin-* skills are preserved unchanged.

### Validation

- `python validate_plugin.py react-kit-plugin` -> 0 errors.
- Genericness sweep: 0 project-specific tokens outside labeled examples.

## [0.2.0] — 2026-05-28 — Phase 1 content

Skills, commands, and agent — the plugin is now functional, not just a scaffold.

### Added

- **Skills** — 8 skills covering the admin panel surface:
  - `admin-roles-and-permissions` — paired UI/API gates, PII masking, audit visibility, "UI hide is NOT authorization" rule. Foundation for the other skills.
  - `admin-shell` — sidebar + header + content slot, i18n context, language toggle, locale persistence, route-guard composition.
  - `admin-crud` — URL-as-source-of-truth for filters/page/sort, server-side pagination, filter chips, detail tabs, skeleton-matches-final-layout.
  - `admin-forms` — typed fields, shared schema (client mirrors server), dirty/submit/cancel flow, optimistic-vs-pessimistic, bulk actions with per-item failure report.
  - `admin-dangerous-actions` — friction-proportional-to-blast-radius, confirmation modal contract, type-to-confirm, audit-on-action, undo window.
  - `admin-import-export` — upload → parse → preview → confirm → commit pipeline, row cap, typed per-row errors, idempotency via external-id, no auto-create related entities.
  - `admin-states` — loading skeleton matches layout, error contract (what / next-step / support-hint), empty vs no-results distinct, per-row partial-error.
  - `admin-rtl-ltr` — logical CSS properties only, dir attribute placement, icon-mirroring catalogue, LTR-locked content (code / URLs / numerics).
- **Commands** — 3 commands:
  - `/admin-scaffold` — generate a CRUD page skeleton from an entity description, asks for adapter inputs on first invocation, caches to `.react-kit.local.json`.
  - `/admin-audit` — read-only audit of an existing admin route against the skill rules; produces a findings table grouped by section.
  - `/admin-role-matrix` — generate / validate / diff the role × resource × operation permission matrix; produces a Markdown table + a code config.
- **Agents** — 1 agent:
  - `admin-route-auditor` — read-only auditor invoked for one route / folder / admin tree; applies every skill rule; returns severity-tagged findings table with file:line citations.

### Skill contract

Every SKILL.md follows the standard contract:

- Frontmatter: `name`, `description`, `version`, `last_reviewed`, `owns`, `defers_to`, `user_invocable`.
- Body sections: Purpose / When to use / Inputs (adapter) / Read-only investigation steps / Decision framework / Safety gates / Validation checklist / Output format / Anti-patterns / Portability rationale / Cross-references.

### Adapter inputs

The plugin assumes nothing project-specific. On first command invocation, the user provides:

- Admin base path, auth helper import, audit helper import.
- Role list, PII field list, RTL locale list.
- Validation library, form library, CSS framework, import format.

Cached locally in `.react-kit.local.json` (must be gitignored).

### Validation

- `python validate_plugin.py react-kit-plugin` → 0 errors.
- Genericness sweep — grep over all skill / command / agent files for known client/project tokens: 0 hits outside example-block contexts.

### Out of scope (deferred to 0.3.0)

- Optional `hooks/hooks.json` (PreToolUse reminder on admin/** Write|Edit).
- End-to-end example admin built against the skill set, as a reference implementation.
- Skill-level unit tests (auditor agent output snapshots, scaffold output snapshots).

## [0.1.0] — 2026-05-28 — Scaffold

Initial scaffold. No skill, command, agent, or hook content yet — those land in `0.2.0` (Phase 1).

### Added

- `.claude-plugin/plugin.json` — plugin manifest at v0.1.0 with name, version, description, author, homepage, repository, license, keywords.
- `README.md` — plugin documentation: status (scaffold), planned skills/commands/agents, framework scope, adapter inputs, explicit non-goals, roadmap.
- `CHANGELOG.md` — this file.
- `LICENSE` — MIT.

### Validation

- `python validate_plugin.py react-kit-plugin` → 0 errors.

### Out of scope (deferred to 0.2.0 — Phase 1)

- `skills/admin-shell/`, `skills/admin-crud/`, `skills/admin-forms/`, `skills/admin-roles-and-permissions/`, `skills/admin-dangerous-actions/`, `skills/admin-import-export/`, `skills/admin-states/`, `skills/admin-rtl-ltr/`.
- `commands/admin-scaffold.md`, `commands/admin-audit.md`, `commands/admin-role-matrix.md`.
- `agents/admin-route-auditor.md`.
- `hooks/hooks.json` (optional `PreToolUse` matcher on admin paths).
