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
- **Git is the source of truth.** No cache, no database, no mirrored state. If
  git, the filesystem, or `claude agents --json` can answer it, the plugin does
  not write it down. *(PDLE adds one exception: a small lane record holding
  ownership, base, owner and dispatch facts — the things genuinely not derivable.
  It is created only when you run lanes.)*
- **Nothing runs unless you invoke it.** The plugin ships no `hooks.json`, so
  installing it registers nothing and cannot interfere with a session. PDLE's
  optional role notice is a hook `/worktree:init` writes into your own settings,
  on request, and `--remove` takes it back out.
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

**If worktrees are all you want, you are done — stop reading here.** Everything
below is opt-in and inert until you use it.

## Plan-Driven Lane Execution

For running several Claude sessions as one team: **one main agent** orchestrating
**worker sessions**, each in its own isolated worktree.

The unit is a **lane** — one work package, one worktree, one branch, one base
commit, one exclusive ownership set. A lane outlives its worker: workers move
between lanes, and the lane and its staged work stay put, which is what makes a
lost worker recoverable rather than expensive.

```
                 ┌──────────────────┐
  you  ────────► │   MAIN AGENT     │   the only session you talk to
                 └────────┬─────────┘
              brief       │      report
        ┌────────────┬────┴───────┬────────────┐
        ▼            ▼            ▼            ▼
     worker       worker       worker       worker
        │            │            │            │
      lane         lane         lane         lane
```

| Command | Role | What it does |
|---|---|---|
| `/worktree:plan-for-parallel` | either | Makes a plan delegation-ready as you write it, or audits one you have |
| `/worktree:completion-contract` | main agent | States what must be true of the whole result, maps packages to outcomes, reconciles on the trunk at convergence |
| `/worktree:lead` | main agent | Take orchestration: read the plan, rebuild the board, find workers, compute what is ready |
| `/worktree:join` | worker | Register under a unique name and confirm reachability |
| `/worktree:board` | either | What every lane is actually doing — derived from git, never narrated |
| `/worktree:delegate` | main agent | Assign a lane through nine pre-flight gates |
| `/worktree:report` | worker | Close a packet: write the report, stage, then notify |
| `/worktree:integrate` | main agent | Converge lanes into the trunk. User-invoked |

### Getting started

```bash
# 1. in the repo, one session:   "You are the main agent. Start execution."
# 2. a background session per worker — launched INSIDE its lane worktree:
cd .claude/worktrees/<lane> && claude --bg 'You are PDLE worker "agent 2".
  Run /worktree:join, then read the brief in .claude/lanes/briefs/ and begin.'
```

Then talk only to the main agent. It discovers the workers, checks each is
reachable, provisions lanes, and dispatches. If capacity is short it will offer
to launch workers for you — one confirmation each, never silently.

Three things worth knowing:

- **Launch inside the lane worktree.** The session's working directory becomes
  the lane, which is how the board knows who owns what.
- **Name the worker in the launch prompt.** A background session otherwise
  auto-names itself from its prompt text, and two sessions sharing a name are two
  sessions pointed at the same worktree.
- **Workers load the *installed* plugin**, not your working copy — so make sure
  this version is installed before starting them.

### The rules that make it safe

- **Workers never commit, merge, or push.** A packet ends *staged* and reported.
  The main agent integrates centrally, once you approve.
- **Two lanes may not run concurrently if their ownership sets intersect.** That
  single rule is what prevents two agents editing the same component.
- **Directives flow by message; durable state flows by file and git.** Messages
  can be held or lost, so a worker writes its report *before* it notifies. A lost
  message costs latency, never work.
- **Capacity is workers that answered a handshake** — not workers that exist. A
  provisioned worktree is not a staffed lane.
- **The board is derived, never stored.** A stored board goes stale and is then
  believed.
- **The run has a written end-state.** A Completion Contract names each required
  outcome with a verification that can fail; packages declare which outcomes they
  satisfy; the main agent reconciles on the merged trunk. MET is derived at
  convergence, never stored.

The only state on disk is `.claude/lanes/` — ownership, base, owner, and
dispatch facts. Nothing that git can answer is written down.

Concepts and protocols live in `references/`: `roles`, `lane-record`,
`board-states`, `plan-schema`, `dispatch-gates`, `convergence`,
`completion-contract`.

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

It ships **no `hooks.json`**, so installing it registers nothing. PDLE's optional
role notice is a `SessionStart` hook that `/worktree:init` writes into *your*
settings, only if you ask for it.

> **Correction, v2.0.0.** v1.0.0 said cross-session messaging was not offered on
> native Windows. That was true against Claude Code 2.1.229 and is false against
> 2.1.241, where it works over Windows named pipes. PDLE still does not *depend*
> on it: discovery is `claude agents --json`, durable state is git and the lane
> records, and messages are only notifications.

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
