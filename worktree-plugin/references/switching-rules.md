# Switching rules

Verified against Claude Code 2.1.229. These are Claude Code's own rules; the
plugin surfaces them rather than implementing them.

## The managed zone

Claude Code creates worktrees under `<repo>/.claude/worktrees/<name>` on a
branch named `worktree-<name>`. That directory is the **switchable zone**.

## Entry is asymmetric

| Situation | Allowed targets |
|---|---|
| First entry, from the launch directory | Any worktree in `git worktree list` — including one created by `git worktree add` anywhere on disk |
| Any later switch (already inside a worktree, or a cwd-pinned agent) | **Only** worktrees under `.claude/worktrees/` of the same repository |

The rejection is explicit:

> `Cannot enter worktree: <path> is not under <repo>/.claude/worktrees.`
> `Switching from this session is limited to worktrees managed by Claude Code`
> `(created under .claude/worktrees/ of this repository).`

Entering a path **outside** `.claude/worktrees/` also raises an approval
prompt. An `EnterWorktree` permission rule and "don't ask again" do not
suppress it; only `bypassPermissions` mode skips it.

## Manual worktrees are first-class inside the zone

`git worktree add .claude/worktrees/<name> -b <any-branch>` produces a
worktree that Claude Code enters and switches to exactly like its own. Verified
by test. This is how a custom branch name is obtained — Claude Code's own
creation path always names the branch `worktree-<name>`.

What such a worktree does *not* get: `.worktreeinclude` copying,
`worktree.sparsePaths`, and `worktree.symlinkDirectories`. Those belong to
Claude Code's creation path.

## A live Claude session blocks entry

`EnterWorktree` refuses a worktree locked by a **running** Claude Code session:

> `Cannot enter worktree: <path> belongs to another running Claude Code session`
> `(locked: claude session <name> (pid <n>)). Wait for that session to finish or`
> `choose a different worktree.`

Claude Code locks each worktree session with a reason of the form
`claude session <name> (pid <n>)` and decides on PID liveness.

**This constrains switching only.** A second session *launched* in that
directory (`cd <worktree> && claude`) works normally and leaves the existing
lock alone — Claude Code calls it a "guest". So `0..N` sessions per worktree is
supported; the route in is launching, not switching.

## Returning works

Switching A → B → A is fine; a previously visited worktree can be re-entered
by path. While the session is elsewhere, the earlier worktree is not writable
from it, and it stays on disk untouched — as do any sessions attached to it.

## Other refusals

- `is not a registered worktree of <repo>` — not in `git worktree list`.
- `is marked prunable by git` — its directory or admin files are missing.
- Symlinked `.claude`, `.claude/worktrees`, or the worktree directory itself.
- `Refusing to use <path> as an isolation worktree` — the directory's git
  identity resolves back into the main checkout.

## Path case (Windows)

The containment check is case-sensitive on the string. A session whose working
directory differs from the canonical on-disk path only in letter case is
rejected with a confusing "git resolves its working tree to ..." error.
Canonicalise paths before comparing them or passing them to `EnterWorktree`.
