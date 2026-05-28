---
description: Audit-first form of a wiki-vs-code sync. Composes /wiki-audit + /wiki-drift into one report a release manager can read before deciding whether to update the wiki, the code, or both. Read-only. NEVER pushes; NEVER applies changes.
argument-hint: "[<wiki-path>] [--include-stray-docs] [--out path]"
author: TAQAT Editorial
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write
---

# /wiki-sync-audit

You are running a combined sync audit. Compose `/wiki-audit` (structural and link health) and `/wiki-drift` (code-vs-wiki content discrepancies) into one report.

This command is read-only. It is the "what would need to change" view, not the "change it" action.

Use this command:

- Before a planned wiki cleanup session.
- Before a release sign-off when the wiki is part of the release deliverable.
- Quarterly, to take stock of accumulated drift.
- After a major code refactor that likely invalidated wiki claims.

## Step 0 — Resolve scope

Same as `/wiki-audit`:

- Wiki path: arg → adapter cache → sibling clone detect → ask.
- Adapter cache loaded for: flavour, retired folders, exceptions, source-of-truth roots.

If source-of-truth roots are missing: the drift portion of the audit is skipped, with a clear note in the report.

## Step 1 — Run `/wiki-audit`

Execute every check from `wiki-link-validation`:

- Filename collisions.
- Broken internal links.
- Internal-link convention violations.
- Visible numeric prefixes.
- Orphan pages.

If `--include-stray-docs`: also run stray-docs detection per `wiki-vs-stray-docs`.

Capture findings.

## Step 2 — Run `/wiki-drift` (if source-of-truth roots configured)

Sweep every wiki page against the source-of-truth roots per `wiki-code-vs-docs-discrepancy`.

Capture discrepancies classified as doc-drift / code-drift / intentional gap / unknown.

## Step 3 — Compose unified report

```
WIKI SYNC AUDIT — <wiki-path> — <date>
  Wiki flavour: <name>
  Pages: <count>
  Source-of-truth roots: <list | "not configured — drift sweep skipped">

EXECUTIVE SUMMARY
  Structural health:
    HIGH: <count> (collisions)
    MEDIUM: <count> (broken links, convention, numeric prefix)
    LOW: <count> (orphans)
  Stray docs detected: <yes — <count> files | no | not scanned>
  Drift discrepancies (if drift sweep ran):
    doc-drift: <count> (wiki out of date)
    code-drift: <count> (code out of policy)
    intentional gap: <count> (target state)
    unknown: <count>
  Overall recommendation:
    <READY TO SHIP — minor cleanup only> |
    <NEEDS CLEANUP — HIGH structural issues> |
    <NEEDS RECONCILIATION — drift items require user direction> |
    <NEEDS BOTH>

STRUCTURAL FINDINGS
  (per-section tables from /wiki-audit)

STRAY DOCS (if --include-stray-docs)
  (table from wiki-vs-stray-docs)

DRIFT DISCREPANCIES (if drift sweep ran)
  (per-block details from /wiki-drift)

RECOMMENDED ACTION QUEUE
  1. <action> — addresses <findings>
  2. <action>
  ...

APPENDICES
  Per-page status:
    | Page | Structural | Drift | Stray overlap |
    |------|-----------|-------|---------------|
    | Home.md | clean | n/a | n/a |
    | Deploy-SOP.md | clean | doc-drift (1) | docs/deploy.md exists |
    ...
```

## Step 4 — Output

Print the executive summary inline. Write the full report to:

```
<wiki-path>/_audit/sync-<YYYY-MM-DD>.md
```

OR `--out <path>` to override.

Suggest next steps based on the overall recommendation:

- **READY TO SHIP** → no immediate action needed; revisit on the next cadence.
- **NEEDS CLEANUP** → fix HIGH structural issues first; re-run.
- **NEEDS RECONCILIATION** → walk each drift block; user picks direction; apply via `/wiki-update` or code-side change.
- **NEEDS BOTH** → cleanup first, then reconciliation.

## Safety

- Read-only.
- Does NOT push.
- Does NOT auto-fix.
- Does NOT silently classify drift (every block has evidence + reasoning).
- Respects retired folders + exceptions.
- Redacts PII / secrets from both sides before quoting.

## Modes

- `--include-stray-docs` — also scan the main repo for stray docs/ folders.
- `--out <path>` — write the full report to a specific path.

## What NOT to do

- Do NOT recommend "ship the wiki" while HIGH structural findings exist.
- Do NOT auto-apply any direction from the drift section.
- Do NOT collapse drift findings into a single number — each block needs its own user decision.
- Do NOT include real PII / secrets in the report (the underlying skills redact; this command must not reintroduce).
