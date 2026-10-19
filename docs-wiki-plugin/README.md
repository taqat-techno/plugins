# docs-wiki

![Version](https://img.shields.io/badge/version-0.9.0-blue.svg)
![Status](https://img.shields.io/badge/status-functional-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Generic toolkit for creating, organising, editing, validating, and auditing a project Wiki.

This plugin packages the conventions and helpers every project needs when its team-facing documentation lives in a wiki — flat-namespace + filename-uniqueness rules for GitHub Wiki, internal-link conventions, Mermaid diagram authoring discipline, broken-link sweeps, and code-vs-wiki drift reporting. It is a **non-blocking helper**: it offers conventions and audits but never gates or blocks your git push, force-push, or writes.

## Explicit boundary — what this plugin does NOT do

> **Wiki-to-memory sync is out of scope.** This plugin only writes, organises, validates, and audits the wiki itself. Synchronising wiki content into long-term Claude memory is a separate future plugin.

## What this plugin owns

### Skills (under `skills/`)

| Skill | Owns |
|---|---|
| `wiki-structure` | Flat-namespace + filename-uniqueness + internal-link convention (GitHub Wiki primary, others adapter-configurable); **hub-first themed IA** (real hub pages, never empty folders) + a validated default structure template; Azure DevOps **page-ID URL** links + `pagemoves`/REST move-delete mechanics |
| `wiki-authoring` | Business docs / engineering SOPs / user manuals / role guides / workflow docs / release & handover / onboarding templates; tenant/client neutralization discipline (per-hit classify-then-act) |
| `wiki-mermaid` | Mermaid diagram authoring rules — TD direction, shape vocabulary, four-class colour palette, label hygiene, code-path scrub from business diagrams |
| `wiki-plantuml` | BPMN-style **swimlane** authoring in PlantUML activity-beta + the per-flavour render → attach → embed pipeline (Azure `/.attachments` base64 REST, GitHub commit-to-`.wiki`, GitLab/MkDocs native). Mermaid stays authoritative for flowchart/sequence/state |
| `wiki-link-validation` | Broken-link sweep, missing-page detection, broken section-anchor detection + heading-anchor slug rules, visible-numeric-prefix scan, internal-link convention check; on Azure validates by **resolution** (not path-existence — flags dashed-relative-on-hyphen-page), tracks read-failures, plus stale-reference + reachability/backlink scans |
| `wiki-code-vs-docs-discrepancy` | Report wiki-vs-code drift with `file:line` evidence; never silently choose one side |
| `wiki-source-of-truth` | Declared knowledge-layer order; current-state vs target separation; config-constant single-location rule; stale-checkbox distrust; provenance-vs-active-prose judgement |
| `wiki-safe-updates` | Optional tips (advisory, non-blocking): diff preview for big overwrites, revert-over-reset rollback, one-purpose commits, retired-folder awareness, optional pre-deletion reference check; **plan-first/dry-run** for multi-step restructures, deterministic content-preserving edits, safe move/rename/delete + link-repointing, and a scoped approval gate for live-wiki/work-item publishes (GitHub git-push stays unrestricted) |
| `wiki-vs-stray-docs` | When a wiki exists and a new `docs/` file appears, surface the wiki-is-the-source option to the user (advisory; never blocks or refuses the write) |
| `wiki-traceability` | Navigation-only bidirectional traceability — backlog work items ↔ wiki workflow pages ↔ Figma design nodes ↔ spec pages, plus the central Epic→Feature matrix. Figma node URL format + colon→dash, harvest-don't-invent, `&t=` share-token omission, exact/lane/pending coverage, visible-heading idempotency, Description-only PBI patching |

### Commands

| Command | Purpose |
|---|---|
| `/docs-wiki:wiki-init <wiki-path>` | Initialise wiki structure (Home / _Sidebar / _Footer scaffolds) |
| `/docs-wiki:wiki-audit` | Link validation + filename-collision audit + visible-prefix scan + drift report |
| `/docs-wiki:wiki-update <page>` | Guided edit of an existing page with diff preview |
| `/docs-wiki:wiki-new <page>` | Create a new page with template (SOP / role guide / runbook / onboarding) |
| `/docs-wiki:wiki-drift` | Code-vs-wiki discrepancy sweep — produces a table; never edits silently |
| `/docs-wiki:wiki-sync-audit` | Audit-first sync mode — reports differences without applying changes |
| `/docs-wiki:wiki-swimlane <page>` | Author/refresh a BPMN swimlane (PlantUML) — preview first (diff + pending actions, no upload or write); render → attach/stage → embed only with `--approve` |

### Agents

| Agent | Purpose |
|---|---|
| `wiki-link-auditor` | Read-only scan for broken links + missing pages + visible-numeric-prefixes |
| `wiki-cleanup-validator` | Pre-delete reference check — refuses to remove a wiki page that other pages still link to |
| `wiki-drift-reporter` | Read-only sweep producing the wiki-vs-code drift table |

### Hooks

None. `hooks/hooks.json` is intentionally empty: there is no push gate and no stray-docs hook. All guidance is delivered by the skills and commands above.

### Scripts (under `skills/wiki-plantuml/scripts/`)

| Script | Purpose |
|---|---|
| `render_puml.ps1` | Local PlantUML render (pinned jar, no network). Needs `pwsh` + Java |
| `upload_attachment.ps1` | Azure DevOps `/.attachments` upload (PAT from `$env:AZDO_PAT`) |
| `embed_swimlane.py` | Idempotent `### Swimlane` block embed; `--dry-run` prints the diff only |
| `publish_update.py` | Swimlane pipeline. Preview by default; uploads, stages and writes only with `--approve`; never commits or pushes |

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
- **Block, gate, or restrict your git operations.** There is no push-approval gate, no force-push block, and no Write/Edit gate — the plugin is a non-blocking helper. Push the wiki whenever you're ready.
- Replace your project's official SOP. It offers conventions; it does not author your business decisions.

## Optional best practices (advisory — nothing is enforced)

These are suggestions the skills offer; none of them block you.

1. **Diff preview before a big overwrite** — handy for catching a wrong edit, but writing directly is fine.
2. **Filename-uniqueness audit** — GitHub Wiki rejects two `.md` files with the same basename; the audit can catch this before you push.
3. **Revert over reset for rollback** — `git revert` keeps published history; `reset --hard` / force-push also work if you prefer.
4. **Surface drift, don't auto-resolve** — code-vs-wiki drift is reported with `file:line` evidence so you decide the direction.
5. **Retired-folder awareness** — folders you mark retired aren't flagged as drift.
6. **Optional pre-deletion check** — before removing a page, you can grep for inbound references first (see `references/safe-doc-deletion.md`).

## Installation

This plugin is published as part of the `taqat-techno-plugins` marketplace. To install:

1. Open Claude Code.
2. Run `/plugins`.
3. Click **Add Marketplace** and enter `https://github.com/taqat-techno/plugins.git` (skip if already installed).
4. Find **docs-wiki** and click **Install**.

## Release history

| Version | Scope |
|---|---|
| `0.1.0` | Scaffold |
| `0.2.0` | Initial skills, commands and agents |
| `0.3.0` | `wiki-source-of-truth` skill + generic page templates |
| `0.4.0` | Heading-anchor slug rules + broken-anchor scan; safe-doc-deletion check; neutralization discipline |
| `0.6.0` | `wiki-plantuml` skill + `/docs-wiki:wiki-swimlane` command + 4 render/embed scripts |
| `0.7.0` | Hub-first IA, resolution-based link validation, single-master-swimlane, `wiki-traceability` skill |
| `0.8.x` | Marketplace-wide frontmatter fixes; behavioural eval suite |
| `0.9.0` (current) | `publish_update.py` makes no upload / staging / page write without `--approve`; README matches shipped components |

See [`CHANGELOG.md`](./CHANGELOG.md) for details.

## Related plugins

- [`react-kit`](../react-kit-plugin/README.md) — for building the admin panel itself.
- [`qa-browser`](../qa-browser-plugin/README.md) — for verifying the admin panel actually works as the wiki claims.

## License

MIT. See [`LICENSE`](./LICENSE).

## Author

TAQAT Techno · [github.com/taqat-techno](https://github.com/taqat-techno) · `info@taqatechno.com`
