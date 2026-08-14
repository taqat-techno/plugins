---
name: clean
description: Remove finished git worktrees safely, with a dry-run preview and per-worktree confirmation. Covers the worktrees Claude Code's own sweep never touches.
disable-model-invocation: true
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh *)
---

# Clean up worktrees

Retire worktrees that are finished with. **Destructive — this skill is
user-invoked only, and never removes anything without explicit confirmation.**

`$0` may name a single worktree. Flags: `--prune` also offers to clear stale
git metadata. There is no flag to skip the preview.

## Always preview first

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh"
```

Do **not** pass `--no-sessions` here: knowing which worktrees have Claude
sessions attached is a safety input, not an optimisation.

Group by `verdict` and print, with the `reason` for every entry:

| Verdict | Heading | Default |
|---|---|---|
| `safe` | SAFE (clean, merged) | offer removal, default **yes** |
| `review` | REVIEW (unmerged commits, or external path) | offer, default **no** |
| `unsafe` | KEPT (work would be lost) | never offer |
| `current` | KEPT (this session is inside it) | never offer |
| `stale` | STALE METADATA | offer `git worktree prune` |
| `skip` | — | omit from the report |

Then state the two limits plainly, every time:

- Session detection covers what `claude agents --json` reports. If
  `sessionsAvailable` is `false`, say attachment could not be checked at all.
- `/worktree:clean` covers the worktrees Claude Code's own retention sweep
  never removes — those made by `--worktree`, by `EnterWorktree`, and by any
  `claude -p` run.

## Confirm, then remove

Ask once per group, or per worktree when the user wants that. On approval, for
each target in turn:

1. **Release the lock, but only if it is ours.** `lockKind: plugin` or
   `claude-stale` → `git worktree unlock "<path>"`. For `foreign` or
   `claude-live`, stop and skip that worktree; never unlock a lock the user or
   a running session set.
2. **Remove:** `git worktree remove "<path>"`
3. If git refuses because of untracked or modified files, **stop**. Show what
   git reported and ask explicitly before considering `--force`. Never pass
   `-f -f`.
4. Delete the branch only if the user asks: `git branch -d "<branch>"` — `-d`,
   never `-D`, so git's own merged check applies.

Never remove the worktree this session is inside. To retire the current one,
call `ExitWorktree({ action: "remove" })` instead, which restores the original
directory first; it refuses when there are uncommitted or unmerged changes
unless `discard_changes: true`, and that needs the user's explicit go-ahead.

## Pruning stale metadata

Only with `--prune` or when the user asks. Preview first:

```bash
git worktree prune --dry-run --verbose
```

Show the output, then run `git worktree prune` on approval. Pruning only
clears administrative entries for worktrees whose directories are already
gone; it never deletes a live directory. Never chain it onto a removal.

## Report

List what was removed, and what was kept with the reason for each. If nothing
qualified, say so in one line.

Full classification table:
`${CLAUDE_PLUGIN_ROOT}/references/cleanup-policy.md`.
