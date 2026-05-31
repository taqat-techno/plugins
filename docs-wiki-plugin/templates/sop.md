# <SOP Title — short, action-oriented, e.g. "Rotate Service Account Credentials">

<!--
  Standard Operating Procedure (SOP) template.
  Replace every <ANGLE_BRACKET> placeholder with real content, then delete this comment block.
  Keep section headings as real Markdown headings (#, ##) so the page stays scannable and indexable.
  Each section is single-topic on purpose — do not merge sections.
-->

## Metadata

- SOP ID: <SOP-NNN or unique identifier>
- Version: <X.Y>
- Status: <Draft | Approved | Deprecated>
- Owner: <role or team responsible for this SOP, e.g. "Platform Team">
- Last reviewed: <YYYY-MM-DD>
- Next review due: <YYYY-MM-DD>

## Purpose

State why this procedure exists in one or two sentences. Describe the outcome a reader achieves by following it and the problem it prevents.

<Explain the goal of this SOP — what it accomplishes and why it matters.>

## Scope

Define exactly what this SOP covers and, just as importantly, what it does not.

- Applies to: <systems, environments, or activities this procedure governs>
- Does not apply to: <related activities handled by a different procedure>
- Frequency / trigger: <on demand | scheduled | triggered by event such as an alert or request>

## Roles and responsibilities

List who does what. One row per distinct role; a single person may hold more than one role.

| Role | Responsibility |
|------|----------------|
| <Operator / Performer> | <Executes the steps in the Procedure section> |
| <Reviewer / Approver> | <Verifies preconditions and signs off where required> |
| <Escalation contact> | <Is contacted when a step fails or a decision is needed> |

## Prerequisites

Everything that must be true or available before starting. Confirm each item, then proceed.

- Access: <required permissions, roles, or accounts>
- Tools: <software, CLI, or utilities needed, with versions if relevant>
- Inputs: <files, parameters, or information the operator must have ready>
- Preconditions: <state the system must be in before starting, e.g. "no active maintenance window">
- Approvals: <any sign-off required before execution>

## Procedure

Perform the steps in order. Do not skip a step unless the SOP explicitly allows it. After each step, confirm the expected result before moving on.

1. <First action — start with a verb. State the expected result.>
2. <Second action. Note any value to record or flag to set.>
3. <Third action. Reference a related page if a sub-procedure applies.>
4. <Continue numbering until the procedure is complete.>

> Tip: If a step has a decision point, state the condition and the branch explicitly, for example: "If the check fails, go to the Safety and rollback section; otherwise continue."

### Example (illustrative — not required)

The block below shows the expected shape of a step. It is a sample only; replace it with steps for your own procedure.

```text
1. Confirm the target environment matches the change request.
2. Take a snapshot or backup of the current state and record its identifier.
3. Apply the change using the approved command or interface.
4. Wait for the system to report a healthy state, then record the timestamp.
```

## Safety and rollback

Describe how to undo the change or contain damage if something goes wrong. Write this so an operator can recover under pressure without improvising.

- Before you start: <what to back up or snapshot, and where the backup identifier is recorded>
- If a step fails: <stop condition — when to halt rather than continue>
- Rollback steps:
  1. <First action to restore the previous known-good state.>
  2. <Second action. Verify the system returned to its prior state.>
- Escalate if: <conditions under which to stop and contact the escalation role>

## Verification

Prove the procedure succeeded. List concrete, observable checks — not "looks fine".

- [ ] <Check 1 — the expected output, status, or value to confirm>
- [ ] <Check 2 — a second independent signal confirming success>
- [ ] <Check 3 — confirm no unintended side effects were introduced>

Record the verification result (who, when, outcome) in your change log or ticket as required by your team's process.

## Related pages

Link to procedures, references, and context a reader may need next.

- <Related SOP or runbook — link>
- <Reference documentation or policy — link>
- <Contact or escalation directory — link>

## Change history

| Version | Date | Author | Summary of change |
|---------|------|--------|-------------------|
| <X.Y> | <YYYY-MM-DD> | <author / role> | <what changed in this revision> |
