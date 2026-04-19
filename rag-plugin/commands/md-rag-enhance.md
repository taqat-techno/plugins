---
description: Enhance Markdown files against the rag-plugin authoring standard (RAG-optimized for the ragtools chunker + MiniLM-L6-v2 embedder). Always safe mode — applies only the two mechanical fixes that cannot change semantic meaning (pseudo-heading → real heading, blank-line normalization around headings and code fences), reports every structural finding for manual review, writes atomic backups. No args → enhance every .md in the project. Optional positional file argument → enhance just that file.
argument-hint: "[<file-path>] [--verbose] [--no-backup]"
allowed-tools: Bash(python:*), Read, Write, Glob, Grep
disable-model-invocation: false
author: TaqaTechno
version: 0.7.0
---

# /md-rag-enhance

**Always-safe** Markdown enhancer for projects indexed into the ragtools RAG pipeline. The command runs the analyzer at `${CLAUDE_PLUGIN_ROOT}/scripts/md_analyzer.py`, which applies exactly two mechanical fixes that cannot change semantic meaning by construction, and reports every structural issue for manual review.

> **Companion skill:** `markdown-authoring` (sibling) handles Markdown **creation** so new files follow the same standard. This command handles **existing** files.

## Invocations

Minimal by design. Four forms, all listed below:

| Form | Behavior |
|---|---|
| `/md-rag-enhance` | Enhance every `.md` file under the current directory (recursive). Skips `.git/`, `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/`. Respects `.gitignore` where safe. |
| `/md-rag-enhance path/to/file.md` | Enhance only that one file. Same safe-fix + backup + report discipline. |
| `/md-rag-enhance --verbose` | Full per-file findings instead of the compact summary (combinable with a path). |
| `/md-rag-enhance --no-backup` | Skip writing `<file>.bak-pre-md-rag-enhance` siblings. For users on git who prefer diff review. |

**Not exposed:** no `--analyze`, no `--fix-safe`, no `--fix-aggressive`, no `--report`, no `--path`, no `--max-files`, no `--dry-run`. The command is always-safe by design — there is no other mode. The 500-file safety cap is hardcoded and surfaces a clear error message when exceeded, with a hint to pass a specific file path.

## What the command does (always, on every invocation)

### Safe fixes applied automatically

These two categories **cannot change semantic meaning** by construction:

1. **Pseudo-heading → real heading.** Bold-text lines used as section titles (`**Text**` on its own line, surrounded by blank lines, outside code fences) are converted to proper `## Text` headings. The ragtools chunker's heading regex doesn't match bold-as-heading, so these lines don't create chunk boundaries — converting them is pure structural improvement.
2. **Blank-line normalization around headings and code fences.** Adds a blank line before/after every `##`/`###`/`####` heading and every fenced code block if missing. Typographical only — never touches content inside a code fence, never changes flowing text.

### Report-only findings (NEVER auto-fixed)

Every other violation is printed with file:line, severity (HIGH/MEDIUM/LOW), and a remediation hint. The human decides whether and how to apply:

