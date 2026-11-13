# env-doctor

## What it does

Diagnoses your local Claude Code and development environment, read-only. When an MCP
server will not load, a tool fails to spawn, login loops on a 401, a language server or
browser is missing, a hook never fires, WSL networking or PowerShell arguments misbehave,
a local service is slow inside WSL, or Syncthing gets in the way, it routes the symptom to
one diagnostic branch, runs inspection-only probes (measured ones for performance),
classifies the failure and proposes one safe fix for you to apply. Diagnosis never changes
your system and never prints secret values.

Three more capabilities sit beside the doctor:

- **Cleaning** (`/env-doctor:clean`): the only part that deletes, behind its own gate. It
  inventories old databases, orphaned Odoo filestores, scratch folders, dead configs,
  caches and an oversized WSL disk image, protects a keep-list, shows a plan, and deletes
  only what you approve by plan id, dumping databases before it drops them.
- **Long jobs never block the session**: a skill and an advisory hook make test suites,
  installs and dumps that take more than ~3 minutes run in the background while work goes on.
- **Authoring**: writing Windows scripts and Scheduled Tasks so the usual failures do not happen.

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
| Python 3.8 or later as `python3`, `python` or `py -3` | runs the hooks and the cleanup planner | `python3 --version` |
| A POSIX shell for hook commands (Git Bash on Windows) | the hook launcher is POSIX sh | `sh --version` |

The command, skills and agent need nothing beyond Claude Code. The probes use whatever
tools are on the machine and report a missing tool as a finding. Cleaning uses `bash`,
`psql`, `pg_dump` and `pg_restore` where the databases live (inside WSL on Windows), and
the optional disk-image compaction needs an elevated PowerShell that you run yourself.

## Commands

| Command | What it does |
|---|---|
| `/env-doctor:diagnose [symptom]` | Loads the `env-doctor-router` skill. With a free-text symptom (for example `MCP server not loading`) it goes straight to the matching branch; with no argument it runs a general read-only triage across all branches. There are no flags. |
| `/env-doctor:clean [--scope db\|files\|docker\|wsl-disk\|all] [--apply <plan-id>]` | Loads `dev-env-cleanup`. With no argument: read-only inventory and a plan with sizes and reasons; nothing is deleted. `--apply <plan-id>` applies exactly the plan you approved, dry run first. |
| `/env-doctor:env-doctor [symptom]` | Deprecated alias for `/env-doctor:diagnose`, kept for one minor version. |

## Skills

| Skill | Use when |
|---|---|
| `env-doctor-router` | the local environment is already broken: MCP, spawn/ENOENT, encoding, 401 login loops, LSP, browser, hooks, WSL networking, a slow local service in WSL (`PoolError`, minutes-long first login, OOM, `0x8007000e`), PowerShell, Syncthing, running-app config |
| `dev-env-cleanup` | the disk or WSL is filling up, or after project work: old databases, orphaned filestores, scratch dirs, dead confs, caches, Docker, an `ext4.vhdx` that never shrank |
| `long-running-jobs` | about to run something that may take more than ~3 minutes (test suite, install/upgrade, migration, dump/restore), or tempted to wait, sleep or poll |
| `machine-mechanic` | an `[env-doctor mechanic]` note arrives while a local service runs (memory, CPU, disk or WSL pressure), or you want to turn the background watcher off or tune it |
| `windows-script-and-task-authoring` | about to write a `.ps1`/`.cmd`/script for Windows, register a Scheduled Task, or compose a command across the Git Bash or WSL boundary |

`env-doctor-router` references (one per branch): `mcp-not-loading.md`, `windows-wsl.md`,
`wsl-performance.md`, `login-auth.md`, `lsp-node-spawn.md`, `python-encoding.md`,
`playwright-browser.md`, `ide-remote-dev.md`, `doctor-command-ambiguity.md`, `syncthing.md`,
`windows-powershell.md`, `ide-mermaid-rendering.md`; read-only probe scripts
`scripts/wsl_perf_probe.sh` and `scripts/windows_perf_probe.ps1`.
`dev-env-cleanup` references: `safety-rules.md`, `odoo-local-contract.md`; scripts
`inventory.sh`, `host_probe.py`, `plan.py`, `apply_files.sh`, `apply_dbs.sh`, `idle_gate.sh`,
`compact-wsl.ps1`.
`windows-script-and-task-authoring` references: `scheduled-task-authoring.md`,
`shell-boundary-hazards.md`.

## Agents

| Agent | Tools | What it does |
|---|---|---|
| `env-probe-reporter` | `Read, Bash, Glob, Grep` | Runs a bounded read-only sweep (OS/shell/WSL, configured MCP servers, tool versions, PATH resolution, login state by shape only) and returns a structured ENVIRONMENT REPORT. Its prompt forbids writes, installs, service control and logins, and forbids revealing any character of a secret. Bash is not technically sandboxed: read-only is a prompt rule, so its commands do run on your machine. |

## Hooks

