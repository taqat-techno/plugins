# Changelog

All notable changes to the `git-safety` plugin are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **`git-safety`** — the remote-mutation preview gate: before any issue/PR/board write
  (above all an automated batch), emit a no-mutation preview of exactly what changes per
  target and wait for an explicit go-ahead; write only the minimal verified set
  (`[ ] → [x]` on verified items only — never reverse an existing `[x]`, close an issue,
  or touch a board field as a side effect). Defers to `qa-browser`
  (`runtime-reality-check`) for whether the claim being written was earned.
- **`shared-checkout-safety`** — the separability proof before staging beside a peer's
  edits (mtime bands + per-file diff + no shared file); HEAD is not stable either
  (a background sync hook can fast-forward the branch between turns, so a finding verified
  last turn may already be fixed, and a manual pull launched alongside one in flight
  collides on `.git/index.lock`); re-read a peer-owned file immediately before editing it;
  per-session database name *and* port, not just an isolated build dir; and the
  coordination file (scope, owned files, the contract the sibling must consume) when two
  agents share a tree by design.

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
