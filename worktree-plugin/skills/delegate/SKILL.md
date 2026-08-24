---
name: delegate
description: Use when the main agent assigns work to a worker session in a parallel run - "assign this to agent 2", "dispatch the next ready work", "give the next lane to whoever is free", "hand P08 to a worker". Runs the pre-flight gates, provisions the lane, writes the brief and tracks the acknowledgement.
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh *), Bash(claude agents --json)
---

# Delegate a lane

Assign one work package to one worker, safely. **Main Agent only.**

`$0` may name the package, the worker, or both. With no argument: the highest
priority ready package, to the next free worker.

A dispatch is not a prompt with a task in it. It is a provisioned lane, a written
brief, nine passed gates, and a tracked acknowledgement.

## 1. Run the gates — all nine, no exceptions

Load `references/dispatch-gates.md` and check every gate. **Any failure queues
the lane** and reports which gate; it never downgrades to a warning.

Fast checks first, so a doomed dispatch fails cheaply:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"   # gates 6,7,9 + live ownership
claude agents --json                                # gates 3,4,5
```

The three that are skipped most often and cost most:

- **Gate 3 — background only.** A dispatch to an interactive session is held for
  its user's approval. Three provisioned lanes once produced nothing while the
  board reported them running.
- **Gate 4 — unambiguous name.** Two live sessions with one name are two sessions
  pointed at the same worktree.
- **Gate 7 — ownership disjoint.** Use `ownsCollisions`. This is the rule that
  decides whether two lanes may run at all.

## 2. Provision the lane

Skip if the lane already exists and is clean.

```bash
git worktree add "<repo>/.claude/worktrees/<lane>" -b "lane/<lane>" <base>
git worktree lock --reason "worktree-plugin: persistent workspace" "<abs path>"
```

**Never `EnterWorktree({name})` for a lane.** It takes no per-call base ref, so
it would cut from `origin/<default>` — usually behind the integrated trunk. The
base must be the **current integrated trunk tip**, which is what makes it
impossible for a lane to depend on work still staged elsewhere.

The lock is what makes the lane outlive its worker.

Then write the lane record — `references/lane-record.md`. Emit **one canonical
path spelling**; a worktree registered under two spellings is the trap where each
shell reports the other's as prunable.

## 3. Write the brief before sending anything

Generate `.claude/lanes/briefs/<lane>.md` from the work package plus the lane
record, using `references/brief-template.md`.

**Generate it; do not compose it freehand.** A hand-written brief drifts from the
plan, and the drift stays invisible until integration.

Carry `env` values through verbatim. Work Tree does not interpret them — ports,
config paths and database prefixes are the project's meaning, not this plugin's.

## 4. Dispatch

```
SendMessage({
  to: "<worker>",              // add " [ref]" ONLY if ListAgents just showed one
  summary: "Lane <lane> — <package title>",
  message: "You are LANE <lane>. Brief: <path>. Read it and
            references/roles.md before starting. Acknowledge and begin in the
            same turn; if your first stretch is investigation that writes no
            files, say so in the ack."
})
```

Re-read the ` [ref]` from `ListAgents` **now**. A ref that was not just read from
a listing or an error will not resolve, which is why one is never stored.

Then record the dispatch: `owner`, `dispatch`, `dispatched-at`.

## 5. Handle the delivery result honestly

| Result | Record | Board |
|---|---|---|
| Delivered | leave `held false`, wait for the ack | `assigned-no-ack` |
| **Held for approval** | `held true` | `dispatch-held` — **not capacity** |

On a `[Cross-session delivery notice]`: **do not resend.** Set `held`, exclude
the lane from capacity, and tell the user plainly that this lane is not staffed
despite being provisioned. That gap — provisioned but unstaffed, while every
board says otherwise — is the failure this whole gate sequence exists to prevent.

Record `acked-at` **only** on a real acknowledgement. Until then the lane is not
staffed, and silence is never consent.

## Reassigning

1. **Send an explicit, named stand-down first** — a correction naming the earlier
   message and saying to disregard it. A silent reassignment leaves a live trap
   in someone's approval queue that may be approved hours later.
2. Clear `owner`, `dispatch`, `dispatched-at`, `acked-at`, `held`.
3. **Leave the worktree and its staged work untouched.** The lane persists; only
   the assignment moved.

## Report

Name the lane, the worker, the base, the ownership set, and the brief path. If
anything was queued instead of dispatched, say which gate stopped it and what
would clear it.

## Guardrails

- Never dispatch beyond capacity — queue, and say so.
- Never dispatch to an interactive session, or to an ambiguous name.
- Never count a dispatch, or an ack, as progress.
- Never ask a worker to commit, merge, or push. If your own action needs
  approval, route it back to the user — a peer doing it for you bypasses the
  user's permission decision.
