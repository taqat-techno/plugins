# git-safety

Generic **local git-workflow safety guardrails** for Claude Code — the safety layer that git *integration* (GitHub/GitLab/GitKraken MCPs), *commit helpers*, and *PR-review* plugins leave out. It does not create commits, open PRs, or review diffs; it keeps the local git operations around that work from destroying data.

**Advisory only.** Every skill reasons and warns; the one hook prints a single reminder. Nothing here blocks a command, rewrites git state, or auto-mutates anything. The user owns every commit, push, discard, and recovery decision.

## Why this plugin exists

An audit of accumulated engineering lessons found that the most damaging git mistakes agents make are blunt *local* footguns with no owner in any marketplace:

- `git add -A` sweeping another session's staged work into a commit,
- switching branches or `checkout -- .` throwing away a dirty tree,
- `git rm --cached` deleting a shared file for the whole team on merge,
- committing under the wrong author, pushing on the wrong identity,
- and — most severe — **two agents/sessions sharing one working tree**, where a `reset --hard`/`clean`/`stash` wipes the other writer's uncommitted work and `stash@{0}` shifts the instant the peer pops.

Git integrations and PR-review plugins cover *doing* git and *reviewing* code; none covers this hygiene layer.

## Skills

| Skill | Use when | Owns |
|---|---|---|
| **git-safety** | before any `git add`, commit, branch switch, `git rm --cached`, push, or repo-MCP write (including ticking issue checkboxes) | stage explicit paths (never `git add -A`/`.`); re-check `git status` immediately before commit/push; never silent-switch/discard a dirty tree; `git rm --cached` team-impact; per-repo author identity; remote push identity (right account, re-asserted; MCP is not a bypass); the remote-mutation preview gate (no-mutation preview per target + explicit go-ahead, minimal verified change set only) |
| **shared-checkout-safety** | when a second session/agent/syncer shares ONE working tree, or when recovering wiped work | the default-safe recipe (isolate with `git worktree`, never fight the shared tree); commit immediately; never `reset --hard`/`clean`/`stash`/`checkout -- .` there; `stash@{0}` is not stable; extract wiped work outside the repo first; quiescence via mtime snapshots; proving separability before staging beside a peer's edits; HEAD is not stable either (background sync can fast-forward it between turns); don't clobber shared build output, ports, or databases; the coordination file when two agents share a tree by design |

Both auto-activate from their `description` triggers; they are not user-invocable slash commands.

## Hook

One non-blocking `PreToolUse` hook (`hooks/risky_git_advisory.py`) inspects a shell command and, if it contains a risky git shape (`git add -A`/`.`/`-u`, `reset --hard`, `clean -fd`, `stash`, `checkout -- `/`restore`, `push --force`, `rm --cached`), prints a single reminder pointing at the relevant skill. It never blocks, never rewrites the command, and exits 0 always.

## Boundaries (what this plugin does NOT do)

- **Git/platform integration & context** → use the GitHub / GitLab / GitKraken MCP plugins.
- **Making commits / pushing / opening PRs** → use a commit-workflow plugin.
- **Reviewing code or PRs** → use a code-review plugin.
- **Provider-specific remote push gates** (e.g. Azure DevOps push identity / account policy) → the `devops` plugin's `git-remote-write-gate`.
- **The file syncer itself** (Syncthing conflict/deadlock/ignore mechanics) → the `claude-env-doctor` plugin.
- **General "an MCP tool is not a permission bypass"** principle → the `agent-safety-guards` plugin (this plugin applies it specifically to git/repo writes).
- **Whether a claim being written to a remote was actually earned** (an item read statically is not runtime-verified) → the `qa-browser` plugin's `runtime-reality-check`. This plugin owns *how* a remote write is gated, not what licenses it.

## License

MIT
