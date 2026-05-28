---
description: Initialise a project wiki — verify the sibling clone (GitHub Wiki) or in-repo wiki folder; scaffold Home / _Sidebar / optional _Footer; cache adapter inputs (wiki flavour, owner/repo, source-of-truth roots, retired folders). Refuses to populate a wiki repo that already has filename collisions. Goes through wiki-safe-updates for every write.
argument-hint: "[<wiki-path>] [--flavour github-wiki|gitlab-wiki|azure-devops-wiki|mkdocs-tree] [--footer]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write, Edit
---

# /wiki-init

You are initialising a project wiki. Apply `wiki-structure`, `wiki-authoring`, `wiki-safe-updates`. Cache adapter inputs to `.docs-wiki.local.json`.

## Step 0 — Resolve the wiki path

Argument resolution order:

1. Explicit `<wiki-path>` argument → use it.
2. Adapter cache `.docs-wiki.local.json` `wikiPath` → use it.
3. Detect a sibling clone matching `../<current-repo>.wiki/` → suggest it.
4. None of the above → ask the user.

Confirm the path exists and is a directory. If it is a git repo, capture the remote URL.

If GitHub Wiki flavour AND no sibling clone present, print the exact clone command and stop:

```
GitHub Wiki not cloned yet. Clone the sibling repo first:

  cd <parent-of-current-repo>
  git clone git@github.com:<OWNER>/<REPO>.wiki.git

Then re-run /wiki-init with the cloned path.
```

## Step 1 — Resolve flavour

Order:

1. `--flavour` flag → use it.
2. Adapter cache `wikiFlavour` → use it.
3. Detect from path / remote URL:
   - Remote matches `*.wiki.git` → `github-wiki`.
   - Path inside a GitLab project → `gitlab-wiki`.
   - Path inside Azure DevOps → `azure-devops-wiki`.
   - Path under `docs/` or `mkdocs.yml` adjacent → `mkdocs-tree`.
4. Ambiguous → ask.

## Step 2 — Pre-flight checks (read-only)

Run `wiki-link-validation` quickly:

- Filename collisions (only on flat-namespace flavours).
- Numeric prefixes.
- Existing Home / _Sidebar status.

If HIGH findings (collisions on a flat-namespace wiki), REFUSE to populate and report:

```
WIKI INIT REFUSED

  Reason: filename collisions detected in <wiki-path>
  Per wiki-structure, GitHub Wiki requires basename uniqueness.

  Collisions:
    <list>

  Fix: rename one of each pair to a disambiguating basename, then re-run.
```

If only LOW / MEDIUM (numeric prefixes), warn and continue with consent.

## Step 3 — Adapter intake

If `.docs-wiki.local.json` is absent or incomplete, prompt for:

1. **Wiki flavour** (defaulted from Step 1).
2. **Owner / repo** (for GitHub Wiki; for constructing the `.wiki.git` URL and the canonical link prefix).
3. **Source-of-truth roots** — which folders in the main repo authoritatively describe runtime behaviour. Typical answers: `src/`, `app/`, `services/`, `prisma/schema.prisma`, `.github/workflows/`. Used by `wiki-code-vs-docs-discrepancy` and `wiki-drift-reporter`.
4. **Retired-folder list** — folders deliberately archived. Default: `_archived/`, `_legacy/`, `_deprecated/`, `historical/`. Configurable.
5. **Exceptions list** for `wiki-vs-stray-docs` — paths inside the main repo that legitimately exist as docs alongside the wiki (e.g., `docs/api/` auto-generated). Default empty.
6. **Sidebar style** — `explicit` (default, hand-authored) or `auto` (generated from page index).

Write `.docs-wiki.local.json` at the **main repo root** (NOT inside the wiki repo). Surface the path; ask the user to add it to `.gitignore` if not already.

## Step 4 — Scaffold the three structural pages

Through `wiki-safe-updates` (diff preview required for each):

