# react-kit

![Version](https://img.shields.io/badge/version-0.8.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## What it does

react-kit packages recurring React / Next.js engineering decisions as skills: async UI states and data-fetching error handling, lint and analyzer triage, React 19 migration, build-and-tooling trap recovery, and a methodology for admin panels (list, tree, kanban, form and dashboard views from one architecture). Three commands scaffold, audit and map access for admin routes in the project's own access model.

It is for developers building or reviewing React / Next.js apps, especially back offices and staff dashboards. Entity names, roles, APIs and libraries are detected from your codebase or asked once; nothing project-specific is baked in. The admin-view idea of "one resource, many views" is inspired by Odoo but targets idiomatic React.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install react-kit@taqat-techno-plugins
```

## Requirements

| Requirement | Why | How to check |
|---|---|---|
| A React 18+ / Next.js 13+ project (Remix, Vite + React and the Pages Router also work) | All skills and commands target it | `package.json` lists `react` |
| Node.js and the project's package manager | Commands that build, type-check or test | `node --version` |

No services, hooks or scripts.

## Commands

| Command | What it does | Bare invocation |
|---|---|---|
| `/react-kit:admin-scaffold [entity]` | Scaffold an admin list + detail + form for an entity in the project's access model; detects adapter values first, asks only for the rest | asks for the entity after detection |
| `/react-kit:admin-audit [path]` | Read-only audit of an admin route or tree against the skill rules; findings table with file:line | audits the detected `panelDir` |
| `/react-kit:admin-role-matrix` | Generate (`--generate`), validate (`--validate`) or diff (`--diff`) the access matrix | generate when none exists, else validate; runs its own detection when no cache exists |

The commands are named for the admin domain, not the plugin, so they keep their names.

## Skills

All skills are model-invoked (`user-invocable: false`).

| Skill | Use when |
|---|---|
| `admin-crud` | Building admin lists, tables, trees, filters, paginators, detail views |
| `admin-dangerous-actions` | Adding delete / suspend / impersonate / mass-update actions |
| `admin-dashboard-overview` | Building a module overview or KPI dashboard |
| `admin-forms` | Building admin forms, rich-text fields, unsaved-changes guards, bulk actions |
| `admin-import-export` | Adding CSV / Excel / JSON import or export |
| `admin-kanban-workflow` | Building boards and status-driven workflows |
| `admin-panel-architecture` | Starting or extending an admin panel; owns the adapter schema and access-model detection |
| `admin-roles-and-permissions` | Gating routes, menus, renders and fields; PII masking; audit visibility |
| `admin-rtl-ltr` | Making admin UI correct in RTL locales |
| `admin-shell` | Building the layout shell, sidebar, header, locale switch |
| `admin-states` | Displaying loading, error, empty, no-results and partial-error states |
| `admin-view-patterns` | Choosing which view type a resource needs |
| `data-fetching-states` | Writing data hooks; debugging blank screens and silent empty lists |
| `frontend-build-traps` | Build / dev-server / test-runner / lockfile failures whose symptom points at the wrong layer (Next.js-version-aware) |
| `react-lint-triage` | Triaging lint, analyzer and IDE findings before auto-fixing |
| `react19-migration` | Upgrading to React 19 |

Reference documents live under each skill's `references/` (adapter schema, view registry, state contract, list/tree, kanban, action workflow, form and dashboard patterns).

## Agents

| Agent | Tools | Purpose |
|---|---|---|
| `admin-route-auditor` | Read, Glob, Grep | Read-only scan of one admin route or folder; findings by section with severity and file:line |

## Hooks

None.

## Configuration

**Per-project file** `.react-kit.local.json` at the project root, written by `/react-kit:admin-scaffold` or `/react-kit:admin-role-matrix` after detection and your answers. Keys are defined once in `skills/admin-panel-architecture/references/admin-panel-adapter.md` (`schemaVersion: 1`). Add the file to `.gitignore`.

First-run questions, asked only when detection cannot answer them, in this order: access model (`role-enum`, `permission-strings`, `module-levels` or `policy-engine`, plus that model's fields), panel location, auth helper, guard helper, audit helper, PII fields (always confirmed), RTL locales, libraries not found in `package.json`, and an optional import format. react-kit never migrates a project to a different access model unless asked.

No environment variables or plugin options.

## Platform support

| Platform | Status |
|---|---|
| Windows / macOS / Linux / WSL | Supported (markdown only). `frontend-build-traps` gives both POSIX and PowerShell commands for finding the process that owns a port. |

## Data & privacy

- **Stored:** `.react-kit.local.json` in your project (adapter values such as directory names, helper imports and PII field names; no secrets), and the files you ask the commands to generate.
- **Leaves the machine:** nothing. The plugin makes no network calls.
- **On screen / in context:** your source files, lint and build output. Tool output and code comments are treated as data, never instructions.

## Limitations

- Patterns are guidance, not a component library; generated code still needs review and tests.
- Out of scope: Django admin, Laravel Nova, Odoo backend, Vue / Svelte / Angular. To test those UIs in a browser, the separate `qa-browser` plugin (https://github.com/taqat-techno/plugins/tree/main/qa-browser-plugin) can help.
- Visual style is not covered; Anthropic's `frontend-design` plugin owns that if installed. Optional companions: `qa-browser` (runtime RBAC checks), `docs-wiki` (SOPs), `env-doctor` (environment problems).
- Evals exist for every skill but have not been run with a recorded Delta.

## License

MIT (see `LICENSE`).
