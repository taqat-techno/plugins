# react-kit

![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)
![Status](https://img.shields.io/badge/status-functional-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Reusable patterns for building and auditing React / Next.js applications.

`react-kit` packages the recurring engineering decisions of React / Next.js work — data-fetching and async UI states, lint/diagnostic triage, React 19 migration, plus a full admin-panel toolkit (sidebar shell, CRUD list/detail/filter shape, role-aware menus, dangerous-action confirmations, import/export safety, RTL/LTR utilities) — into a single skill set that any project can pick up without dragging in a specific business domain. Admin panels are one capability here, not the whole plugin.

## What this plugin owns

### Skills (under `skills/`)

**General React / Next.js skills** (apply to any app):

| Skill | Owns |
|---|---|
| `react-lint-triage` | Reading and prioritizing ESLint / TypeScript / build diagnostics, grouping by root cause, safe-fix vs. needs-review classification |
| `data-fetching-states` | Loading / error / empty / success state machines, async boundaries, cache + revalidation patterns across client and server components |
| `react19-migration` | Migrating to React 19 — Actions, `use`, ref-as-prop, removed APIs, codemods, and incremental upgrade strategy |

**Admin-panel skills** (one capability of the kit):

| Skill | Owns |
|---|---|
| `admin-shell` | Sidebar + header + layout shell, i18n context, language toggle, persistent locale, route guard composition |
| `admin-crud` | List / table / detail / filter / pagination patterns |
| `admin-forms` | Field components, validation, row actions, bulk actions |
| `admin-roles-and-permissions` | Role-aware menus, "UI hide is NOT authorization" rule, PII masking, audit visibility |
| `admin-dangerous-actions` | Confirmation dialog patterns for destructive operations |
| `admin-import-export` | Preview, row caps, typed errors, per-row report, idempotency, no-auto-create |
| `admin-states` | Loading / error / empty state conventions |
| `admin-rtl-ltr` | Direction-aware utilities, locale-driven layout direction |

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

### Hooks (deferred to v0.3.0)

`PreToolUse` reminder on `Write|Edit` matching `admin/**` paths is planned for v0.3.0. Will be opt-in and configurable in `hooks/hooks.json`.

## Framework scope

| Tier | Frameworks |
|---|---|
| Primary | React 18+, Next.js 13+ App Router |
| Secondary | Remix, Vite + React, Pages Router |
| Out of scope | Django admin, Laravel Nova, Odoo backend, Vue/Svelte/Angular (use [`qa-browser`](../qa-browser-plugin/README.md) to TEST those, but not to author them) |

## Adapter inputs (asked the first time you invoke a command)

The plugin makes **no assumptions** about your project. The first invocation asks for:

1. Admin base path (e.g. `app/admin`, `src/admin`, `pages/admin`).
2. i18n provider location, or "none".
3. Role list + a short brief on which roles can do what.
4. PII field list (names + masking rule).
5. Auth helper import (e.g. `getServerSession`, `getUser`, a custom one).
6. Audit-log helper import, or "none".
7. RTL languages list, or "none".
8. Import format (CSV / Excel / JSON).

Adapter answers are cached locally (not committed) so you don't re-answer every time.

## What this plugin deliberately does NOT do

- Define your business domain models, role names, or PII fields.
- Replace your auth / authorization. UI hide is **not** authorization — backend re-checks always required.
- Replace API-level access control. See [`qa-browser`](../qa-browser-plugin/README.md) for verifying that the API actually enforces what the UI hides.
- Document the wiki / SOPs / runbooks that explain admin operations. See [`docs-wiki`](../docs-wiki-plugin/README.md) for that.

## Installation

This plugin is published as part of the `taqat-techno-plugins` marketplace. To install:

1. Open Claude Code.
2. Run `/plugins`.
3. Click **Add Marketplace** and enter `https://github.com/taqat-techno/plugins.git` (skip if already installed).
4. Find **react-kit** and click **Install**.

## Roadmap

| Version | Scope |
|---|---|
| `0.1.0` | Scaffold, manifest, marketplace registration, README, CHANGELOG, LICENSE |
| `0.2.0` (this release) | All 8 skills + 3 commands + 1 agent |
| `0.3.0` | End-to-end example admin built against the skills; optional `hooks/hooks.json` |
| `1.0.0` | First stable release after real-project shakedown |

## License

MIT. See [`LICENSE`](./LICENSE).

## Author

TAQAT Techno · [github.com/taqat-techno](https://github.com/taqat-techno) · `info@taqatechno.com`
