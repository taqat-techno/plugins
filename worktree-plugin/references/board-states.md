# Board states — derivation and anomalies

The board is **rendered truth**. It is never stored, and it can never contradict
git, because it is computed from git.

Everything here comes from one call:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"
```

Add `--no-sessions` to skip owner-liveness discovery, `--fast` to skip git state.
`pdle: false` means no `.claude/lanes/` exists — this repository is not running
lanes, and that is not an error.

## The seven states

Evaluated in this order. Order matters: **work is checked before ownership**, so
staged or dirty work is never hidden behind `queued` when a worker died.

| # | State | Condition | Meaning |
|---|---|---|---|
| 1 | `merged` | `commitsFromBase > 0` ∧ branch is ancestor of default ∧ tree clean | The lane's work landed. Retire it |
| 2 | `dispatch-held` | `held` ∧ no `acked-at` | Delivery was held for the recipient's approval. **Not staffed. Not capacity** |
| 3 | `in-progress` | `modified > 0` ∨ `untracked > 0` | Work in flight |
| 4 | `at-gate` | `staged > 0` ∨ `commitsFromBase > 0` | A packet is banked, waiting for integration |
| 5 | `queued` | no `owner` | Provisioned, unstaffed. Honestly idle |
| 6 | `assigned-not-begun` | `owner` ∧ `acked-at` ∧ tree clean | Acked, nothing written yet |
| 7 | `assigned-no-ack` | `owner` ∧ no `acked-at` | Dispatched, never acknowledged. **Treat as unstaffed** |

### Why `commitsFromBase` exists

A lane branch cut from the integrated base and never committed to is
**trivially an ancestor** of the default branch. Without counting the commits
the lane actually produced, every un-started lane reports `merged` — the most
dangerous possible false positive, because it says *done* about work that was
never begun.

`merged` therefore means *"this lane's work landed"*, never *"this ref is
reachable"*.

## Stall detection

There is no `stalled` state, because stalling is not a property of the
filesystem — it is `at-gate` or `assigned-not-begun` that has **stopped
changing while its owner is idle**.

Read it from two facts the board already carries:

| Signal | Reading |
|---|---|
| `at-gate` ∧ `reportCount == 0` (flag `staged-but-unreported`) | A packet is banked and nobody was told. **This is the Lane-D signature** — the worker finished a task and started nothing new |
| `assigned-not-begun` ∧ owner idle ∧ acked long ago | Acked and stopped. The turn ended on the acknowledgement |

**Ask rather than assume, and name the possibilities** — *are you mid-investigation
with nothing written yet (legitimate — reading source produces no files); did you
hit a stop condition that did not reach me; or is something blocking you that you
have not raised?* Asking "are you stalled?" invites a defensive answer; naming the
three cases gets a straight one.

**Never poll in a loop.** To learn when a worker goes idle, subscribe once:
`SendMessage({to: "<worker>", notify_when_idle: true})` — omit `message` for a
pure subscription that costs the worker nothing.

## Anomaly flags

Every flag below exists because its absence caused a real, documented failure.

| Flag | Means | Act on it by |
|---|---|---|
| `worktree-missing` | recorded path is gone | Re-provision, or retire the lane |
| `worktree-not-registered` | directory exists, git does not know it | Do not dispatch. Investigate before touching |
| `worktree-registered-twice` | same directory under two path spellings, one `prunable` | **Never run `git worktree prune`.** One spelling came from WSL (`/mnt/c/...`), the other from Git Bash (`C:/...`). A prune from the wrong shell deregisters staged work |
| `branch-mismatch` | worktree is on a different branch than the record says | The directory name is not identity. Reconcile before dispatching |
| `behind-default-branch` | lane branch is behind the current integration base | Rebase, back-merge, or close the packet and re-cut in the next wave |
| `owner-name-ambiguous` | two live sessions answer to the owner's name | **Blocking.** Resolve to a `[ref]` and stand down the stale holder. Two sessions with one name are two sessions pointed at the same worktree |
| `owner-not-live` | owner named, no such live session | Worker died. **The lane and its staged work survive** — clear the owner and requeue |
| `owner-not-background` | owner is an interactive session | Its inbound dispatches are held for its user's approval. Not reliable capacity |
| `dispatch-held` | delivery was held | Never counts toward capacity; re-check on every board change |
| `staged-but-unreported` | packet banked, no report file | Probable stall between tasks |
| `merged-but-still-assigned` | work landed, lane still shows an owner | **Tell the lane.** A gate released centrally that the holder was not told about leaves it reporting a state that no longer exists |
| `staged-work-no-live-owner` | staged work, dead owner | Fully recoverable — the staged diff *is* the deliverable |

## Ownership collisions

`ownsCollisions` lists every pair of lanes sharing a component:

```json
{"a": "WP-A", "b": "WP-B", "component": "shared_util"}
```

**Two lanes may not run concurrently if their ownership sets intersect.** A
collision between two live lanes is a dispatch error that has already happened;
between a live lane and a queued one it is a scheduling constraint. Either way it
is decided here, before work starts, not discovered at merge time.

## What the board must never do

- Assert a state it did not compute.
- Report a lane as staffed without an `acked-at`.
- Report "no sessions" when session discovery was unavailable — say **unknown**.
- Persist anything. If it can be rendered, it is not written down.
