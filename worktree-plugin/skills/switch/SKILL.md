---
name: switch
description: Use when the user asks to switch to, move to, jump to, or continue work in a different existing worktree by name. Moves only this session; other sessions are unaffected.
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh *)
---

# Switch worktree

Move **this** session into another worktree. Other sessions keep their own
working directories; nothing about them changes.

`$0` is an optional worktree name or path. With no argument, show a picker.

## Resolve the target

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh"
```

- **Argument given** — match it against `name`, then against `path`. No match:
  list the available names and ask. Do not guess.
- **No argument** — partition on `switchable`. If there are 4 or fewer
  switchable candidates, use `AskUserQuestion` with one option per worktree,
  labelling each with its branch and state. With more than 4, print the table
  and use `AskUserQuestion` for the 3 most recently useful, letting the user
  type any other name via "Other".

Never offer the current worktree or the main checkout as a switch target.

## Enforce the rules before calling the tool

Read `switchable` and `switchBlockedBy` and act on them rather than letting
the tool fail:

- **`kind: external`** (outside `.claude/worktrees/`) — a session already
  inside a worktree **cannot** switch there; Claude Code rejects it. From the
  main checkout it works as a first entry, but Claude Code will ask for
  approval, and that prompt cannot be pre-approved by a permission rule. Say
  so before trying.
- **`lockKind: claude-live`** — another **running** Claude Code session holds
  it. `EnterWorktree` refuses. Do not retry. Tell the user the working
  alternative: open a terminal in that directory and run `claude` there. Two
  sessions in one worktree is supported; only *switching* into an occupied one
  is not.
- **`prunable` or missing directory** — offer `/worktree:clean` instead.

## Switch

```
EnterWorktree({ path: "<absolute path>" })
```

If the tool still returns an error, report it verbatim. Do not attempt
`git worktree` commands or `cd` as a workaround — the session's working
directory is owned by Claude Code, and the previous worktree stays writable
only through a proper re-entry.

## Report

- New path and branch.
- The previous worktree stays on disk untouched, and any session attached to
  it is unaffected.
- This session can no longer write to the previous worktree until it re-enters
  that path. Re-entering later works normally.
- If `sessionCount > 0` on the target, mention that other sessions are already
  there — that is allowed, but coordinate to avoid editing the same files.

Full rules: `${CLAUDE_PLUGIN_ROOT}/references/switching-rules.md`.
