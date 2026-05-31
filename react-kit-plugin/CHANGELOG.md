# Changelog

All notable changes to `react-kit-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

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
- Genericness sweep — grep over all skill / command / agent files for `aqraboon|beneficiar|coupon|qid|qatar|taqat|AdminUser|AppConfig|HELPDESK|MANAGER|SUPER_ADMIN`: 0 hits outside example-block contexts.

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
