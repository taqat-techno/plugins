# Changelog

All notable changes to the Git Worktree Workspaces plugin.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.1.0] - 2026-09-02

Adds the **completion contract** — the task-level layer above the work
packages: what must be objectively true of the whole integrated result before a
plan-driven parallel run may be called complete, which package serves which
outcome, and a reconciliation on the merged trunk at convergence. Additive: a
plan without a `## Completion Contract` section behaves exactly as in 2.0.0.

### Added

- `/worktree:completion-contract` — establish, audit, or reconcile the
  contract. Main Agent only. `reconcile` runs the named instruments on the trunk
  and merges nothing.
- `references/completion-contract.md` — the owning reference: `CC-nn` entry
  shape (Outcome / Verification / Expected), expectations that can fail, the
  `Satisfies` mapping with its two coverage findings, the state model (MET /
  UNMET derived at reconciliation and never stored; ABANDONED as a recorded
  amendment), revision and amendments, and the reconciliation procedure.

### Changed

- `plan-schema.md` — `Satisfies` field, Completion Contract section pointer,
  two audit checks (uncovered outcome, orphan package), worked example.
- `convergence.md` — step 8b, reconcile the completion contract.
- `dispatch-gates.md` — gate 2 also requires `Satisfies` when a contract exists.
- `brief-template.md` — `Satisfies` carried into the brief; MET is decided at
  convergence, never by the lane.
- `report-template.md` — `Contract evidence` section: where to look, never a
  MET claim.
- `plan-for-parallel`, `lead`, `integrate` — one routing line each.

### Provenance

Adapted from the acceptance-ledger idea in the `unlazy` skill
(github.com/Leonxlnx/unlazy, MIT): gates written before the work, expectations
that can fail, MET / UNMET / ABANDONED, reconciliation against the request and
its amendments, re-measuring every reported number. Deliberately not ported:
its Node checker, approval store, ownership leases, dispatch-wave machinery,
Stop hook, `GATES.md` / `.unlazy/` state, and the Depth Tree effort arithmetic
— each is either native to Claude Code, already owned by this plugin or
`agent-safety-guards`, or retracted upstream. No hooks, no scripts, no new
on-disk state.

## [2.0.0] - 2026-08-24

Adds **Plan-Driven Lane Execution (PDLE)** — one main agent orchestrating several
worker sessions, each in its own isolated worktree lane. Verified against Claude
Code 2.1.241 and git 2.49 on Windows 11.

**Everything is additive.** With no `.claude/lanes/` directory present the plugin
behaves exactly as 1.0.0 did: same five skills, same behaviour, no hooks, no
state on disk. The major version reflects two amended design commitments, not a
breaking change.

### Added

- `/worktree:lead` — become the main agent: read the plan, rebuild the board from
  git, discover and handshake workers, compute readiness. `--recover` after a
  restart.
- `/worktree:join` — register a worker session under a **unique** name, and warn
  loudly when a session's kind means dispatches to it will be held for approval.
- `/worktree:board` — the orchestration board, **derived** from git, the
  filesystem and the live session list. Seven states, twelve anomaly detectors,
  cross-lane ownership collisions. Read-only, never stored.
- `/worktree:delegate` — nine pre-flight gates, lane provisioning, generated
  brief, dispatch, ack tracking, and honest handling of held delivery.
- `/worktree:report` — worker packet close: **write the report, stage, then
  notify**, in that order.
- `/worktree:integrate` — convergence: verify each lane from git, capture a
  pre-merge baseline, re-derive merge order, one consolidated approval, central
  merge, attribute new failures, tell every gate holder. User-invoked.
- `/worktree:plan-for-parallel` — makes a plan delegation-ready as it is written,
  or audits an existing one. Stays silent on plans too small to benefit.
- `scripts/wt-lanes.sh` — the lane primitive. Same bash 3.2, no-jq, fork-frugal
  style as `wt-inventory.sh`.
- `hooks/pdle_session_start.py` — optional role notice, installed **into user
  settings by `/worktree:init`**, never shipped as a plugin `hooks.json`.
