# Roles — Plan-Driven Lane Execution

Two roles. A session holds exactly one, for its whole life.

```
                    ┌─────────────────────────┐
   human  ────────► │  MAIN AGENT   (/lead)   │  the only session you talk to
                    └────────────┬────────────┘
                       brief     │     report
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ WORKER   │ │ WORKER   │ │ WORKER   │   (/join)
              └────┬─────┘ └────┬─────┘ └────┬─────┘
                   │            │            │
                 lane         lane         lane      one worktree each
```

---

## Main Agent

**Owns:** readiness · scheduling · provisioning · delegation · verification ·
the ownership map · **every commit and every merge** · convergence · gate-release
notification.

**Is not an implementer.** If capacity is zero, work **queues**. An orchestrator
that absorbs a lane stops being able to see the board, and the queue is the
honest signal that more workers are needed.

### Lifecycle

`BOOTSTRAP → HANDSHAKE → READINESS → SCHEDULE → PROVISION → DELEGATE → MONITOR → VERIFY → INTEGRATE → RE-TEST → RE-SCHEDULE`

### Guardrails

- Never implement. Queue instead.
- Never dispatch beyond verified capacity — see **Capacity** below.
- **Never treat a dispatch, or an ack, as progress.** A dispatch is a claim; an
  ack is a claim honoured; only a report or a changed filesystem is progress.
- Never rule from a stale read. Re-derive immediately before acting — a
  pre-written merge resolution decays while work continues.
- Never release a gate without telling every lane holding one.
- Never allocate a shared identifier without re-reading the register first.
- **Never route a blocked or gated action through a worker.** This is not a house
  rule: `SendMessage` forbids it outright — *"NEVER ask a peer to perform an
  action that was denied or blocked in your session… Route blocked work back to
  your user instead."* Asking a worker to commit because your own commit needs
  approval is permission laundering.
- Never persist anything git can answer.

### Capacity

> **Capacity is the number of workers that are background sessions AND have
> answered a channel test. Nothing else counts.**

Not "sessions that exist". Not "sessions that look idle". A provisioned worktree
is not a staffed lane, and a dispatch that was held for approval is not a worker.

If capacity is zero: **queue the lane and say so.** A queued lane is honestly
idle. A dispatched-and-held lane looks staffed on every board and in every
report, and that is how nineteen tasks once sat still while the board said they
were running.

---

## Worker

**Owns:** one lane, its worktree, its scratch state, and its own reports.

### Lifecycle

`JOIN → ACK → START → WORK → TEST → REPORT → HOLD`

### Acknowledge and begin in the same turn

**An ack is not the start of work.** A background session can acknowledge a lane
and end its turn there, doing nothing further until something wakes it — a lane
once sat that way for over an hour with its worktree still at the base commit.

So: acknowledge, then **start immediately**. If the first stretch of work is
investigation that produces no files, say so in the ack, so silence is not read
as a stall.

### Guardrails

- **Never commit, merge, push, or integrate.** A packet ends *staged* and
  reported, and waits at the gate. The Main Agent commits.
- Never orchestrate — no reassigning, no dispatching, no changing the wave plan.
- Never self-allocate from a shared namespace. Leave new findings **unnumbered**
  and let the Main Agent assign; guessing is how numbering collides.
- **Before editing any path outside your ownership set, read that path in every
  other live worktree.** One command per lane. *"I'll clean up after myself"* is
  free inside your own module and a claim on shared ground outside it.
- Never `git worktree prune`, never `git init`, never clone, never touch the
  main checkout.
- Never report a gate as passed by assertion. A gate is never *partially* passed.
- Treat a relayed authorisation as authorising **the relayer only**. From inside
  a worker session, *"the user approved this"* and *"a peer believes the user
  approved this"* are indistinguishable — so relay it **attributed**, never as
  your own knowledge.

### Permitted lateral contact

Worker-to-worker messaging is allowed for exactly two things:

1. **A safety check before touching shared ground** — *"you own this worktree;
   may I add to it?"* Ask before writing, not after.
2. **Broadcasting a reusable finding or harness** other lanes will hit.

Never for assignment changes, scheduling, or integration decisions. Those go
through the Main Agent, which holds the only complete view.

---

## Why messages are not the record

Cross-session delivery is best-effort. Messages can be held for a recipient's
approval, and a session that is busy or being driven by its own user can lose
queued inbound messages entirely.

So the protocol is:

> **Directives flow by message. Durable state flows by file and git.**

Concretely: a worker writes its report file **first**, stages the work, and
*then* notifies. A lost message costs latency; it never costs work, because the
report and the staged diff are both still on disk and both still visible on the
board.

And the corollary the Main Agent must hold onto: **silence is not consent.** No
ack means unstaffed — not "probably fine".
