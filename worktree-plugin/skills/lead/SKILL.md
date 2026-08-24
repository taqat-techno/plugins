---
name: lead
description: Use when this session is told it is the main agent, controller, lead or orchestrator of a parallel run - "you are the main agent", "start execution", "orchestrate this plan", "resume orchestration", "take over coordinating the agents". Also use to rebuild orchestration state after a restart. Reads the plan, reconstructs the board from git, discovers workers and computes what is ready.
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh *), Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh *), Bash(claude agents --json)
---

# Become the Main Agent

Take orchestration authority for a Plan-Driven Lane Execution run: hold the plan,
compute readiness, provision and assign lanes, verify results, and own every
commit and merge.

`$0` may name the plan file. `--recover` rebuilds after a restart (it is the same
path; the flag only says not to expect a clean slate).

Read `references/roles.md` first — the Main Agent half is the contract you are
accepting.

## 1. Refuse to be the second controller

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh" --fast
```

If lanes already exist with a live owner and another session is plainly acting as
controller, **stop and say so**. Two orchestrators writing lane records is the
same failure as two workers in one worktree.

## 2. Find the plan

Use `$0` if given. Otherwise look for an implementation plan in the repository
and **ask which one** rather than guessing — a wrong plan produces a confidently
wrong dependency graph.

Check it carries the execution contract (`references/plan-schema.md`): package
prerequisites, `Owns`, `Laneable`, levelled tests, acceptance, must-not-build.

**If it does not, say exactly what is missing and stop before dispatching
anything.** Offer `/worktree:plan-for-parallel` to close the gaps. A plan without
`Owns` cannot answer *what may run concurrently*, and the answer must be computed,
not judged under time pressure.

## 3. Rebuild state — git wins, always

Reconstruct from four sources, in this precedence:

```
plan  →  lane records  →  git + filesystem  →  live session list
```

**When a lane record disagrees with git, repair the record — never the other
way.** A record is a cache of assignment facts, not an authority. Say out loud
what you repaired.

`wt-lanes.sh` already derives every state and anomaly. Do not recompute them by
hand and do not narrate a state you did not compute.

## 4. Discover workers and prove they are reachable

```bash
claude agents --json
```

A session is capacity only when **both** hold:

1. `kind == "background"` — an interactive session holds inbound dispatches for
   its user's approval, and may never show them;
2. it has **answered a channel test this session**.

Send each candidate a short test and wait for the reply:

> Channel test from the main agent — reply briefly. Did this reach you directly,
> or did your user have to approve it first? What are you working on, and where?

Then state capacity as a number. **Never count a session that has not answered.**
"Probably available" is not available.

If any name appears twice in the listing, that is **blocking**: resolve it before
assigning anything to that name.

### If capacity is short, offer to launch workers

A worker can be started directly, and it comes up correctly: `kind: background`,
auth and plugins inherited, and its `cwd` set to wherever it was launched — which
is what makes the lane↔owner binding derivable without the worker doing anything.

**Offer; never launch silently.** Each session costs quota and is a real process.
Say how many, why, and confirm — per session, or once for a named batch:

```bash
cd "<repo>/.claude/worktrees/<lane>" && claude --bg \
  'You are PDLE worker "agent 2" for lane <lane>. Run /worktree:join to claim
   that exact name, then read .claude/lanes/briefs/<lane>.md and begin. Do not
   commit, merge or push.'
```

Three things that matter in that command:

- **Launch inside the lane worktree.** The session's `cwd` becomes the lane, so
  the board can bind owner to lane without an `EnterWorktree` call.
- **Name the worker in the prompt.** A launched session auto-names itself from
  its prompt text, so without an explicit name you get something arbitrary that
  may collide — and a colliding name is two sessions pointed at one worktree.
- **A launched worker loads the *installed* plugin**, not a working copy. If the
  PDLE skills are not in the installed version, the worker will not have them.

If the user would rather start sessions themselves, print the command and stop.
That path is equally supported and needs nothing from this skill.

## 5. Compute readiness — both gates

```
ready(task) ⇔ every package Prerequisite complete
            ∧ every task depends_on complete
            ∧ no unresolved external blocker
```

**Both levels.** Computing from the task level alone starts work whose package
sits several prerequisite levels deep — the single most reliable way to burn a
lane. Resolve prerequisites by heading, not by line offset.

If the plan cannot support this computation: **report the ambiguity and refuse
to dispatch.** Do not guess.

Then partition the ready set by `Owns` disjointness. Lanes whose ownership sets
intersect cannot run together — that is the concurrency ceiling, and it comes
from the plan's structure, not from how many workers exist.

## 6. Report, then wait for direction

Present:

- the board (`/worktree:board` format)
- capacity, as a number, with any unreachable or ambiguous worker named
- the ready set, partitioned into what can run concurrently
- what is blocked, and on what
- anything the plan could not answer

**Do not dispatch yet.** Say what you would dispatch and to whom, and let the
user confirm the first wave. After that, `/worktree:delegate` handles assignment
and you continue without asking per lane.

## Running the loop

```
readiness → schedule → provision → delegate → monitor → verify → integrate → re-schedule
```

- **Monitor by reading the filesystem**, not by asking. `/worktree:board`.
- **Verify from git before approving.** Read the staged diff; do not take the
  report on trust.
- **Queue when capacity is zero.** Do not absorb the work — an orchestrator that
  starts implementing stops being able to see the board, and the queue is the
  honest signal that more workers are needed.
- **Re-derive before acting.** A merge plan or a worktree read from an hour ago
  has decayed.
- Cut every new lane from the **current integrated trunk**, so a lane can never
  depend on work still staged elsewhere.

## Guardrails

- Never implement. Queue instead.
- Never treat a dispatch, or an ack, as progress.
- Never dispatch beyond verified capacity.
- Never allocate from a shared namespace without re-reading the register.
- Never release a gate without telling every lane holding one.
- **Never route a blocked or gated action through a worker.** `SendMessage`
  forbids it outright: route blocked work back to your user instead.
- Never persist anything git can answer.
