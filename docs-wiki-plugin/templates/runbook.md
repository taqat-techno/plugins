# Runbook: <OPERATION NAME>

> One-line summary of what this runbook does and the outcome it produces.
> Replace every `<PLACEHOLDER>` and delete guidance lines (those starting with `>`) before publishing.

| Field | Value |
|-------|-------|
| Owner | `<TEAM OR ROLE RESPONSIBLE>` |
| Status | `<DRAFT / REVIEWED / APPROVED>` |
| Last reviewed | `<YYYY-MM-DD>` |
| Risk level | `<LOW / MEDIUM / HIGH>` |
| Estimated duration | `<e.g. 15 minutes>` |
| Reversible | `<YES / NO / PARTIAL — see Failure modes>` |

## When to use

> State the trigger conditions. Be specific about the symptom, alert, or scheduled event that brings someone here.

- Use this runbook when `<TRIGGER CONDITION, e.g. an alert fires / a scheduled task is due / a request comes in>`.
- Do NOT use this runbook when `<OUT-OF-SCOPE CONDITION>`; instead see [Related pages](#related-pages).

## Preconditions

> Everything that must be true before starting. The operator should verify each item, not assume it.

- Access: `<REQUIRED ROLE / PERMISSION / CREDENTIAL SOURCE>` is available. Never paste secrets into this page; reference where they live (e.g. a vault or secret manager).
- Tools installed: `<TOOL 1>`, `<TOOL 2>` at the expected versions.
- State: `<SYSTEM / SERVICE>` is in `<EXPECTED STATE>` before changes begin.
- Backups / snapshots: `<WHAT TO CAPTURE>` taken and confirmed restorable.
- Notification: relevant stakeholders or channels informed if this operation is user-visible.

## Steps

> Number every step. Each step has an action, the command (or UI path) to run, and the expected result so the operator knows whether to continue.

### 1. `<SHORT ACTION DESCRIPTION>`

- Command:

  ```bash
  <COMMAND OR UI NAVIGATION PATH>
  ```

- Expected result: `<WHAT SUCCESS LOOKS LIKE — exact output, status code, or state change>`.
- If different: stop and go to [Failure modes & recovery](#failure-modes--recovery).

### 2. `<SHORT ACTION DESCRIPTION>`

- Command:

  ```bash
  <COMMAND OR UI NAVIGATION PATH>
  ```

- Expected result: `<WHAT SUCCESS LOOKS LIKE>`.

### 3. `<SHORT ACTION DESCRIPTION>`

- Command:

  ```bash
  <COMMAND OR UI NAVIGATION PATH>
  ```

- Expected result: `<WHAT SUCCESS LOOKS LIKE>`.

> Add or remove numbered steps as needed. Keep each step to one logical action so it can be retried independently.
>
> Example (illustrative — not required):
>
> ### 1. Confirm the service is reachable
>
> - Command:
>
>   ```bash
>   curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health
>   ```
>
> - Expected result: prints `200`.

## Failure modes & recovery

> List the realistic ways each step can fail, how to recognize each, and how to recover or roll back. One row per failure mode.

| Symptom | Likely cause | Recovery action | Rollback safe? |
|---------|--------------|-----------------|----------------|
| `<OBSERVED ERROR / OUTPUT>` | `<ROOT CAUSE>` | `<STEPS TO RECOVER>` | `<YES / NO>` |
| `<OBSERVED ERROR / OUTPUT>` | `<ROOT CAUSE>` | `<STEPS TO RECOVER>` | `<YES / NO>` |
| `<TIMEOUT / PARTIAL COMPLETION>` | `<ROOT CAUSE>` | `<STEPS TO RECOVER>` | `<YES / NO>` |

Rollback procedure (if the operation must be undone):

1. `<ROLLBACK STEP 1 — e.g. restore from the snapshot captured in Preconditions>`.
2. `<ROLLBACK STEP 2>`.
3. Confirm the system is back to its pre-change state using [Verification](#verification).

## Escalation

> Who to contact, when, and how — when the operator cannot resolve the issue alone.

- Escalate when: `<CONDITION, e.g. recovery actions above fail / impact exceeds threshold / time budget exceeded>`.
- Primary contact: `<TEAM OR ROLE>` via `<CHANNEL — chat, ticket queue, on-call rotation>`.
- Secondary / after-hours: `<ESCALATION PATH>`.
- Include in the escalation: this runbook link, the failing step number, exact command output (with any secrets redacted), and the timeline of actions taken.

## Verification

> How to prove the operation succeeded — independent of the steps above. The operator should be able to confirm a good end state without trusting intermediate output.

- [ ] `<CHECK 1 — e.g. service reports healthy>`:

  ```bash
  <VERIFICATION COMMAND>
  ```

  Expected: `<EXPECTED OUTPUT>`.

- [ ] `<CHECK 2 — e.g. key metric within normal range>`.
- [ ] `<CHECK 3 — e.g. no new errors in logs for N minutes>`.
- [ ] Cleanup done: temporary files, flags, or maintenance modes removed.
- [ ] Record the run: `<WHERE TO LOG COMPLETION — ticket, log entry, channel post>`.

## Related pages

> Link to adjacent runbooks, reference docs, and architecture pages. Use relative wiki links.

- [`<RELATED RUNBOOK — e.g. the rollback or teardown procedure>`](<RELATIVE/PATH>)
- [`<REFERENCE DOC — e.g. system architecture or configuration reference>`](<RELATIVE/PATH>)
- [`<TROUBLESHOOTING / FAQ PAGE>`](<RELATIVE/PATH>)
