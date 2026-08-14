---
name: new
description: Use when the user wants an isolated worktree or workspace for a task, wants to work on something in parallel without touching the current checkout, or asks to start a new worktree. Creates it and moves this session into it.
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh *)
---

# Create a worktree

Create an isolated worktree under `.claude/worktrees/` and move this session
into it. `$0` is the name; if the user gave none, propose one from the task
they described (kebab-case, e.g. `wallet-fix`).

## Pre-flight

Run the inventory first:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh" --no-sessions --fast
```

Then check, and stop with a plain explanation if any of these hold:

- **Not a git repository** (`ok: false`) — worktrees need one. Stop.
- **Name already exists** — offer `/worktree:switch` to it instead, or a new name.
- **This session is already inside a worktree** (`isCurrent` on a non-main
  entry). Claude Code forbids creating a worktree from within one. Offer to
  switch instead, or to exit the current worktree first.
- **`.claude/worktrees/` is not gitignored** — offer to add it to `.gitignore`
  before proceeding. Without it, every worktree's contents show up as
  untracked files in the main checkout.

## Confirm, then create

State the name, the resulting branch, and the base ref, then create it.

### Default path — native

```
EnterWorktree({ name: "<name>" })
```

The branch is always `worktree-<name>`; Claude Code does not accept a custom
branch name here. The base comes from the `worktree.baseRef` setting:
`fresh` (default) branches from `origin/<default-branch>`, `head` from the
current local HEAD. `--head` for this invocation means: tell the user to set
`worktree.baseRef` to `head`, since the tool takes no per-call override.

Prefer this path. It is the only one that honours `.worktreeinclude` (which
copies gitignored files such as `.env` into the new worktree),
`worktree.sparsePaths`, and `worktree.symlinkDirectories`.

### `--branch <branch-name>` — custom branch name

Only when the user explicitly asks for a specific branch name:

```bash
git worktree add "<repo>/.claude/worktrees/<name>" -b "<branch-name>"
```

A worktree created this way is fully first-class: it can be entered and
switched to exactly like a native one. Then enter it with
`EnterWorktree({ path: "<abs path>" })`.

**Say this trade-off out loud before using this path:** `.worktreeinclude`,
sparse checkout, and symlinked directories are *not* applied, because those
belong to Claude Code's own creation path. If the project relies on `.env`
being present, the user must copy it themselves.

## Make it persistent

After the worktree exists, lock it so it survives session exit:

```bash
git worktree lock --reason "worktree-plugin: persistent workspace" "<abs path>"
```

Why: when a session exits with a clean worktree, Claude Code removes the
worktree and its branch automatically. The lock prevents that — every removal
path Claude Code uses passes at most a single `--force`, and git refuses to
remove a locked worktree unless `-f -f` is given. The lock does **not** block
entering or switching, and Claude Code never releases a lock whose reason it
did not write.

Skip the lock only if the user asks for a throwaway worktree.

## Report

Give the path, the branch, the base, and one caution: a worktree is a fresh
checkout, so dependencies are **not** installed. Do not run any install
command unless asked.
