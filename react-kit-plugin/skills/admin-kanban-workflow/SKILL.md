---
name: admin-kanban-workflow
description: Kanban/board views and status-driven workflow state machines for admin UI. Owns the rule that board columns are workflow stages from a project-supplied state set (never hardcoded), the full-height horizontal-scroll board layout with collapsible columns and per-column scroll, compact cards that open a detail drawer, and action-based transitions where each move is a typed action with allowed-from-states, a role gate, pre-move validation, destructive-move confirmation, an optimistic-vs-confirmed update rule, and a success audit entry. Activates when building any board or kanban view, or any status-driven workflow with transition actions surfaced on a board or as action buttons in a form or drawer, including assignment, approve/reject, cancel/expire, and reopen.
version: 0.4.0
last_reviewed: 2026-05-31
owns:
  - board-columns-are-workflow-stages-from-a-supplied-state-set rule (never hardcode states)
  - full-height board layout (horizontal scroll, collapsible columns, per-column scroll/pagination)
  - column header with live count + empty-column affordance
  - compact card -> detail drawer pattern
  - typed transition contract (allowed-from-states, role gate, validation, confirmation, update rule, audit entry)
  - generic workflow actions (assignment/ownership, approve/reject, cancel/expire, reopen)
  - the project-adapter state-machine shape (states + transitions + guards)
defers_to:
  - admin-roles-and-permissions (who may perform a transition)
  - admin-dangerous-actions (confirmation for destructive / irreversible moves)
  - data-fetching-states (loading / error / empty / refetch affordances on the board)
  - admin-view-patterns (the detail drawer surface itself)
user_invocable: false
---

# admin-kanban-workflow

## Purpose

A board is a workflow rendered as columns. The two failure modes are: (1) hardcoding the stages so the board only works for one project, and (2) letting the UI "move" a card without a server-side authorization and validation check behind it. This skill makes columns a project-supplied state set, makes every move a typed transition with a guard and an audit trail, and keeps the board layout stable at any height.

## When to use

Activate when:

- Building any board or kanban view (columns = stages of a pipeline).
- Building any status-driven workflow, whether moves happen on the board or via action buttons in a form/drawer.
- Adding a transition action: assignment/ownership change, approve/reject, cancel/expire, reopen, or any custom stage move.
- Adding validation that must pass before a record can leave its current stage.
- Adding confirmation for a destructive or irreversible move.

Do NOT activate for plain CRUD lists with no status workflow (use `admin-crud`) or for pure loading/error display (use `data-fetching-states`).

## Inputs (adapter)

Every project-specific value is a NAMED adapter input. The skill hardcodes none of them.

1. **`STATE_SET`** — the ordered list of workflow stages (e.g. the columns). Source of truth for both column order and the state machine. The board renders this order regardless of API response order.
2. **`TRANSITIONS`** — list of typed transitions, each `{ action, from[], to, roleGate, guard, destructive, updateRule, auditEvent }`. See the state-machine shape below.
3. **`roleCheck(role, action)`** — adapter that resolves whether the current actor may invoke a transition. Owned by `admin-roles-and-permissions`; this skill only calls it.
4. **`boardQuery(stages)`** — data adapter returning records grouped (or groupable) by stage, plus `{ isLoading, isError, refetch, isFetching }`. Loading/error/empty affordances are owned by `data-fetching-states`.
5. **`transitionMutation(action)`** — server call that performs one transition; returns `{ isPending, mutateAsync, error }`. The server enforces authorization + validation; the UI never decides the outcome.
6. **`recordSummary(record)`** — adapter mapping a record to the compact card fields (title/id, status badge, owner badge).
7. **`auditSink`** — where a successful transition is recorded. The frontend assumes the backend writes the audit entry; this input names the expectation, it does not implement logging.
8. **`labels` / i18n keys** — column labels, action labels, empty-column copy. No domain copy is hardcoded.

## Read-only investigation steps

