---
name: shared-checkout-safety
description: Advisory safety for when more than one writer shares ONE git working tree — a second Claude session or automation, a teammate's agent, or a file syncer (Syncthing/Dropbox) writing into the same checkout. Owns the default-safe recipe (isolate with `git worktree` — never fight over the shared tree), and the subtle second-order traps that a careful agent still hits under real mid-task pressure — uncommitted work is not safe for even an hour (commit immediately, path-scoped) because a peer's `git reset --hard` + `git clean` wipes YOUR unstaged/untracked changes as collateral (no reflog for those); `git stash`/`reset --hard`/`clean`/`checkout -- .` on the shared tree destroy the OTHER writer's uncommitted work; `stash@{0}` is NOT stable — it silently shifts the instant the peer pops, so recovering via stash ordering can restore an ancient stash over your files; if work is already wiped, extract it to a scratchpad OUTSIDE the repo FIRST (verify) then restore; confirm quiescence with two mtime snapshots over real elapsed time before editing (a mid-run file change is the peer/syncer, not a misbehaving subagent); and don't clobber shared build output or ports. Advisory only — reasons and warns, never auto-mutates git. Activates whenever a second session/agent/syncer is (or may be) writing the same working tree, when a `git status` shows files you did not touch, or when recovering work that was wiped on a shared checkout.
version: 0.1.0
last_reviewed: 2026-07-23
owns:
  - the default-safe recipe for a shared tree — isolate with `git worktree`, never fight over the shared checkout
  - commit-immediately (uncommitted work on a shared tree is not safe; a peer's reset --hard + clean wipes it)
  - the discarding-op ban on a shared tree (reset --hard / clean / stash / checkout -- . destroy the peer's work)
  - the `stash@{0}`-is-not-stable trap (it shifts the instant the peer pops; never recover via stash ordering here)
  - extract-wiped-work-outside-the-repo-first, then restore (do not trust in-repo stash/reflog ordering)
  - the quiescence check (two mtime snapshots over real elapsed time; a mid-run change is the peer, not a subagent)
  - don't clobber shared build output / ports (a shared build dir or a held port skews or breaks the other writer)
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

### 6. Don't clobber shared build output or ports

- A shared build directory is a shared resource: `npm run build` overwrites a shared `.next`/`dist` and breaks the peer's running dev server. Build in your worktree, not over theirs.
- If the peer holds the default port, your server dies with `EADDRINUSE` and you may QC *their* stale build on the wrong port — run your dev/QC server on a **distinct port** and confirm which build you are actually testing.

## Decision framework

```
need a clean tree to build/test?     --> `git worktree add --detach ../x HEAD` and work THERE; never clean the shared tree
peer's changes "in the way"?         --> isolate via worktree; do NOT stash/reset/clean the shared tree
your change is coherent?             --> commit it NOW (path-scoped); a peer's reset can wipe uncommitted work anytime
work already wiped?                  --> extract recoverable files to a scratchpad OUTSIDE the repo first, verify, then restore
recovering via the stash stack?      --> STOP: `stash@{0}` shifted when the peer popped; address by message/SHA, not order
about to edit the shared tree?       --> two mtime snapshots over real elapsed time; a mid-run change = the peer, not a subagent
running build / dev server?          --> build in your worktree; run on a distinct port; confirm which build you test
```

## Validation checklist

- [ ] A clean tree was obtained via `git worktree` (or committing your own paths) — not by cleaning/resetting/stashing the shared tree.
- [ ] Your coherent change was committed promptly (path-scoped), not left dirty on a tree a peer can reset.
- [ ] No `reset --hard` / `git clean` / `git stash` / `checkout -- .` was run on the shared checkout.
- [ ] No recovery relied on `stash@{0}` / stash ordering on the shared tree.
- [ ] Any wiped work was extracted outside the repo and verified before being restored.
- [ ] Quiescence was confirmed (two mtime snapshots) before editing; mid-run changes were attributed to the peer/syncer, not a subagent.
- [ ] Builds ran in an isolated worktree and servers on a distinct port — the peer's build/port was not clobbered.

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| `git stash` / `git reset --hard` / `git clean -fd` to clear the shared tree for a baseline | Destroys the other writer's unstaged/untracked work (no reflog) and races their live edits | `git worktree add --detach ../x HEAD` and build/test there; the shared tree is untouched |
| Leave your change dirty "until it's ready" on a shared tree | A peer's reset --hard + clean wipes uncommitted work as collateral | Commit the coherent change immediately, path-scoped |
| `git stash apply stash@{0}` to recover your work | The stack shifted when the peer popped; you may restore an ancient stash over good files | Never recover by stash order on a shared tree; address by message/SHA, or reconstruct from a diff |
| Reconstruct wiped work in place on a still-volatile tree | A second reset/pop can clobber your half-restored files | Extract recoverable files outside the repo first, verify, then restore |
| Assume a file that changed under you means your subagent misbehaved | The peer or the syncer wrote it; blaming a subagent chases the wrong bug | Attribute mid-run changes to the peer/syncer; confirm with mtime snapshots |
| `npm run build` over the shared `.next`/`dist` while the peer serves it | Overwrites the peer's running build → ChunkLoadError on their side | Build in your worktree; run your server on a distinct port |

## Red flags — STOP

- "The other session's changes are in my way — I'll just stash/clean them."
- "I'll `git reset --hard` to a known state and re-apply mine."
- "I'll grab my work back from `stash@{0}`."
- "A file changed that I didn't touch — a subagent must be broken."
- "I'll `npm run build` here real quick" (on a tree a peer is serving).

**All of these mean: STOP. Isolate with a worktree, commit what's yours, and never discard/stash/reset the shared tree.**

## Cross-references

- `git-safety` (skill) — single-writer local hygiene: `git add -A`, dirty-tree branch switch, `git rm --cached`, author/push identity, re-check status before push. This skill covers the multi-writer hazards; that one the solo footguns.
- `claude-env-doctor` — the file **syncer** itself (Syncthing conflict resolution, venv/`node_modules` delete-deadlock, `.stignore` not syncing). When a syncer is the second writer, its own operational quirks live there.
- The user — owns every commit, discard, and recovery decision on a shared tree. This skill never decides on their behalf.
