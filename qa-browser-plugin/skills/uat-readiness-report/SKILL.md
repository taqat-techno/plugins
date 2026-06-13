---
name: uat-readiness-report
description: Composing the final PASS / BLOCKED / NOT-TESTABLE report from per-skill evidence. Owns the report layout, the sign-off recommendation rule, the failure grouping (HIGH / MEDIUM / LOW), the evidence-link convention, and the "explicit-acceptance for BLOCKED" requirement before sign-off. Activates at the close of a QA pass; before any "ready for release" claim.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - final-report layout
  - sign-off recommendation rule (YES / NO / CONDITIONAL)
  - failure grouping by severity
  - evidence-link convention (relative paths under qa-evidence/)
  - explicit-acceptance gate for BLOCKED items before sign-off
defers_to:
  - browser-qa-discipline (every status traces back to the vocabulary)
  - all other qa-browser skills (each contributes evidence rows)
  - project release SOP (any project-specific sign-off conventions)
user_invocable: false
---

# uat-readiness-report

## Purpose

Every QA pass produces evidence rows from multiple skills (reality-check, smoke, access matrix, walkthroughs, import/export). This skill composes those rows into a single report a release manager can act on. It enforces the sign-off rule: **no YES recommendation while any BLOCKED or HIGH-severity FAIL is unresolved.**

## When to use

Activate when:

- All other QA skills have produced their rows.
- A release is about to be signed off.
- Stakeholders ask "are we ready to ship?"

Do not invoke earlier — partial reports invite premature sign-off.

## Inputs

- All evidence rows from the QA pass (from the skills above).
- The evidence files referenced by each row (under `qa-evidence/<date>/<env>/`).
- The project's release SOP (if any).
- The list of stakeholders the report needs to be readable by (engineers, PM, business owner, sponsor — affects technical detail level).

## Report layout

```
UAT READINESS REPORT — <env-name> — <date> — build <commit-sha>

EXECUTIVE SUMMARY
  Sign-off recommendation: YES | NO | CONDITIONAL — <one-line justification>
  Total checks: <N>
  PASS: <n>     BLOCKED: <n>     NOT-TESTABLE: <n>     FAIL: <n>
  Highest-severity failure: <ID — one-line description>
  Critical path items unblocked: <yes | no — list missing>

REALITY CHECK
  <one row, must be PASS or the rest is NOT-TESTABLE>

ROLE SMOKE — <count> rows
  Summary: PASS: <n>  BLOCKED: <n>  FAIL: <n>
  Cross-role consistency: PASS | <count> mismatches detailed below
  Detailed rows: <link to section>

ROUTE ACCESS MATRIX — <count> rows
  Summary: PASS: <n>  Shape-A FAIL: <n>  Shape-B FAIL: <n>
  Detailed rows: <link to section>

ACTION WALKTHROUGHS — <count> rows
  Pattern 1: PASS: <n>  FAIL: <n>
  Pattern 2: PASS: <n>  FAIL: <n>
  Dirty-leave checks: PASS: <n>  FAIL: <n>
  Detailed rows: <link to section>

IMPORT / EXPORT — <count> rows
  Pattern 1: PASS: <n>  FAIL: <n>
  Pattern 2: PASS: <n>  FAIL: <n>
  Idempotency: <PASS | FAIL>
  Cap rejection: <PASS | FAIL>
  Export: <PASS | FAIL>
  Detailed rows: <link to section>

CONSOLE / NETWORK SUMMARY
  Console errors detected: <n> unique messages — top-5 listed
  Network 5xx detected: <n> endpoints — top-5 listed
  Performance regressions noted: <n>

FAILURES BY SEVERITY

  HIGH
    | ID | Skill | File / Route | Issue | Evidence | Owner |
    |----|-------|--------------|-------|----------|-------|
    | RAM-1 | route-access-matrix | GET /api/audit-log | Shape-A: UI denies, API allows | qa-evidence/.../...png | <unassigned> |

  MEDIUM
    ...

  LOW
    ...

BLOCKED ITEMS REQUIRING USER DECISION
  | ID | Item | Precondition | Resolution path |
  |----|------|--------------|------------------|
  | RS-blocked-1 | role-smoke for "auditor" role | Credentials not in `.qa-browser.local.json` | Add credentials or remove role from scope |

NOT-TESTABLE ITEMS
  | ID | Item | Reason | What would unblock |
  |----|------|--------|---------------------|
  | RAM-nt-1 | role=auditor × /admin/audit-log | role not configured | Add role to credentials |

APPENDICES
  Detailed reality-check row
  Detailed role-smoke rows
  Detailed route-access-matrix rows
  Detailed action-walkthrough rows
  Detailed import/export rows
  Evidence index (paths to every screenshot / console / HAR)
```

## Sign-off recommendation rule

```
IF any HIGH-severity FAIL is unresolved → recommendation: NO
ELIF any BLOCKED item lacks explicit user acceptance → recommendation: CONDITIONAL — list BLOCKED items
ELIF NOT-TESTABLE items affect the critical path → recommendation: CONDITIONAL — name what is missing
ELSE → recommendation: YES
```

