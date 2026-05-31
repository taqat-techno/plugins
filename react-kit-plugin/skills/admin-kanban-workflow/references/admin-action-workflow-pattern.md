# Admin action / workflow pattern

A reusable reference for status-transition actions in admin surfaces — Kanban boards, list rows, and detail drawers. The same action (approve, reject, assign, cancel, reopen, reveal) may be invoked from a card on a board, an inline row button in a table, or a button inside a detail drawer. The contract is identical regardless of surface. Domain nouns below (Orders, Tickets, Requests, Customers, Products, Records) are neutral placeholders; substitute your own. Roles (admin, manager, operator, viewer) are illustrative.

## What a transition is

A transition is a single, named change to a record's state. Model every admin action as a transition object with a fixed set of fields. Treat the transition definition as data, not scattered conditionals — one source of truth that the board, the row, and the drawer all read from.

A transition is defined by:

| Field | Meaning |
|---|---|
| `name` | Stable action identifier (e.g. `approve`, `reject`, `assign`, `cancel`, `reopen`, `reveal`). |
| `from` | Set of states the record must currently be in for this action to be offered. |
| `to` | The single state the record moves to on success (or `same` for in-place actions like reveal). |
| `roleGate` | Which roles may invoke it (UX gating only — see "Server is the boundary"). |
| `guard` | Precondition that must hold before the action is allowed (required input present, dependency satisfied, not already terminal). |
| `requiresInput` | Whether the action needs operator-supplied data (reason, reference, assignee). |
| `requiresProof` | Whether the action exposes or consumes sensitive/evidence data that must be audited on access. |
| `destructive` | Whether the action is irreversible or high-impact and therefore needs explicit confirmation. |
| `commit` | `optimistic` or `confirmed` — how the UI reflects the change relative to server acknowledgement. |
| `onSuccessInvalidate` | Which cached queries to refresh (the record's detail, its list/board column, any aggregate/summary). |
| `audit` | Whether the server is expected to record who/when/what on success (default: yes for any state change). |

## Generic transition table shape

Author transitions as a flat table or array. Example (illustrative — not required):

| name | from | to | roleGate | guard | requiresInput | requiresProof | destructive | commit |
|---|---|---|---|---|---|---|---|---|
| `approve` | `pending` | `approved` | manager | none | no | no | no | confirmed |
| `reject` | `pending` | `rejected` | manager | reason non-empty | yes (reason) | no | yes | confirmed |
| `assign` | `pending`, `approved` | `same` | manager, operator | assignee selected | yes (assignee) | no | no | confirmed |
| `process` | `approved` | `processed` | operator | reference non-empty | yes (reference) | no | yes | confirmed |
| `cancel` | `pending`, `approved`, `active` | `cancelled` | manager | none | optional (reason) | no | yes | confirmed |
| `expire` | `active` | `expired` | system/manager | past expiry | no | no | no | confirmed |
| `reopen` | `cancelled`, `rejected`, `expired` | `pending` | manager | none | no | no | no | confirmed |
| `reveal` | any | `same` | manager | none | no | yes | no | confirmed |
| `rename` | any | `same` | operator | name non-empty | yes (name) | no | no | optimistic |

State transitions are `confirmed`. Only low-risk metadata edits (rename, description, tags) may be `optimistic`.

## Rule: the server is the boundary, not the UI

UI gating is convenience, never security. Every rule below must be re-checked server-side on each request.

- Render an action only when `record.status ∈ transition.from` AND the current role satisfies `roleGate` AND `guard` holds. This is purely to reduce confusion and clicks.
- The server must re-authorize (role/permission) AND re-validate (`from`-state, guard, input) every transition, independent of what the client sent.
- Assume any client gate can be bypassed (dev tools, scripted calls, stale tab). The server must reject the bypass with the correct status code.
- Never send the acting user's identity in the payload as the authority for the action. The server derives the actor from the authenticated session; a payload claiming a different actor is rejected.

| Server rejects with | When |
|---|---|
| `401` | Not authenticated. |
| `403` | Authenticated but role/permission lacks the action. |
| `409` | State conflict — record is no longer in a valid `from` state (e.g. already approved). |
| `400` / `422` | Missing or invalid required input / guard not satisfied. |

## Conditional rendering by state

Map current state to the set of offered actions; never render permanently-disabled "ghost" buttons.

- For each surface, compute the allowed action set from the transition table: `actions = transitions.filter(t => record.status ∈ t.from && roleAllows(t) && guard(t))`.
- Terminal states (`processed`, `rejected`, `cancelled`, `expired`) show no transition actions — only read-only detail and history.
- An unknown/unmapped state shows no actions, not a crash and not every action.
- Disable an offered button only transiently (during its own pending mutation or while its required input is empty), not as a permanent state.

## Assignment / ownership actions

Ownership transfer (assign, claim, take over) is a transition like any other.

- The server sets the owner/assignee and the timestamp from the authenticated actor or the validated `assignee` input; the client never asserts ownership directly beyond naming the target assignee.
- After success, refetch the record so the UI shows the authoritative owner and timestamp — do not paint owner state from local guesses.
- `roleGate` controls who may assign; the server enforces that only permitted roles can transfer ownership and rejects attempts to assign to ineligible targets.

## Approve / reject

- `approve`: `from = pending → to = approved`. Typically no extra input; `confirmed` commit.
- `reject`: `from = pending → to = rejected`. `requiresInput` (reason) and `destructive` (terminal). Button stays disabled until the reason is non-empty; the server independently requires a non-empty reason and rejects with `400`/`422` if missing.
- Both invalidate the record's detail, its board column / list page, and any pending-count summary on success.

## Cancel / expire / reopen

- `cancel`: operator-initiated terminal transition from several active states; `destructive`, confirmation required, reason optional.
- `expire`: usually system- or schedule-initiated; guard is a time/precondition rather than operator input. The UI reflects it on refetch; it is still audited.
- `reopen`: moves a terminal record back to an active state. Treat as a state transition (`confirmed`), gated by role, and audited — it is not a "free undo."

## Proof / evidence-required actions (reveal pattern)

Some actions expose sensitive data (masked identifiers, contact details, account references) or require attaching evidence. These carry `requiresProof = true`.

- Fetch sensitive data only on an explicit user action via a dedicated endpoint — never prefetch on mount, never batch it into the normal record fetch.
- Reveal is itself an audited access event: the server logs actor, target, timestamp, and source on each reveal. Tell the operator the access was logged.
- Do not cache revealed values beyond the immediate session/component lifetime; each reveal is a fresh, individually-logged request.
- Evidence-required actions (e.g. attach proof before completing) guard on the presence of the evidence both client-side (button disabled) and server-side (rejected without it).

## Confirmation for destructive actions

- Any transition with `destructive = true` must require explicit confirmation before firing: a confirmation step that may also collect the required input (reason/reference) in the same step.
- Non-destructive, reversible actions (e.g. assign to a teammate) need not interrupt with a confirmation dialog.
- Confirmation is UX; it never substitutes for the server's re-validation of state and authorization.

## Optimistic vs confirmed commit

| Commit mode | Use for | UI behavior |
|---|---|---|
| `confirmed` | All state transitions (approve, reject, process, cancel, expire, reopen) and any high-stakes change. | Show pending spinner; update UI only after the server confirms; refetch/close on success; surface error on failure. |
| `optimistic` | Low-risk, easily-reversible metadata edits (rename, description, tags). | Apply locally immediately; reconcile on success; roll back to the prior value on error. |

- Never use optimistic commit for a state transition: a phantom "approved" that silently reverts is worse than a brief spinner.
- For confirmed actions, wait for the resolved success signal before closing a drawer or removing a card from a column — do not close on fire-and-forget.

## Audit on success

- Every transition that changes state, ownership, or exposes sensitive data is expected to be recorded server-side: actor, action name, record type, record id, timestamp, source, and sanitized payload.
- The client assumes the server (middleware/service layer) writes the audit record; the client does not call a separate audit endpoint after the action.
- Reveal / proof accesses are flagged as high-sensitivity audit events distinct from ordinary state changes.
- A read-only history view (reverse-chronological "who did what, when") can render from the same audit records so operators can trace a record's lifecycle.

## Error handling per transition

On failure, extract a human-readable message and show it in a dismissible, scoped alert near the action. Clear the error before re-attempting so a fixed retry does not show a stale message.

| Condition | Operator-facing message intent | Retry offered? |
|---|---|---|
| `401` | Session expired — re-authenticate. | After re-auth. |
| `403` | No permission for this action. | No (needs role change). |
| `409` | Record state changed — refresh and reassess. | After refetch. |
| `400` / `422` | Fix the highlighted input, then retry. | Yes, after correction. |
| `5xx` | Transient server error — try again later. | Yes, explicit button. |
| network | Connection failed — check connectivity. | Yes, explicit button. |

- Distinguish `401` (auth) from `403` (authz) from `409` (state conflict); do not collapse them all into "Server error."
- Do not auto-retry `409` or `5xx` in a loop; require an explicit operator retry.

## State coverage on every surface

Every surface (board column, list, drawer) must render an explicit state for each data condition — never a blank shell.

- `loading` → skeleton/spinner.
- `error` → message plus retry (per the table above).
- `empty` (zero records) → an explicit empty state, not a blank area.
- `stale` (refetching while showing old data) → keep data visible; do not flash "loading."
- `success` → the records.
- Cache invalidation on a successful transition refreshes the record's detail, its containing column/list, and any dependent aggregate (counts, totals) so the board and summaries never display stale numbers.
