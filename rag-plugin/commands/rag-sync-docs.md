---
description: MAINTAINER-ONLY. Compare bundled references against the upstream ragtools_doc.md and report which references have drifted. Never auto-rewrites — diff and report only. Hidden from automatic invocation.
argument-hint: "[--source <path-to-ragtools_doc.md>]"
allowed-tools: Bash(diff:*), Bash(wc:*), Bash(test:*), Bash(grep:*), Bash(sha256sum:*), Bash(shasum:*), Bash(certutil:*), Read
disable-model-invocation: true
author: TaqaTechno
version: 0.1.0
---

# /rag-sync-docs

> **MAINTAINER-ONLY COMMAND.** This command exists for plugin maintainers to detect drift between the bundled references library and the upstream `ragtools_doc.md` source-of-truth. It is **not** part of the user surface. `disable-model-invocation: true` keeps the model from auto-invoking it during normal operation.
>
> **End users should never need this command.** If you are an end user, you are looking at the wrong file. See `README.md` for the user-facing command catalog.

## Purpose

The references library at `skills/ragtools-ops/references/` was originally derived from `ragtools_doc.md` (workspace root) in Phase 1. As ragtools evolves, the upstream doc will change: new failure IDs, new gaps, new platform support, new HTTP API endpoints, new versions. This command surfaces that drift so a human maintainer can decide which reference files need a sync.

This command **never auto-rewrites** the references. It only:
1. Reads the upstream `ragtools_doc.md`
2. Reads the bundled references
3. Reports drift signals
4. Recommends which reference files a human should review

The maintainer then opens the affected files and updates them by hand. This is intentional — auto-rewriting would risk silently introducing inaccuracies into the failure catalog, the playbook gating discipline, or the boundary rules.

## Behavior

1. **Resolve the upstream doc path.** Default: `C:/MY-WorkSpace/claude_plugins/ragtools_doc.md` (workspace root). Override with `--source <path>`.
2. **Read** the upstream doc.
3. **Compute a SHA-256 hash** of the upstream doc and compare against the hash recorded in `references/_meta.md` (if present).
4. **Section-by-section drift check:**
   - List sections in the upstream doc by their `## N. Title` headings
   - List references in `references/` by their `source-sections` frontmatter field
   - Identify upstream sections with no matching reference (potential new content)
   - Identify references with `source-sections` pointing at sections that no longer exist (potential removed content)
5. **Failure-ID drift check:** parse F-IDs out of the upstream §14 and out of `references/known-failures.md`. Report any deltas.
6. **Gap-ID drift check:** parse G-IDs out of the upstream §19 and out of `references/gaps.md`. Report any deltas.
7. **Version check:** parse the version from upstream §17 (`Current version: X.Y.Z`) and compare against `references/_meta.md`'s recorded version. Report if different.
8. **Render** a compact maintainer-facing report.
9. **Stop.** Never write to any reference file.

## Required steps

### Step 1 — Resolve the upstream doc

```bash
test -f "${SOURCE:-C:/MY-WorkSpace/claude_plugins/ragtools_doc.md}" || echo MISSING
```

If missing, print: `cannot find ragtools_doc.md. specify --source <path>` and stop.

### Step 2 — Hash compare

```bash
# Windows
certutil -hashfile <doc-path> SHA256

# macOS
shasum -a 256 <doc-path>

# Linux
sha256sum <doc-path>
```

Read the recorded hash from `references/_meta.md` (if any). Compare. If they match, the upstream doc has not changed since the last sync — short-circuit with: `up to date. upstream sha256 matches references/_meta.md.` and stop. If they differ (or no recorded hash exists), continue.

### Step 3 — Section-by-section drift

Use `grep` to extract section headings from the upstream doc:

```bash
grep -E '^## [0-9]+\.' <doc-path>
```

Then read each reference file's frontmatter and extract the `source-sections` field. Build a coverage map.

Report:
- **Upstream sections not covered by any reference** — these are new content the references should be updated to include
- **References with stale `source-sections`** — these point at upstream sections that no longer exist or have been renumbered
- **Section count delta** — upstream had N sections last time, now has M

### Step 4 — Failure-ID drift

Parse F-IDs from upstream §14:
```bash
grep -E '^### F-[0-9]+' <doc-path>
```
Or look for the table of failure modes if the upstream uses a tabular format.

Parse F-IDs from `references/known-failures.md`:
```bash
grep -E '^### F-[0-9]+' references/known-failures.md
```

Compare the two sets:
- F-IDs in upstream but not in references → new failures to add
- F-IDs in references but not in upstream → upstream removed/merged a failure

### Step 5 — Gap-ID drift

Same as Step 4 but with G-IDs from §19 and `references/gaps.md`.

### Step 6 — Version check

Parse the version line from upstream §17:
```bash
grep -E 'Current version' <doc-path>
```

Compare against `references/_meta.md`'s `ragtools version at split time` field. Report if different.

### Step 7 — Render the report

Compact maintainer-facing output:

```
=== rag-plugin doc sync report ===

upstream: C:/MY-WorkSpace/claude_plugins/ragtools_doc.md
upstream sha256: <new-hash>
recorded sha256: <recorded-hash or "none">
status: <DRIFT DETECTED | UP TO DATE>

upstream version: <X.Y.Z>
recorded version: <Y.Y.Z>
version drift: <YES | NO>

section coverage:
  upstream sections: <N>
  covered by references: <M>
  uncovered: <list>
  references with stale source-sections: <list>

failure-id drift:
  added in upstream: <list of F-IDs>
  removed in upstream: <list of F-IDs>
  unchanged: <count>

gap-id drift:
  added in upstream: <list of G-IDs>
  removed in upstream: <list of G-IDs>
  unchanged: <count>

recommended manual edits:
  • <reference file> — <reason>
  • <reference file> — <reason>
  ...

next steps for maintainer:
  1. open the affected reference files
  2. apply edits by hand (do NOT auto-rewrite)
  3. update references/_meta.md with the new sha256 and version
  4. re-run /rag-sync-docs to confirm "UP TO DATE"
```

If no drift, the report is much shorter:

```
=== rag-plugin doc sync report ===

upstream: C:/MY-WorkSpace/claude_plugins/ragtools_doc.md
status: UP TO DATE

no edits needed.
```

## Failure handling

| Situation | Behavior |
|---|---|
| Upstream doc not found | Print error, suggest `--source <path>`, stop |
| `references/_meta.md` missing | Print warning, treat as "first sync" — full drift check, no hash compare |
| Hash tool unavailable | Print warning, skip hash compare, still do section/F-ID/G-ID drift |
| Reference file frontmatter unparseable | Print warning naming the file, skip it in the coverage map |
| `grep` returns no sections (upstream doc is empty or wrong format) | Print error, stop |

## Boundary reminders

- **NEVER auto-rewrite reference files.** This is binding. The whole point of this command is to surface drift, not to silently apply changes that might introduce inaccuracies.
- **NEVER call any rag-plugin user command** from this command. It is an isolated maintenance tool.
- **NEVER delete reference files** even if their `source-sections` are stale. The maintainer decides what to do.
- **`disable-model-invocation: true`** keeps Claude from running this during normal user interactions. It is invoked manually by maintainers via `/rag-sync-docs`.
- **No network egress.** This command reads local files only.
- **Compact output for the report.** Even maintainer reports honor D-008.

## See also

- `references/_meta.md` — source-of-truth metadata: hash, version, split date
- `ARCHITECTURE.md` — boundary rules
- `docs/decisions.md#d-003` — references are bundled inline, sync command keeps them aligned
- `CHANGELOG.md` — phase-by-phase deliverables
