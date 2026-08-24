---
name: board
description: Use when someone asks what every agent or lane is doing, for orchestration status, which lanes are ready, blocked, stalled or waiting to integrate, who owns what, or whether a worker is still alive. Renders the parallel-execution board from git and the live session list. Read-only.
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh *)
---

# Lane board

Show every lane, who owns it, and what state it is actually in. **Read-only —
never dispatch, provision, commit, or write a lane record here.**

`$0` may name a single lane. Flags: `--fast` skips git state, `--no-sessions`
skips owner liveness.

## Who runs this

**Both roles.** The main agent uses the whole board to schedule. A worker uses it
for two specific things, and should not read it as an invitation to act on
another lane:

- **Before touching any path outside its own ownership set** — `roles.md`
  requires reading that path in every other live worktree first, and the board is
  where those worktrees are listed. Use `ownsCollisions` and the `worktree`
  column, then read; do not write.
- **To confirm its own lane's state** — particularly whether its work has already
  been integrated (`merged`), which a worker cannot detect from inside its own
  session.

A worker seeing a problem on someone else's lane **reports it to the main agent**
and does not act on it. The board is information, not authority.

## Run

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"
```

If it returns `"pdle": false`, there are no lanes in this repository. Say so
plainly and stop — that is not an error, and it is not an invitation to create
one. Offer `/worktree:list` if they wanted worktrees.

## Render

One row per lane, ordered by wave then lane id:

```
Lane        Package   Owner              Branch          Δmain  staged  dirty  State
WP-P08      P08       agent 2            lane/WP-P08        +3      12      0  at-gate
WP-P12      P12       —                  lane/WP-P12         0       0      0  queued
WP-P15      P15       agent 1            lane/WP-P15         0       0      4  in-progress
WP-P19      P19       agent 4            lane/WP-P19         0       0      0  dispatch-held
```

- `Δmain` is `ahead`. Show `-N` when `behind` is non-zero and the lane is not merged.
- `dirty` is `modified + untracked`.
- Owner `—` means unassigned. Append ` [ref]` only when `ownerCount > 1`.

Then **capacity**, because every scheduling decision depends on it:

```
Capacity: 2 background workers idle, 1 busy, 1 unreachable
```

A worker counts as capacity only if it is a background session **and** has
answered a handshake. Say `unknown` — never `none` — if `sessionsAvailable` is
false.

## Report anomalies before anything else

Every `flags` entry is a real defect, not a warning to scroll past. Lead with
them, most severe first. `references/board-states.md` has the full table; the
ones to never bury:

- `owner-name-ambiguous` — **blocking.** Two live sessions answer to one name,
  which means two sessions pointed at one worktree.
- `worktree-registered-twice` — **never run `git worktree prune`.** Say so
  explicitly.
- `merged-but-still-assigned` — the lane's work landed and nobody told it. It is
  reporting a state that no longer exists.
- `staged-but-unreported` — a packet is banked and nobody was told.
- `staged-work-no-live-owner` — the worker died; the staged diff is the
  deliverable and is fully recoverable.
- `behind-default-branch` — the lane is building against a superseded base.

If `ownsCollisions` is non-empty, show it. Two lanes sharing a component may not
run concurrently.

## Reading stalls

There is no `stalled` field, because stalling is not visible in a single
snapshot. Infer it, then **ask rather than assert**:

| Signal | Reading |
|---|---|
| `at-gate` + `staged-but-unreported` | banked a packet, started nothing new |
| `assigned-not-begun` + owner idle | the turn ended on the acknowledgement |

Name the possibilities when you ask — *mid-investigation with nothing written
yet; a stop condition that did not reach me; or something blocking you that you
have not raised.* Asking "are you stalled?" invites a defensive answer.

**Never poll.** To learn when a worker next goes idle, subscribe once:
`SendMessage({to: "<worker>", notify_when_idle: true})` with no `message` — a
pure subscription that costs the worker nothing. This works from a background
main agent as well as an interactive one.

**But treat the notice as an optimisation, not a guarantee.** It reaches the
subscriber only when both sessions are in the same permission class; otherwise it
is shown to the user's transcript instead. So a subscription may simply never
arrive, and **the absence of an idle notice means nothing.** Git is what says
whether work happened.

## Notes

- The board is **rendered, never stored.** Do not write a summary of it to disk;
  a stored board goes stale and is then believed.
- Never report a state the script did not compute.
- Never report a lane as staffed without an `ackedAt`.