- References: `lane-record`, `board-states`, `roles`, `plan-schema`,
  `dispatch-gates`, `brief-template`, `report-template`, `convergence`,
  `platform-capabilities`.

### Changed

- `/worktree:new` — optional `--lane`, `--owns`, `--base`. Lane mode always uses
  `git worktree add` rather than `EnterWorktree({name})`, because that tool takes
  no per-call base ref and would cut from `origin/<default>` instead of the
  integrated trunk. Emits one canonical path spelling.
- `/worktree:clean` — new `lane-active` verdict; a lane with an owner or unmerged
  work is never offered however clean its tree. Refuses to prune when a duplicate
  path registration is present.
- `/worktree:init` — optional PDLE section: lane directories, the role-notice
  hook, and a CLAUDE.md stanza. All three off by default, confirmed separately,
  reversed by `--remove`. `--remove` never deletes `.claude/lanes/`.
- `/worktree:list` and `/worktree:switch` — **unchanged**.

### Fixed

- **Session attachment never matched — a latent 1.0.0 defect.**
  `wt-inventory.sh`'s JSON reader stripped the opening quote of each value but
  not the closing one, so every field came back with a trailing `"`:

  ```
  1.0.0   cwd=[C:\\MY-WorkSpace\\odoo\\projects\\medline-19"]   name=[main agent"]
  2.0.0   cwd=[C:\\MY-WorkSpace\\odoo\\projects\\medline-19]    name=[main agent]
  ```

  Because `cwd` is normalised and compared against worktree paths, the stray
  quote guaranteed a mismatch: `/worktree:list` always showed **0 attached
  sessions**, and `/worktree:clean`'s `unsafe` verdict for *"Claude sessions
  attached"* could never fire. Cleanup was still protected by the independent
  `claude-live` lock check, so nothing was lost — but one of the two safety
  inputs was silently dead. Fixed in both scripts.

- **Corrected a stale platform claim.** `README.md` and
  `references/windows-notes.md` stated that cross-session messaging was *"not
  offered on native Windows"*. True against 2.1.229; false against 2.1.241, where
  it works over Windows named pipes. The design does not depend on it either way.
- `references/switching-rules.md` now documents the **prunable-duplicate trap**:
  a worktree created from WSL registers `/mnt/c/...` and from Git Bash `C:/...`,
  each shell reports the other's as prunable, and a prune from the wrong shell
  deregisters staged work.

### Platform capabilities verified live

Established by launching a real background session into a real worktree and
having it report back, rather than inferred from documentation. Full matrix in
`references/platform-capabilities.md`.

- **`claude --bg` from a worktree works** — returns immediately, comes up
  `kind: background`, inherits auth and plugins, and receives its initial prompt.
- **A launched session's `cwd` is the worktree**, so the lane↔owner binding is
  derivable from launch alone. **A worker never has to call `EnterWorktree`.**
- **`notify_when_idle` works from a background session.** The schema's *"from the
  main conversation only"* means main conversation vs subagent, not interactive
  vs background. It reaches the subscriber only when both sessions share a
  permission class, otherwise it goes to the user's transcript — so it is an
  optimisation, and **the absence of an idle notice means nothing**.
- **A launched session auto-names itself from its prompt.** A launch prompt must
  name the worker explicitly, or the auto-name may collide — and a collision is
  two sessions pointed at one worktree.
- **A launched worker loads the *installed* plugin, not a working copy.** Plugins
  resolve from `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>`, so
  workers only get these skills once 2.0.0 is actually installed.
- `agents --json` `state` (`working` / `done` / `blocked`) is real and was seen
  to transition, but is undocumented — advisory only.

### Design notes

- **Two commitments amended, narrowly and reversibly.**
  *"The plugin stores nothing"* → it stores lane records, and only those:
  ownership, base, owner, and dispatch/ack facts. Nothing git, the filesystem, or
  `claude agents --json` can answer is persisted — every stale-state failure this
  protocol prevents was a stored copy of a computable fact.
  *"Zero hooks"* → one advisory `SessionStart` hook, installed into user settings
  **only on request**. The plugin still ships no `hooks.json`, so installing it
  registers nothing and cannot interfere with a session.