### `Home.md`

```markdown
# <Project> Wiki

> **Audience:** anyone working on or with the project
> **Last reviewed:** <YYYY-MM-DD> by <maintainer>

<one-paragraph: what this wiki is>

## Quickstart

- I'm a **new engineer** → [Onboarding-Engineer](Onboarding-Engineer)
- I'm **on-call** → [On-Call-SOP](On-Call-SOP)
- I'm onboarding a **customer** → [Customer-Onboarding](Customer-Onboarding)

## By topic

- **SOPs** — [Deploy-SOP](Deploy-SOP), [Incident-Response-SOP](Incident-Response-SOP)
- **Runbooks** — [Restart-API-Runbook](Restart-API-Runbook)
- **Architecture** — [Architecture-Overview](Architecture-Overview)
- **Decisions** — [Decision-Records](Decision-Records)

## Source-of-truth assignments

The wiki is authoritative for:
- Business processes, SOPs, workflows
- Operator runbooks
- Role guides + onboarding
- Decision records (ADRs)

The code repo is authoritative for:
- Runtime API behavior
- Database schema
- Deployment process (the wiki documents; the workflow files execute)
- Permission matrix (the wiki documents; the route handlers enforce)

When the wiki and the code contradict, follow wiki-code-vs-docs-discrepancy:
report; do not silently choose.

## Maintainers

<list with contact + on-call rotation link>
```

(Substitute placeholders with real values during scaffold.)

### `_Sidebar.md`

```markdown
- [Home](Home)
- **Onboarding**
  - [Engineer onboarding](Onboarding-Engineer)
  - [Operator onboarding](Onboarding-Operator)
- **SOPs**
  - [Deploy](Deploy-SOP)
  - [Incident response](Incident-Response-SOP)
  - [On-call](On-Call-SOP)
- **Runbooks**
  - [Restart API](Restart-API-Runbook)
- **Reference**
  - [Architecture](Architecture-Overview)
  - [Decisions](Decision-Records)
```

(Sidebar order matters — curated, not auto-generated.)

### `_Footer.md` (only if `--footer` flag)

```markdown
> Maintained by <team>. Pages have a "Last reviewed" header at the top.
> For wiki contribution guidelines, see [Contributing-to-the-Wiki](Contributing-to-the-Wiki).
```

## Step 5 — Verify + report

After all writes through `wiki-safe-updates`:

```
WIKI INITIALISED — <wiki-path>
  Flavour: <github-wiki | ...>
  Sibling clone: <verified path>
  Files created:
    Home.md
    _Sidebar.md
    _Footer.md   ← only if --footer
  Adapter cache: .docs-wiki.local.json — <count> keys
  Source-of-truth roots: <list>
  Retired folders: <list>
  Exceptions: <list>

  Next steps:
    1. Review the scaffolded Home.md and _Sidebar.md (placeholders to fill in).
    2. /wiki-new <Page-Name> --template <sop|runbook|role-guide|...> for first content pages.
    3. /wiki-audit periodically to catch drift.
    4. To publish: cd <wiki-path>; git status; git add ... ; git commit; git push (push-approval gate applies).
```

## Safety

- Refuses to populate a wiki repo with existing filename collisions (HIGH findings).
- Every write goes through `wiki-safe-updates` (diff preview).
- Never pushes; push is always a separate explicit user action with the approval phrase.
- Refuses to write the adapter cache inside the wiki repo (it belongs in the main repo).
- Refuses to write any file outside the wiki repo path (no escape).
- Scaffold templates include placeholders, not real content; the user fills in their domain.

## Modes

- `--flavour <type>` — override detected flavour.
- `--footer` — also scaffold `_Footer.md`.

## What NOT to do

- Do NOT push the wiki after scaffolding. The user pushes when ready.
- Do NOT auto-populate page content beyond the structural scaffold.
- Do NOT modify the main repo's `.gitignore` automatically — print the line for the user to add.
