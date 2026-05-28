---
name: wiki-structure
description: GitHub Wiki organization rules — flat-namespace, filename-uniqueness, internal-link convention without .md extension, Home and _Sidebar and _Footer ownership, sibling-clone path convention. Activates when initialising a new wiki, adding or renaming a wiki page, restructuring sidebar / Home navigation, or auditing the wiki for filename collisions. Adapter switches behavior for GitLab / Azure DevOps / MkDocs wikis (tree namespaces allowed).
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - flat-namespace rule for GitHub Wiki (filenames become URLs)
  - filename-uniqueness rule across the wiki repo
  - internal-link convention (no .md extension, no folder path for GitHub Wiki)
  - Home / _Sidebar / _Footer authorship rules
  - sibling-clone path convention (the wiki repo lives next to the main repo)
  - rename-on-collision pattern
  - no-numeric-prefix-in-visible-labels rule
  - wiki-flavour adapter (github-wiki / gitlab-wiki / azure-devops-wiki / mkdocs-tree)
defers_to:
  - wiki-link-validation (the audit that enforces these rules at scan time)
  - wiki-safe-updates (the workflow that applies any structural change)
  - wiki-code-vs-docs-discrepancy (when structural changes contradict code-side documentation)
  - project owner (the user picks the wiki flavour and resolves naming collisions)
user_invocable: false
---

# wiki-structure

## Purpose

GitHub Wiki has surprising constraints that bite teams who learned wiki conventions on platforms with tree namespaces. The biggest surprise: in GitHub Wiki, the filename IS the URL slug. Two `.md` files anywhere in the wiki repo with the same basename collide silently. This skill owns those constraints and the conventions that work with them.

For other wiki flavours (GitLab, Azure DevOps, MkDocs), the constraints differ. The skill adapts via the `wikiFlavour` adapter input. The default is `github-wiki` because that is where the constraints are tightest.

## When to use

Activate when:

- Initialising a new wiki (running `/wiki-init`).
- Adding a new wiki page.
- Renaming a wiki page.
- Restructuring the sidebar, Home page, or footer.
- Auditing the wiki for collisions or link breakage.
- Migrating between wiki flavours.

Skip when:

- Editing content within an existing page (no structural change). Use `wiki-authoring` instead.

## Inputs (adapter)

1. **Wiki location** — path to the wiki repo's local checkout.
   - Convention for GitHub Wiki: sibling clone at `../<repo>.wiki/`.
   - In-repo `wiki/` folder for repos that publish via CI.
   - GitLab / Azure DevOps Wiki: cloned per platform's instructions.
2. **Wiki flavour** — `github-wiki` (default), `gitlab-wiki`, `azure-devops-wiki`, `mkdocs-tree`.
3. **Owner / repo identifiers** — for GitHub Wiki, the `<OWNER>/<REPO>` pair. Used to construct the wiki repo URL `<OWNER>/<REPO>.wiki.git`.
4. **Sidebar style** — explicit list (default) or auto-generated from page index.

## The flat-namespace rule (GitHub Wiki)

GitHub Wiki publishes every `.md` file in the repo as a page at:

```
https://github.com/<OWNER>/<REPO>/wiki/<basename-without-md>
```

Critical consequences:

1. **Folders are organisation only.** A file at `runbooks/deploy.md` and a file at `sop/deploy.md` BOTH publish as `https://github.com/<OWNER>/<REPO>/wiki/deploy` — and only one wins (last write).
2. **Internal links use basename only.** `[Deploy SOP](deploy)` — NOT `[Deploy SOP](sop/deploy.md)`.
3. **`Home.md` is the wiki's landing page.** Always named `Home.md`, always at the wiki repo root.
4. **`_Sidebar.md` is the navigation sidebar.** Visible on every page. Always at the wiki repo root.
5. **`_Footer.md` is the page footer.** Optional. Always at the wiki repo root.
6. **Spaces in filenames become hyphens in URLs.** `Engineering Handbook.md` → `Engineering-Handbook`.

For `gitlab-wiki`, `azure-devops-wiki`, and `mkdocs-tree`: folders ARE part of the URL; tree namespaces are valid. The skill relaxes the flat-namespace and filename-uniqueness rules and uses platform-appropriate link conventions.

## The filename-uniqueness rule (GitHub Wiki)

