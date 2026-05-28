---
description: Edit an existing wiki page with diff preview before write. Goes through wiki-safe-updates. Supports targeted edits (e.g., update the Procedure section) without rewriting the whole page. Never pushes.
argument-hint: "<page-name> [--section <heading>] [--reason \"why\"]"
author: TAQAT Editorial
version: 0.2.0
allowed-tools: Read, Glob, Grep, Edit
---

# /wiki-update

You are editing an existing wiki page. Apply `wiki-safe-updates`, `wiki-structure`, `wiki-link-validation`, and `wiki-authoring` (if restructuring).

## Step 0 — Resolve page

Argument `<page-name>` resolves to a basename. Locate the corresponding `.md` file in the wiki repo:

- Exact basename match → use it.
- Case-insensitive match → suggest "did you mean <X>?" and confirm.
- No match → REFUSE with: "No page named `<X>` in the wiki. Run `/wiki-new` to create."

Read the current page content. Capture last-modified date.

## Step 1 — Identify the change

Two paths:

### Path A — `--section <heading>` targeted edit

The user wants to change one section (e.g., "Procedure step 3 needs updating").

1. Parse the page's headings; locate the section.
2. Surface the current section content.
3. Ask the user for the new content (or accept the prompt as the new content if it already includes it).
4. Build the proposed edit: replace just that section, keep the rest unchanged.

### Path B — Page-level edit

The user wants to make a broader change. Ask for the change scope:

- Update specific paragraphs?
- Add a new section?
- Restructure into a different template (per `wiki-authoring`)?
- Update the audience / last-reviewed header?

Then propose accordingly.

## Step 2 — Diff preview (mandatory, per wiki-safe-updates)

Compute the diff. Show inline:

```
PROPOSED CHANGE — <wiki-path>/<page>.md
  Section affected: <heading | full page>
  Reason: <as provided via --reason or asked>

  --- current
  +++ proposed
  @@ ...
  (diff)

  Apply this change? [yes / no / edit]
```

Three response paths per `wiki-safe-updates`:

- `yes` → apply via Edit (one targeted replacement).
- `no` → discard; report no change.
- `edit` → user refines; re-propose.

## Step 3 — Apply

Use the Edit tool with the targeted change:

- For Path A: Edit with `old_string` = current section content (or sufficient context), `new_string` = proposed.
- For Path B: multiple Edit calls if needed, each with a targeted change.

DO NOT use Write (full overwrite). Write loses the surrounding context's editorial history; Edit preserves intent.

## Step 4 — Post-edit validation

After the edit:

1. Run a lightweight `wiki-link-validation` on the edited page:
   - Any new internal links resolve?
   - Any link convention violations introduced?
   - Any visible numeric-prefix added?
2. Update the "Last reviewed" header if the edit was substantive (ask the user; small typo fix typically does NOT update last-reviewed).

If validation surfaces a new issue, surface it; do NOT auto-fix. Ask the user.

## Step 5 — Report

```
WIKI UPDATED — <page>
  File: <wiki-path>/<page>.md
  Section: <heading | full page>
  Diff applied: <bytes added / removed>
  Reason: <as provided>
  Last-reviewed updated: <yes (to <date> by <name>) | no — typo fix>
  Post-edit validation: <pass | <findings>>

  Next:
    - Review remaining changes in <wiki-path> with `git status`.
    - When ready to publish: cd <wiki-path>; git add <page>.md; git commit -m "[<area>] <subject>"
      then `git push` (push-approval gate applies).
```

## Safety

- Diff preview mandatory.
- User confirmation per `wiki-safe-updates`.
- Never overwrites without Edit (preserves git diff fidelity).
- Refuses to edit a file outside the wiki repo path.
- Refuses to edit `Home.md`, `_Sidebar.md`, `_Footer.md` without an explicit `--allow-structural` flag (these change navigation and merit extra care).
- Does NOT push.
- Scans the proposed content for secrets / PII before write; refuses if detected.

## Modes

- `--section <heading>` — targeted section edit.
- `--reason "<why>"` — captured in the diff preview; helps reviewers and future readers.
- `--allow-structural` — allow editing `Home.md` / `_Sidebar.md` / `_Footer.md` (otherwise refused).

## What NOT to do

- Do NOT use Write to overwrite the page (loses history fidelity).
- Do NOT auto-update "Last reviewed" without asking; the timestamp is a human attestation.
- Do NOT migrate content from a stray docs/ file silently — that flow is `/wiki-new` after the user decides per `wiki-vs-stray-docs`.
- Do NOT push.
