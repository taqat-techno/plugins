---
name: git-safety
description: Advisory local git-workflow safety for any session that stages, commits, switches branches, or pushes. Owns the "stage explicit paths, never `git add -A`/`git add .`" rule (a broad add sweeps unrelated or co-staged files into your commit), the "re-check the FULL `git status` immediately before commit/push" rule (an external process — a sync daemon, a formatter, another session — may have changed the tree since your last check), the "never silent-switch or discard with a dirty tree" rule (archive or label-stash first; a bare `git checkout <branch>` / `git checkout -- .` throws work away), the `git rm --cached` team-impact rule (untracking a shared tracked file deletes it for everyone on merge), the per-repo author-identity rule (a repo with no `user.email` commits under a wrong global identity), and remote-push identity (the push account must actually have access; the active CLI identity can silently revert between shell calls; an MCP write tool is not a permission bypass). Advisory only — it reasons and warns, never auto-mutates git or blocks a command. Activates before any `git add`, `git commit`, `git checkout`/`switch`, `git rm --cached`, `git push`, or `gh`/MCP repo write, and when a working tree is dirty or a branch switch/discard is imminent.
version: 0.1.0
last_reviewed: 2026-07-23
owns:
  - stage explicit paths — never `git add -A` / `git add .` (a broad add co-stages unrelated files)
  - re-check the full `git status` immediately before commit/push (the tree is not stable between checks)
  - never silent-switch branches or discard with a dirty tree (archive / label-stash first)
  - the `git rm --cached` team-impact rule (untracking a shared tracked file deletes it for everyone on merge)
  - per-repo author identity (set `user.name`/`user.email` before the first commit; no-identity repos default to a wrong global)
  - remote-push identity (push account has access; CLI identity can revert between calls; MCP is not a permission bypass)
defers_to:
  - shared-checkout-safety skill when more than one agent/session/syncer shares the SAME working tree
  - devops (git-remote-write-gate) for the Azure DevOps / provider-specific remote push-identity gate
  - agent-safety skill for the general "don't route around a permission denial / MCP is not a bypass" principle
  - claude-env-doctor for a Windows git "dubious ownership" (BUILTIN\\Administrators) block on running git at all
  - the user for every commit, push, branch, and destructive-op decision
user_invocable: false
---

# git-safety

## Purpose

Most git problems agents cause are not merge-conflict subtleties — they are a handful of blunt local footguns: a `git add -A` that sweeps someone else's staged work into your commit, a branch switch that silently throws away a dirty tree, an untrack that deletes a shared file for the whole team, a commit landing under the wrong author, a push on the wrong identity. This skill is the advisory checklist for those reflexes. It reasons and recommends; it never auto-mutates git and never blocks a command.

**A convenience that widens blast radius is not worth it.** `git add -A` is one keystroke shorter than staging explicit paths and can ship files you never reviewed. Prefer the narrow, explicit operation every time.

## When to use

Activate when any of these is about to happen:

- A `git add` — especially `git add -A`, `git add .`, or `git add -u`.
- A `git commit` (author identity, and *what* is actually staged).
- A `git checkout <branch>` / `git switch`, `git checkout -- <path>`, `git restore`, or any branch change while the tree may be dirty.
- A `git rm --cached` (to gitignore an already-tracked file).
- A `git push`, `gh pr create`, or an MCP repository write (branch/PR/file).
- You are about to trust an earlier `git status` to decide what to commit.

**If a second agent, session, or a file syncer shares this same working tree, use `shared-checkout-safety` first** — the discarding-op hazards there are more severe than anything on this list.

## The primitives

### 1. Stage explicit paths — never `git add -A` / `git add .`

- Stage the exact files your change owns: `git add path/one path/two`, or a scoped commit `git commit -- path/one path/two`.
- **Never `git add -A`, `git add .`, or `git add -u`.** A broad add stages everything in the tree — including files another session pre-staged in the index, an editor's scratch file, a generated artifact, a secret a formatter dropped, or a deletion you did not intend. Those ride into your commit silently.
- Before committing, print `git diff --cached --name-only` and confirm it is EXACTLY your files. If a path you don't own appears, unstage it (`git restore --staged <path>`) — do not commit "to be safe."
- The index can already hold files you didn't stage (a prior session, a merge, a hook). A path-limited commit (`git commit -- <your paths>`) commits only your paths from the index and leaves the rest staged and untouched.

### 2. Re-check the FULL working tree immediately before commit/push

- The tree is **not stable between checks.** A sync daemon, a linter/formatter, a build, or another session can add, delete, or modify files in the seconds between your last `git status` and your commit.
- Run `git status --porcelain` **immediately before** `git add`/commit/push — not a status from earlier in the turn. An earlier "clean" does not license a later push.
- When an unexpected path appears, **investigate before acting**: `git show HEAD:<path>` to see what it was; restore with `git checkout HEAD -- <path>` if a sync/backup churn deleted it. A stray deletion (e.g. a `.gitignore` an external process removed) is a scope leak, not a no-op.
- This is exactly the class of drift a dedicated scope check catches: assert "EXACTLY these N files changed; anything else is a blocker" right before the write.

### 3. Never silent-switch branches or discard with a dirty tree

- Before `git checkout <branch>` / `git switch` with uncommitted changes, **preserve first**: commit on the current branch, or stash **with a label** (`git stash push -m "<what-this-is>"`), or copy the changed files to a dated backup outside the repo. Then switch.
- `git checkout -- <path>`, `git restore <path>`, and `git checkout .` **discard** uncommitted changes with no undo. Treat them as destructive; confirm the target is disposable before running them.
- A bare `git checkout <branch>` that "wants to delete" an uncommitted file is a warning, not a nuisance — do not force past it.

### 4. `git rm --cached` deletes a shared file for the whole team

