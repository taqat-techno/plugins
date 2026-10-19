---
description: Author or refresh a BPMN-style swimlane on a wiki page — PlantUML activity-beta source (.puml), render to PNG/SVG, embed per wiki flavour (GitHub commit-to-.wiki / Azure /.attachments / GitLab+MkDocs native), and publish through the diff-preview + approval gate. Mermaid stays for non-swimlane diagrams.
argument-hint: "<page> [--render local|kroki] [--format svg|png] [--epic <epic>] [--slug <slug>]"
allowed-tools: Read, Glob, Grep, Edit, Write, Bash
---

# /docs-wiki:swimlane

Generate or refresh an actor-lane / BPMN-pool **swimlane** for a wiki page. Apply the
`wiki-plantuml` skill for every authoring + pipeline rule; this command is the thin router.

> **Scope:** swimlanes only. For a process flow, sequence, or state diagram, use Mermaid
> (`wiki-mermaid`) — it renders natively + inline on both GitHub and Azure DevOps wikis.
> For strict OMG BPMN 2.0, escalate to bpmn.io (surface to the user; do not author).

## Step 0 — Resolve page + flavour

- Resolve the wiki path + `wikiFlavour` like `/docs-wiki:audit` Step 0 (explicit arg → adapter cache `.claude/docs-wiki.local.json` → sibling-clone detect → ask).
- If the target page does not exist → suggest `/docs-wiki:new` first; do not create it here.
- Load adapter keys this command needs: `javaExe`, `plantumlJar`, `renderMode`, `krokiEndpoint`, `org`, `projectGuid`, `wikiId`, `attachmentApiVersion`, `swimlaneNaming`, `palette`.

## Step 1 — Author the `.puml` (apply `wiki-plantuml`)

- **Derive lanes and steps from the named source** (the epic / process doc / code path). **Refuse to invent** actors or steps not present in the source.
- Apply the swimlane rules: `|Actor|` lanes + exactly one tinted system lane, `start`/`stop`, **balanced** `if/elseif/else/endif`, `:activity;` nodes, **3-6 lanes** (decompose by phase if wider).
- **Colour rule:** end-of-line suffix stereotype `:text; <<#RRGGBB>>` only — **never** the deprecated prefix `#color:` form; lanes use `|#color|Name|`. Palette: ok `#d6f5d6`, block `#ffd6d6`, ext = the system lane, audit `#fff2cc`.
- Write `swimlane-<epic>-<slug>.puml` next to the wiki (the `.wiki` sibling clone for GitHub; the repo for Azure/GitLab/MkDocs).
- **Refuse** and report if the draft has an invented actor, >6 lanes, a prefix-colour, or unbalanced gateways.

## Step 2 — Render

- `--render local` (default, privacy-safe): `python "${CLAUDE_PLUGIN_ROOT}/skills/wiki-plantuml/scripts/render_puml.py" --puml <file> --format <fmt>` with a **pinned 1.2026.x jar** (reject the Maven `8059` trap) and `PLANTUML_LIMIT_SIZE`. Needs **Java 8+ and the jar** (`--plantuml-jar` / `PLANTUML_JAR`) or the `plantuml` CLI on PATH — no PowerShell. If neither is found the script prints install steps; relay them (see `wiki-plantuml` → Requirements).
- `--render kroki` (with `--kroki-endpoint` or `DOCS_WIKI_KROKI_ENDPOINT`): `publish_update.py` POSTs the source to a **self-hosted** Kroki only after `--approve`; the preview makes no network call. A public `kroki.io` / `plantuml.com` endpoint is **refused** (paste-leak) — surface the governance flag.
- `--format` default: **PNG** on github/azure (SVG sanitized there), SVG on gitlab/mkdocs.

## Step 3 — Embed per flavour

- **github**: commit the image into the `OWNER/REPO.wiki.git` sibling clone `/images`, embed a **leading-slash wiki-link** `[[/images/<name>.png|Alt]]`.
- **azure**: `upload_attachment.py` → PUT to `/.attachments` (**PAT from the `AZDO_PAT` env var, never echoed; base64 body by default, `--body-encoding raw` if base64 shows a broken image; verify-on-500**), embed **root-relative** `![Alt](/.attachments/<name>.png)`.
- **gitlab / mkdocs**: **no attach** — embed the inline ` ```plantuml ` fence (native render); self-host the render server for private diagrams.
- `embed_swimlane.py` replaces the page's `### Swimlane` block **idempotently** (re-running yields no diff).

## Step 4 — Publish (governed)

- `python "${CLAUDE_PLUGIN_ROOT}/skills/wiki-plantuml/scripts/publish_update.py"` runs in two passes. Its `_Source:` link is the `.puml` path relative to the wiki root (`--wiki-root`), never an absolute local path. **Without `--approve`** (default) it is a pure preview: it renders into a temp dir, prints the page diff (`embed_swimlane.py --dry-run`) and the list of pending actions — no Azure upload, no image staged into the wiki clone, no page write. **With `--approve`** it renders, uploads (azure) or stages (github), then writes the page. It never commits or pushes.
- Follow the **`wiki-safe-updates`** write policy: show the diff, and pass `--approve` only after the user approves it. Commit and push only when the user asks for that publish.

## Step 5 — Report

Output: the `.puml` source path, the artifact path, the flavour-correct embed snippet, the render command, and next steps. Keep the `.puml` as the source of truth (never hand-edit the image).

## Idempotency

Re-running `/docs-wiki:swimlane` on the same page overwrites the same artifact name and replaces the same `### Swimlane` block — a no-op `.puml` change produces no diff and no commit.

## What NOT to do

- Do NOT fake a swimlane with Mermaid `subgraph` lanes.
- Do NOT use the deprecated prefix colour `#color:` in activity-beta.
- Do NOT embed SVG by default on GitHub/Azure (both sanitize it) — PNG default; SVG only where verified.
- Do NOT hotlink a live render URL; do NOT echo the PAT; do NOT push without `wiki-safe-updates` approval.