1. **Where do the stages come from today?** If the column list is a literal array in a component (`['todo','doing','done']`), that is the smell — it must be the `STATE_SET` adapter input.
2. **Is each move backed by a server call that authorizes AND validates?** Find one transition. If the UI mutates local state and only then calls the API (or never calls it), fix to confirmed-update.
3. **Are transition buttons gated by role, current state, and record preconditions — or just by role?** A button visible from the wrong stage is a bug even if the role is correct.
4. **Does a destructive move (cancel, delete-on-board, irreversible reject) prompt for confirmation?** If it fires on a single click, route through `admin-dangerous-actions`.
5. **Is there an audit entry on success?** Confirm the backend records who/when/what. The frontend should not call a separate audit endpoint.
6. **Does the board survive a missing stage in the API response?** If the layout collapses when a stage has zero records, synthesize an empty column.

## Decision framework

### State-machine shape (adapter input)

Provide the workflow as data, not code. Example (illustrative — not required):

```
STATE_SET = [ "New", "InProgress", "Review", "Done", "Cancelled" ]

TRANSITIONS = [
  { action: "start",    from: ["New"],                to: "InProgress",
    roleGate: "operator", guard: null,                destructive: false,
    updateRule: "confirmed", auditEvent: "record.started" },
  { action: "assign",   from: ["New","InProgress"],   to: "(same)",
    roleGate: "manager",  guard: "ownerRequired",     destructive: false,
    updateRule: "confirmed", auditEvent: "record.assigned" },
  { action: "approve",  from: ["Review"],             to: "Done",
    roleGate: "manager",  guard: "proofRequired",     destructive: false,
    updateRule: "confirmed", auditEvent: "record.approved" },
  { action: "reject",   from: ["Review"],             to: "InProgress",
    roleGate: "manager",  guard: "reasonRequired",    destructive: false,
    updateRule: "confirmed", auditEvent: "record.rejected" },
  { action: "cancel",   from: ["New","InProgress","Review"], to: "Cancelled",
    roleGate: "manager",  guard: "reasonRequired",    destructive: true,
    updateRule: "confirmed", auditEvent: "record.cancelled" },
  { action: "reopen",   from: ["Done","Cancelled"],   to: "InProgress",
    roleGate: "manager",  guard: null,                destructive: false,
    updateRule: "confirmed", auditEvent: "record.reopened" },
]
```

A transition is *available* for a record only when ALL hold:

```
record.status ∈ transition.from
  AND roleCheck(currentRole, transition.action) == true
  AND transition.guard is satisfied (required fields/proof present or collected)
```

### Transition contract

| Field | Meaning | Rule |
|---|---|---|
| `from[]` | stages the action may start from | If `record.status ∉ from`, do not render the button. |
| `roleGate` | who may invoke | Resolved via `admin-roles-and-permissions`. If denied, do not render the button. |
| `guard` | precondition / required input | Validate client-side for UX; server re-validates. Empty guard = no input needed. |
| `destructive` | irreversible / data-losing | If true, route confirmation through `admin-dangerous-actions`. |
| `updateRule` | how the UI reflects the change | State transitions are `confirmed` (wait for success). See below. |
| `auditEvent` | event name recorded on success | Backend writes it; frontend names the expectation. |

### Optimistic vs confirmed update rule

```
State-transition move (approve/reject/cancel/assign/reopen/start)
   → CONFIRMED: disable action → spinner → await server success → refetch/close
   → never reflect the new stage before the server confirms

Low-risk inline edit (rename, note, tag)
   → OPTIMISTIC allowed: show change → spinner → revert on error
```

Status changes are high-stakes; a card must not appear in the next column until the server confirms. Only cosmetic edits may update optimistically.

### Board layout

