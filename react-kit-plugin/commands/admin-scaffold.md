---
description: Scaffold an admin CRUD page (list + detail + form) for a given entity, applying the react-kit skill set. Detects the project's adapter values (including its access model) from the codebase, asks only for what detection cannot resolve, and caches the answers locally.
argument-hint: "[entity-name] [--list-only | --detail-only | --form-only]"
author: TAQAT Techno
version: 0.3.0
allowed-tools: Read, Glob, Grep, Write, Edit
---

# /admin-scaffold

You are scaffolding an admin CRUD surface for one entity. Apply the patterns from the `react-kit` skill set:

- `admin-panel-architecture` — adapter schema, access-model detection, one navigation builder that mirrors the route guard.
- `admin-roles-and-permissions` — paired UI/API gates, PII masking, audit visibility.
- `admin-shell` — the new pages must compose into the existing shell (do not duplicate chrome).
- `admin-crud` — URL-as-source-of-truth, server-side pagination, filter chips, detail tabs.
- `admin-forms` — typed fields, shared validation, dirty/cancel/submit flow.
- `admin-dangerous-actions` — destructive actions go through the confirmation contract.
- `admin-import-export` — only if the user opts in.
- `admin-states` — loading skeleton matches final layout; empty vs no-results distinct.
- `admin-rtl-ltr` — logical CSS only; no physical `ml-`/`mr-`/`text-left`/`text-right`.

Every adapter key named below is defined in `skills/admin-panel-architecture/references/admin-panel-adapter.md` (the adapter schema). Use those key names exactly; do not invent others.

## Step 0 — Read the adapter cache

Look for `.react-kit.local.json` in the project root.

- If present with `schemaVersion: 1`, load it and skip to Step 2 (fill any missing required key via Step 1 first).
- If present without `schemaVersion`, it is a legacy cache: map its keys per the schema's *Legacy cache keys* table, then run Step 1 to confirm `accessModel` (a legacy `roleList` does not prove the project uses a role enum).
- If absent, run Step 1.

## Step 1 — Detect, then ask only what is unresolved

**1a. Detect** (read-only) every key the schema lists a detection source for: `framework`, `panelDir`, `panelBasePath`, `accessModel` + `access` fields, `authHelper`, `guardHelper`, `auditHelper`, `navSource`, `rtlLocales`, `i18nLibrary`, `dataLibrary`, `uiLibrary`, `validationLibrary`, `formLibrary`, `cssFramework`. For `accessModel`, run the schema's *Detecting the access model* greps and keep the file:line evidence.

Show the user what was detected (key, value, evidence) in one compact table.

**1b. Ask** — one short batch via AskUserQuestion if available, otherwise plain prompts — only the questions whose key is still unresolved, in this order:

1. **Access model** — asked only when detection is inconclusive: `role-enum`, `permission-strings`, `module-levels`, or `policy-engine` (show the trade-off line for each from the schema). Then that model's required `access` fields (roles; permission format + list; modules + ordered levels + optional admin module; engine + ability import + actions + subjects + policy source).
2. **Panel location** — `panelDir` and `panelBasePath`.
3. **Auth helper** — the import that returns the verified current user on the server.
4. **Guard helper** — the one access-check function routes, nav, and APIs share. If none exists, offer to scaffold one for the selected access model.
5. **Audit helper** — how an audit row is written, or `none` (a minimal one is scaffolded).
6. **PII fields** — always confirmed on first run (detection only suggests candidates).
7. **RTL locales** — empty if the app is LTR-only.
8. **Libraries** — any of `validationLibrary`, `formLibrary`, `cssFramework`, `dataLibrary`, `uiLibrary` not found in `package.json`.
9. **Import format** (optional) — `csv`, `xlsx`, `json`, or `none`.

Write the merged result to `.react-kit.local.json` with `schemaVersion: 1`. Tell the user to add it to `.gitignore` if it is not already there.

Never change the project's access model. If the user asks for a migration to a different model, treat that as a separate, explicitly requested task — not part of scaffolding.

## Step 2 — Entity intake

Argument `entity-name` is the singular name (e.g., `User`, `Product`, `Order`). If absent, ask.

Then ask:

- **Plural name** (default: `<entity-name>s`).
- **Field list** — for each field: `name`, `type` (string / number / boolean / enum / date / datetime / file / relation), `required` (yes/no), `pii` (yes/no — defaults from `piiFields`).
- **List columns** — which fields to show on the list page. Default: name + a few key fields.
- **Default sort** — field + direction. Default: `created_at DESC`.
- **Filter set** — which fields are filterable, by what operator (`eq`, `contains`, `range`, `in`).
- **Row actions** — `view`, `edit`, plus any of `archive`, `delete`, `impersonate`, `custom`.
- **Bulk actions** — `none`, `archive`, `export`, custom.
- **Access requirements** — for each operation (`read`, `create`, `update`, `delete`, plus each custom action), the requirement in the `accessModel` shape:

  | `accessModel` | Requirement asked per operation | Proposed default |
  |---|---|---|
  | `role-enum` | which of `access.roles` may perform it | every role that can already reach comparable entities (from the matrix or existing guards) |
  | `permission-strings` | the permission string, in `access.permissionFormat` | `<plural>:<operation>` rendered in the project's format |
  | `module-levels` | `{ module, minLevel }` from `access.modules` / `access.levels` | owning module; lowest level for `read`, next level for writes |
  | `policy-engine` | `{ action, subject }` from `access.actions` / `access.subjects` | `{ action: <operation>, subject: <Entity> }` |

  Show the defaults as a proposal; the user confirms or edits. Never widen an existing requirement.

