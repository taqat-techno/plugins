# git-safety

## What it does

Local git-workflow safety for Claude Code. Two skills teach the habits that stop an agent
from destroying work: stage explicit paths, re-check the tree right before commit and push,
never discard a dirty tree, get author and push identity right, and handle a working tree
that a second session or a file syncer is also writing to. One hook spots risky git
commands; by default it reminds Claude, and in the opt-in `ask` mode it makes you confirm
irreversible operations before they run.

It is for anyone who lets Claude run git in a real repository, and especially for setups
where several sessions, agents or a syncer (Syncthing, Dropbox) share one checkout. It does
not make commits, open PRs or review code.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install git-safety@taqat-techno-plugins
```

On Claude Code 2.1.275 or later, one step also works:
`/plugin install git-safety --marketplace taqat-techno/plugins`.

## Requirements

| Requirement | Why | Check |
|---|---|---|
| Python 3.8 or later as `python3`, `python` or `py -3` | runs the hook | `python3 --version` |
| A POSIX shell for hook commands (Git Bash on Windows) | the hook launcher is POSIX sh | `sh --version` |
| git | the commands the hook inspects | `git --version` |

Without Python or a POSIX shell the hook exits 0 and does nothing; the skills still work.

## Skills

| Skill | Use when |
|---|---|
| `git-safety` | about to `git add`, commit, switch or restore, `git rm --cached`, push, merge two long-lived branches, or write to issues or PRs through `gh` or an MCP tool |
| `shared-checkout-safety` | a second session, agent or file syncer may be writing the same working tree, or you are recovering work wiped on such a tree |

Both load automatically from their descriptions. Neither is a slash command. There are no
commands or agents.

## Hooks

| Hook | Event / matcher | What it does | Can block? |
|---|---|---|---|
| `hooks/risky_git_advisory.py` | `PreToolUse` on `Bash\|PowerShell` | Finds risky git operations in the command and either reminds Claude (`advise`) or asks you to confirm (`ask`) | Only in `ask` mode, and only for irreversible operations, by asking you; it never denies |

**Timing matters.** In `advise` mode the reminder is PreToolUse `additionalContext`, which
Claude Code hands to Claude together with the tool result. The command has already run by
the time Claude reads it. Advise mode improves the next step; it prevents nothing. Only
`ask` mode stops an irreversible command before it runs.

What it detects:

| Operation | Irreversible (asks in `ask` mode) |
|---|---|
| `reset --hard` | yes |
| `clean` with `-f`/`--force` (not with `-n`/`--dry-run`) | yes |
| `checkout -f`, `checkout -- <paths>`, `checkout .`, `switch --discard-changes`/`-f`, `restore <paths>` without `--staged` | yes |
| `push --force`, `push -f`, `push <remote> +<ref>`, `push --mirror` | yes |
| `push --delete`, `push -d`, `push <remote> :<ref>`, `push --prune` | yes |
| `branch -D`, `branch --delete --force` | yes |
| `tag -d` | yes |
| `filter-branch`, `filter-repo` | yes |
| `reflog expire`/`delete`, `gc --prune=now`, `prune` | yes |
| `update-ref -d` | yes |
| `push --force-with-lease` | no (reminder only) |
| `stash drop`/`clear`, `stash`/`stash pop`/`apply` (not `list`/`show`) | no |
| `add -A`, `add --all`, `add -u`, `add .` | no |
| `rm --cached` | no |
| push to a branch listed in `protected_branches` | no |

How it reads a command: it splits on unquoted `;`, `&&`, `||`, `|`, `&` and newlines, and
looks only at segments whose program is `git` (also `git.exe` or a full path to it). It
skips `VAR=value` prefixes, wrappers such as `command`, `sudo`, `env` and `nohup`, and git's
global options (`-C <path>`, `-c key=value`, `--git-dir`, `--work-tree`, `--no-pager`, ...).
Flags count anywhere after the subcommand. It looks inside `sh -c` / `bash -c` /
`pwsh -Command` bodies. Text in quotes, comments, `echo` and `grep` patterns and commit
messages is not matched.

What it cannot see: git aliases (`git config alias.nuke 'reset --hard'`), scripts that call
git (`./cleanup.sh`), commands assembled at runtime (`eval`, `$(...)`), IDE git
integrations and MCP git tools. Treat it as a seatbelt, not a sandbox.

Check the detection table offline: `python hooks/risky_git_advisory.py --self-test`.

## Configuration

| Setting | Where | Values | Default |
|---|---|---|---|
| `guard_mode` | plugin option (`/config`, stored by Claude Code; reaches the hook as `CLAUDE_PLUGIN_OPTION_GUARD_MODE`) | `advise`, `ask`, `off` | `advise` |
| `GIT_SAFETY_MODE` | environment variable set before you start Claude Code (overrides `guard_mode`) | `advise`, `ask`, `off` | unset |
| `.claude/git-safety.local.json` | per project, at the repository root | `{"mode": "ask", "protected_branches": ["main", "release/*"]}` | absent |

The project file can only make the guard stricter (`advise` to `ask`). It cannot lower the
mode or turn the hook off, because Claude can write files in the repository.
`protected_branches` takes shell-style patterns; a push whose target matches gets a
reminder (a bare `git push` targets the current branch from `.git/HEAD`). A missing or
malformed file is ignored.

To turn the hook off, set `guard_mode` to `off`, or disable the plugin with `/plugin`.

## Platform support

| Platform | Status |
|---|---|
| Linux, macOS | Supported. |
| Windows with Git Bash | Supported, for both the Bash and PowerShell tools; `git.exe` and full paths are recognised. |
| Windows without Git Bash | Claude Code runs hook commands in PowerShell, where the POSIX launcher does not parse; the hook fails open (does nothing). Skills work. |
| WSL | Same as Linux. |

## Data & privacy

The hook reads the command from the hook payload, `.claude/git-safety.local.json` and
`.git/HEAD` in the current repository. It writes no files, keeps no log, makes no network
calls and never echoes the command text: its messages are fixed strings. Nothing leaves the
machine. The reminder or the confirmation prompt is what appears on screen.

## Limitations

- Advise mode cannot stop a command; see "Timing matters" above.
- String matching on shell commands misses aliases, scripts, runtime-built commands and
  non-shell git tools.
- Ask mode follows Claude Code's permission flow; how an `ask` behaves under a permission
  mode that skips prompts is decided by Claude Code, not by this plugin.
- The skills are advice. They never run git themselves and never decide for you.
- Related plugins are optional: if `devops`, `agent-safety-guards`, `qa-browser` or
  `env-doctor` is installed, the skills point to it for provider push gates, the general
  permission principle, evidence classes and syncer or Windows git problems.

## License

MIT. See `LICENSE`.