No two `.md` files anywhere in the wiki repo may share a basename. The rule is non-negotiable on GitHub Wiki — collisions cause silent overwrite, broken navigation, and lost content.

Enforcement:

- Initialisation (`/wiki-init`) refuses to populate a wiki repo that already has collisions.
- Audit (`/wiki-audit`) lists collisions as a HIGH finding.
- New page creation (`/wiki-new`) refuses a basename that already exists.

Rename strategy for collisions: append a disambiguating qualifier:

```
sop/deploy.md          + runbooks/deploy.md
→ Deploy-SOP.md        + Deploy-Runbook.md
```

Choose qualifiers that read naturally as page titles (the basename is the URL AND the default page title).

## The internal-link convention

For GitHub Wiki:

| Link target | Wrong | Right |
|---|---|---|
| Page in the wiki | `[Deploy](sop/deploy.md)` | `[Deploy](Deploy-SOP)` |
| Page with spaces in title | `[Engineering Handbook](Engineering%20Handbook.md)` | `[Engineering Handbook](Engineering-Handbook)` |
| Section in another page | `[Rollback](sop/deploy.md#rollback)` | `[Rollback](Deploy-SOP#rollback)` |
| File in main repo | `[deploy.sh](deploy.sh)` | `[deploy.sh](https://github.com/<OWNER>/<REPO>/blob/main/deploy.sh)` |

For `gitlab-wiki`, `azure-devops-wiki`, `mkdocs-tree`: folder paths and `.md` extensions in links may be valid per platform; the skill adjusts.

## Home, _Sidebar, _Footer authorship

### Home.md

- Index page. First thing visitors see at `https://github.com/<OWNER>/<REPO>/wiki`.
- Recommended sections:
  - **What this wiki is** (1 paragraph).
  - **Quickstart** (3–6 links to the most-used pages).
  - **By role** (e.g., "I'm a new engineer", "I'm on-call", "I'm onboarding a customer").
  - **By topic** (links into each major area: SOPs, runbooks, integrations, …).
  - **Source of truth assignments** (which topics are wiki-authoritative vs code-authoritative — see `wiki-code-vs-docs-discrepancy`).
  - **Maintainers + last reviewed date**.
- Anti-pattern: a 200-line `Home.md` that everyone scrolls past. Keep it scannable.

### _Sidebar.md

- Renders on every page.
- Hierarchical bullet list of links.
- Group by major section; do NOT put every page in the sidebar.
- Use the page's title (NOT the filename, NOT a numeric prefix) as the link label.

```markdown
- [Home](Home)
- **SOPs**
  - [Deploy](Deploy-SOP)
  - [Incident response](Incident-Response-SOP)
  - [On-call](On-Call-SOP)
- **Runbooks**
  - [Restart the API](Restart-API-Runbook)
  - [Rotate database password](Rotate-DB-Password-Runbook)
```

### _Footer.md

- Optional. Renders on every page.
- Use for: maintenance contact, last-reviewed convention, link to the contribution guide.
- Do NOT use for promotional content / corporate boilerplate.

## No-numeric-prefix-in-visible-labels rule

It is tempting to number wiki pages (`01-Home.md`, `02-Deploy.md`) to control sort order in a flat directory. Do not.

- The numeric prefix becomes part of the URL: `Deploy` → `02-Deploy`. Existing inbound links break.
- The numeric prefix shows in the page title by default. "02 Deploy" is not a title.
- Re-ordering forces re-numbering, which forces URL-renames, which forces link updates.

The right approach: use the sidebar for navigation order; let filenames be stable URL slugs.

If a project's wiki already uses numeric prefixes, migrate page-by-page (with redirect docs if needed). Audit flags numeric-prefix usage as a MEDIUM finding.

## Sibling-clone path convention (GitHub Wiki)

GitHub Wiki is a separate git repository from the main repo. The recommended local layout:

```
~/code/<organisation>/
  <repo>/          ← main repo (app code; CI; etc.)
  <repo>.wiki/     ← sibling clone of the wiki repo
```

Clone the wiki the first time:

```bash
git clone git@github.com:<OWNER>/<REPO>.wiki.git
# This creates a sibling directory <repo>.wiki/
```

The wiki repo has its own `git push`, its own commit history, its own branch (default: `master`). Pushes to the main repo do NOT update the wiki. Updating the wiki requires a separate `git push` from the wiki clone.

