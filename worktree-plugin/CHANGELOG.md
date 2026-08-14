# Changelog

All notable changes to the Git Worktree Workspaces plugin.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
