---
name: wiki-structure
description: GitHub Wiki organization rules — flat-namespace, filename-uniqueness, internal-link convention without .md extension, Home and _Sidebar and _Footer ownership, sibling-clone path convention. Also owns hub-first themed IA (parents are real hub pages, never empty folders) and a validated default structure template. Activates when initialising a new wiki, adding or renaming a wiki page, restructuring sidebar / Home navigation, or auditing the wiki for filename collisions. Adapter switches behavior for GitLab / Azure DevOps / MkDocs wikis (tree namespaces allowed); on azure-devops-wiki the reliable internal link is the page-ID URL form.
version: 0.4.0
last_reviewed: 2026-06-22
owns:
  - flat-namespace rule for GitHub Wiki (filenames become URLs)
  - filename-uniqueness rule across the wiki repo
  - internal-link convention (no .md extension, no folder path for GitHub Wiki)
  - Home / _Sidebar / _Footer authorship rules
  - sibling-clone path convention (the wiki repo lives next to the main repo)
  - rename-on-collision pattern
  - no-numeric-prefix-in-visible-labels rule
  - wiki-flavour adapter (github-wiki / gitlab-wiki / azure-devops-wiki / mkdocs-tree)
  - azure-devops-wiki specifics (.order encoded basenames, auto-built nav, human-provisioned wiki, MCP reversed insert order)
  - hub-first themed-section IA (every parent is a real hub page, never an empty/link-only folder)
  - reader-facing section labels (name the reader's target artifact, not internal provenance doctrine)
  - validated default structure template for business/product wikis (adapt per project)
  - azure-devops-wiki page-ID URL link convention (the reliable resolvable internal-link form)
  - azure-devops-wiki pagemoves/REST mechanics (newOrder mandatory, REST-for-move/delete, tree-omits-id, childless-delete, no-auto-repoint of inbound links)
  - azure-devops-wiki spaces-vs-hyphens slug risk (dashed relative links break on hyphen-titled pages)
defers_to:
  - wiki-link-validation (the audit that enforces these rules at scan time; owns the resolution-based audit that proves a page-ID link actually resolves)
  - wiki-safe-updates (the workflow that applies any structural change; owns the approval/diff gate plus the repoint ordering for move/rename/delete)
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

## Hub-first themed IA (real hub pages, never empty folders)

Every parent / section node is a **real hub page**, never a blank or link-only placeholder. A hub carries:

- a one-line purpose;
- a "what is in here / who should read it" responsibilities table;
- an optional compact orientation map (a few Mermaid nodes — keep it small);
- curated links to its children and to the matching workflow pages;
- an explicit "this hub summarises; the authoritative rules live on the child pages" note.

Section labels name the **reader's target artifact** (e.g. `Product-Specification`), not an internal provenance doctrine (e.g. `Business-Source-of-Truth`). "Source of truth" is a principle expressed *inside* the landing page, never a navigation label.

Hard line: a hub **never** restates a child's authoritative rule bodies — that would create a competing second source. (Defer journey-vs-source separation and master-swimlane-once to `wiki-mermaid` / `wiki-source-of-truth`; only the IA shape is owned here.)

On `azure-devops-wiki` this is **structurally enforced**: there is no empty-folder option, so a missing hub is a missing page.

## Recommended default structure template (business/product wikis)

A **validated default to adapt per project**, not a mandate. The exact section set should be tuned to the project; this is the validated shape that worked for a real business/product wiki.

Compact top-level shape:

```
Home
Product-Specification        (rich landing + themed hubs)
Workflows-Overview           (master swimlane + journey pages)
Technical-Reference          (engineering reference)
Development-SOPs              (engineering governance)
```

| Section | Purpose | Expected child pages | Required hub content | Must NOT contain |
|---|---|---|---|---|
| **Home** | Wiki entry point + source-of-truth model + reading path | (none; links out) | What the wiki is; quickstart; by-role/by-topic links; source-of-truth assignments; "backlog is delivery tracking, not a wiki source" note | Full rule bodies; long prose |
| **Product-Specification** | Business/system source-of-truth landing | the themed hubs below | Reading path; "how this section is organised" table; journey-view-vs-source-page explainer; doc-structure Mermaid map | Authoritative rule restatement |
| **Overview-and-Scope** | Orientation: what the product is, in/out scope, actors | Product-Overview; Scope-and-Non-Scope; Actors-and-Operating-Model | Short product summary; scope posture; actor summary; page table | Detailed rules; full scope tables (link to child) |
| **Administration-and-Configuration** | Platform vs tenant administration | Platform-Administration; Tenant-Administration | Platform-vs-tenant responsibility table; provision→configure mini-map | Per-field config contracts (live on children) |
| **Core-Records-and-Processing** | Core workspace + document processing | Records-Workspace-and-Correspondence; OCR-Search-and-Document-Processing | How correspondence/records/OCR/search relate; compact capability map | The full letter state machine / OCR pipeline (children own these) |
| **Workflows-Overview** | Journey hub | one journey page per workflow + a Deferred/Out-of-Scope notes page | The single master end-to-end swimlane; index table (workflow → detail page → optional backlog ref) | Authoritative rules; duplicated full diagrams |
| **Rules-Audit-and-Governance** | Cross-cutting rules, SLA, audit, retention | Business-Rules-SLA-and-Audit | Summary of rule families with explicit "summary, not source" disclaimer | Re-derived rule bodies |
| **Integrations-and-Contracts** | External integration contracts | one contract page per integration | Contract-vs-workflow distinction; integration list | Wire-level detail duplicated from the contract page |
| **Technical-Reference** | Engineering reference (stack/architecture) | Technology-Stack-and-Architecture | "how it's built, not what it must do" framing | Business rules |
| **Development-SOPs** | Engineering governance | the SOP set | Orientation + grouped SOP index | Business rules |

General hub rule for every section (stated once): explainer + orienting table + curated links; **never** a blank or link-only parent, and **never** a restatement of a child's authoritative rules.

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
- **Never** leave a parent/section as a blank or link-only folder — every parent is a real hub page (and a hub never restates a child's authoritative rules).
- **Never** emit a relative `[text](/Dashed-Path)` link to a hyphen-titled page on `azure-devops-wiki` — use the page-ID URL form and validate by resolution (defer the audit to `wiki-link-validation`).
- **Never** call `pagemoves` without `newOrder` (HTTP 500), and **never** delete a section page that still has children (move children out first).
- **Never** assume "dashes = spaces" on `azure-devops-wiki`; pick one slug convention deliberately and never auto-migrate space-vs-hyphen titles.

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
- [ ] Every parent/section is a real hub page (one-line purpose + responsibilities table + curated links; non-empty), and no hub restates a child's authoritative rules.
- [ ] Section labels name the reader's target artifact, not internal provenance doctrine.
- [ ] (`azure-devops-wiki`) Internal links use the page-ID URL form `/{pageId}/{Slug}`; no dashed relative links to hyphen-titled pages.
- [ ] (`azure-devops-wiki`) Any move used `pagemoves` with `newOrder`; any section delete operated on a childless page; inbound links repointed (per `wiki-safe-updates`).

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
| `azure-devops-wiki` | Yes (`.order` controls hierarchy) | Per-folder | Page-ID URL `/{pageId}/{Slug}` (dashed relative links break on hyphen-titled pages); see adapter section |
| `mkdocs-tree` | Yes | Per-folder | Folder-path with `.md` |

Beyond the constraint list, the rest of the skill (Home / Sidebar / Footer authorship, the no-numeric-prefix rule, the curated-sidebar principle) applies to every flavour.

## Azure DevOps Wiki adapter (`azure-devops-wiki`)

Azure DevOps project wikis are git-backed but differ from GitHub Wiki in ways that silently break a naive copy:

- **No `_Sidebar.md` / `_Footer.md`.** Azure auto-builds the left-hand navigation from the page tree and has no footer concept — those files just render as ordinary pages. Drop them on migration.
- **A `.order` file controls nav order.** It lists page basenames, one per line. Azure encodes a literal hyphen in a page filename as `%2D`, so `.order` entries must use the exact **encoded** basenames or the ordering silently no-ops.
- **Link by page-ID URL, not by dashed relative path.** The reliable resolvable internal-link form is the page-ID URL `.../_wiki/wikis/{WikiName}/{pageId}/{Slug}` (owner-confirmed). Do NOT emit a relative `[text](/Dashed-Path)` link to a hyphen-titled page: Azure resolves the hyphens as spaces (`?pagePath=/Dashed Path`) and the link 404s **even though the API path exists** — so a path-existence audit false-passes. Plain dashed relative links resolve ONLY for genuine space-titled pages. Pick one convention deliberately (page-ID URL recommended) and validate by resolution — defer that audit to `wiki-link-validation`.
- **Collapsible nav = sub-folders.** Nesting a page under a folder makes it a child in the tree but changes its path, so every inbound internal link to it must be rewritten.
- **The wiki must already exist — a human provisions it.** Neither the Azure DevOps REST API nor the `azure-devops` MCP can *create* a project wiki; a human creates it once via Project Settings → Wiki ("Create project wiki"). A page-write that returns **"Wiki not found" is NOT a permission error** — it means no wiki exists yet. Ask the user to create it, then fill pages via MCP.
- **MCP page-create order comes out reversed.** The MCP inserts each new sub-page at the **top** of the parent's order file, so pages land in reverse creation order. The fix is a `pagemoves` call with `newOrder` per page (see Move/delete/reorder below) rather than re-creating pages.

### Move, delete, reorder — REST mechanics (`azure-devops-wiki`)

The `azure-devops` MCP has **no move and no delete tool**. REST is required for move, delete, in-place reorder, ETag-based content edits, and page-id lookup. The MCP `wiki_*` tools cover create/update/read only.

- **Move via REST.** `POST .../wiki/wikis/{id}/pagemoves` with body `{path, newPath, newOrder}`. **`newOrder` is MANDATORY** — omitting it returns HTTP 500 `"Nullable object must have a value."` A move/rename of a parent re-paths all of its descendants.
- **Delete via REST, childless only.** `DELETE .../pages?path=<enc>` operates on a **childless** page. Move children out first; a section is a real page, so there is no "delete an empty folder" — deleting a section deletes a real page.
- **Azure NEVER auto-repoints inbound links** on a move or rename. Every inbound reference (other pages, landing/index pages, intra-page anchors) must be repointed deterministically. Defer the repoint workflow, its approval gate, and the replacement ordering to `wiki-safe-updates`.
- **The page-tree REST omits page id.** `GET .../wiki/wikis/{id}/pages?path=/&recursionLevel=full` returns the tree **without** page `id`; fetch each id per page (`GET .../pages?path=<enc>`) before building page-ID links or a `pagemoves` worklist.

### Slug convention risk: spaces vs hyphens (`azure-devops-wiki`)

A single Azure wiki can MIX space-titled pages (dashed relative links resolve) and hyphen-titled pages (dashed relative links break). Do NOT assume "dashes = spaces." Pick one convention deliberately and validate by resolution. Trade-off *(uncertain)*: converting to genuine space titles fixes dashed links but changes display titles and breaks `?pagePath=`-form links — decide per project, never auto-migrate.

See `wiki-mermaid` → Platform compatibility for the matching Azure DevOps Mermaid fence rules (`::: mermaid`, `graph` not `flowchart`, no subgraph links).

## Cross-references

- `wiki-link-validation` — enforces these rules during audit; owns the resolution-based audit that proves a page-ID link actually resolves (not just that the API path exists).
- `wiki-safe-updates` — the workflow for applying structural changes; owns the approval/diff gate and the repoint ordering for move/rename/delete (specific-child-paths first, bare-parent path last).
- `wiki-authoring` — content patterns inside the structure this skill defines.
- `wiki-vs-stray-docs` — refuses to create `docs/` folders that compete with the wiki.
- `wiki-code-vs-docs-discrepancy` — applied when wiki claims contradict the code.
- `wiki-mermaid` — Azure DevOps Mermaid fence rules that pair with this adapter.
- `wiki-plantuml` — where swimlane artifacts live under each flavour: GitHub commits the rendered image into the `.wiki` repo `/images/` (leading-slash wiki-link); Azure uploads to the hidden `/.attachments` folder (root-relative ref); the `.puml` source sits next to the wiki. Filename-uniqueness applies to the `swimlane-<epic>-<slug>` basename.
- `wiki-link-auditor` (agent) — automates the audit.
