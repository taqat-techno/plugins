# react-kit

![Version](https://img.shields.io/badge/version-0.5.0-blue.svg)
![Status](https://img.shields.io/badge/status-functional-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Reusable patterns for building and auditing React / Next.js applications — with a flexible, Odoo-inspired admin-panel toolkit.

`react-kit` packages the recurring engineering decisions of React / Next.js work — data-fetching and async UI states, lint/diagnostic triage, React 19 migration — plus a **flexible admin-panel methodology** that guides an agent to plan and build list, tree, kanban, form, and dashboard views from one consistent architecture. It is generic: entity names, roles, APIs, and libraries are project-supplied adapter inputs, never baked in. Admin panels are a major capability here, not the whole plugin.

> **Inspiration, not implementation:** the admin-view model draws on Odoo's "one resource, many views" idea (list / tree / kanban / form / dashboard) but targets idiomatic React / Next.js — it does not rebuild Odoo.

## What this plugin owns

### General React / Next.js skills

| Skill | Owns |
|---|---|
| `react-lint-triage` | Treat analyzer findings as hypotheses; classify safe-mechanical / needs-judgment / false-positive / forbidden-zone; never chase the score; false-positive catalog (incl. admin-panel triage); lint the new file by path before push |
| `frontend-build-traps` | Deterministic recovery for build/dev-server/test/CI traps where the symptom layer ≠ cause layer — Turbopack HMR stale-module 500 full reset, vitest/rolldown-vite jsx-preserve (oxc not esbuild), lockfile CI-PM-major mismatch, TipTap `addAttributes` casing + `renderHTML` serialization scope, ORM client/schema drift via mtime, lint-the-new-file-before-push |
| `data-fetching-states` | The status→state contract (loading / empty / no-results / access-required / forbidden / not-found / business-rule / error / partial / stale); never a silent empty shell; admin-panel examples |
| `react19-migration` | forwardRef→ref-prop, `useContext`→`use`, server/client metadata split; behavior-preserving, type-check-gated |

### Admin-panel skills

**Plan & choose:**

| Skill | Owns |
|---|---|
| `admin-panel-architecture` | Design-before-coding: project adapter, route structure, navigation-builder model, role/menu model, **view registry**, data/state + action/workflow contracts, component inventory, plan template |
| `admin-view-patterns` | The **view-type chooser** — when to use list / tree / kanban / form / dashboard / settings / detail-drawer / import-export / audit; routes to the owning skill (does not re-implement) |

**Build views:**

| Skill | Owns |
|---|---|
| `admin-shell` | Sidebar + header + layout shell, responsive collapse + mobile overlay, longest-prefix active-route, i18n context, route-guard composition |
| `admin-crud` | List / table / detail / filter / pagination **and** tree / nested-list / parent-child hierarchy (expandable rows, lazy children, nested-route detail) |
| `admin-kanban-workflow` | Kanban / board view **and** the workflow state machine — columns from a project state set, collapsible columns, role-gated + validated transitions, audit-on-move (states never hardcoded) |
| `admin-forms` | Fields, inline + server validation, grouped sections + tabs, relation pickers, file attachments, dirty-state, save / cancel / reset / archive / delete, read-only-vs-editable, audit metadata |
| `admin-dashboard-overview` | KPI / overview cards, role-aware metrics, quick actions, recent-activity feed, data-freshness, no-data-vs-failed-KPI states, chart-vs-table balance |

**Cross-cutting rules:**

| Skill | Owns |
|---|---|
| `admin-roles-and-permissions` | Role/module-aware menus + actions + field editability, "UI hide is NOT authorization", PII masking, audit visibility, paired UI/API gates |
| `admin-dangerous-actions` | Confirmation patterns for destructive operations (friction proportional to blast radius) |
| `admin-import-export` | Upload→preview→commit, row caps, typed per-row errors, idempotency, no auto-create |
| `admin-states` | Loading / error / empty / no-results / partial-error **display** conventions |
| `admin-rtl-ltr` | Direction-aware utilities, locale-driven layout direction |

### References (progressive disclosure, under the owning skill)

`admin-panel-architecture/references/`: `admin-panel-adapter.md`, `admin-view-registry.md`, `admin-state-contract.md` · `admin-crud/references/admin-list-tree-pattern.md` · `admin-kanban-workflow/references/`: `admin-kanban-pattern.md`, `admin-action-workflow-pattern.md` · `admin-forms/references/admin-form-pattern.md` · `admin-dashboard-overview/references/admin-dashboard-pattern.md`.

### Commands

| Command | Purpose |
|---|---|
| `/admin-scaffold` | Generate a CRUD page skeleton from a model description |
| `/admin-audit` | Audit an existing admin route against the plugin's skill rules |
| `/admin-role-matrix` | Generate or validate a role/permission matrix |

### Agents

| Agent | Purpose |
|---|---|
| `admin-route-auditor` | Read-only scan of one admin route for missing role gates, missing audit-log, unmasked PII, missing confirmation on destructive actions |

## Framework scope

| Tier | Frameworks |
|---|---|
| Primary | React 18+, Next.js 13+ App Router |
| Secondary | Remix, Vite + React, Pages Router |
| Out of scope | Django admin, Laravel Nova, Odoo backend, Vue/Svelte/Angular (use [`qa-browser`](../qa-browser-plugin/README.md) to TEST those, not to author them) |

## How react-kit fits with other plugins

- **Aesthetics / visual design** → the official `frontend-design` plugin owns net-new visual style. react-kit owns **structure, state, CRUD, views, and workflow methodology**, not the look.
- **Testing the running UI** → `qa-browser` (layered over the official Playwright MCP) verifies roles, RBAC, and that the API enforces what the UI hides.
- **Docs / SOPs** → `docs-wiki`.
- **Environment problems** → `claude-env-doctor`.

## Adapter inputs (asked the first time you invoke a command)

The plugin makes **no assumptions** about your project. The first invocation asks for: admin base path; role/module model + level semantics; auth + audit helper imports; data-fetching library; UI/component library + status-badge palette; PII field list + masking rule; RTL languages; import format. Answers are cached locally (gitignored), never committed.

## What this plugin deliberately does NOT do

- Define your business domain models, role names, or PII fields.
- Replace your auth / authorization. UI hide is **not** authorization — backend re-checks always required.
- Replace API-level access control (see `qa-browser`).
- Hardcode any workflow states — your state set is an adapter input.

## Roadmap

| Version | Scope |
|---|---|
| `0.1.0` | Scaffold, manifest, marketplace registration |
| `0.2.0` | 8 admin skills + 3 commands + 1 agent |
| `0.3.0` | Renamed `react-admin-kit`→`react-kit`; added `react-lint-triage`, `data-fetching-states`, `react19-migration` |
| `0.4.0` | Flexible admin **view patterns** — `admin-panel-architecture`, `admin-view-patterns`, `admin-kanban-workflow`, `admin-dashboard-overview`; tree/nested + form-tabs/relations/attachments enhancements; 8 reference docs |
| `0.5.0` (this release) | `frontend-build-traps` skill — deterministic recovery for HMR stale-module 500s, vitest/rolldown-vite jsx-preserve, lockfile PM-major mismatch, TipTap attributes, ORM client/schema drift; `react-lint-triage` gains the lint-the-new-file-before-push rule |
| `1.0.0` | First stable release after real-project shakedown |

## License

MIT. See [`LICENSE`](./LICENSE).

## Author

TAQAT Techno · [github.com/taqat-techno](https://github.com/taqat-techno) · `info@taqatechno.com`