| Hook | Event | What it does | Can block? |
|---|---|---|---|
| `hooks/session_start_env_advisory.py` | `SessionStart` | Runs cheap read-only checks and speaks only when one fails: a project `.mcp.json` that is invalid JSON, or that uses `${NAME}` without a default while `NAME` is unset (in the environment and in the `env` block of `.claude/settings*.json` and `~/.claude/settings.json`); a project inside a Syncthing folder whose `node_modules`, `.venv` or `venv` is not in `.stignore`; and on Windows (via `hooks/host_pressure.py`) a system drive under 10% free, a running WSL distro whose `ext4.vhdx` is over 1.5x its used space, or a WSL version with a known crash. It never starts WSL. The note goes to Claude as `additionalContext` and names variables, never values. A healthy machine gets nothing. | No |
| `hooks/long_job_advisory.py` | `PreToolUse` (`Bash\|PowerShell`) | When a command looks like a long job (full or module-wide test run, install/upgrade with `--stop-after-init`, whole-tree `pytest`, label-less `manage.py test`, `test:e2e`, `pg_dump`/`pg_restore`) and would run in the foreground with a timeout above 3 minutes or none, reminds Claude to run it in the background and keep working. Also flags foreground sleep/poll loops and `pgrep -f`/`pkill -f`. Advisory only. | No |
| `hooks/mechanic_hook.py` + `hooks/mechanic.py` | `PostToolUse` (`asyncRewake`), `UserPromptSubmit` | The machine mechanic. When Claude starts a local service, starts one background watcher per machine that samples memory, CPU, free disk and WSL every ~45 s at below-normal priority, matches `data/mechanic_rules.json`, and wakes Claude with a finding marked either "you may fix what you started" or "ask the user". A finding that arrives while Claude is idle is added to your next message. It never changes anything and stops 30 minutes after the last activity. See the `machine-mechanic` skill. | No |

## Configuration

| Setting | Where | Values | Default |
|---|---|---|---|
| `session_checks` | plugin option (`/config`; reaches the hook as `CLAUDE_PLUGIN_OPTION_SESSION_CHECKS`) | `true`, `false` | `true` |
| `ENV_DOCTOR_HINT` | environment variable; `off` silences the SessionStart check | `off` | unset |
| `ENV_DOCTOR_HOST_CHECKS` | environment variable; `off` skips only the host-pressure part of the SessionStart check | `off` | unset |
| `long_job_advice` | plugin option (`CLAUDE_PLUGIN_OPTION_LONG_JOB_ADVICE`) | `true`, `false` | `true` |
| `ENV_DOCTOR_LONG_JOBS` | environment variable; `off` silences the long-job advisory | `off` | unset |
| `mechanic` | plugin option (`CLAUDE_PLUGIN_OPTION_MECHANIC`) | `true`, `false` | `true` |
| `ENV_DOCTOR_MECHANIC` | environment variable; `off` turns the mechanic off (the watcher exits at its next sample) | `off` | unset |
| `~/.config/env-doctor/keep.txt` | file inside the environment being cleaned; one glob per line (database names, paths, file names) that cleaning never offers | patterns | absent |

No per-project files. Cleaning writes plans to `~/.claude/env-doctor/plans/`, backups to
`~/env-doctor-backups/clean_<date>/` and a log to `~/.local/state/env-doctor/clean_<date>.log`
(the last two inside the environment being cleaned), and only after you approve a plan.

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
  `.stignore` markers; on Windows also the drive's free space, the WSL registry keys and
  disk-image sizes, and (only for running distros) `wsl.exe --list --running` and `df`
  inside the distro. It writes nothing and makes no network calls. Its message names MCP
  servers, variable names, folder and distro names only.
- The long-job hook reads the command text of Bash/PowerShell calls and writes nothing.
- The mechanic reads system memory and CPU counters, free disk space, the WSL VM's memory
  (`tasklist`), `%USERPROFILE%\.wslconfig` and, hourly while WSL runs, the disk-image size and
  `df` inside the distro. It writes only its own state (`$CLAUDE_PLUGIN_DATA/mechanic/`:
  findings, last sample, session markers) and changes nothing on the machine.
- Cleaning reads database names, sizes and activity, conf keys (never `db_password` unless
  you set `ENVDOC_USE_CONF_PASSWORD=1`, and then only into psql's environment) and file
  sizes. It deletes only an approved plan, after a dry run.
- Diagnosis runs read-only commands on your machine (version checks, config reads, port and
  process listings). Results stay in the session. Secrets are reported by name and shape
  only (for example "set, 40 chars, base64-like").
- The plugin sends nothing anywhere. A probe you approve that contacts a service (for
  example a connectivity check) talks to that service directly.

## Limitations

- Diagnosis proposes fixes; it never applies them. Cleaning applies only an approved plan
  and never runs `wsl --shutdown`, the compaction in run mode, `sudo` steps or Docker prunes
  for you.
- The inventory takes minutes on a machine with hundreds of databases (measured: ~3 min for
  ~700); it runs in the background.
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
