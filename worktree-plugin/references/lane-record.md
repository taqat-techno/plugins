# The lane record

A **lane** is the execution unit of Plan-Driven Lane Execution: one work
package, one worktree, one branch, one base commit, one exclusive ownership
set, and at most one worker at a time.

Most of that is already knowable from git. The lane record persists **only what
git cannot answer**.

## The test for adding a field

> Can git, the filesystem, or `claude agents --json` answer this?

If yes, it does not belong here. Every stale-state failure this protocol exists
to prevent was a persisted copy of a computable fact.

## Location and format

```
.claude/lanes/<lane-id>.lane        one file per lane
.claude/lanes/reports/<lane-id>-<nnn>.md    append-only worker reports
```

The format is **porcelain-style**: one `key value` pair per line, first space
separates. Same shape as `git worktree list --porcelain`, for the same reason —
it is unambiguous to write, trivial to parse in bash 3.2 without `jq`, and it
diffs cleanly.

```
lane            WP-11-cash
package         WP-11-cash
owns            cash_custody
owns            field_cash_portal
worktree        .claude/worktrees/WP-11-cash
branch          lane/WP-11-cash
wave            3
base            6725511f4c2a8b1d9e0f3a5c7b2d4e6f8a0c1b3d
owner           agent 4
dispatch        d-014
dispatched-at   2026-08-22T22:47:02Z
acked-at        2026-08-22T22:47:10Z
held            false
env             config odoo.lane-p11-cash.conf
env             ports 8703,8704
env             db_prefix medline_p11c_
```

## Fields

| Key | Repeatable | Written by | Why it cannot be derived |
|---|---|---|---|
| `lane` | no | Main Agent | identity |
| `package` | no | Main Agent | the plan work package this lane executes |
| `owns` | **yes** | Main Agent | a *decision* about exclusive ownership. Only the plan and the Main Agent know it |
| `worktree` | no | Main Agent | repo-relative path; the binding is conventional until a worker enters it |
| `branch` | no | Main Agent | git knows the branch exists, not that it is this lane's |
| `wave` | no | Main Agent | which integration round this lane belongs to |
| `base` | no | Main Agent | git records the commit; it cannot say *why* that commit was chosen |
| `owner` | no | Main Agent | assignment fact. Absent = unassigned |
| `dispatch` | no | Main Agent | correlates a dispatch with its ack |
| `dispatched-at` | no | Main Agent | ISO-8601 UTC |
| `acked-at` | no | Main Agent | absent = **not acked**. An unacked lane is not staffed |
| `held` | no | Main Agent | `true` when delivery was held for approval. A held lane is never capacity |
| `env` | **yes** | Main Agent | `env <key> <value>` — **opaque project metadata.** Work Tree carries it into the brief and never interprets it |

## There is exactly one writer

**Only the Main Agent ever writes a `.lane` file.** Not the worker, not a hook,
not a script.

Workers write **new files** under `.claude/lanes/reports/` and never modify an
existing one. The "last report" is therefore *derived* — it is the
highest-numbered report file for that lane — and never stored.

This is deliberate. A single mutable file with two writers is the shape that
produces silent lost updates: no conflict marker, no error, no recovery. One
writer per file plus append-only reports removes that failure class entirely
rather than managing it.

## What is deliberately absent

No status label. No `ahead` / `behind` / staged counts. No merge state. No
session pid, ref, or kind. No message history.

All of it is derived — see `references/board-states.md`.

The one that matters most: **a lane's state is never written down.** A record
saying `at-gate` while git says the branch is already merged into `main` is
worse than no record at all, because it is believed.

## Lifecycle

| Event | Change |
|---|---|
| Provisioned | file created with `lane`…`base`, `env`; no `owner` |
| Dispatched | `owner`, `dispatch`, `dispatched-at` set; `held` set from the delivery result |
| Delivery held | `held true`, no `acked-at` → excluded from capacity |
| Acked | `acked-at` set |
| Reassigned | `owner`, `dispatch*`, `acked-at`, `held` cleared. **The worktree and its staged work are untouched** |
| Worker reports | worker adds `reports/<lane>-<nnn>.md`; the `.lane` file does not change |
| Merged | nothing is written. `git merge-base --is-ancestor <branch> main` is the answer |
| Retired | record removed only once the branch is an ancestor of the default branch |

## Legacy mode

If `.claude/lanes/` does not exist, this plugin behaves exactly as it did
before PDLE existed. No file here is created unless a lane is provisioned or
`/worktree:init --project` is run and confirmed.
