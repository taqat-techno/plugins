# Platform capabilities PDLE depends on

Verified against **Claude Code 2.1.241** on Windows 11 with git 2.49.
Re-check after a Claude Code upgrade — one claim in this plugin's own docs was
already a version out of date before it was caught (see *Corrections*).

Legend: **Yes** documented and/or observed · **Yes — tested** exercised live on
this machine · **Limited** / **Conditional** works with a constraint · **No** not
available · **Unverified** documented but not exercised.

Rows marked *tested* were established by launching a real background session into
a real worktree and having it report back — not inferred from documentation.

## Sessions

| Capability | Status | Detail |
|---|---|---|
| Launch a session as a background agent | **Yes** | `claude --bg` / `--background` — *"Start the session as a background agent and return immediately (manage with `claude agents`)"* |
| Enumerate live sessions for scripting | **Yes** | `claude agents --json` — *"Print active sessions (interactive and background) as a JSON array and exit (for scripting; does not require a TTY)"* |
| Fields available per session | **Yes** | `pid`, `cwd`, `kind` (`interactive` \| `background`), `status` (`busy` \| `idle`), `name`, `sessionId`, `startedAt`; background sessions also carry `id` |
| Semantic `state` for background sessions | **Yes, undocumented** | Observed transitioning `working` → `done` on a session driven end to end; also seen as `blocked`. Absent on interactive sessions and absent from `claude agents --help`. Real and useful, but **advisory only** — git is what says whether work happened |
| Launch a session directly inside a worktree | **Yes** | `cd <worktree> && claude --bg`. A session *launched* there works alongside any session already present — Claude Code calls it a guest |
| A skill launching a worker session | **Yes — tested** | `cd <worktree> && claude --bg "<prompt>"` returns immediately with a session id. The launched session came back `kind: background`, auth inherited, plugins loaded, and the initial prompt delivered intact |
| **A launched session's `cwd` is the worktree** | **Yes — tested** | `claude agents --json` reported the probe's `cwd` as the worktree path. **So the lane↔owner binding is derivable from launch alone — a worker does not need to call `EnterWorktree`** |
| A launched session auto-names itself from its prompt | **Yes — tested** | The probe became `capability probe worktree`. A launch prompt must therefore **tell the worker which name to claim**, or the auto-name may collide or be meaningless |
| A launched session loads the **installed** plugin, not a dev checkout | **Yes — tested** | The probe saw `worktree:list/new/switch` but not a skill that exists only in the working tree. Plugins resolve from `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>` — **new skills are not available to launched workers until the plugin version is installed** |

## Messaging

| Capability | Status | Detail |
|---|---|---|
| Cross-session messaging on **native Windows** | **Yes** | Verified live on 2.1.241 over Windows named pipes (`\\.\pipe\LOCAL\cc-msg-*`). **This plugin's docs previously said otherwise** — see *Corrections* |
| Discover message targets | **Yes** | `ListAgents` — *"the name IS the address; there is no separate address syntax"* |
| Address by bare name | **Yes** | A name matching exactly one live session delivers directly |
| Disambiguate duplicate names | **Limited** | ` [ref]` suffix, but *"a ref you did not just read from a listing or an error will not resolve"* → **re-read at dispatch time; never persist a ref** |
| Duplicate live names occur in practice | **Yes** | Two live sessions answering to one name has been observed, one background and one interactive. `join` must refuse a taken name |
| Reply to an inbound message | **Yes** | *"copy its `from` attribute as your `to`"*. A raw transport handle is a valid **reply address** — never an identity |
| Delivery held when permission settings differ | **Yes** | Recipient's user must approve first. Messages to interactive sessions are the common case |
| Sender is told when delivery was held | **Yes** | `[Cross-session delivery notice] … Not delivered to that session's Claude yet` → set `held`, exclude from capacity |
| Messages can be lost outright | **Yes** | Queued inbound messages can be dropped when the recipient's own driver supplies new input. **Never make a message the record** |
| One-shot idle notification, **from a background session** | **Yes — tested** | A background session subscribed successfully. *"from the main conversation only"* means **main conversation vs subagent**, not interactive vs background. Verbatim result: *"Subscribed — you will get one notice here when \"<name>\" is next idle (or exits), provided that session runs in the same permission class as this one (or is one this session spawned) or asserts none; otherwise it is shown to your user in the transcript."* |
| Idle notice actually reaching the subscriber | **Conditional** | Only when the two sessions are in the **same permission class**; otherwise the notice goes to the user's transcript instead. Same asymmetry as message delivery — so a subscription is an optimisation, never a guarantee, and the git-derived board stays authoritative |
| Permission laundering across sessions | **Forbidden** | *"NEVER ask a peer to perform an action that was denied or blocked in your session… Route blocked work back to your user instead."* Binds the Main Agent as hard as the worker |