| Concern | Rule |
|---|---|
| Container height | Fill parent: `h-full flex flex-col`. Never `h-screen` or fixed pixel height. |
| Board row | `flex-1 min-h-0` so it grows to remaining height; never `overflow-x-hidden` (kills horizontal column scroll). |
| Column | `h-full flex flex-col`; expanded width ≈ 240–280px, collapsed ≈ 56px. |
| Column header | `sticky top-0 z-10` with live count badge; expanded = horizontal layout, collapsed = vertical rotated label. `aria-expanded` + descriptive `aria-label`. |
| Card scroll area | `flex-1 overflow-y-auto`; hidden when the column is collapsed (a thin `flex-1` filler holds the height). |
| Column order | Always `STATE_SET` order. Reorder the API response to match; synthesize an empty column for any omitted stage. |
| Large stages | Per-column scroll; per-column pagination only when the data adapter supports it — do not fake it client-side. |

```
+-- toolbar (shrink-0): refresh, hint ------------------------------+
+-- board row (flex-1 min-h-0, overflow-x-auto) -------------------+
| [New 4]   | [InProgress 7] | [Review 2] | [Done 31] | [Cxl ▮]   |
|  card     |  card          |  card      |  card     | (collapsed)|
|  card     |  card          | (empty:    |  card     |            |
|  card     |  card          |  centered) |   …       |            |
+------------------------------------------------------------------+
```

### Card and drawer

- Card = compact summary only: title/id, a status badge, an owner badge. Clicking opens the detail drawer (surface owned by `admin-view-patterns`).
- Transitions live in the drawer's actions section as action buttons (and optionally as drag, see below). Each button is rendered only when its transition is available.
- Guard input (reason, proof, assignee) is collected in an inline panel inside the drawer before the move fires; the move calls `transitionMutation` only after the guard is satisfied.
- On success: refetch the board (cache invalidation), then either keep the drawer open with refreshed card state or close it. Never leave the drawer showing the old stage.

### Drag (optional)

Drag-to-move is an optional convenience, never the only path and never the source of truth. A drop must resolve to the same typed transition (same `from`/`role`/`guard`/confirmation/audit) as the button. If a guard needs input or the move is destructive, the drop opens the same confirmation/panel rather than moving silently. If drag is not implemented, action buttons fully cover the workflow.

## Safety gates

- **Never** perform a transition without a server-side authorization AND validation check. UI gating is UX, not security.
- **Never** hardcode the stage list, the column set, or the transition table — they are `STATE_SET` / `TRANSITIONS` adapter inputs.
- **Never** reflect a state change optimistically; wait for server confirmation before moving the card.
- **Never** render a transition button when `record.status ∉ from`, when the role gate denies it, or when its guard cannot be satisfied — do not render-and-disable.
- **Never** fire a destructive or irreversible move on a single click; route through `admin-dangerous-actions`.
- **Never** let a successful transition skip its audit entry (the backend must record who/when/what).
- **Never** trust drag-and-drop to bypass a guard, role gate, or confirmation.
- **Never** render columns in API response order or drop a stage that returned zero records — keep `STATE_SET` order and synthesize empty columns.
- **Never** leave the drawer showing the pre-transition stage after a successful move.

## Validation checklist

Before committing a board/workflow change:

- [ ] Columns come from `STATE_SET`; no literal stage array in any component.
- [ ] Board uses `h-full flex flex-col` + `flex-1 min-h-0`; horizontal scroll works; no fixed/`h-screen` height.
- [ ] Each column header shows a live count; collapsed columns keep their height.
- [ ] Empty stages render a centered empty-column affordance, not a blank gap.
- [ ] Every transition button is gated by state (`from`), role, and guard before rendering.
- [ ] Each transition calls a server mutation that authorizes and validates; no client-only moves.
- [ ] State transitions use confirmed updates (no optimistic stage change); only cosmetic edits may be optimistic.
- [ ] Destructive/irreversible moves route through `admin-dangerous-actions`.
- [ ] A successful transition triggers a board refetch and refreshes/closes the drawer.
- [ ] An audit event name is defined for each transition; backend records it.
- [ ] Drag (if present) resolves to the same typed transition as the button.