Critical-path items are project-specific. The release SOP (if any) names them; otherwise, ask the user at the start of the pass which items are critical.

## Explicit acceptance for BLOCKED items

The recommendation can be YES even with BLOCKED items only if the user has explicitly accepted them in writing during this session. Example:

```
USER: "Skip the auditor-role smoke for this release — auditor isn't going live until next sprint."
QA: [marks RS-blocked-1 as accepted; cites user message; recommendation can be YES]
```

Implicit acceptance — "they didn't say anything" — does NOT count. Silence is not approval.

## Failure grouping by severity

| Severity | Examples (across skills) |
|---|---|
| HIGH | Shape-A failure (UI hides but API allows); service-layer Shape-A (sibling route leaks another principal's data / IDOR); client-rendered artifact used as authentication (no signature/binding/expiry); mutating endpoint accepts a no-Origin-and-no-Referer request (CSRF surface); missing audit-log row on destructive action; 5xx on a critical path endpoint; commit-on-upload behavior; unmasked PII in evidence |
| MEDIUM | Shape-B failure (UI advertises but API denies); missing dirty-leave warning; inconsistent modal behavior (Esc does not close); slow page (>5s) on a routine view; missing per-row error report on import |
| LOW | Cosmetic: wrong icon mirror in RTL; missing favicon; bare export filename; console warning |

The severity assignments are defaults. The project can override by writing `<skill>.severityOverrides` into the adapter cache.

## Evidence-link convention

Every reference to evidence in the report is a relative path under `qa-evidence/<date>/<env>/`:

```
Evidence: qa-evidence/2026-05-28/staging/admin/admin-users/screenshot.png
```

Reports are portable: handing the directory `qa-evidence/2026-05-28/` to a stakeholder gives them the report + every artifact.

The plugin command `/qa-report` produces the report; the evidence directory accompanies it.

## Decision framework

- If sign-off is YES → archive the report; the evidence directory becomes the audit trail for the release.
- If sign-off is NO → produce the bug list (link each HIGH FAIL to a tracker ticket); the report becomes the gate.
- If sign-off is CONDITIONAL → produce both: the list of accepted BLOCKED items + the list of items that need user decision before ship.

## Safety gates

- **Never** recommend YES while HIGH FAIL is unresolved.
- **Never** silently accept BLOCKED items.
- **Never** include unredacted PII / secrets in the report (per `console-and-network-capture`).
- **Never** mark NOT-TESTABLE items as "we'll test post-release" without naming who and when.
- **Never** ship the report referencing evidence on a developer's local machine — copy the artifacts in.

## Validation checklist

Before sending the report:

- [ ] Reality-check row is the first reportable row.
- [ ] Every PASS row has an evidence path.
- [ ] Every BLOCKED row has a named precondition.
- [ ] Every NOT-TESTABLE row has a "what would unblock" line.
- [ ] Every FAIL row has a severity AND a link to evidence.
- [ ] Sign-off recommendation follows the rule.
- [ ] No PII / secrets in any visible row.
- [ ] Evidence directory accompanies the report.

## Output format

See the report layout section above. Two modes:

- **Full report** (default) — every section, every appendix.
- **Executive summary only** — top of the layout, no detailed rows. For stakeholders who need the verdict, not the audit trail.

Both modes share the same source data; the difference is in inclusion.

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Sign-off YES while a HIGH FAIL stands | Bug ships; incident follows | Rule enforced |
| Silently accept BLOCKED ("we know about it") | No paper trail; recurring blocks | Explicit acceptance recorded |
| Report skips the evidence index | Cannot audit later | Index every artifact |
| Severity assigned per gut feel | Inconsistent across passes | Defaults; project overrides |
| "Critical path" defined post-hoc to explain a YES | The path was always critical; redefining it justifies the wrong call | Define critical path at pass start |
| Report mixes findings across envs (staging + UAT in one report) | Confused recommendations | One report per env per build |
| Stakeholders given a screenshot in chat, not the full report | Decisions made on partial info | Always ship the full report or executive summary, never ad-hoc fragments |

## Portability rationale

The report layout and sign-off rule apply to any QA discipline. The skill does not depend on:

- A specific framework
- A specific reporting tool
- A specific release process

Adapter: project release SOP can override severity defaults, critical-path definitions, and sign-off-recommendation rules.

## Cross-references

- `browser-qa-discipline` — vocabulary at the row level.
- `runtime-reality-check`, `role-smoke-tests`, `route-access-matrix`, `modal-and-action-walkthroughs`, `import-export-ui-checks`, `console-and-network-capture`, `safe-destructive-testing`, `verify-identity-and-rbac`, `anti-fraud-and-guard-hygiene` — all produce rows that feed this skill.
- `references/uat-smoke-report-template.md` — copy-paste fill-in skeleton: per-role × route matrix (PASS / BLOCKED / NOT-TESTABLE), severity tables, and the sign-off recommendation rule.
- `/qa-report` — the command that invokes this skill at the end of a pass.