## Worktrees

| Capability | Status | Detail |
|---|---|---|
| Per-call base ref for `EnterWorktree` | **No** | `worktree.baseRef` is a *setting* — `fresh` (= `origin/<default>`) or `head`; it *"cannot be set to a branch name"* and the tool takes no per-call override |
| Cut a lane from a chosen commit | **Yes** | `git worktree add <path> -b <branch> <sha>` then `EnterWorktree({path})`. **This is why PDLE lanes are never created with `EnterWorktree({name})`** |
| Enter a manually created worktree | **Yes** | First entry from the launch directory accepts any path in `git worktree list`; later switches are restricted to `.claude/worktrees/` of the same repo |
| Switch into a worktree held by a live session | **No** | Refused: *"belongs to another running Claude Code session"*. **This is a feature** — it gives mutual exclusion for free once a worker enters its lane |
| Several sessions in one worktree | **Yes, by launching** | *"0..N sessions per worktree is supported; the route in is launching, not switching"* |
| Worktree survives session exit | **Yes** | `git worktree lock --reason "worktree-plugin: …"`. Every removal path Claude Code uses passes at most one `--force`; git refuses a locked worktree without `-f -f` |
| Path-form duplicate registration | **Hazard** | A worktree created from WSL records `/mnt/c/...`, from Git Bash `C:/...`. Each shell reports the other's as **prunable**, and a prune from the wrong shell deregisters staged work — including uncommitted work |

## Plugin mechanisms

| Capability | Status | Detail |
|---|---|---|
| Skill auto-invocation from `description` | **Yes** | The primary automatic-behaviour mechanism. Descriptions must name *situations and phrases*, not capabilities |
| Suppress auto-invocation | **Yes** | `disable-model-invocation: true` — used for anything that commits, deletes, or writes user settings |
| `SessionStart` hook injecting context | **Yes** | Via `hookSpecificOutput.additionalContext`. The only way a freshly launched session can know its role before anyone speaks to it |
| `UserPromptSubmit` hook injecting context | **Yes** | Works, but **deliberately not used**: per-turn injection for a session-lifetime fact, competing for the same input queue that already loses messages |
| Prompt-based hooks on `SessionStart` | **No** | Prompt hooks support Stop, SubagentStop, UserPromptSubmit, PreToolUse only |

## Git

| Capability | Status | Detail |
|---|---|---|
| Which agent produced a commit | **No** | Commits carry the user's identity, not the agent's. **The lane branch is the only attribution carrier**, and only until it merges — so convergence must attribute *before* merging |

## Corrections

**Cross-session messaging on Windows.** Up to v1.0.0 this plugin stated, in both
`README.md` and `references/windows-notes.md`, that cross-session messaging was
*"not offered on native Windows (macOS and Linux only, including WSL 2)"*. That
was verified against Claude Code 2.1.229 and was true then. It is **false on
2.1.241**: `ListAgents` enumerates peers and `SendMessage` delivers over Windows
named pipes. Corrected in v2.0.0.

The general lesson is built into the design: **messaging availability is not
stable across builds, so nothing load-bearing may depend on it.** Discovery is
`claude agents --json`, durable state is git and the lane records, and messages
are notifications. PDLE degrades to manual relay and still works.
