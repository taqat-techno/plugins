# Git Worktree Workspaces

Make git worktrees a first-class workspace inside Claude Code.

Claude Code already creates, enters, isolates, and resumes worktrees very
capably. What it has no built-in surface for is **seeing** your worktrees,
**choosing** one, and **safely retiring** them. This plugin is that surface —
an inventory and decision layer over `git worktree list --porcelain` that
drives Claude Code's native tools rather than replacing them.

```
🌳 wallet-fix | fix/wallet-131 | wallet-dev
◉ MAIN | develop
```

## Design commitments

- **A worktree is a place, not a session.** Zero, one, or many Claude sessions
  may use one. Sessions come and go; the workspace persists.
- **Git is the source of truth.** No registry, no cache, no database. The
  plugin stores nothing.
- **Zero hooks.** Nothing runs unless you invoke it. Installing this plugin
  cannot interfere with a session.
- **No session modes.** No reader/writer split, no artificial edit locks.
- **The main checkout stays valid.** Worktrees are optional.
- **Conservative cleanup.** Nothing meaningful is ever deleted silently.
- **Windows is first-class.** No WSL required.

## Install

```bash
/plugin marketplace add taqat-techno/plugins
/plugin install worktree@taqat-techno-plugins
```

Then, once:

```
/worktree:init
```

`init` is optional — every command works without it. It installs the status
line (a plugin cannot ship one itself) and offers a few defaults. Each change
is shown as a diff and confirmed separately, and `/worktree:init --remove`
reverses all of it.

**Requirements:** git, and a POSIX shell. On Windows that means Git for
Windows, which you already have if git works. Nothing else.

## Commands

| Command | What it does |
|---|---|
| `/worktree:list` | Every worktree, its state, attached sessions, and what you can do with it. Read-only. |
| `/worktree:new [name]` | Create an isolated worktree and move this session into it. |
| `/worktree:switch [name]` | Move this session to another worktree. Other sessions are untouched. |
| `/worktree:clean` | Retire finished worktrees. Dry-run first, always. |
| `/worktree:init` | One-time setup. `--remove` to undo. |

All five run sensibly with no arguments. `list`, `new`, and `switch` also
respond to plain language — "create an isolated worktree for the wallet issue",
"switch to voucher-refactor", "which worktree am I in?". `clean` and `init`
are deliberately user-invoked only, because they have side effects.

## Two things worth knowing

**Worktrees survive their session.** When a session exits with a clean
worktree, Claude Code removes it automatically. `/worktree:new` locks each
worktree it creates (`worktree-plugin: persistent workspace`) so that cannot
happen. Git refuses to remove a locked worktree unless `-f -f` is given, and
every removal path Claude Code uses passes at most a single `--force`. The lock
does not block entering or switching, and `/worktree:clean` releases it when
you actually want the worktree gone.

**Several sessions can share one worktree — by launching, not switching.**
`cd .claude/worktrees/wallet-fix && claude` works alongside any session already
there. But `EnterWorktree` refuses to *switch into* a worktree held by a
running Claude session, so `/worktree:switch` tells you to open a terminal
there instead. Both sessions keep full capability; there are no modes.

## Status line

Installed by `/worktree:init` to a stable path in your home directory
(`~/.claude/worktree-plugin/`), never to the versioned plugin cache — so plugin
updates don't break it.

Optional environment overrides:

| Variable | Default | Effect |
|---|---|---|
| `WT_GLYPH_TREE` | 🌳 | Marker when inside a worktree |
| `WT_GLYPH_MAIN` | ◉ | Marker for the main checkout |
| `WT_SEP` | ` \| ` | Separator |
| `WT_SHOW_DIRTY` | unset | Set to `1` to append a changed-file count. Off by default: it costs a `git status` on every render. |

The script reads `.git/HEAD` directly instead of shelling out to git, so a
render costs about 80 ms.

## What this plugin deliberately does not do

Claude Code already handles these, and reimplementing them would make things
worse:

- Worktree creation, entry, and write isolation → `--worktree`, `EnterWorktree`
- Carrying `.env` into new worktrees → `.worktreeinclude`
- Monorepo speed and disk use → `worktree.sparsePaths`, `worktree.symlinkDirectories`
- Subagent and background-session worktree cleanup → the built-in retention sweep
- Running many agents on one task → `/batch`, subagents, agent teams

It also ships **no `WorktreeCreate` hook**. That hook *replaces* git worktree
creation entirely and disables `.worktreeinclude`; adopting it would remove
capability, not add it.

Cross-session messaging (`/list-agents`, `SendMessage`) is a good fit for
coordinating parallel worktrees, but Claude Code does not offer it on native
Windows, so it is out of scope for now. Session *discovery* via
`claude agents --json` does work on Windows and is used by `list` and `clean`.

## Uninstalling

Run `/worktree:init --remove`, then remove the plugin. Your worktrees are plain
git objects and keep working through `--worktree`, `EnterWorktree`, and
`git worktree` as normal.

## Reference

- `references/switching-rules.md` — where you can and cannot switch, and why
- `references/cleanup-policy.md` — the full safety classification
- `references/windows-notes.md` — path spellings, MSYS pitfalls, performance

## License

MIT
