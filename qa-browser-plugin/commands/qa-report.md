---
description: Compile the final UAT readiness report from previously captured evidence (qa-evidence/ directory). Produces a single Markdown report with executive summary + per-skill sections + failure grouping + sign-off recommendation. Read-only.
argument-hint: "[--date YYYY-MM-DD] [--env name] [--summary-only] [--out path]"
author: TAQAT Techno
version: 0.2.0
allowed-tools: Read, Glob, Grep, Bash, Write
---

# /qa-report

You are compiling the UAT readiness report. Apply `uat-readiness-report` for layout, sign-off rule, severity grouping, and explicit-acceptance discipline.

This command does NOT run new QA checks. It aggregates the evidence already captured by `/qa-smoke`, `/qa-roles`, `/qa-route`, and any action/import walkthroughs from earlier in the session.

## Step 0 — Locate evidence

By default, look for evidence under:

```
qa-evidence/<latest-date>/<env-from-qa-target>/
```

With flags:

- `--date YYYY-MM-DD` — pin to a specific date directory.
- `--env name` — pin to a specific env directory.

If multiple env directories exist under the date and no `--env` is given, ask the user which to compile (do not silently pick).

If no evidence exists, surface:

```
No evidence found under qa-evidence/.
Run /qa-smoke <role> or /qa-roles first.
```

## Step 1 — Read evidence

Scan the evidence directory:

```
qa-evidence/2026-05-28/staging/
  admin/
    login/
      screenshot.png
      console.log.json
      network.har
      notes.md
    admin-users/
      ...
  manager/
    ...
  _reality-check.md          ← top-level reality check artifacts
  _access-matrix/            ← if /qa-route ran
  _walkthroughs/             ← if action walkthroughs ran
  _import-export/            ← if import/export checks ran
```

For each evidence row, extract:

- Status (from a small status file or convention: PASS / BLOCKED / FAIL).
- Evidence path (screenshot / console / network).
- Per-row notes if a `notes.md` is present.

If a row has no status file, mark it `UNKNOWN — evidence present but no status recorded` and flag in the report.

## Step 2 — Aggregate

Compose the report per `uat-readiness-report`:

```
UAT READINESS REPORT — <env> — <date> — build <commit-sha if known>

EXECUTIVE SUMMARY
  Sign-off recommendation: <YES | NO | CONDITIONAL> — <one-line>
  Total checks: <N>
  PASS: <n>   BLOCKED: <n>   NOT-TESTABLE: <n>   FAIL: <n>
  Highest-severity failure: <ID — one-line description>

REALITY CHECK
  <row from _reality-check.md>

ROLE SMOKE
  Summary: ...
  Detailed rows: ...

ROUTE ACCESS MATRIX
  ...

ACTION WALKTHROUGHS
  ...

IMPORT / EXPORT
  ...

CONSOLE / NETWORK SUMMARY
  Console errors: <n unique> — top-5 listed
  Network 5xx: <n endpoints> — top-5 listed

FAILURES BY SEVERITY
  HIGH
    | ID | Skill | File / Route | Issue | Evidence | Owner |
    ...
  MEDIUM
    ...
  LOW
    ...

BLOCKED ITEMS REQUIRING USER DECISION
  ...

NOT-TESTABLE ITEMS
  ...

APPENDICES
  Evidence index (every artifact, relative path)
```

## Step 3 — Sign-off recommendation

Apply the rule from `uat-readiness-report`:

```
IF any HIGH FAIL unresolved              → NO
ELIF any BLOCKED lacks explicit accept   → CONDITIONAL — list BLOCKED items
ELIF NOT-TESTABLE on critical path       → CONDITIONAL — list missing
ELSE                                     → YES
```

The user can override the recommendation by passing `--accept-blocked ID1,ID2` (records explicit acceptance) or `--critical-path-override "reason"` (records reasoned dismissal). All overrides appear in the report appendix.

## Step 4 — Write the report

Default output path: `qa-evidence/<date>/<env>/REPORT.md`.

With `--out <path>`: write to the given path instead.

Print the executive summary inline; tell the user where the full report was saved.

## Modes

- `--summary-only` — produce only the executive summary, skip per-skill detail sections.
- `--accept-blocked ID1,ID2` — explicit acceptance for listed BLOCKED items.
- `--critical-path-override "reason"` — explicit override for NOT-TESTABLE on critical path.

## Safety

- Read-only. Does not modify evidence files.
- Refuses to write the report if any captured evidence file contains an unredacted token (auto-scans HAR + console files for common token patterns).
- Refuses to recommend YES while HIGH FAIL is unresolved — even if the user asks.
- Never silently accepts BLOCKED items; explicit `--accept-blocked` is required.

## Output

Report file path on disk. Executive summary printed inline. Suggested next step:

```
Report: qa-evidence/2026-05-28/staging/REPORT.md
Recommendation: NO — 2 HIGH failures unresolved (see RAM-1, MAW-3)
Next: address HIGH failures, then re-run /qa-roles + /qa-report to refresh.
```