- **One writer per file.** The main agent is the only writer of a `.lane` record;
  workers only add append-only reports and never modify one. A single mutable
  file with two writers is the shape that loses updates silently.
- **A lane is a work-package execution environment, not a session workspace.**
  Agents move between lanes; the lane and its staged work persist, which is what
  makes worker loss recoverable.
- `merged` means *this lane's work landed*, never *this ref is reachable*. A lane
  branch cut from the base and never committed to is trivially an ancestor of the
  trunk, so commits-from-base is counted first — otherwise every un-started lane
  reports done.
- Capacity is background sessions that have **answered a handshake**. A
  provisioned worktree is not a staffed lane, and a dispatch held for approval is
  not a worker.

## [1.0.0] - 2026-08-14

Initial release. Verified against Claude Code 2.1.229 and git 2.49 on
Windows 11; scripts are written for bash 3.2+ so macOS and Linux are covered.

### Added

- `/worktree:list` — inventory of every worktree with state, lock provenance,
  attached Claude sessions, and switchability. Read-only.
- `/worktree:new` — creates a worktree via `EnterWorktree`, then locks it so it
  survives session exit. `--branch` creates via `git worktree add` when a
  custom branch name is required.
- `/worktree:switch` — picker plus `EnterWorktree({path})`, enforcing the
  managed-zone rule and detecting worktrees held by a running Claude session.
- `/worktree:clean` — conservative cleanup with a mandatory dry run,
  per-worktree confirmation, lock-provenance checks, and gated
  `git worktree prune`.
- `/worktree:init` — installs the status line to a stable user-level path and
  offers worktree defaults, a prefer-worktrees CLAUDE.md stanza, and project
  files. `--remove` reverses everything.
- `scripts/wt-inventory.sh` — the single deterministic primitive; emits JSON
  from `git worktree list --porcelain` enriched with git state, lock kind, and
  session attachment.
- `scripts/wt-install-statusline.sh` — platform detection and status-line
  installation to `~/.claude/worktree-plugin/`.
- `statusline/worktree-statusline.sh` and `.ps1` — three-tier rendering
  (`worktree.*` → `workspace.git_worktree` → main checkout).
- Reference docs for switching rules, cleanup policy, and platform notes.

### Design notes

- **Zero hooks.** Every candidate was evaluated and rejected: `WorktreeCreate`
  replaces git worktree logic and disables `.worktreeinclude`; `Stop`,
  `SubagentStop`, `PreToolUse`, `PostToolBatch` and `PreCompact` can block a
  session; `CwdChanged`, `SessionStart` and `SessionEnd` are redundant with the
  status line and native behaviour.
- **No plugin-owned state.** Git and Claude Code own everything; the plugin
  reads and never mirrors.
- Persistence uses `git worktree lock` with a non-Claude reason, which blocks
  every removal path Claude Code uses (all pass at most a single `--force`)
  while leaving entry and switching unaffected.
- The status line is installed to a stable home-directory path rather than the
  versioned plugin cache, so plugin updates do not break it.

### Platform notes

- `scripts/wt-inventory.sh` uses fork-free bash helpers; an earlier
  `sed`/`tr` implementation took 23 s on an 8-worktree repository against
  2.5 s now (Windows process spawns cost ~100 ms each).
- PID liveness on Windows requires `MSYS_NO_PATHCONV=1` so Git Bash does not
  rewrite `tasklist /FI` into a filesystem path.
- Path comparison normalises the three spellings in play (`C:/x` from git,
  `C:\\x` from `claude agents --json`, `/c/x` from Git Bash) and folds case on
  Windows.
- The status line prefers the `.sh` script on all platforms, including Windows,
  where PowerShell startup costs roughly 600 ms against about 80 ms for Git
  Bash.
