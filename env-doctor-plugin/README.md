# env-doctor

## What it does

Diagnoses your local Claude Code and development environment, read-only. When an MCP
server will not load, a tool fails to spawn, login loops on a 401, a language server or
browser is missing, a hook never fires, WSL networking or PowerShell arguments misbehave,
or Syncthing gets in the way, it routes the symptom to one diagnostic branch, runs
inspection-only probes, classifies the failure and proposes one safe fix for you to apply.
It never changes your system and never prints secret values. A second skill covers the
authoring side: writing Windows scripts and Scheduled Tasks so those failures do not happen.

It is for anyone whose Claude Code tooling misbehaves on their own machine. It is not a
server-operations, deployment or CI tool.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install env-doctor@taqat-techno-plugins
```

On Claude Code 2.1.275 or later, one step also works:
`/plugin install env-doctor --marketplace taqat-techno/plugins`.

This plugin was called `claude-env-doctor` before 0.7.0; the marketplace migrates old installs.

## Requirements

| Requirement | Why | Check |
|---|---|---|
| Python 3.8 or later as `python3`, `python` or `py -3` | runs the SessionStart check | `python3 --version` |
| A POSIX shell for hook commands (Git Bash on Windows) | the hook launcher is POSIX sh | `sh --version` |

The command, skills and agent need nothing beyond Claude Code. The probes use whatever
tools are on the machine and report a missing tool as a finding.

## Commands

| Command | What it does |
|---|---|
| `/env-doctor:diagnose [symptom]` | Loads the `env-doctor-router` skill. With a free-text symptom (for example `MCP server not loading`) it goes straight to the matching branch; with no argument it runs a general read-only triage across all branches. There are no flags. |
| `/env-doctor:env-doctor [symptom]` | Deprecated alias for `/env-doctor:diagnose`, kept for one minor version. |

## Skills

| Skill | Use when |
|---|---|
| `env-doctor-router` (folder `skills/env-doctor/`) | the local environment is already broken: MCP, spawn/ENOENT, encoding, 401 login loops, LSP, browser, hooks, WSL, PowerShell, Syncthing, running-app config |
| `windows-script-and-task-authoring` | about to write a `.ps1`/`.cmd`/script for Windows, register a Scheduled Task, or compose a command across the Git Bash or WSL boundary |

`env-doctor-router` references (one per branch): `mcp-not-loading.md`, `windows-wsl.md`,
`login-auth.md`, `lsp-node-spawn.md`, `python-encoding.md`, `playwright-browser.md`,
`ide-remote-dev.md`, `doctor-command-ambiguity.md`, `syncthing.md`,
`windows-powershell.md`, `ide-mermaid-rendering.md`.
`windows-script-and-task-authoring` references: `scheduled-task-authoring.md`,
`shell-boundary-hazards.md`.

## Agents

| Agent | Tools | What it does |
|---|---|---|
| `env-probe-reporter` | `Read, Bash, Glob, Grep` | Runs a bounded read-only sweep (OS/shell/WSL, configured MCP servers, tool versions, PATH resolution, login state by shape only) and returns a structured ENVIRONMENT REPORT. Its prompt forbids writes, installs, service control and logins, and forbids revealing any character of a secret. Bash is not technically sandboxed: read-only is a prompt rule, so its commands do run on your machine. |

## Hooks

| Hook | Event | What it does | Can block? |
|---|---|---|---|
| `hooks/session_start_env_advisory.py` | `SessionStart` | Runs cheap read-only checks on the project and speaks only when one fails: a project `.mcp.json` that is invalid JSON, or that uses `${NAME}` without a default while `NAME` is unset (in the environment and in the `env` block of `.claude/settings*.json` and `~/.claude/settings.json`); or a project inside a Syncthing folder whose `node_modules`, `.venv` or `venv` is not in `.stignore`. The note goes to Claude as `additionalContext` and names variables, never values. A healthy project gets nothing. | No |

## Configuration

| Setting | Where | Values | Default |
|---|---|---|---|
| `session_checks` | plugin option (`/config`; reaches the hook as `CLAUDE_PLUGIN_OPTION_SESSION_CHECKS`) | `true`, `false` | `true` |
| `ENV_DOCTOR_HINT` | environment variable; `off` silences the SessionStart check | `off` | unset |

No per-project files.

## Platform support

| Platform | Status |
|---|---|
| Windows | Deepest coverage: PowerShell 5.1, Git Bash/MSYS, Scheduled Tasks, WSL boundary. The hook needs Git Bash; without it Claude Code runs hook commands in PowerShell, where the launcher does not parse, and the hook does nothing. |
| macOS, Linux | MCP, login, LSP/Node, browser, IDE remote-dev, Syncthing and Mermaid branches apply; the skill skips Windows-only branches and uses POSIX probes. |
| WSL | Supported, including Windows/WSL networking across the boundary. |

The `env-doctor-router` skill has a table of which branches apply on which OS.

## Data & privacy

- The SessionStart hook reads `.mcp.json`, `.claude/settings.json`,
  `.claude/settings.local.json`, `~/.claude/settings.json` and Syncthing's `.stfolder` /
  `.stignore` markers. It writes nothing, runs no subprocesses and makes no network calls.
  Its message names MCP servers, variable names and folder names only.
- Diagnosis runs read-only commands on your machine (version checks, config reads, port and
  process listings). Results stay in the session. Secrets are reported by name and shape
  only (for example "set, 40 chars, base64-like").
- The plugin sends nothing anywhere. A probe you approve that contacts a service (for
  example a connectivity check) talks to that service directly.

## Limitations

- It proposes fixes; it never applies them.
- The SessionStart check is deliberately small. It does not start MCP servers or test
  connectivity; run `/env-doctor:diagnose` for that.
- Hook event names, settings keys and manifest fields change between Claude Code releases.
  The skill checks them against the official documentation for your installed version
  instead of a list of its own.
- Related plugins are optional: if `git-safety`, `agent-safety-guards` or `docs-wiki` is
  installed, the skills point to them for staging discipline, test evidence, permission
  rules and Mermaid authoring.

## License

MIT. See `LICENSE`.
