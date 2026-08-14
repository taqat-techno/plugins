# Cleanup policy

Conservative by construction: anything not provably safe is kept. The
classification is computed by `scripts/wt-inventory.sh` and exposed as
`verdict` + `reason`.

## What Claude Code already cleans, and what it does not

| Path | Behaviour |
|---|---|
| Interactive exit, clean tree, unnamed session | Worktree and branch removed automatically |
| Interactive exit, clean tree, named session | Prompts first |
| Interactive exit, work present | Prompts keep/remove |
| `claude -p` | **No exit prompt and no cleanup.** Also leaves its lock behind |
| Retention sweep | Removes **subagent and background-session** worktrees older than `cleanupPeriodDays`, skipping any holding work |
| Retention sweep vs `--worktree` | Never removes them |

`/worktree:clean` exists for the gap: worktrees from `--worktree`,
`EnterWorktree`, and `-p` runs.

## Verdicts

| Verdict | Condition | Action |
|---|---|---|
| `safe` | Clean tree, branch merged into the default branch | Offer, default yes |
| `review` | Clean but has commits not on the default branch; or an external path | Offer, default no |
| `unsafe` | Modified or untracked files; Claude sessions attached; `claude-live` or `foreign` lock; git state unreadable | Never offer |
| `current` | This session is inside it | Never remove in place — use `ExitWorktree` |
| `stale` | Directory missing, or git marks it prunable | Offer `git worktree prune` |
| `skip` | Main checkout, or a bare repo entry | Omit |

An `external` worktree (outside `.claude/worktrees/`) is never allowed to reach
`safe`: it was placed deliberately and its path may be depended on.

## Lock provenance

`git worktree list --porcelain` reports `locked [<reason>]`. The reason tells
you who owns it:

| `lockKind` | Reason shape | Meaning | May the plugin unlock it? |
|---|---|---|---|
| `plugin` | `worktree-plugin: …` | Persistence lock set by `/worktree:new` | Yes |
| `claude-live` | `claude … (pid N)`, N alive | A running Claude session | **No** |
| `claude-stale` | `claude … (pid N)`, N dead | An exited session left it | Yes |
| `foreign` | anything else | Set by the user or another tool | **No** |

Why the plugin's lock works: every removal path Claude Code uses passes at most
a single `--force`, and git refuses to remove a locked worktree unless `-f -f`
is given. Claude Code's own reaper also keeps anything "locked by a live Claude
Code process, or with a reason we did not write". The lock does not block
entering or switching.

## Removal rules

1. Unlock only `plugin` and `claude-stale` locks.
2. `git worktree remove "<path>"` — plain, no force.
3. If git refuses, stop, show its message, and ask. `--force` only after the
   user has seen the file list. **Never `-f -f`.**
4. Delete a branch only when asked, with `git branch -d` (never `-D`), so
   git's merged check still applies.

## Pruning

`git worktree prune` removes administrative entries for worktrees whose
directories are already gone. It never deletes a live directory. Always run
`git worktree prune --dry-run --verbose` and show the output first, and never
chain it onto a removal.

## Limits to state every time

- Session attachment comes from `claude agents --json`. If it is unavailable,
  attachment is **unknown**, not "none".
- Locks are advisory. A user who runs `git worktree remove -f -f` themselves
  bypasses everything here.