`/wiki-init` checks for the sibling clone; if missing, prints the exact clone command and stops.

## Safety gates

- **Never** create a wiki page whose basename collides with an existing page (GitHub Wiki) — refuse and surface.
- **Never** restructure the wiki to use tree namespaces on GitHub Wiki (folders → URL collisions).
- **Never** use numeric prefixes in filenames.
- **Never** use `.md` extensions in internal links on GitHub Wiki.
- **Never** push the wiki repo without going through `wiki-safe-updates` (approval gate).
- **Never** modify `_Sidebar.md` or `Home.md` without diff preview (per `wiki-safe-updates`).

## Validation checklist

Before committing a structural wiki change:

- [ ] No filename collisions in the wiki repo (basename comparison).
- [ ] No numeric prefixes in filenames.
- [ ] All internal links use the basename-only convention (GitHub Wiki) or the adapter's convention.
- [ ] `Home.md` exists at wiki repo root.
- [ ] `_Sidebar.md` exists at wiki repo root (recommended).
- [ ] New page's basename matches its intended URL slug.
- [ ] Cross-references from other pages updated for any rename.
- [ ] Wiki sibling clone present (or in-repo `wiki/` folder for non-GitHub flavours).

## Output format

When initialising a wiki, output:

```
WIKI INITIALISED — <wiki-path>
  Flavour: github-wiki
  Sibling clone: <path> (verified)
  Files created:
    Home.md          ← index / quickstart / by-role / source-of-truth assignments
    _Sidebar.md      ← navigation
    _Footer.md       ← optional; not created unless --footer flag
  Source-of-truth assignments: <list — supplied by user or prompted>
  Next: /wiki-new <Page-Name> to add the first content page
```

When auditing structure, output:

```
WIKI STRUCTURE AUDIT — <wiki-path>
  Flavour: github-wiki
  Pages: <count>
  Filename collisions: <count> — see findings table
  Numeric-prefix violations: <count>
  Internal-link convention violations: <count>
  Missing Home.md: <yes | no>
  Missing _Sidebar.md: <yes | no>
  Sidebar references missing pages: <list>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Folders in GitHub Wiki for namespacing | Folders become URL collisions; one page silently wins | Flat namespace; disambiguate via filename |
| `.md` extension in internal links | GitHub Wiki returns 404 for `Page.md` URLs | Basename only |
| Numeric prefix on filenames | URL renames every reorder; titles read as "02 Deploy" | No numeric prefix |
| Two pages with same basename in different folders | Silent overwrite on push | Refuse; rename |
| Editing wiki by typing in the GitHub Wiki web UI | No diff preview; no review; no audit | Use the local sibling clone + git workflow |
| 500-line Home.md | Nobody scrolls; defeats the index purpose | Keep scannable; link to detail pages |
| Sidebar mirrors every single page | Sidebar becomes 200 entries; nobody navigates it | Curated; major sections only |
| Creating a wiki page about a wiki page | Confusing meta; usually redundant | Document the topic; not the doc |

## Portability rationale

The flat-namespace and filename-uniqueness rules are specific to GitHub Wiki. The skill explicitly adapts via `wikiFlavour`:

| Flavour | Folders allowed | Filename uniqueness across repo | Internal-link convention |
|---|---|---|---|
| `github-wiki` (default) | No (URL-flat) | Required | Basename only |
| `gitlab-wiki` | Yes | Per-folder | Folder-path with optional `.md` |
| `azure-devops-wiki` | Yes (`.order` controls hierarchy) | Per-folder | Folder-path with `.md` |
| `mkdocs-tree` | Yes | Per-folder | Folder-path with `.md` |

Beyond the constraint list, the rest of the skill (Home / Sidebar / Footer authorship, the no-numeric-prefix rule, the curated-sidebar principle) applies to every flavour.

## Cross-references

- `wiki-link-validation` — enforces these rules during audit.
- `wiki-safe-updates` — the workflow for applying structural changes.
- `wiki-authoring` — content patterns inside the structure this skill defines.
- `wiki-vs-stray-docs` — refuses to create `docs/` folders that compete with the wiki.
- `wiki-code-vs-docs-discrepancy` — applied when wiki claims contradict the code.
- `wiki-link-auditor` (agent) — automates the audit.
