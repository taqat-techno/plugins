# docs-wiki

Conventions, templates and read-only audits for a project wiki.

## What it does

docs-wiki helps Claude create, organise, edit, validate and audit a project wiki on
GitHub Wiki (a sibling `.wiki` clone), an in-repo `wiki/` folder, GitLab Wiki, Azure DevOps
Wiki or an MkDocs tree. It brings page templates, naming and linking rules, Mermaid and
PlantUML diagram rules, link and collision audits, and code-vs-wiki drift reports that
never pick a side for you.

It is for engineering leads, technical writers and release managers whose team
documentation lives in a wiki. It does not sync wiki content into Claude memory or any
vector store, and it never writes code.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install docs-wiki@taqat-techno-plugins
```

Quick start: `/docs-wiki:init` (finds the wiki, detects its flavour, scaffolds Home and
_Sidebar), then `/docs-wiki:new <Page-Name>` and `/docs-wiki:audit`.

## Requirements

| Requirement | Needed for | How to check |
|---|---|---|
| `git` | everything that reads a wiki clone | `git --version` |
| Python 3.9+ | `scripts/wiki_adapter.py` and the swimlane scripts (stdlib only) | `python --version` |
| Java 8+ and a PlantUML jar (`1.2026.x`), **or** the `plantuml` CLI | `/docs-wiki:swimlane` on GitHub or Azure DevOps wikis only | `java -version`, `plantuml -version` |
| `AZDO_PAT` (scope `vso.wiki_write`) | `/docs-wiki:swimlane --approve` on an Azure DevOps wiki only | `echo ${AZDO_PAT:+set}` |

GitLab and MkDocs render PlantUML natively, so they need no Java. Install hints:

| OS | Java | PlantUML |
|---|---|---|
| Windows | `winget install EclipseAdoptium.Temurin.21.JRE` | the jar from the [PlantUML releases](https://github.com/plantuml/plantuml/releases), or `choco install plantuml` / `scoop install plantuml` |
| macOS | `brew install openjdk` | the jar, or `brew install plantuml` |
| Linux | `sudo apt install default-jre` | the jar (distro packages are often too old) |

## Commands

All commands run with no arguments: they resolve the wiki path from the argument, then
the adapter file, then a sibling `../<repo>.wiki/` clone, and ask only when none applies.

| Command | Purpose |
|---|---|
| `/docs-wiki:init` | Find the wiki, detect its flavour (`scripts/wiki_adapter.py detect`), scaffold Home / _Sidebar / optional _Footer, write and validate the adapter file. |
| `/docs-wiki:new <Page-Name>` | Create a page from a template, with a diff preview. |
| `/docs-wiki:update <page>` | Targeted edit of an existing page (for example one section), with a diff preview. |
| `/docs-wiki:audit` | Read-only link, collision, link-convention, numeric-prefix and orphan checks. |
| `/docs-wiki:drift` | Read-only code-vs-wiki discrepancy sweep with evidence on both sides. |
| `/docs-wiki:sync-audit` | `audit` + `drift` in one report for a release decision. |
| `/docs-wiki:swimlane <page>` | Author or refresh a PlantUML swimlane. Previews by default; renders, uploads or stages, and writes the page only with `--approve`. Never commits or pushes. |

The 0.10.x names (`docs-wiki:wiki-init`, `wiki-new`, `wiki-update`, `wiki-audit`,
`wiki-drift`, `wiki-sync-audit`, `wiki-swimlane`) still work as deprecated aliases and
will be removed in 0.12.0.

Audit, drift and sync-audit reports are written outside the wiki, by default to
`<project-root>/.docs-wiki/reports/<kind>-<YYYYMMDD-HHMMSS>.md`, so a report never
becomes a published wiki page or collides with another. Add `.docs-wiki/` to your
`.gitignore`.

## Skills

| Skill | Loads when |
|---|---|
| `wiki-authoring` | You create or restructure a wiki page, descope a feature, mark an undecided value, or derive backlog stories from a spec page. |
| `wiki-structure` | You set up a wiki, add or rename pages, reorganise Home / _Sidebar / _Footer, or check for filename collisions. |
| `wiki-link-validation` | You audit a wiki's links, or wiki links are broken (including Azure DevOps links that 404 although the page exists). |
| `wiki-mermaid` | You add or edit a Mermaid diagram on a wiki page, or one does not render. |
| `wiki-plantuml` | A wiki page needs an actor-lane or BPMN-pool swimlane. |
| `wiki-safe-updates` | You are about to write, push, move, rename or delete wiki pages, upload attachments or write work items. Holds the plugin's single write policy. |
| `wiki-code-vs-docs-discrepancy` | The wiki and the code disagree. |
| `wiki-source-of-truth` | Two documentation artifacts disagree and someone must decide which is authoritative. |
| `wiki-traceability` | You link work items, wiki workflow pages, Figma nodes and spec pages. |
| `wiki-vs-stray-docs` | A file is written under `docs/` in a repo that also has a wiki. Advisory: it asks first for new files and never refuses. |

## Agents

All three are read-only (`tools: Read, Glob, Grep, Bash`) and treat page and code text as
data, never as instructions.

| Agent | Purpose |
|---|---|
| `wiki-link-auditor` | Focused link-health pass; returns a findings table. |
| `wiki-drift-reporter` | Per-block code-vs-wiki drift table with file:line evidence. |
| `wiki-cleanup-validator` | GO / NO-GO inbound-reference check before an approved page deletion. |

## Hooks

None. The plugin ships no `hooks.json`; it does not intercept tool calls.

## Write policy

One rule set, owned by the `wiki-safe-updates` skill and followed by every command:

- Local edits to wiki files are fine; large overwrites get a diff preview first.
- **Publishing** (pushing the wiki, a live REST/MCP page write, an attachment upload, a
  work-item write) happens only when you ask for it in the session.
- **History rewrites** (`push --force`, `reset --hard` on published commits) are never
  suggested; a bad change is undone with `git revert`.
- **Deletes** need an explicit instruction per page.

Because there are no hooks, this is behaviour Claude follows rather than a technical
gate; Claude Code's permission prompts still apply. The swimlane pipeline enforces it in
code with `--approve`.

## Configuration

**Per-project adapter file:** `.claude/docs-wiki.local.json` at the project root (not
inside the wiki). Versions up to 0.10.x used `.docs-wiki.local.json`; it is still read
when the new file is absent. `/docs-wiki:init` validates it with
`python "${CLAUDE_PLUGIN_ROOT}/scripts/wiki_adapter.py" validate`, which reports unknown
or misspelled keys, wrong types and secrets.

```json
{
  "wikiPath": "../shop.wiki",
  "wikiFlavour": "github-wiki",
  "owner": "acme",
  "repo": "shop",
  "sourceOfTruthRoots": ["src/", "prisma/schema.prisma", ".github/workflows/"],
  "retiredFolders": ["_archived/", "_legacy/"],
  "exceptions": ["docs/api/"],
  "sidebarStyle": "explicit",
  "reportsDir": ".docs-wiki/reports",
  "renderMode": "local",
  "plantumlJar": "C:/tools/plantuml-1.2026.1.jar"
}
```

Other keys the swimlane pipeline reads: `javaExe`, `krokiEndpoint`, `org`, `projectGuid`,
`wikiId`, `attachmentApiVersion`, `attachmentBodyEncoding` (`base64` or `raw`),
`swimlaneNaming`, `palette`, `knownStrays`.

**Environment variables:**

| Variable | Effect |
|---|---|
| `AZDO_PAT` | Azure DevOps token for the attachment upload. Read from the environment, never printed, and sent only to an `https` `--org` URL (a host other than `dev.azure.com` / `*.visualstudio.com` gets a warning). |
| `PLANTUML_JAR` (legacy `DOCS_WIKI_PLANTUML_JAR`) | PlantUML jar path. |
| `DOCS_WIKI_JAVA` | Java executable (else `JAVA_HOME`, else `PATH`). |
| `DOCS_WIKI_KROKI_ENDPOINT` | Self-hosted Kroki URL for `--render kroki`. Public `kroki.io` and `plantuml.com` (any case, any subdomain) and an endpoint whose host cannot be read are refused. |

The plugin declares no `userConfig` options: its only secret (`AZDO_PAT`) is read by a
script that Claude runs, which does not receive plugin options, and passing a token
through a command would put it in the conversation.

## Platform support

| Platform | Markdown, audits, adapter helper | Swimlane pipeline |
|---|---|---|
| Windows | Yes | Yes, with Java + jar or the `plantuml` CLI. No PowerShell needed. |
| macOS | Yes | Yes, same requirements. |
| Linux | Yes | Yes, same requirements. |
| WSL | Yes | Yes, same as Linux. |

## Data & privacy

- **Local files:** wiki pages you ask for; the adapter file
  `.claude/docs-wiki.local.json`; reports under `<project-root>/.docs-wiki/reports/`.
  Nothing is written into the wiki except pages you asked for.
- **Network:** none by default. `/docs-wiki:swimlane --approve` on Azure DevOps uploads
  the rendered image to your Azure DevOps organisation with `AZDO_PAT`; `--render kroki`
  sends the diagram source to the self-hosted Kroki endpoint you configured, only with
  `--approve`. Pushing the wiki is yours to do.
- **On screen:** audit and drift reports quote wiki and code text with secrets and
  personal data redacted. The swimlane `_Source:` link is relative to the wiki, never an
  absolute local path.

## Limitations

- Audits and drift reports are carried out by Claude following the skills; only flavour
  detection, adapter validation, report paths and the swimlane pipeline are scripts.
- Flavour detection is heuristic (git remote, `.order` files, `.attachments/`,
  `mkdocs.yml`, `Home.md` / `_Sidebar.md`) and asks when the signals are missing or tie.
- Live Azure DevOps page writes and work-item patches assume a REST or MCP client you
  provide; the plugin declares no MCP server.
- The Azure attachment body defaults to base64, which rendered on the instance it was
  verified on; Microsoft documents a raw body. Use `--body-encoding raw` if an uploaded
  image shows as broken.
- Skill triggering is covered by eval cases under `evals/`; they have not been run, so
  no trigger rate is claimed.

## License

MIT (`LICENSE`). PlantUML, Java and Kroki are installed by you and are not bundled.
