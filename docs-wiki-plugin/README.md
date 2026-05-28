# docs-wiki

![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)
![Status](https://img.shields.io/badge/status-functional-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Generic toolkit for creating, organising, editing, validating, and auditing a project Wiki.

This plugin packages the rules every project needs when its team-facing documentation lives in a wiki — flat-namespace + filename-uniqueness rules for GitHub Wiki, internal-link conventions, Mermaid diagram authoring discipline, broken-link sweeps, code-vs-wiki drift reporting, and a push-approval gate that refuses to publish without explicit user approval.

## Explicit boundary — what this plugin does NOT do

> **Wiki-to-memory sync is out of scope.** This plugin only writes, organises, validates, and audits the wiki itself. Synchronising wiki content into long-term Claude memory is a separate future plugin.

## What this plugin owns

### Skills (under `skills/`)

| Skill | Owns |
|---|---|
| `wiki-structure` | Flat-namespace + filename-uniqueness + internal-link convention (GitHub Wiki primary, others adapter-configurable) |
| `wiki-authoring` | Business docs / engineering SOPs / user manuals / role guides / workflow docs / release & handover / onboarding templates |
| `wiki-mermaid` | Mermaid diagram authoring rules — TD direction, shape vocabulary, four-class colour palette, label hygiene, code-path scrub from business diagrams |
| `wiki-link-validation` | Broken-link sweep, missing-page detection, visible-numeric-prefix scan, internal-link convention check |
| `wiki-code-vs-docs-discrepancy` | Report wiki-vs-code drift with `file:line` evidence; never silently choose one side |
| `wiki-safe-updates` | Diff preview before write, no force-push, push-approval gate, retired-folder awareness |
| `wiki-vs-stray-docs` | Refuse to create stray `docs/` folders when a wiki exists; surface the conflict to the user |

### Commands

| Command | Purpose |
|---|---|
| `/wiki init <wiki-path>` | Initialise wiki structure (Home / _Sidebar / _Footer scaffolds) |
| `/wiki audit` | Link validation + filename-collision audit + visible-prefix scan + drift report |
| `/wiki update <page>` | Guided edit of an existing page with diff preview |
| `/wiki new <page>` | Create a new page with template (SOP / role guide / runbook / onboarding) |
| `/wiki drift` | Code-vs-wiki discrepancy sweep — produces a table; never edits silently |
| `/wiki sync-audit` | Audit-first sync mode — reports differences without applying changes |

### Agents

| Agent | Purpose |
|---|---|
| `wiki-link-auditor` | Read-only scan for broken links + missing pages + visible-numeric-prefixes |
| `wiki-cleanup-validator` | Pre-delete reference check — refuses to remove a wiki page that other pages still link to |
| `wiki-drift-reporter` | Read-only sweep producing the wiki-vs-code drift table |

### Hooks

| Hook | Trigger | Purpose |
|---|---|---|
| `PreToolUse` | `Bash(git push)` against any path containing `.wiki` | Push-confirmation gate — refuse without explicit user approval |
| `PreToolUse` | `Write` matching `docs/**` in a repo that has a `<repo>.wiki/` sibling | Stray-docs warning — suggest the wiki instead |

## Wiki flavours supported

| Flavour | Notes |
|---|---|
| GitHub Wiki (sibling `<owner>/<repo>.wiki.git`) | Primary target. Flat-namespace + filename-uniqueness strictly enforced. |
| In-repo `wiki/` folder | Used as a staging ground or single-repo team docs. Adapter switches the link convention accordingly. |
| GitLab Wiki | Adapter-configurable; tree namespace allowed. |
| Azure DevOps Wiki | Adapter-configurable; tree namespace allowed. |
| MkDocs / Docusaurus markdown | Adapter `mkdocs-tree` mode — folders allowed, link convention adjusted. |

## Adapter inputs (asked once)

| Input | Notes |
|---|---|
| Wiki location | Sibling clone path / in-repo `wiki/` folder / GitLab path / Azure DevOps path |
| Source-of-truth roots | Which folders authoritatively describe runtime behaviour — typically `src/`, `app/`, `services/`, ORM schema, `.github/workflows/` |
| Retired-folder list | Folders deliberately archived — historical noise, never reported as drift |
| Wiki flavour | `github-wiki` (default) / `gitlab-wiki` / `azure-devops-wiki` / `mkdocs-tree` |

## What this plugin deliberately does NOT do

- Sync wiki content into Claude memory or any vector store. **Separate future plugin.**
- Author or modify code. It only reads code (for drift detection) and writes wiki pages.
- Push to remote without explicit user approval. The push-approval gate is non-negotiable.
- Recreate `docs/` folders. If a wiki exists, the wiki is the source of truth.
- Replace your project's official SOP. It enforces conventions, it does not author your business decisions.

## Safety rules baked in

1. **Push-approval gate** — `git push` against any `.wiki` path requires explicit per-push approval.
2. **Diff preview before write** — every `/wiki update` shows the diff and waits for confirmation.
3. **Filename-uniqueness audit** — GitHub Wiki rejects two `.md` files with the same basename anywhere in the wiki repo; the audit catches this before push.
4. **No force-push** — ever.
5. **Never silently choose** — code-vs-wiki drift is always surfaced to the user with `file:line` evidence; the plugin never picks a side on its own.
6. **Retired-folder awareness** — folders the user has marked retired are never flagged as drift, but stray-docs warnings still apply.

## Installation

This plugin is published as part of the `taqat-techno-plugins` marketplace. To install:

1. Open Claude Code.
2. Run `/plugins`.
3. Click **Add Marketplace** and enter `https://github.com/taqat-techno/plugins.git` (skip if already installed).
4. Find **docs-wiki** and click **Install**.

## Roadmap

| Version | Scope |
|---|---|
| `0.1.0` | Scaffold |
| `0.2.0` (this release) | 7 skills + 6 commands + 3 agents + 2 hooks (push gate + stray-docs warning) |
| `0.3.0` | Polished GitLab / Azure DevOps Wiki adapters; `/wiki-archive` command; ADR numbering helper |
| `1.0.0` | First stable release after real-project shakedown |

## Related plugins

- [`react-admin-kit`](../react-admin-kit-plugin/README.md) — for building the admin panel itself.
- [`qa-browser`](../qa-browser-plugin/README.md) — for verifying the admin panel actually works as the wiki claims.

## License

MIT. See [`LICENSE`](./LICENSE).

## Author

TAQAT Techno · [github.com/taqat-techno](https://github.com/taqat-techno) · `info@taqatechno.com`