## Output format

When scaffolding a board/workflow, output a WORKFLOW SPEC block:

```
WORKFLOW SPEC for <board-name>

STATES (column order):
  <S1> -> <S2> -> <S3> -> <S4>   (+ terminal: <St>)

TRANSITIONS:
  action     | from            | to        | role    | guard          | destructive | update    | audit
  -----------|-----------------|-----------|---------|----------------|-------------|-----------|------------------
  <start>    | <S1>            | <S2>      | operator| -              | no          | confirmed | record.started
  <assign>   | <S1>,<S2>       | (same)    | manager | ownerRequired  | no          | confirmed | record.assigned
  <approve>  | <S3>            | <S4>      | manager | proofRequired  | no          | confirmed | record.approved
  <reject>   | <S3>            | <S2>      | manager | reasonRequired | no          | confirmed | record.rejected
  <cancel>   | <S1>,<S2>,<S3>  | <St>      | manager | reasonRequired | YES         | confirmed | record.cancelled
  <reopen>   | <S4>,<St>       | <S2>      | manager | -              | no          | confirmed | record.reopened

BOARD COLUMN ORDER: [<S1>, <S2>, <S3>, <S4>, <St>]   (from STATE_SET; API order ignored)
CARD: title/id + status badge + owner badge -> opens detail drawer (admin-view-patterns)
DESTRUCTIVE MOVES: <cancel> -> confirm via admin-dangerous-actions
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Hardcoded column array in the component | Board works for one project only; adding a stage means editing code | Render from `STATE_SET` adapter input |
| Move card by mutating local state, then call API (or never) | UI and server can diverge; unauthorized/invalid moves slip through | Confirmed update: await server success, then refetch |
| Optimistic stage change for approve/reject/cancel | High-stakes move shown as done before it is; bad rollback | Wait for confirmation; optimistic only for cosmetic edits |
| Render-and-disable a forbidden transition button | Implies the action is reachable; confusing and probes capability | Do not render it at all (gate on state + role + guard) |
| Destructive move on a single click | Irreversible data loss with no confirmation | Route through `admin-dangerous-actions` |
| Drag-to-move bypasses guard/role/confirmation | Silent illegal transition | Drop resolves to the same typed transition as the button |
| Columns in API response order; skip empty stages | Layout shifts; tests flake; users lose orientation | Fixed `STATE_SET` order; synthesize empty columns |
| Frontend calls a separate audit endpoint | Duplicates/contradicts backend log; trust boundary leak | Backend records the audit event on the transition |
| Fixed/`h-screen` board height, `overflow-x-hidden` row | Breaks responsiveness and horizontal column scroll | `h-full flex flex-col` + `flex-1 min-h-0`, horizontal scroll |
| Leaving the drawer on the old stage after a move | User sees stale state; re-clicks the action | Refetch then refresh or close the drawer |

## Portability rationale

The board and workflow are entirely data-driven, so the skill is reusable across domains (Orders, Tickets, Requests, Records) and frameworks:

- Stages, transitions, and guards are adapter inputs, not literals — any team supplies its own `STATE_SET`/`TRANSITIONS`.
- Roles resolve through an adapter (`roleCheck`), so any RBAC model plugs in.
- The layout rules (full-height flex, sticky headers, per-column scroll) are CSS-pattern level, not tied to a UI kit.
- Authorization, validation, and audit live server-side; the frontend names the expectations rather than implementing policy.

## Cross-references

- `admin-roles-and-permissions` — resolves the role gate for each transition.
- `admin-dangerous-actions` — confirmation flow for destructive / irreversible moves.
- `data-fetching-states` — loading / error / empty / refetch affordances for the board query.
- `admin-view-patterns` — the detail drawer surface that a card opens.
- `admin-crud` — plain status-less lists (use instead of a board when there is no workflow).
- See `references/admin-kanban-pattern.md` and `references/admin-action-workflow-pattern.md` for the layout and transition detail.
