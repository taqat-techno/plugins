---
name: join
description: Use when this session is told it is a worker, agent, or lane executor in a parallel run - "you are agent 2", "join as a worker", "register with the main agent", or when a lane brief arrives and this session has not yet registered. Claims a unique name and confirms reachability.
allowed-tools: Bash(claude agents --json), Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh *)
---

# Join as a worker

Make this session a addressable, uniquely named worker in a Plan-Driven Lane
Execution run.

`$0` is the desired name (e.g. `agent 2`). With no argument, propose one from
the first free `agent <n>`.

## 1. Claim a unique name

```bash
claude agents --json
```

**Refuse a name that is already live.** Two sessions answering to one name are
two sessions pointed at the same worktree; both may act, and the branch then
holds staged content from two writers with no commit boundary between them. This
is not hypothetical — it has happened, and the warning was visible on every
message for a whole night before anyone acted on it.

If the name is taken, propose the next free one and **stop**. Do not proceed
silently with a colliding name.

The user sets the session name themselves — tell them the exact step:

> Set this session's name to `agent 2` (`/name agent 2`), then I will register.

## 2. Report this session's kind — honestly

Find this session in the JSON by name and read `kind`.

| `kind` | What it means for this session |
|---|---|
| `background` | Dispatches arrive directly. **This is the one that works.** |
| `interactive` | Inbound dispatches are **held for your user's approval** and may never be seen |

If this session is `interactive`, say so prominently and without softening it:

> **This session is interactive, so lane dispatches to it will be held for your
> approval before I see them.** Provisioned lanes have sat idle for hours this
> way while the board reported them running. For lane work, launch a background
> session instead: `claude --bg` from the repository root.

Do not offer to work around it. Report it and let the user decide.

## 3. Read the protocol, not the whole plan

Read `references/roles.md` — the worker half. That is the contract.

**Do not read the plan.** A worker gets its context from its brief. Reading the
whole plan is how a worker starts forming opinions about other lanes' work.

## 4. Announce readiness

If a Main Agent is already running, reply to it — or if this session has not been
contacted yet, tell the user this session is ready and give them the name to use.

State plainly, in one line each: the name claimed, the session kind, and that
this session is a **worker** — it will not commit, merge, or dispatch.

## 5. Wait for a brief

Do not claim a lane. Do not start work. Do not read `.claude/lanes/` looking for
something to do.

When a brief arrives, the rule that matters most:

> **Acknowledge and begin in the same turn.** An ack claims a lane; it is not the
> start of work. A background session can ack and end its turn there — one lane
> sat that way for over an hour with its worktree still at the base commit. If
> the first stretch is investigation that produces no files, **say so in the
> ack**, so silence is not read as a stall.

## Guardrails

- Never claim a name that is live.
- Never claim a lane; wait to be assigned one.
- Never commit, merge, push, or dispatch — see `references/roles.md`.
- If `claude agents --json` is unavailable, say uniqueness could **not** be
  verified. Do not assume the name is free.
