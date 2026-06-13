# UAT smoke-report template (fill-in)

A copy-paste skeleton for the role × route smoke report. Replace every `<…>` placeholder. Keep the
status vocabulary exactly: **PASS / BLOCKED / NOT-TESTABLE / FAIL** (defined in `browser-qa-discipline`).
One report per environment per build. Every PASS needs an evidence path; every BLOCKED needs a named
precondition; every NOT-TESTABLE needs a "what would unblock" line; every FAIL needs a severity + evidence.

## Status vocabulary (do not improvise)

| Status | Means |
|---|---|
| **PASS** | Observed at runtime to behave as required; evidence captured |
| **FAIL** | Observed at runtime to behave incorrectly; evidence captured + severity assigned |
| **BLOCKED** | Could not run because a named precondition was not met (missing credential, safety gate, prod refusal) |
| **NOT-TESTABLE** | Out of scope to test here (role not configured, feature flagged off, depends on external system) |

---

```
# UAT SMOKE REPORT — <env-name> — <YYYY-MM-DD> — build <commit-sha>

## EXECUTIVE SUMMARY
Sign-off recommendation: <YES | NO | CONDITIONAL> — <one-line justification>
Reality check: <PASS | FAIL>   (if FAIL, every row below is NOT-TESTABLE)
Roles in scope: <role-a, role-b, role-c>
Totals — PASS: <n>   FAIL: <n>   BLOCKED: <n>   NOT-TESTABLE: <n>
Highest-severity failure: <ID — one line, or "none">
Critical-path items unblocked: <yes | no — name what is missing>

## ROLE × ROUTE MATRIX
Legend: P=PASS  F=FAIL  B=BLOCKED  N=NOT-TESTABLE   (one cell per role × route)

| Route \ Role            | <role-a> | <role-b> | <role-c> | Expected for denied roles |
|-------------------------|:--------:|:--------:|:--------:|---------------------------|
| <route 1 (e.g. /dashboard)>      | <P> | <P> | <P> | n/a (all allowed) |
| <route 2 (e.g. /admin/users)>    | <P> | <F> | <B> | deny (UI + API + service) |
| <route 3 (e.g. /admin/audit)>    | <P> | <N> | <N> | deny |
| <route 4 (e.g. /admin/settings)> | <P> | <P> | <F> | deny |

Cross-role consistency: <PASS | N mismatches — listed below>
(A mismatch = the same route behaves inconsistently across roles in a way the matrix did not predict.)

## FAILURES BY SEVERITY

### HIGH
| ID | Role × Route | Layer | Issue | Evidence | Owner |
|----|--------------|-------|-------|----------|-------|
| F-1 | <role-b> × <route 2> | <UI / API edge / service> | <Shape-A: UI hides but API allows> | <qa-evidence/<date>/<env>/...png> | <unassigned> |

### MEDIUM
| ID | Role × Route | Layer | Issue | Evidence | Owner |
|----|--------------|-------|-------|----------|-------|
| F-2 | <role-c> × <route 4> | <UI> | <Shape-B: link advertised, API denies> | <path> | <unassigned> |

### LOW
| ID | Role × Route | Issue | Evidence |
|----|--------------|-------|----------|
| F-3 | <role-a> × <route 1> | <console warning on load> | <path> |

## BLOCKED ITEMS (require a user decision before sign-off)
| ID | Role × Route | Precondition (why blocked) | Resolution path |
|----|--------------|----------------------------|------------------|
| B-1 | <role-c> × <route 2> | <credentials for role-c not in .qa-browser.local.json> | <add credentials OR drop role from scope> |

Explicit acceptance recorded? <yes — cite the user message | no>
(Silence is NOT acceptance. A BLOCKED item without explicit written acceptance forces CONDITIONAL or NO.)

## NOT-TESTABLE ITEMS
| ID | Role × Route | Reason | What would unblock |
|----|--------------|--------|--------------------|
| N-1 | <role-b> × <route 3> | <role not provisioned this release> | <provision role / add to scope> |

## EVIDENCE INDEX
All paths relative to qa-evidence/<date>/<env>/ :
- <route 2 / role-b screenshot + network capture>
- <route 4 / role-c screenshot>
- <reality-check capture>
```

---

## Sign-off recommendation rule (apply mechanically)

```
IF reality-check FAILED                              -> NO (nothing below is trustworthy)
ELIF any HIGH-severity FAIL is unresolved            -> NO
ELIF any BLOCKED item lacks explicit user acceptance -> CONDITIONAL (list the BLOCKED items)
ELIF any NOT-TESTABLE item is on the critical path   -> CONDITIONAL (name what is missing)
ELSE                                                 -> YES
```

## Filling rules

- Every matrix cell is one of P / F / B / N — never blank, never "ok", never a checkmark.
- A denied-role cell is **PASS** only when denial holds at all asserted layers (see
  `references/rbac-three-layer-checklist.md` under `verify-identity-and-rbac`). A cell that is "UI
  denied" but API/service untested is **NOT-TESTABLE**, not PASS.
- Move every F cell into the severity tables with an ID, layer, evidence path, and owner.
- Redact tokens / cookies / PII from every evidence artifact before it lands in the report
  (`console-and-network-capture`).
- One env per report. Do not mix staging and UAT rows.

## Cross-references

- `uat-readiness-report` — owns the full report layout and the sign-off rule this template applies.
- `browser-qa-discipline` — the PASS / BLOCKED / NOT-TESTABLE vocabulary.
- `verify-identity-and-rbac` + `references/rbac-three-layer-checklist.md` — what makes a denied-role
  cell a true PASS.
- `anti-fraud-and-guard-hygiene` — feeds artifact-is-not-auth and CSRF/host-guard findings into the
  HIGH severity table.
