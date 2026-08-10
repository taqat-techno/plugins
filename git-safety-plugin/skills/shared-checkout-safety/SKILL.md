---
name: shared-checkout-safety
description: Advisory safety for when more than one writer shares ONE git working tree — a second Claude session or automation, a teammate's agent, or a file syncer (Syncthing/Dropbox) writing into the same checkout. Owns the default-safe recipe (isolate with `git worktree` — never fight over the shared tree), and the subtle second-order traps that a careful agent still hits under real mid-task pressure — uncommitted work is not safe for even an hour (commit immediately, path-scoped) because a peer's `git reset --hard` + `git clean` wipes YOUR unstaged/untracked changes as collateral (no reflog for those); `git stash`/`reset --hard`/`clean`/`checkout -- .` on the shared tree destroy the OTHER writer's uncommitted work; `stash@{0}` is NOT stable — it silently shifts the instant the peer pops, so recovering via stash ordering can restore an ancient stash over your files; if work is already wiped, extract it to a scratchpad OUTSIDE the repo FIRST (verify) then restore; confirm quiescence with two mtime snapshots over real elapsed time before editing (a mid-run file change is the peer/syncer, not a misbehaving subagent); prove your files and the peer's are separable (mtime bands + per-file diff + no shared file) before staging an explicit list; HEAD itself is not stable either — a background sync hook can fast-forward the branch between turns, so a finding verified last turn may already be fixed; and don't clobber shared build output, ports, or databases. Advisory only — reasons and warns, never auto-mutates git. Activates whenever a second session/agent/syncer is (or may be) writing the same working tree, when a `git status` shows files you did not touch, when re-reporting findings a background sync may have moved HEAD past, or when recovering work that was wiped on a shared checkout.
version: 0.1.0
last_reviewed: 2026-07-23
owns:
  - the default-safe recipe for a shared tree — isolate with `git worktree`, never fight over the shared checkout
  - commit-immediately (uncommitted work on a shared tree is not safe; a peer's reset --hard + clean wipes it)
  - the discarding-op ban on a shared tree (reset --hard / clean / stash / checkout -- . destroy the peer's work)
  - the `stash@{0}`-is-not-stable trap (it shifts the instant the peer pops; never recover via stash ordering here)
  - extract-wiped-work-outside-the-repo-first, then restore (do not trust in-repo stash/reflog ordering)
  - the quiescence check (two mtime snapshots over real elapsed time; a mid-run change is the peer, not a subagent)
  - proving separability before staging beside a peer's edits (mtime bands, per-file diff, no shared file)
  - HEAD is not stable either — background sync automation can fast-forward the branch between turns
  - don't clobber shared build output / ports / databases (a shared build dir, held port, or clone DB breaks the other writer)
  - the coordination file when two agents share a tree by design (scope, owned files, contract for the sibling)
defers_to:
  - git-safety skill for single-writer local hygiene (add -A, dirty-tree switch, rm --cached, author/push identity)
  - claude-env-doctor for the file-syncer itself (Syncthing conflict/deadlock/ignore mechanics)
  - the user for every commit, discard, and recovery decision on a shared tree
user_invocable: false
---

# shared-checkout-safety

## Purpose

When two writers share one working tree — a second Claude session, a teammate's automation, or a file syncer dropping changes in — the tree is a shared mutable resource with no lock. The dangerous instinct is to *fight over it*: clean it, stash the other writer's changes, reset it to a known state. Every one of those destroys work that has **no reflog** (unstaged and untracked changes are gone forever) and races a live process.

**The default-safe move is to stop sharing: get an isolated pristine checkout with `git worktree` and work there.** The shared tree is never disturbed, which is also what makes "put it back exactly" trivial — nothing was taken. This skill codifies that recipe and the subtle traps that bite even a careful agent during real mid-task recovery.

## When to use

Activate when any of these is true:

- A second Claude session, subagent fleet, teammate agent, or CI runner is working in the **same working tree** right now.
- A file **syncer** (Syncthing, Dropbox, OneDrive, a backup job) writes into the checkout.
- `git status` shows modified/added/deleted files **you did not touch**, or file mtimes change while you work.
- You need a clean tree to build/test/baseline, and the other writer's changes are "in the way."
- You are **recovering** work that was wiped, reset, or stashed on a shared checkout.

For single-writer local footguns (`git add -A`, dirty-tree branch switch, `git rm --cached`, author/push identity), use `git-safety` instead.

## The default-safe recipe: isolate with `git worktree`

Do not fight over the shared tree. Take a linked, pristine checkout and do your build/test there:

```bash
# 0. Read-only recon FIRST — confirm your files and the peer's are disjoint.
git status --short
git worktree list

# 1. Snapshot only YOUR files onto a scratch branch (explicit paths — never `git add .`/-A).
git switch -c my-baseline
git add -- path/one path/two path/three
git commit -m "wip: isolated baseline (temp)"

# 2. A pristine sibling checkout that shares .git but not the working files.
git worktree add --detach ../my-baseline HEAD
cd ../my-baseline
#   deps do NOT carry over — a worktree has its own node_modules/.venv:
npm ci        # or: uv sync / pip install -e .
npm test      # the runner sees only committed content — never the peer's foreign edits

# 3. Tear down; the shared tree was never touched.
cd -            # back to the shared tree
git worktree remove --force ../my-baseline
git switch -    # back to your branch
git branch -D my-baseline
#   want your files back as the original UNSTAGED edits? (reflog-reversible, peer untouched)
git reset --mixed HEAD~1
```

If you must not even move the shared HEAD/index, skip the branch+commit and reconstruct inside the worktree instead: `git worktree add --detach ../base HEAD`, then `git diff HEAD -- <your paths> | (cd ../base && git apply)`. Nothing shared is mutated, and there is nothing to "put back."

### Step 0 in detail — prove the two change sets are separable

`git status --short` listing files you did not touch does not tell you whether you can commit around them. Before staging anything (and never with `git add -A`/`.`), prove separability three ways:

1. **The mtimes cluster into distinct time windows.** List the modified files with timestamps; your edits and the peer's should fall in separate bands. Overlapping bands mean you cannot yet tell the sets apart — stop and look closer.
2. **Each of your files carries only your change.** Run `git diff -- <your file>` and grep the diff for the *other* domain's tokens (a module path, class, or import only the peer's work touches). A hit means the file is shared, not yours.
3. **No file appears in both sets.**

Then stage the explicit list and assert the negative before committing:

```bash
git add -- path/one path/two
git diff --cached --name-only                        # must be EXACTLY your files
git diff --cached --name-only | grep <other-domain>  # must print nothing
```

The peer's work stays **uncommitted in the tree** — that is the intended outcome, not an oversight. Your commit and push carry only your feature.

## The traps (even when you are careful)

### 1. Commit your work immediately — uncommitted work on a shared tree is not safe

- A peer running `git reset --hard` + `git clean` to reset *their* view **wipes your unstaged and untracked changes as collateral** — and those have no reflog. Assume the tree can be reset out from under you at any moment.
- The moment your change is coherent, **commit it** (path-scoped, explicit files — see `git-safety`). A commit is in the object store and survives a peer's reset; a dirty working file does not.

### 2. Never run tree-discarding ops on a shared checkout

- `git reset --hard`, `git clean -fd`, `git stash` (which *removes* the changes from the tree), `git checkout -- .`, `git restore .` — each **destroys the other writer's uncommitted work** and/or races their live edits.
- Even `git stash push` of the peer's files yanks them out from under a running process; a later `git stash pop` merge-conflicts against their newer edits and bundles two writers' work into one entry.
- If you genuinely need a clean tree, use the worktree recipe above — it needs none of these.

### 3. `stash@{0}` is NOT stable on a shared tree

- Stash entries are a stack shared across the whole repo. The instant the peer runs `git stash pop`/`push`, **`stash@{0}` refers to a different entry** than it did a second ago.
- Recovering "my work" via `git stash apply stash@{0}` on a shared tree can silently apply a **months-old** stash over your files — clobbering the versions that were actually correct. Never recover by stash ordering here; address a stash by its message/SHA, and prefer not to use the shared stash stack at all.

### 4. If work is already wiped, extract OUTSIDE the repo first — then restore

- When a reset/clean/stash has already destroyed work, do not reconstruct in place while the tree is still volatile. **Copy whatever you can recover to a scratchpad outside the repo first** (a temp dir), verify its contents are the right version, and only then restore into the tree.
- This avoids the `stash@{0}`-shift trap (trap 3) turning your recovery into a second clobber.

### 5. Confirm quiescence before you edit the shared tree

- Before editing, take **two mtime snapshots over real elapsed time** (e.g. list the tree, wait, list again). If nothing changed across a genuine interval, you are effectively the sole writer for now; if files changed, a peer/syncer is active — proceed with extra care or wait.
- A file that changes **mid-run** is the peer or the syncer, **not** evidence that one of your own subagents misbehaved. Line numbers drifting under you is the same cause — re-read before trusting an offset.
- Quiescence is per-file and it expires. **Re-read any file the peer owns immediately before you edit it** — not once at the start of the task. A sibling can rewrite the same file twice inside a single edit of yours, so a body or an offset captured minutes ago is already stale.

### 6. Don't clobber shared build output, ports, or databases

- A shared build directory is a shared resource: `npm run build` overwrites a shared `.next`/`dist` and breaks the peer's running dev server. Build in your worktree, not over theirs.
- If the peer holds the default port, your server dies with `EADDRINUSE` and you may QC *their* stale build on the wrong port — run your dev/QC server on a **distinct port** and confirm which build you are actually testing.
- Isolate the **runtime**, not just the code. A scratch/clone database is as shared as the port: two sessions whose boot gate creates or drops the same clone DB collide mid-test — one wipes or locks the database the other is running against, and the failure looks like a flaky test rather than a collision. Give each session its own **database name *and* port**, and check for a concurrent run already in flight before launching one.

### 7. HEAD moves too — background automation is a second writer

- A second writer does not have to touch a file to change what you are looking at. A background session-start or repo-sync hook that runs `git fetch` + `git merge --ff-only` on the checked-out branch **advances HEAD between turns**. The tree you verified a finding against is not the tree you are now reporting on.
- So a finding you hand-verified last turn can be **already fixed** this turn, because the branch fast-forwarded onto merged work. Before re-reporting any prior finding, re-confirm `git rev-parse HEAD` and **re-verify against live source**; when a finding flips, diff the new commits (`git log --merges <old-head>..HEAD`, `git diff <old-head>..HEAD -- <path>`) to see what fixed it instead of assuming your earlier read was wrong.
- Launching a manual sync/pull while the background one is still in flight **collides on git's lock files** (`.git/index.lock` and friends), and one of the two aborts half-done. Check for the in-flight run — the process itself, or its completion marker in the hook's log — and wait for it rather than starting a parallel pull.

### 8. When the second session is deliberate, coordinate in a file

- Two agents on one checkout *by explicit instruction* still share no memory. Write the split down where both read it: a file under `.claude/tasks/` (e.g. `SESSION_COORDINATION_<date>.md`) naming each session's scope, the **files/models it owns**, and — as work lands — the **contract the sibling must consume** (the signature, field, or fixture it now has to build against). Ownership that exists only inside one session's context is not ownership.
- Declared ownership does not freeze a file. A sibling can reshape a model you depend on while your tests are running; re-read before editing (trap 5) and expect to adapt a fixture, rather than chasing the change as a regression in your own work.

## Decision framework

```
need a clean tree to build/test?     --> `git worktree add --detach ../x HEAD` and work THERE; never clean the shared tree
peer's changes "in the way"?         --> isolate via worktree; do NOT stash/reset/clean the shared tree
your change is coherent?             --> commit it NOW (path-scoped); a peer's reset can wipe uncommitted work anytime
work already wiped?                  --> extract recoverable files to a scratchpad OUTSIDE the repo first, verify, then restore
recovering via the stash stack?      --> STOP: `stash@{0}` shifted when the peer popped; address by message/SHA, not order
about to edit the shared tree?       --> two mtime snapshots over real elapsed time; a mid-run change = the peer, not a subagent
about to edit a file the peer owns?  --> re-read it NOW; a declared owner can rewrite it twice inside one of your edits
peer's edits sitting in `git status`? --> prove separability (mtime bands, per-file diff, no shared file) THEN stage explicit paths
re-reporting a finding from earlier? --> re-confirm HEAD (a background sync can fast-forward it); re-verify live; diff the new commits
about to launch a sync / pull / run? --> check nothing equivalent is in flight (git locks, held port, same clone DB)
running build / dev server?          --> build in your worktree; distinct port AND database name; confirm which build you test
two agents here by design?           --> coordination file: scope, owned files, the contract the sibling must consume
```

## Validation checklist

- [ ] A clean tree was obtained via `git worktree` (or committing your own paths) — not by cleaning/resetting/stashing the shared tree.
- [ ] Your coherent change was committed promptly (path-scoped), not left dirty on a tree a peer can reset.
- [ ] No `reset --hard` / `git clean` / `git stash` / `checkout -- .` was run on the shared checkout.
- [ ] No recovery relied on `stash@{0}` / stash ordering on the shared tree.
- [ ] Any wiped work was extracted outside the repo and verified before being restored.
- [ ] Quiescence was confirmed (two mtime snapshots) before editing; mid-run changes were attributed to the peer/syncer, not a subagent.
- [ ] Any file the peer owns was re-read immediately before being edited, not once at the start of the task.
- [ ] Staging beside a peer's edits was preceded by a separability proof (mtime bands, per-file diff grepped for the other domain, no shared file), and `git diff --cached --name-only` held no foreign paths.
- [ ] Findings carried over from an earlier turn were re-verified against the *current* HEAD, not one a background sync has since fast-forwarded past.
- [ ] No manual sync/pull/test run was launched while an equivalent one was still in flight (git locks, held port, same clone database).
- [ ] Builds ran in an isolated worktree, servers on a distinct port, tests against a per-session database name — the peer's build/port/DB was not clobbered.
- [ ] Where two sessions work the tree by design, scope, file ownership, and the sibling's contract are written in a coordination file both read.

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| `git stash` / `git reset --hard` / `git clean -fd` to clear the shared tree for a baseline | Destroys the other writer's unstaged/untracked work (no reflog) and races their live edits | `git worktree add --detach ../x HEAD` and build/test there; the shared tree is untouched |
| Leave your change dirty "until it's ready" on a shared tree | A peer's reset --hard + clean wipes uncommitted work as collateral | Commit the coherent change immediately, path-scoped |
| `git stash apply stash@{0}` to recover your work | The stack shifted when the peer popped; you may restore an ancient stash over good files | Never recover by stash order on a shared tree; address by message/SHA, or reconstruct from a diff |
| Reconstruct wiped work in place on a still-volatile tree | A second reset/pop can clobber your half-restored files | Extract recoverable files outside the repo first, verify, then restore |
| Assume a file that changed under you means your subagent misbehaved | The peer or the syncer wrote it; blaming a subagent chases the wrong bug | Attribute mid-run changes to the peer/syncer; confirm with mtime snapshots |
| `npm run build` over the shared `.next`/`dist` while the peer serves it | Overwrites the peer's running build → ChunkLoadError on their side | Build in your worktree; run your server on a distinct port |
| `git add -A` beside a parallel session's edits because "the diff looks like mine" | Ships the peer's half-finished work under your commit message; a `git status` glance never proved the sets disjoint | Prove separability (mtime bands, per-file diff, no shared file), stage the explicit list, assert `git diff --cached --name-only` has no foreign paths |
| Re-report a finding that was hand-verified an earlier turn | A background sync hook can `merge --ff-only` the branch forward between turns — the finding may already be fixed upstream | Re-confirm `git rev-parse HEAD`, re-verify live; diff the new commits when a finding flips |
| Start a manual sync/pull while the background one is still running | Both grab `.git/index.lock`; one aborts half-done and leaves the repo mid-operation | Check for the in-flight run (process, or its completion marker in the hook's log) and wait |
| Two sessions run tests from one repo on the default port and the same clone database | The runs collide — one drops or locks the database the other is testing against, and it reads as a flaky test | Per-session database name *and* port; check for a concurrent run before launching |
| Split work between two sessions and keep who-owns-what in each session's head | Neither context can see the other's; the overlap surfaces as a mid-edit rewrite of a file you thought was yours | Write scope, owned files, and the sibling's contract into a coordination file both sessions read |

## Red flags — STOP

- "The other session's changes are in my way — I'll just stash/clean them."
- "I'll `git reset --hard` to a known state and re-apply mine."
- "I'll grab my work back from `stash@{0}`."
- "A file changed that I didn't touch — a subagent must be broken."
- "I'll `npm run build` here real quick" (on a tree a peer is serving).
- "I verified this finding last turn — I'll just re-report it." (HEAD may have moved under you.)
- "Both change sets look separable enough — I'll `git add -A` and sort it out in review."

**All of these mean: STOP. Isolate with a worktree, commit what's yours, and never discard/stash/reset the shared tree.**

## Cross-references

- `git-safety` (skill) — single-writer local hygiene: `git add -A`, dirty-tree branch switch, `git rm --cached`, author/push identity, re-check status before push. This skill covers the multi-writer hazards; that one the solo footguns.
- `claude-env-doctor` — the file **syncer** itself (Syncthing conflict resolution, venv/`node_modules` delete-deadlock, `.stignore` not syncing). When a syncer is the second writer, its own operational quirks live there.
- The user — owns every commit, discard, and recovery decision on a shared tree. This skill never decides on their behalf.
