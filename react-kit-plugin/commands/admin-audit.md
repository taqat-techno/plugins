---
description: Audit an existing admin route against the react-kit skill rules. Read-only — produces a Markdown table of findings with file:line citations. Optionally suggests a fix per finding.
argument-hint: "<path-to-admin-route> [--suggest-fixes]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep
---

# /admin-audit

You are auditing one admin route (a single page, a folder, or a whole admin tree) against the `react-kit` skill set. **Read-only.** No edits. Produce a findings table.

The skill rules being applied:

- `admin-roles-and-permissions` — paired UI/API gates, PII masking, audit-on-action, audit visibility.
- `admin-shell` — composition only, no business logic in shell.
- `admin-crud` — URL-as-state, server-side pagination, distinct empty / no-results, skeleton matches layout.
- `admin-forms` — server validation primary, dirty-state warning, no fire-and-forget submit, magic-byte file validation.
- `admin-dangerous-actions` — friction matches blast radius, audit-on-action, no one-click destruction, consequence summary in modals.
- `admin-import-export` — preview phase, row cap, typed per-row errors, idempotency, no auto-create.
- `admin-states` — what / next-step / support-hint on errors; no raw stack traces; no spinner-on-blank.
- `admin-rtl-ltr` — logical CSS only; directional icons mirror; LTR-locked content for code/URLs/numerics.

## Step 0 — Resolve the target

Argument `path-to-admin-route` resolves to:

- A single file: audit that file in detail.
- A folder: glob `**/*.{tsx,jsx,ts,js,vue,svelte}` and audit each.
- Empty argument: ask for the path.

Confirm the path exists. If it does not, ask the user to recheck.

## Step 1 — Read the adapter cache

Load `.react-kit.local.json` if present. This gives you the project's role list, PII fields, auth helper, and audit helper names — so the audit checks against actual identifiers, not generic ones.

If the cache is absent, run the audit with generic checks and note in the report that role / PII / auth specifics could not be verified.

## Step 2 — Run the audit (read-only)

For each file in scope, check:

### Section A — Authorization

| Check | How |
|---|---|
| Paired UI/API gate | For each role-conditional render (`if (role === ...)`, `{allowedRoles.includes(...) && <X/>}`), grep the matching API path for a server-side role check. If missing → finding. |
| Role claim source | Find role reads. If from URL params, headers under client control, or unverified context → finding. |
| Per-action permission | For each row/bulk destructive action, check that the API endpoint re-checks the permission predicate. |

### Section B — PII

| Check | How |
|---|---|
| PII fields masked by default | For each known PII field name from the cache, grep for renders. Any unmasked render → finding. |
| Reveal-on-click + audit | For each `RevealOnClick` (or equivalent), check that `onReveal` writes to the audit helper. |
| PII in logs | Grep for `console.log`, `logger.*`, `toast.*` with PII field names. Any hit → finding. |
| PII in URL params | Grep for known PII field names in `useSearchParams` keys or URL building. |

### Section C — CRUD

| Check | How |
|---|---|
| URL-as-state | List pages should read filter/page/sort from URL. If filter state is only in `useState` → finding. |
| Server-side pagination | List endpoints should accept `page` + `pageSize`; client should not request all rows then `.slice()`. |
| Skeleton matches layout | Loading state should be a skeleton with matching column count, not a generic spinner over a blank table. |
| Empty vs no-results | Distinct affordances. If they share the same component without filter awareness → finding. |
| Detail tabs only when content exists | Empty tabs → finding. |

### Section D — Forms

| Check | How |
|---|---|
| Server validation exists | For each form submit endpoint, validation schema present. If only client → finding. |
| Dirty-state warning | For each form, beforeunload warning + cancel confirmation when dirty. Missing → finding. |
| Submit disabled in flight | Submit button disabled while in-flight. Missing → finding. |
| Magic-byte file validation | For file upload endpoints, validation by magic bytes (not just extension). |
| `autocomplete` on sensitive | `autocomplete="new-password"` or `"off"` on sensitive inputs. |

### Section E — Dangerous actions

