---
description: Create a new wiki page with one of the wiki-authoring templates (SOP / runbook / role-guide / onboarding / release-handover / user-manual / workflow / architecture / decision-record). Asks for audience + summary; scaffolds the template; diff-previews; goes through wiki-safe-updates.
argument-hint: "<Page-Name> [--template sop|runbook|role-guide|onboarding|release-handover|user-manual|workflow|architecture|decision-record|freeform] [--audience <role>]"
author: TAQAT Editorial
version: 0.2.0
allowed-tools: Read, Glob, Grep, Write
---

# /wiki-new

You are creating a new wiki page. Apply `wiki-authoring` (template), `wiki-structure` (filename / URL slug), `wiki-link-validation` (the new page must not collide), and `wiki-safe-updates` (diff preview before write).

## Step 0 — Resolve filename

Argument `<Page-Name>` becomes the page title AND the filename basename:

- Normalise: `Title Case` → `Title-Case.md` (per `wiki-structure`).
- Collision check (flat-namespace flavours): if basename already exists, REFUSE.
- Numeric-prefix check: refuse names like `01-Foo`.

Confirm with user:

```
PROPOSED PAGE
  Title: Restart API Runbook
  Filename: Restart-API-Runbook.md
  URL: <wiki>/Restart-API-Runbook
  Path: <wiki-path>/Restart-API-Runbook.md

  Confirm? [yes / no / rename]
```

## Step 1 — Resolve template

Order:

1. `--template <type>` flag → use it.
2. Heuristic from page name (e.g., `*Runbook` → runbook, `*SOP` → sop, `ADR-NN-*` → decision-record).
3. Ask:

```
What kind of page is this?
  1. SOP (procedure operators follow)
  2. Runbook (emergency response steps)
  3. Role guide (what someone in role X does)
  4. Onboarding (first weeks in role X)
  5. Release / handover (what shipped, who owns now)
  6. User manual (how to use a product)
  7. Workflow (multi-party process)
  8. Architecture overview (engineering reference)
  9. Decision record (ADR — why we chose X)
  10. Freeform (no template — for Home, Index, About only)
```

Default to "freeform" only when the user explicitly says so.

## Step 2 — Resolve audience

`--audience <role>` flag → use it.

Otherwise ask:

```
Who is this page for?
  (Examples by template:
    SOP / Runbook  → "on-call engineers", "operators"
    Role guide     → "<role-name>"
    Onboarding     → "new <role-name>"
    User manual    → "<end-user role>"
    Architecture   → "engineers")
```

## Step 3 — Scaffold the body

Apply the chosen template from `wiki-authoring`. The scaffold:

- Title (matches filename, no numeric prefix).
- Audience header.
- Last-reviewed placeholder (`<YYYY-MM-DD> by <name> · Reviewed every: <interval>`).
- Summary placeholder (`<one-paragraph: what this page covers>`).
- Template-specific sections with placeholders (e.g., for SOP: "When to run this", "Before you start", "Procedure", "How to know it worked", "If it does not work", "Escalation", "Audit log", "Related").

The body has placeholders, not real content. The user fills in their domain knowledge.

For decision-record template: also ask for the ADR number (NN) and prefix the filename / title.

## Step 4 — Diff preview (technically a "new file preview")

Per `wiki-safe-updates`:

```
PROPOSED NEW PAGE — <wiki-path>/<filename>
  Template: <type>
  Audience: <role>
  Size: <line count>
  First 20 lines:
    # <Title>

    > **Audience:** <role>
    > **Last reviewed:** <YYYY-MM-DD> by <name>

    ...

  Apply? [yes / no / edit]
```

## Step 5 — Write

Use the Write tool. Confirm the file does not exist first (collision check).

## Step 6 — Sidebar suggestion

After writing, suggest a `_Sidebar.md` update (do NOT auto-apply):

```
SUGGESTED SIDEBAR ADDITION

  In _Sidebar.md, under "Runbooks":
  - [Restart API](Restart-API-Runbook)

  Apply via /wiki-update _Sidebar --section "Runbooks" --allow-structural
```

## Step 7 — Report

```
WIKI PAGE CREATED — <filename>
  Template: <type>
  Audience: <role>
  Path: <wiki-path>/<filename>
  Placeholders to fill: <count>     ← list them with file:line
  Sidebar entry suggested: <yes — see above>

  Next:
    1. Open the file and fill placeholders with domain content.
    2. Add the sidebar entry (see suggestion above).
    3. Run /wiki-audit to confirm no link issues.
    4. When ready to publish: cd <wiki-path>; git add <filename> _Sidebar.md; git commit; git push (approval gate applies).
```

## Safety

- Refuses to create a page that collides on basename.
- Refuses to create a page with a numeric prefix.
- Refuses to write inside a retired folder unless `--allow-retired` (rare).
- Refuses to write outside the wiki repo path.
- Refuses to inject any real PII / secrets / customer identifiers into placeholders.
- Goes through `wiki-safe-updates` for the new file preview.
- Does NOT push.
- Does NOT auto-modify `_Sidebar.md` (only suggests).

## Modes

- `--template <type>` — pre-select the template.
- `--audience <role>` — pre-set the audience.
- `--allow-retired` — allow writing into a retired folder (uncommon; usually you don't want to).

## What NOT to do

- Do NOT invent domain content. Templates provide structure; the user provides substance.
- Do NOT auto-add the sidebar entry; the maintainer chooses where it lives in the navigation order.
- Do NOT push the wiki after creation.
