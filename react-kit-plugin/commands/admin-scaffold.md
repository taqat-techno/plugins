---
description: Scaffold an admin CRUD page (list + detail + form) for a given entity, applying the react-kit skill set. Asks for adapter inputs the first time, caches answers locally.
argument-hint: "[entity-name] [--list-only | --detail-only | --form-only]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep, Write, Edit
---

# /admin-scaffold

You are scaffolding an admin CRUD surface for one entity. Apply the patterns from the `react-kit` skill set:

- `admin-roles-and-permissions` — paired UI/API gates, PII masking, audit visibility.
- `admin-shell` — the new pages must compose into the existing shell (do not duplicate chrome).
- `admin-crud` — URL-as-source-of-truth, server-side pagination, filter chips, detail tabs.
- `admin-forms` — typed fields, shared validation, dirty/cancel/submit flow.
- `admin-dangerous-actions` — destructive actions go through the confirmation contract.
- `admin-import-export` — only if the user opts in.
- `admin-states` — loading skeleton matches final layout; empty vs no-results distinct.
- `admin-rtl-ltr` — logical CSS utilities only; no physical `ml-`/`mr-`/`text-left`/`text-right`.

## Step 0 — Read the adapter cache

Look for `.react-kit.local.json` in the project root.

- If present, load: `adminBasePath`, `i18nProvider`, `roleList`, `piiFields`, `authHelperImport`, `auditHelperImport`, `rtlLocales`, `importFormat`, `validationLibrary`, `formLibrary`, `cssFramework`.
- If absent, fall through to Step 1.

## Step 1 — Adapter intake (only on first invocation)

Ask the user (one short batch via AskUserQuestion if available, otherwise plain prompts):

1. **Admin base path** — where do admin pages live? (Default suggestion based on detected framework: `app/admin/`, `src/admin/`, `pages/admin/`.)
2. **Auth helper import** — what function returns the current session + role? (Example: `import { getSession } from '@/lib/auth'`.)
3. **Role list** — what roles exist? (Comma-separated.)
4. **PII field list** — which fields across the app are sensitive? (Comma-separated. Used by the form scaffolder to wrap them in `<MaskedField>`.)
5. **Audit helper import** — how is an audit-log row written? (Example: `import { audit } from '@/lib/audit'`. If "none" yet, scaffold a minimal one.)
6. **RTL locales** — which configured locales are RTL? (Comma-separated. Empty if none.)
7. **Validation library** — `zod`, `yup`, `joi`, `valibot`, `none`?
8. **Form library** — `react-hook-form`, `formik`, `tanstack-form`, `plain useState`?
9. **CSS framework** — `tailwind`, `css-modules`, `vanilla`, `styled-components`?
10. **Import format** (optional) — `csv`, `xlsx`, `json`, or `not now`.

Write the answers to `.react-kit.local.json` (gitignored). Tell the user to add it to `.gitignore` if not already there.

## Step 2 — Entity intake

Argument `entity-name` is the singular name (e.g., `User`, `Product`, `Order`). If absent, ask.

Then ask:

- **Plural name** (default: `<entity-name>s`).
- **Field list** — for each field: `name`, `type` (string / number / boolean / enum / date / datetime / file / relation), `required` (yes/no), `pii` (yes/no — defaults from the PII list).
- **List columns** — which fields to show on the list page. Subset of fields. Default: name + a few key fields.
- **Default sort** — field + direction. Default: `created_at DESC`.
- **Filter set** — which fields are filterable, by what operator (`eq`, `contains`, `range`, `in`).
- **Row actions** — `view`, `edit`, plus any of `archive`, `delete`, `impersonate`, `custom`.
- **Bulk actions** — `none`, `archive`, `export`, custom.
- **Role-action matrix** — for each (role × action), allow / deny. (Default: highest-privilege role can do everything; "viewer" role can only view.)

## Step 3 — Plan the file diff

Before writing, list every file you will create or modify and what each contains:

```
PLAN
  CREATE  <admin-base>/<plural>/page.tsx              ← list page
  CREATE  <admin-base>/<plural>/[id]/page.tsx         ← detail page (tabs)
  CREATE  <admin-base>/<plural>/[id]/edit/page.tsx    ← edit form (if separate route)
  CREATE  <admin-base>/<plural>/new/page.tsx          ← create form
  CREATE  <admin-base>/<plural>/_schema.ts            ← shared validation schema
  CREATE  <admin-base>/<plural>/_components.tsx       ← list table, filters, row actions
  MODIFY  <admin-base>/_menu.ts                       ← add menu item with allowedRoles
  MODIFY  <admin-base>/_matrix.ts                     ← add entity to permission matrix
```

Tailor the file layout to the detected framework (Next.js App Router vs Pages Router vs Remix vs Vite). If you cannot detect, ask.

Wait for the user to approve the plan before writing any file.

## Step 4 — Write the files

Apply the skills:

- List page: read filter / page / sort from URL; render filter chips; render table with sortable columns; render row actions; render skeleton matching final layout on first load; render no-results vs empty correctly.
- Detail page: tabs (Overview / Edit / Related / Audit — drop unused); audit query scoped to this record; per-row permissions read from API.
- Form: typed field components per type; shared validation schema (client + server reference); dirty-state warning on cancel + beforeunload; submit button disabled in flight; PII fields masked by default with reveal-on-click + audit.
- Menu: add `{ href, labelKey, icon, allowedRoles }` to `_menu.ts`. Allowed roles come from the matrix.
- Matrix: add the entity's row to `_matrix.ts`.

Do NOT write business logic. The scaffold renders skeleton calls to placeholder API handlers (`listX`, `getX`, `createX`, `updateX`, `deleteX`) with TODO comments where the user adds their domain code.

For every destructive row action, generate the confirmation modal per `admin-dangerous-actions` — including consequence summary, blast-radius classification, audit-on-action.

For every PII field, generate the masked render + reveal-on-click + audit.

Use logical CSS utilities throughout (`ms-`/`me-`/`ps-`/`pe-`/`start-`/`end-`/`text-start`/`text-end`) per `admin-rtl-ltr`.

## Step 5 — Verify

After writing:

1. Grep your output for `ml-`, `mr-`, `pl-`, `pr-`, `text-left`, `text-right`, `margin-left`, `margin-right`, `padding-left`, `padding-right`. Any hit is a bug — fix to logical equivalent.
2. Confirm every destructive action has: blast-radius classification + consequence summary + audit-on-action.
3. Confirm every PII field is masked by default.
4. Confirm the menu entry's `allowedRoles` matches the matrix row.
5. Confirm no business logic was generated — only scaffolding with TODO markers.

## Step 6 — Report

Report what was created with file paths and key decisions:

```
SCAFFOLDED <entity>
  Files created: <count>
  Files modified: <count>
  Menu entry: added with roles [<role>, <role>]
  Matrix row: added
  Destructive actions: <count> with confirmation contract
  PII fields: <count> masked by default
  Direction-aware: <yes>
  TODO markers for user: <count>     ← list each with file:line
```

## Modes

- `--list-only`: skip detail + form scaffolding.
- `--detail-only`: skip list + form scaffolding.
- `--form-only`: skip list + detail scaffolding.

Useful when iterating on one surface at a time.