| Check | How |
|---|---|
| Friction matches blast radius | One-click destruction → finding. Modal-summary on low-blast → minor smell only. |
| Audit-on-action | Each destructive endpoint writes audit. Missing → finding. |
| Consequence summary | Modal body lists what will happen. Missing → finding. |
| Destructive button not default focus | Destructive button is `tabIndex` after Cancel. |
| Destructive color not brand primary | Red / orange / outlined, not blue (or whatever the brand is). |
| Bulk destructive per-item failure report | Bulk endpoint returns per-item result. |

### Section F — Import / export

| Check | How |
|---|---|
| Preview phase before commit | No commit-on-upload. |
| Row cap | Client and server both enforce. |
| Typed per-row errors | Errors include `row`, `field`, `code`, `message`. |
| External-id idempotency | Re-import produces no duplicates. |
| No auto-create related entities | Default policy is `error` unless explicit per-import sign-off. |
| Export filename includes filter context + timestamp | Bare `export.csv` → finding. |

### Section G — States

| Check | How |
|---|---|
| Loading shows skeleton | Not spinner-on-blank. |
| Error: what / next-step / support | "Error" alone → finding. Raw stack → finding. |
| Empty vs no-results distinct | Same component without filter-awareness → finding. |
| Per-row partial-error | One row failing crashes whole list → finding. |
| Auto-dismiss error toast | Errors should be manual-dismiss. |

### Section H — RTL/LTR (only if RTL locales configured)

| Check | How |
|---|---|
| Logical CSS only | Grep `ml-`, `mr-`, `pl-`, `pr-`, `text-left`, `text-right`, `margin-left`, `margin-right`, `padding-left`, `padding-right`, `left:`, `right:`. Any hit → finding (`R-1`). |
| Directional icons mirror | Arrows in pagination / breadcrumb wrapped with conditional `scale-x-[-1]` or `[dir="rtl"]` rule. |
| LTR-locked content | Code blocks, URLs, file paths, ISO timestamps wrapped in `dir="ltr"`. |
| Toast position uses logical | `inset-inline-end`, not `right:`. |

## Step 3 — Produce the report

Markdown table grouped by section:

```
ADMIN AUDIT — <path>

SUMMARY
  Files audited: <N>
  Findings: <H high / M medium / L low>
  Sections with no findings: <list>

FINDINGS

Section A — Authorization
| ID | Severity | File:Line | Issue | Fix |
|----|----------|-----------|-------|-----|
| A-1 | HIGH | app/admin/users/page.tsx:42 | Role-conditional render with no matching server check on DELETE /api/users/[id] | Add `await requireRole('admin')` at the top of the DELETE handler |
| A-2 | MEDIUM | components/admin/MenuItem.tsx:12 | Menu item filters by `role` read from React context populated by a child page | Move role read to session helper at shell level |

Section B — PII
| B-1 | HIGH | app/admin/users/page.tsx:88 | `phone` field rendered unmasked in list | Wrap in `<MaskedField mask={maskPhone}/>` |

...
```

Each finding has:

- **ID** (`<Section>-<n>`): stable, sortable.
- **Severity**: HIGH / MEDIUM / LOW. HIGH means data loss, security breach, or compliance issue. MEDIUM means UX bug or scaling risk. LOW means cosmetic or convention drift.
- **File:Line**: exact location.
- **Issue**: 1–2 sentences. No jargon.
- **Fix**: one-line directive. If `--suggest-fixes` is set, expand with a code snippet.

After the table, write a one-paragraph summary:

```
SUMMARY
  Most common finding category: <e.g., missing audit-on-action — 12 occurrences>
  Highest-risk finding: <ID — one-line description>
  Recommended order of fixes: <list of finding IDs in priority order>
```

## Step 4 — What NOT to do

- Do NOT edit any file.
- Do NOT run any script.
- Do NOT call any API.
- Do NOT submit a PR.
- Do NOT generate findings for things the skills do not own (e.g., performance optimization unless it intersects with skipping pagination).
- Do NOT report a false positive when the user has documented a deliberate exception (look for `// kit-exception: <reason>` comments — respect them).

The output of this command is a report. The user decides what to act on.
