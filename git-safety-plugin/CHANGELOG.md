# Changelog

All notable changes to the `git-safety` plugin are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-07-23

Initial release. The generic **local git-workflow safety** layer that git-integration,
commit-workflow, and PR-review plugins leave out. Advisory only — nothing blocks a
command or auto-mutates git.

### Added
- **`git-safety` skill** — local-operation hygiene: stage explicit paths (never
  `git add -A`/`.`/`-u`); re-check the full `git status` immediately before commit/push;
  never silent-switch or discard with a dirty tree; the `git rm --cached` team-impact
  rule; per-repo author identity; and remote push identity (right account, re-asserted in
  the same shell, MCP is not a permission bypass).
- **`shared-checkout-safety` skill** — for when more than one agent/session/syncer shares
  ONE working tree: the default-safe `git worktree` isolation recipe; commit immediately
  (a peer's `reset --hard` + `clean` wipes uncommitted work); never `reset --hard`/`clean`/
  `stash`/`checkout -- .` there; the `stash@{0}`-shifts-when-the-peer-pops trap;
  extract-wiped-work-outside-the-repo-first; the mtime quiescence check; and don't clobber
  a shared build dir or port.
- **`risky_git_advisory` hook** — one non-blocking `PreToolUse` hook that prints a single
  reminder when a shell command contains a risky git shape (`git add -A`/`.`/`-u`,
  `reset --hard`, `clean -fd`, `stash`, `checkout -- `/`restore`, `push --force`,
  `rm --cached`). Never blocks, never rewrites the command, exit 0 always.

### Boundaries
- Defers git/platform integration to the GitHub/GitLab/GitKraken MCP plugins, commit/PR
  workflows to a commit-workflow plugin, code/PR review to a review plugin, provider-specific
  remote push gates to `devops` (`git-remote-write-gate`), the file syncer itself to
  `claude-env-doctor`, and the general "an MCP tool is not a permission bypass" principle
  to `agent-safety-guards`.
