# Dispatch pre-flight gates

Nine gates. **All must pass.** Any failure queues the lane and reports which
gate — it never downgrades to a warning and sends anyway.

Every gate exists because skipping it caused a documented failure.

| # | Gate | Check | Failure it prevents |
|---|---|---|---|
| 1 | **Ready** | Package prerequisites complete ∧ task `depends_on` complete ∧ no unresolved blocker | A lane assigned to work several prerequisite levels deep. It produced nothing and its branch never left the base commit |
| 2 | **Contract sufficient** | Package has `Owns`, `Laneable: yes`, tests, acceptance — and `Satisfies` when the plan carries a Completion Contract | Dispatching work whose done-condition nobody can state, or that serves no required outcome |
| 3 | **Background** | Target `kind == "background"` in `claude agents --json` | Dispatch to an interactive session is **held for its user's approval** and may never be seen. Three provisioned lanes once produced nothing while the board reported them running |
| 4 | **Unambiguous** | Exactly one live session answers to that name | Two sessions sharing a name are two sessions pointed at the same worktree. Both may act; the branch then holds staged content from two writers with no commit boundary between them |
| 5 | **Handshake answered** | The target has answered a channel test this session | "Probably available" is not available |
| 6 | **Free** | Target holds no other lane in `assigned*`, `in-progress`, or `at-gate` | One worker, one lane |
| 7 | **Ownership disjoint** | `Owns` intersects no live lane's `Owns` | Two lanes independently editing the same component — which surfaces as a merge conflict between two *correct* fixes |
| 8 | **Correct base** | Lane base == current integrated default-branch tip | Building on unintegrated work. Because workers never commit, a lane cannot see another lane's staged work at all |
| 9 | **No stale dispatch** | No unacked or `held` dispatch outstanding for this lane | Approving a stale message later starts work that is already finished, on a branch that already holds a tested packet |

## Capacity

> **Capacity = background sessions that have answered a handshake.**

Compute it before scheduling, not after. If capacity is zero, **queue** — do not
dispatch and hope.

## When a gate fails

Say which gate, why, and what would clear it. Then queue the lane.

```
LANE WP-11-cash NOT DISPATCHED — gate 7 (ownership disjoint)
  WP-11-cash owns: cash_custody, field_cash_portal
  WP-08      owns: field_cash_portal          <-- intersection
  Clears when: WP-08 reaches `merged`, or field_cash_portal is moved out of one set.
  Lane queued.
```

## Held delivery is not an error to retry

`SendMessage` tells the sender when delivery was held:

```
[Cross-session delivery notice] Your message to another session was held for the
recipient user's approval … Not delivered to that session's Claude yet.
```

On that notice: set `held true`, leave `acked-at` unset, and **exclude the lane
from capacity**. Do not resend. Re-check on every board change.

Before reassigning a held lane, **send an explicit, named stand-down** — a
correction that names the earlier message and says to disregard it. A silent
reassignment leaves a live trap in someone's approval queue.

## Ack tracking

- Record `dispatch`, `dispatched-at` at send.
- Record `acked-at` **only** when the worker acknowledges.
- An unacked lane is `assigned-no-ack` and **is not staffed**.
- Re-read the target's ` [ref]` from `ListAgents` **at dispatch time**. A ref
  that was not just read from a listing or an error will not resolve, so a ref
  is never stored in a lane record.
