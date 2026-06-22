---
description: Author or refresh a BPMN-style swimlane on a wiki page — PlantUML activity-beta source (.puml), render to PNG/SVG, embed per wiki flavour (GitHub commit-to-.wiki / Azure /.attachments / GitLab+MkDocs native), and publish through the diff-preview + approval gate. Mermaid stays for non-swimlane diagrams.
argument-hint: "<page> [--render local|kroki] [--format svg|png] [--epic <epic>] [--slug <slug>]"
author: TAQAT Techno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Edit, Write, Bash
---

# /wiki-swimlane

Generate or refresh an actor-lane / BPMN-pool **swimlane** for a wiki page. Apply the
`wiki-plantuml` skill for every authoring + pipeline rule; this command is the thin router.

> **Scope:** swimlanes only. For a process flow, sequence, or state diagram, use Mermaid
> (`wiki-mermaid`) — it renders natively + inline on both GitHub and Azure DevOps wikis.
> For strict OMG BPMN 2.0, escalate to bpmn.io (surface to the user; do not author).

## Step 0 — Resolve page + flavour

- Resolve the wiki path + `wikiFlavour` like `/wiki-audit` Step 0 (explicit arg → adapter cache `.docs-wiki.local.json` → sibling-clone detect → ask).
- If the target page does not exist → suggest `/wiki-new` first; do not create it here.
- Load adapter keys this command needs: `javaExe`, `plantumlJar`, `renderMode`, `krokiEndpoint`, `org`, `projectGuid`, `wikiId`, `attachmentApiVersion`, `swimlaneNaming`, `palette`.

## Step 1 — Author the `.puml` (apply `wiki-plantuml`)

- **Derive lanes and steps from the named source** (the epic / process doc / code path). **Refuse to invent** actors or steps not present in the source.
- Apply the swimlane rules: `|Actor|` lanes + exactly one tinted system lane, `start`/`stop`, **balanced** `if/elseif/else/endif`, `:activity;` nodes, **3-6 lanes** (decompose by phase if wider).
- **Colour rule:** end-of-line suffix stereotype `:text; <<#RRGGBB>>` only — **never** the deprecated prefix `#color:` form; lanes use `|#color|Name|`. Palette: ok `#d6f5d6`, block `#ffd6d6`, ext = the system lane, audit `#fff2cc`.
- Write `swimlane-<epic>-<slug>.puml` next to the wiki (the `.wiki` sibling clone for GitHub; the repo for Azure/GitLab/MkDocs).
- **Refuse** and report if the draft has an invented actor, >6 lanes, a prefix-colour, or unbalanced gateways.

## Step 2 — Render

- `--render local` (default, privacy-safe): `scripts/render_puml.ps1 -Puml <file> -Format <fmt>` with a **pinned 1.2026.x jar** (reject the Maven `8059` trap) and `PLANTUML_LIMIT_SIZE`.
- `--render kroki`: **self-hosted endpoint required**. A public `kroki.io` / `plantuml.com` endpoint is **refused** (paste-leak) — surface the governance flag.
- `--format` default: **PNG** on github/azure (SVG sanitized there), SVG on gitlab/mkdocs.

## Step 3 — Embed per flavour

- **github**: commit the image into the `OWNER/REPO.wiki.git` sibling clone `/images`, embed a **leading-slash wiki-link** `[[/images/<name>.png|Alt]]`.
- **azure**: `scripts/upload_attachment.ps1` → PUT to `/.attachments` (**PAT from `$env:AZDO_PAT`, never echoed; base64 body; verify-on-500**), embed **root-relative** `![Alt](/.attachments/<name>.png)`.
- **gitlab / mkdocs**: **no attach** — embed the inline ` ```plantuml ` fence (native render); self-host the render server for private diagrams.
- `scripts/embed_swimlane.py` replaces the page's `### Swimlane` block **idempotently** (re-running yields no diff).

## Step 4 — Publish (governed)

- `scripts/publish_update.py` orchestrates render → attach/stage → embed → **diff preview** → approval.
- Route through **`wiki-safe-updates`**: show the diff, get explicit approval, then commit/push. **Never** push or publish an attachment without approval.

## Step 5 — Report

Output: the `.puml` source path, the artifact path, the flavour-correct embed snippet, the render command, and next steps. Keep the `.puml` as the source of truth (never hand-edit the image).

## Idempotency

Re-running `/wiki-swimlane` on the same page overwrites the same artifact name and replaces the same `### Swimlane` block — a no-op `.puml` change produces no diff and no commit.

## What NOT to do

- Do NOT fake a swimlane with Mermaid `subgraph` lanes.
- Do NOT use the deprecated prefix colour `#color:` in activity-beta.
- Do NOT embed SVG by default on GitHub/Azure (both sanitize it) — PNG default; SVG only where verified.
- Do NOT hotlink a live render URL; do NOT echo the PAT; do NOT push without `wiki-safe-updates` approval.
