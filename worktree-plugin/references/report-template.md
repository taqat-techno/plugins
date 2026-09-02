# Lane report template

Written to `.claude/lanes/reports/<lane>-<nnn>.md`, numbered sequentially.

**Append-only.** Never modify a report that already exists; write the next
number. This is what makes the worker's writes collision-free — the worker never
touches the `.lane` record, and the Main Agent never touches a report.

## Order of operations — not negotiable

```
1. write the report file
2. stage the work        (git add — never commit)
3. notify the Main Agent
```

In that order. If the notification is lost, the report and the staged diff are
both on disk and both visible on the board. **A lost message must cost latency,
never information.**

---

```markdown
# LANE <lane-id> — report <nnn>

**<date time>** · branch `<branch>` @ `<base>` · **staged, uncommitted**

## Outcome

<One sentence. If you cannot state it in one sentence, it was two packets.>

## Covered

<Task ids this packet closes, and any it deliberately did not.>

## Staged

```
<git diff --cached --stat, or the file list>
```

## Tests

```
                             defined   started
<test class>                      13        13
<test class>                      12        12
                                  25        25     0 failed, 0 errors
```

<Any gap between defined and started, explained. A gap is not publishable as a
pass: if class setup raises, every test in that class is skipped and the run
still reports zero failures.>

<For each instrument used to prove a negative: the known positive it was checked
against. A text scan that has never been seen to fail is not evidence.>

## Contract evidence

<For each CC in this lane's `Satisfies`: where the Main Agent can observe it on
this staged work — a test id, a file:line, a measurement. Evidence toward the
outcome, never a MET claim: MET is decided at convergence, on the integrated
trunk. Omit this section when the plan has no Completion Contract.>

## Decisions

<Anything chosen rather than found, and why. Silence here is not an answer.>

## Blockers

<None, or: what is blocked, what would unblock it, and what you moved to
instead. A blocked stream is never a reason to stop.>

## New dependencies discovered

<Anything the plan did not know about — especially a dependency on another
lane's output. Name it even if it did not block you.>

## Findings for allocation

<Anything needing a number, name, or id from a shared namespace.
**Leave it UNNUMBERED.** Describe it; the Main Agent allocates.>

## Boundary check

- Ownership set: `<owns>` — nothing outside it was touched
- Paths outside the set that were read in other worktrees first: <list, or none>
- Nothing committed, merged, or pushed
```

---

## What makes a report verifiable

The Main Agent must be able to check every claim **from git**, without
believing the report:

| Claim | Checked by |
|---|---|
| staged file list | `git -C <worktree> diff --cached --name-only` |
| nothing committed | `git -C <worktree> rev-parse HEAD` still equals the base |
| nothing outside ownership | the staged paths against `Owns` |
| branch and base | `git -C <worktree> symbolic-ref --short HEAD`, `rev-list` |
| contract evidence | re-running the CC's `Verification` on the trunk at convergence |

Write the report so those checks agree with it. A report that cannot be
independently verified is a claim, not evidence — and *"the server started"* is
not a passing workflow.
