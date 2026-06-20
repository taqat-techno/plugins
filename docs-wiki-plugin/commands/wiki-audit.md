---
description: Run all read-only wiki checks — link validation, filename collisions, internal-link convention, visible numeric prefixes, orphan pages, stray-docs detection. Produces a severity-grouped findings table. Never auto-fixes.
argument-hint: "[<wiki-path>] [--include-stray-docs] [--out path]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write
---

# /wiki-audit

You are auditing a wiki against every read-only check the plugin owns. Apply:

- `wiki-link-validation` — collisions, broken links, convention, numeric prefixes, orphans.
- `wiki-structure` — rules being validated.
- `wiki-vs-stray-docs` — stray docs/ folder detection in the main repo (when `--include-stray-docs`).
- `wiki-code-vs-docs-discrepancy` — surface possible code-vs-wiki drift (lightweight; full sweep is `/wiki-drift`).

Read-only. No fixes. The report is the deliverable.

## Step 0 — Resolve wiki path + adapter

Same as `/wiki-init` Step 0: explicit arg → adapter cache → sibling clone detect → ask.

Load `.docs-wiki.local.json` for: `wikiFlavour`, `retiredFolders`, `exceptions`, `sourceOfTruthRoots`.

If adapter cache absent: run with defaults (`github-wiki` flavour, default retired folders, no exceptions, no source-of-truth roots — drift sweep skipped).

## Step 1 — Pre-flight

- Confirm wiki path exists.
- Confirm it has at least one `.md` file (empty wiki → "nothing to audit; consider /wiki-init or /wiki-new").

## Step 2 — Run scans

Run each scan from `wiki-link-validation` independently and aggregate:

1. **Filename collisions** (flat-namespace flavours only).
2. **Broken internal links** — every wiki page; classify per flavour.
3. **Internal-link convention violations** — flavour-aware.
4. **Visible numeric prefixes** — filenames + sidebar.
5. **Orphan pages** — respect retired folders.

If `--include-stray-docs`:

6. **Stray docs/ scan** in the main repo (per `wiki-vs-stray-docs`).
7. **Lightweight code-vs-wiki overlap** — pages whose name matches a known stray-docs file; flag as possible drift.

## Step 3 — Compose findings report

Per `wiki-link-validation` output format:

```
WIKI AUDIT — <wiki-path> — <date>
  Flavour: <name>
  Pages: <count>
  Scans run: <list>
  Adapter cache: <loaded | not loaded>

SUMMARY
  HIGH: <count> — recommend fixing before push (advisory)
  MEDIUM: <count>
  LOW: <count>

FINDINGS

[Collisions — HIGH] (flavour: github-wiki)
| ID | Basename | Files | Fix |
|----|----------|-------|-----|
| C-1 | deploy | sop/deploy.md, runbooks/deploy.md | rename one to disambiguate |

[Broken Internal Links — MEDIUM]
| ID | Source | Target | Suggestion |
|----|--------|--------|------------|

[Convention Violations — MEDIUM]
| ID | Source | Issue | Fix |
|----|--------|-------|-----|

[Numeric Prefixes — MEDIUM]
| ID | Item | Issue | Fix |
|----|------|-------|-----|

[Orphan Pages — LOW]
| ID | Page | Last modified | Note |
|----|------|---------------|------|

[Stray Docs — MEDIUM]   ← only if --include-stray-docs
  Wiki present + stray folder: docs/
  Files in stray folder: <count>
  Possible drift overlaps: <list>

[Possible Drift — informational]   ← only if --include-stray-docs
  | docs/ file | wiki page | Run /wiki-drift for full sweep |

RECOMMENDED ORDER OF FIXES
  1. <ID> — <one-liner>
  2. ...
```

## Step 4 — Output

Print the summary inline. Write the full report to:

```
<wiki-path>/_audit/<YYYY-MM-DD>.md
```

OR `--out <path>` to override.

Suggest next steps:

- HIGH findings → recommend fixing before push (advisory; not enforced).
- MEDIUM → fix opportunistically; track in maintainer's queue.
- LOW (orphans) → confirm intent; either link, archive, or accept.

## Safety

- Read-only. No file writes inside the wiki repo (only writes the report under `_audit/`).
- No fixes applied. Every suggested fix is for the user to apply via `/wiki-update` or `/wiki-new`.
- Skips retired folders (per adapter).
- Skips exceptions (per adapter).
- Does NOT validate external links (out of scope).

## Modes

- `--include-stray-docs` — also scan the main repo for stray docs/ folders (per `wiki-vs-stray-docs`).
- `--out <path>` — write the full report to a specific path instead of `<wiki>/_audit/`.

## What NOT to do

- Do NOT auto-rename collision-clashing pages.
- Do NOT delete orphan pages.
- Do NOT migrate stray-docs content automatically.
- Do NOT fix broken links by Levenshtein-matching silently.
- Do NOT push the wiki after writing the audit report (the report is a wiki-internal artifact; push only on user demand).