## Step 3 — Plan the file diff

Before writing, list every file you will create or modify and what each contains:

```
PLAN
  CREATE  <panelDir>/<plural>/page.tsx              ← list page
  CREATE  <panelDir>/<plural>/[id]/page.tsx         ← detail page (tabs)
  CREATE  <panelDir>/<plural>/[id]/edit/page.tsx    ← edit form (if separate route)
  CREATE  <panelDir>/<plural>/new/page.tsx          ← create form
  CREATE  <panelDir>/<plural>/_schema.ts            ← shared validation schema
  CREATE  <panelDir>/<plural>/_components.tsx       ← list table, filters, row actions
  MODIFY  <navSource>                               ← add nav item with `requires` (accessModel shape)
  MODIFY  <access definition for accessModel>       ← see table below
```

Where the access definition lives, per `accessModel`:

| `accessModel` | File modified | What is added |
|---|---|---|
| `role-enum` | the permission matrix (`/admin-role-matrix` output) or the existing role map | entity row: role × operation |
| `permission-strings` | the permission registry (`access.permissions` source) and, if present, `access.rolePermissionsSource` | the entity's permission strings; role bundles only if the user approves |
| `module-levels` | the existing module/requirement map | entity → `{ module, minLevel }` per operation |
| `policy-engine` | `access.policySource` when policies live in the repo (CASL rules, Casbin `policy.csv`) | rules for the new subject; if policies live in an external service, write nothing there — list the rules the user must add |

Tailor the file layout to `framework` (Next.js App Router vs Pages Router vs Remix vs Vite). If it is `other`, ask.

Wait for the user to approve the plan before writing any file.

## Step 4 — Write the files

Apply the skills:

- List page: read filter / page / sort from URL; render filter chips; render table with sortable columns; render row actions; render skeleton matching final layout on first load; render no-results vs empty correctly.
- Detail page: tabs (Overview / Edit / Related / Audit — drop unused); audit query scoped to this record; per-row permissions read from API.
- Form: typed field components per type; shared validation schema (client + server reference); dirty-state warning on cancel + beforeunload; submit button disabled in flight; PII fields masked by default with reveal-on-click + audit.
- Guards: every page, server action, and API handler calls `guardHelper` with the operation's requirement. Generated code uses the model's native check:

  | `accessModel` | Generated check (illustrative) |
  |---|---|
  | `role-enum` | `await guardHelper(user, { roles: ['owner', 'editor'] })` |
  | `permission-strings` | `await guardHelper(user, { permission: 'orders:update' })` |
  | `module-levels` | `await guardHelper(user, { module: 'orders', minLevel: 'edit' })` |
  | `policy-engine` | `ability.can('update', subject('Order', record))` via `access.abilityImport` |

- Navigation: add `{ href, labelKey, icon, requires }` to `navSource`, where `requires` is the `read` requirement. If the project's existing nav uses another field name for the same thing (e.g. `allowedRoles`, `permission`), keep the project's name.
- Access definition: add the entity per the Step 3 table.

Do NOT write business logic. The scaffold renders skeleton calls to placeholder API handlers (`listX`, `getX`, `createX`, `updateX`, `deleteX`) with TODO comments where the user adds their domain code.

For every destructive row action, generate the confirmation modal per `admin-dangerous-actions` — including consequence summary, blast-radius classification, audit-on-action.

For every PII field, generate the masked render + reveal-on-click + audit.

Use logical CSS throughout per `admin-rtl-ltr` (Tailwind: `ms-`/`me-`/`ps-`/`pe-`/`start-`/`end-`/`text-start`/`text-end`; plain CSS: `margin-inline-start`, `inset-inline-end`, `text-align: start`).

## Step 5 — Verify

After writing:

1. Grep your output for physical direction (`ml-`, `mr-`, `pl-`, `pr-`, `text-left`, `text-right` for Tailwind; `margin-left`, `margin-right`, `padding-left`, `padding-right`, `text-align: left|right` for CSS). Any hit is a bug — fix to the logical equivalent.
2. Confirm every destructive action has: blast-radius classification + consequence summary + audit-on-action.
3. Confirm every PII field is masked by default.
4. Confirm the nav item's `requires` equals the `read` requirement in the access definition, and every handler's guard equals its operation's requirement (same `guardHelper`, same value).
5. Confirm the existing access model was not changed and no requirement was widened.
6. Confirm no business logic was generated — only scaffolding with TODO markers.

## Step 6 — Report

Report what was created with file paths and key decisions:

```
SCAFFOLDED <entity>
  Access model: <accessModel> (<detected: file:line | chosen by user>)
  Files created: <count>
  Files modified: <count>
  Nav entry: added, requires <read requirement>
  Access definition: <file> updated (<n> operations)
  Destructive actions: <count> with confirmation contract
  PII fields: <count> masked by default
  Direction-aware: <yes>
  TODO markers for user: <count>     ← list each with file:line
  External policy rules to add: <none | list>   ← policy-engine with an external policy service
```

## Modes

- `--list-only`: skip detail + form scaffolding.
- `--detail-only`: skip list + form scaffolding.
- `--form-only`: skip list + detail scaffolding.

Useful when iterating on one surface at a time.