| Finding | Severity | Why report-only |
|---|---|---|
| Content before first heading | HIGH | Adding a title requires judgment (what's the title?) |
| Oversized leaf section (>300 words) | HIGH | Splitting requires topic decomposition |
| Vague heading (Overview, Notes, Details, Section N) | MEDIUM | Renaming requires knowing what the section is actually about |
| Duplicate leaf heading within file | MEDIUM | Disambiguation requires judgment |
| Code block > 60 lines | MEDIUM | Breaking into steps requires understanding the code |
| Table > 15 rows | MEDIUM | Splitting requires categorization |
| YAML frontmatter with knowledge (`tags:`, `keywords:`, `description:`) | MEDIUM | Extracting into body is semantic work |
| Code block without prose intro | LOW | Writing the intro sentence requires understanding |
| Heading level skipped (`##` → `####`) | LOW | Restructuring needs judgment |

## Binding safety invariants

From `${CLAUDE_PLUGIN_ROOT}/docs/decisions.md` D-023:

- **Never modify content inside fenced code blocks** — not even blank-line normalization touches fenced-block interiors.
- **Never change commands, URLs, file paths, config keys, version numbers, or any numeric value** — the safe-fix categories do not write into flowing text.
- **Never delete content.** The two safe fixes only ADD structure (headings, blank lines) or CONVERT pseudo-headings to real headings.
- **Atomic file writes.** Every write: load → modify in-memory → write to `<file>.tmp` → `os.replace()`. Never in-place edit.
- **Backup before every write.** `<file>.bak-pre-md-rag-enhance` sibling is written unless `--no-backup` is passed.
- **Skip binary files, symlinks, and files > 1 MB.** Defensive.
- **Skip standard dirs** (`.git/`, `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/`) and respect `.gitignore`.

## Step 0 — State detection (shared preamble)

Follow the canonical recipe in `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md`. Print the 6-line mode banner. **This command does not require ragtools to be installed or running** — it operates purely on the filesystem — but the banner remains part of the compact output so the user has context.

If `state.install_mode == not-installed`, the command still works: it's a filesystem tool, not a ragtools client. Print an info line: `[info] ragtools is not installed — /md-rag-enhance still works since it operates on files, not on the service.` Continue.

## Step 1 — Parse arguments

Parse the positional file argument (if any) and the two optional flags. Invalid combinations (e.g. non-existent file path) → print error + usage + exit 1.

## Step 2 — Run the analyzer

Invoke:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/md_analyzer.py <args>
```

Where `<args>` is the positional file (if any) + `--verbose` and/or `--no-backup` as passed. The script:

1. Discovers `.md` files (just the given file, or recursive scan of `$CWD`).
2. For each file: parses structure, runs the 10 checks (`GL-01..GL-10`), applies the two safe fixes, writes atomic + backup.
3. Emits a compact summary report to stdout (or verbose with `--verbose`).

## Step 3 — Report (the command's output)

The stdout from the analyzer is the command's primary output. Format:

```
md-rag-enhance — summary
  files scanned:              <N>
  files enhanced:             <M>
  safe mechanical fixes:      <K>
  report-only findings:       <total>
    HIGH:    <count>
    MEDIUM:  <count>
    LOW:     <count>

top findings for manual review (up to 20):
  [HIGH]   GL-01 path/to/file.md:1 — Content appears before the first heading...
  [HIGH]   GL-02 path/to/other.md:42 — Leaf section 'Overview' is ~540 words (>300)...
  [MEDIUM] GL-03 path/to/third.md:12 — Vague heading 'Details' — ...
  ...
```

`--verbose` appends a per-file detail block with every finding + remediation.

## Failure handling

| Situation | Behavior |
|---|---|
| `python` not on PATH | Print `md-rag-enhance: python interpreter not found on PATH. The analyzer requires Python 3.10+.` Exit 1. |
| Given file does not exist | Print `md-rag-enhance: not a file or directory: <path>`. Exit 1. |
| 500-file safety cap exceeded | Print `md-rag-enhance: exceeded 500-file safety cap under <path>. Pass a specific file path or narrow the working directory.` Exit 1. |
| File unreadable | Skip it with a `SKIPPED (read failed: <reason>)` line; continue with other files; exit 0. |
| Atomic write fails | Print the OS error; `<file>.tmp` is cleaned up; `<file>` is unchanged; exit 1. |
| `--no-backup` was passed but `--verbose` shows a dangerous set of findings | The flag is respected; user made the choice. No prompt. |

## Companion — the `markdown-authoring` skill

`/md-rag-enhance` handles **existing** Markdown. The `markdown-authoring` skill handles **new** Markdown — it auto-activates when Claude is asked to create a README, runbook, SOP, or any `.md` file, and produces content that satisfies the same standard from the start. See `${CLAUDE_PLUGIN_ROOT}/skills/markdown-authoring/SKILL.md`.

## Verification recipes

```bash
# Run against the plugin's own documentation (a good meta-test)
cd plugins/rag-plugin
/md-rag-enhance --verbose

# Run against a specific file
/md-rag-enhance plugins/rag-plugin/README.md

# CI-style: no backups, just enhance, full output
/md-rag-enhance --no-backup --verbose
```

## See also

- `${CLAUDE_PLUGIN_ROOT}/skills/markdown-authoring/SKILL.md` — companion skill for creation
- `${CLAUDE_PLUGIN_ROOT}/skills/markdown-authoring/references/rag-md-guidelines.md` — full authoring standard
- `${CLAUDE_PLUGIN_ROOT}/scripts/md_analyzer.py` — the analyzer + safe-fix engine
- `${CLAUDE_PLUGIN_ROOT}/docs/decisions.md` — D-023 (authoring standard + always-safe command boundary)
- `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md` — shared state-detection preamble
