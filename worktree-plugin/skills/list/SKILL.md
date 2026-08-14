---
name: list
description: Use when the user asks which worktree they are in, what worktrees exist, the state of their parallel workspaces, or which worktrees are safe to switch to or clean up. Read-only.
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh *)
---

# List worktrees

Show every git worktree of the current repository, its state, and what can be
done with it. **Read-only — never create, remove, lock, or switch here.**

## Run

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-inventory.sh"
```

Add `--no-sessions` if the user asks for a fast answer or if `claude agents`
is unavailable. The script prints JSON and always exits 0; on failure it
returns `{"ok": false, "error": "..."}` — report that error plainly and stop.

## Render

Print a compact table, current worktree first. Use the `name`, `branch`,
`kind`, `verdict`, `reason`, `sessionCount`, `lockKind` and `switchable`
fields. Suggested shape:

```
Repository: <repo dir name>      Current: <marker> <name> (<branch>)

 ●  NAME              BRANCH            STATE                     SWITCH
 ◉  (main checkout)   develop           3 modified                 —
 🌳 wallet-fix        worktree-wallet.  clean, 2 ahead             yes
 🌳 voucher-refactor  worktree-vouch.   5 modified · 1 session     yes
 ⚠  ../old-spike      spike/old         clean                      no — external
```

Rules for the rendering:

- Mark the entry with `isCurrent: true`.
- `kind: external` means the worktree lives outside `.claude/worktrees/`.
  Flag it and explain once: it can be entered as a **first** entry from the
  launch directory, but a session already inside a worktree cannot switch to
  it.
- If `sessionCount > 0`, say how many Claude sessions are attached and name
  them. This comes from `claude agents --json` and covers interactive and
  background sessions.
- Surface `lockKind` only when it is not `none`:
  - `plugin` — kept persistent by `/worktree:new`
  - `claude-live` — a running Claude session holds it; it cannot be switched into
  - `claude-stale` — left behind by an exited session; harmless, `/worktree:clean` can clear it
  - `foreign` — locked by the user or another tool; never touched
- If `sessionsAvailable` is `false`, add one line: session detection was
  unavailable, so attachment is unknown.

End with the single most useful next step (`/worktree:switch`,
`/worktree:new`, or `/worktree:clean`) — one line, no menu.

## Notes

Git is the source of truth; this skill keeps no state. Details of the
switching rules are in `${CLAUDE_PLUGIN_ROOT}/references/switching-rules.md`.