- Gitignoring a file that is currently **tracked and shared** requires `git rm --cached <file>` — which removes it from the remote **for everyone** on merge.
- If the file is a shared team artifact (a committed `CLAUDE.md`, a config, a fixture), untracking it silently breaks every teammate's setup on their next pull.
- Surface this as a **consequential** change: flag the team-wide impact, get explicit confirmation, and document the regenerate/restore path in the commit/PR body. Never slip a `git rm --cached` of a shared file into an unrelated commit.

### 5. Set per-repo author identity before the first commit

- A repo with no local `user.name`/`user.email` commits under whatever **global** identity is configured — often the wrong author for this repo/account.
- Before the first commit in a repo, verify `git config user.email`; if it is empty or wrong for this repo, set it locally (`git config user.email "<the-right-address>"`) — do not rely on the global default.
- Getting the author wrong is hard to fix cleanly after the fact (it is baked into every commit object).

### 6. Remote push identity: right account, re-asserted, no MCP bypass

- The push **account** must actually have write access to the target repo. A push on the wrong identity fails at the remote (e.g. `403 … denied to <user>`) — that error names the identity that was actually used; trust it over any CLI "active account" readout.
- The active CLI identity (`gh`, cloud CLIs) **can silently revert between shell calls.** Switch and push in the **same shell/command** as the write, and re-assert the identity immediately before the push rather than trusting a switch from an earlier call.
- An **MCP repository-write tool is not a permission bypass.** If a server-side operation (create branch, push, merge) is denied for your identity, the MCP equivalent is denied too. Do not route around a denial by switching tools — surface it and ask the user.
- For provider-specific remote gates (Azure DevOps push identity, account auto-switch policy), defer to `devops` (git-remote-write-gate).

## Decision framework

```
about to `git add`?          --> stage explicit paths; NEVER add -A / . / -u; then diff --cached --name-only
about to commit/push?        --> re-run `git status --porcelain` NOW; confirm the staged set is exactly yours
switch branch, tree dirty?   --> preserve first (commit / label-stash / dated backup) THEN switch; never discard silently
`git checkout -- ` / restore? --> destructive discard; confirm the target is disposable
gitignore a tracked file?    --> `git rm --cached` deletes it team-wide on merge; flag consequential + confirm
first commit in this repo?   --> verify local user.email; set it if empty/wrong before committing
pushing / gh / MCP write?    --> right account has access; re-assert identity in the same shell; MCP != a bypass
shared working tree?         --> STOP: use shared-checkout-safety (discarding-op hazards are worse there)
```

## Validation checklist

- [ ] Nothing was staged with `git add -A` / `git add .` / `git add -u`; the commit's paths were explicit and diff-verified.
- [ ] `git status --porcelain` was re-checked immediately before the commit/push, not trusted from earlier.
- [ ] No branch switch or `checkout -- ` / `restore` discarded a dirty tree without preserving it first.
- [ ] Any `git rm --cached` of a shared tracked file was flagged as team-wide and confirmed.
- [ ] Local `user.email` was verified/set before the first commit in the repo.
- [ ] The push used an identity with access, re-asserted in the same shell; no MCP tool was used to route around a denied write.

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| `git add -A` / `git add .` to "just stage everything" | Sweeps co-staged, generated, scratch, or secret files into your commit | Stage explicit paths; `git commit -- <your paths>`; verify with `git diff --cached --name-only` |
| Commit on the strength of a `git status` from earlier in the turn | The tree changed underneath (syncer / formatter / other session); the earlier clean is stale | Re-run `git status --porcelain` immediately before the commit/push |
| Trust that a clean earlier check means the push is safe | An external write can appear between check and push (a deleted `.gitignore`, a new artifact) | Investigate any new path (`git show HEAD:<path>`); restore or unstage before pushing |
| `git checkout <branch>` with a dirty tree to "get moving" | Silently throws away or blocks on uncommitted work | Preserve first (commit / `stash push -m` / dated backup), then switch |
| `git checkout -- .` / `git restore .` to "clean up" | Destructively discards all uncommitted changes, no undo | Confirm the target is disposable; prefer a scoped, reviewed discard |
| `git rm --cached <shared file>` slipped into an unrelated commit | Deletes the file team-wide on merge; breaks every teammate | Flag it as consequential, confirm, document the restore path |
| Commit in a fresh repo without checking `user.email` | Lands every commit under the wrong global author; hard to fix later | Verify/set local `user.email` before the first commit |
| Retry a denied push by calling the MCP branch/push tool instead | The MCP is not a permission bypass; the server-side denial stands | Surface the denial; ask the user to grant access or switch to an authorized identity |
| Assume the CLI "active account" holds across calls | The identity can silently revert between shell calls | Re-assert the identity in the same shell as the push |

## Cross-references

- `shared-checkout-safety` (skill) — when more than one agent/session/syncer shares ONE working tree. Its discarding-op hazards (`reset --hard`/`clean`/`stash` wiping a peer's uncommitted work; `stash@{0}` shifting) are more severe than the local footguns here; use it first whenever a second writer is present.
- `devops` (git-remote-write-gate) — the provider-specific remote push permission + push-identity gate (e.g. Azure DevOps). This skill owns the generic push-identity reflex; that owns the provider gate.
- `agent-safety` (skill) — the general "don't route around a permission denial; an MCP tool is not a bypass" principle. This skill applies it to git/`gh`/repo-MCP writes.
- `claude-env-doctor` — if git itself refuses to run with a Windows "dubious ownership" error (`BUILTIN\Administrators`-owned dir), that is an environment block, not a workflow issue; a scoped `git -c safe.directory=<dir> …` avoids mutating global config.
- The user — owns every commit, push, branch, and destructive-op decision. This skill never decides on their behalf.
