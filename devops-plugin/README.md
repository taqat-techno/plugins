# devops — Azure DevOps for Claude Code

## What it does

Lets you work with Azure DevOps in plain language: create and update work items (with
state pre-flight and @mention resolution), review and open pull requests, produce sprint
reports and standup notes, log time, and run `az devops` CLI commands. It talks to Azure
DevOps through the official `@azure-devops/mcp` server (pinned at 2.8.0) and the Azure CLI,
and Claude asks for your confirmation before every write. Hooks back that up: they ask
you directly before 26 MCP write tools, `az devops|boards|repos|pipelines` CLI writes and
`git push` to an Azure DevOps remote; the five most-used work-item/PR write tools are
validated instead and ask only on a rule violation.

It is for developers, testers and project leads whose team tracks work in Azure DevOps
Boards and Repos. It is Azure DevOps-only.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install devops@taqat-techno-plugins
```

When the plugin is enabled, Claude Code asks for its options (organization and Personal
Access Token among them). You can change them later in `/config`. Then run `/init`.

## Requirements

| Requirement | Used for | Check |
|-------------|----------|-------|
| Node.js with `npx` (current LTS, 20 or later) | Runs the MCP server launcher and `@azure-devops/mcp@2.8.0` (downloaded from npm on first start) | `node --version`, `npx --version` |
| Python 3.8+ as `python3`, `python` or `py -3` | The three hooks | `python3 --version` |
| An Azure DevOps organization and a Personal Access Token | Every MCP call | `/init status` |
| Azure CLI 2.30+ with the `azure-devops` extension (optional) | `/cli-run`, team members during `/init profile`, CLI fallbacks | `az --version`, `az extension show --name azure-devops` |

**PAT scopes:** grant the narrowest set you need, typically Work Items (Read & Write),
Code (Read & Write) and Build (Read). Add Build (Read & Execute) only to run pipelines.
Use a short expiry.

## Commands

| Command | What it does |
|---------|--------------|
| `/devops:init` | Setup: checks configuration, the MCP server and the CLI, detects the project's process, generates your profile. `/init status`, `/init profile`, `/init profile --refresh` |
| `/devops:create` | Create a work item (task, bug, enhancement, user story) with the parent and sprint resolved. Asks for a title when run bare |
| `/devops:workday` | Daily dashboard: your active work items and today's hours against the target |
| `/devops:log-time` | Log hours against a work item (updates Completed Work after confirmation) or a category (local timesheet) |
| `/devops:timesheet` | Local time views (`--week`, `--month`, `--date`) and time off (`--off`, `--off-list`, `--off-remove`) |
| `/devops:standup` | Yesterday / Today / Blockers notes from your work items. `--copy` copies to the clipboard |
| `/devops:sprint` | Sprint progress report; `--full` adds builds, tests, PRs and security alerts |
| `/devops:task-monitor` | Reports new assignments and state changes since the last run; use with `/loop 15m /devops:task-monitor` |
| `/devops:cli-run` | Run an `az devops` / `boards` / `repos` / `pipelines` / `artifacts` command. Reads run directly, anything else needs your yes |

## Skills

| Skill | Loads when |
|-------|-----------|
| `devops` (model-invoked only) | You work with Azure DevOps work items, PRs, sprints, pipelines, wiki or the `az devops` CLI, or an Azure DevOps call fails (TF401320, MCP auth, unknown tool). Routes between MCP and CLI and carries the workflows behind the commands |

## Agents

All three are read-only. When a task needs a write, they return a `PROPOSED WRITE`
(tool, arguments, summary) and the main conversation asks you before making the call.

| Agent | Model | Tools |
|-------|-------|-------|
| `work-item-ops` | haiku | Read, work-item reads, identity lookup |
| `sprint-planner` | sonnet | Read, Glob, Grep, work-item / iteration / capacity reads, search |
| `pr-reviewer` | sonnet | Read, Bash (local read-only git for diffs), Glob, Grep, repo / branch / PR / thread reads, identity lookup |

## Hooks

| Hook | Event | What it does | Can block? |
|------|-------|--------------|-----------|
| `session_start_check.py` | SessionStart (`startup`) | Reports missing organization/token, a missing, stale or legacy-location profile, and broken data files, as context for Claude. Prints nothing when all is well | No |
| `pre_write_validate.py` | PreToolUse: `wit_create_work_item`, `wit_update_work_item`, `wit_add_work_item_comment`, `wit_work_items_link`, `repo_create_pull_request` | Hierarchy and state reminders; asks (`permissionDecision: "ask"`) when a target state is not in your process preset or a preset/profile role or naming rule is broken; flags a repository name passed where a GUID is needed | Yes, two cases: a comment with an unresolved `@mention` (a plain `@name` notifies nobody), and rule violations when your profile sets `enforcement: block` |
| `pre_write_confirm.py` | PreToolUse: the 26 other write tools (pipeline runs, artifact downloads, PR complete/vote/reviewers/threads, branches, batch and link work-item writes, wiki, iterations and capacity, test plans; list in `rules/write-gate.md`) | Asks you to confirm, naming the action and its target | It asks; you decide |
| `pre_bash_write_gate.py` | PreToolUse: `Bash` | Asks you to confirm an `az devops\|boards\|repos\|pipelines\|artifacts` command whose verb is not a read (`list`, `show`, `query`, `list-member`, `status`, GET `invoke`; same rule as `/cli-run`) and a `git push` to an Azure DevOps remote. Silent for every other command. `DEVOPS_BASH_WRITE_GATE=off` disables it | It asks; you decide |

All hooks fail open: an internal error or a missing Python lets the call through to the
normal Claude Code permission flow.

## Configuration

**Plugin options** (`/config`, or the dialog shown when the plugin is enabled):

| Option | Meaning | Fallback environment variable |
|--------|---------|-------------------------------|
| `ado_organization` | Organization name (e.g. `contoso` for `https://dev.azure.com/contoso`) | `ADO_ORGANIZATION` |
| `ado_token` | Personal Access Token. Sensitive: kept in the OS credential store, never in `settings.json` | `ADO_MCP_AUTH_TOKEN` |
| `ado_project` | Default project, so the server never stops to ask which project | `ADO_MCP_PROJECT` |
| `ado_team` | Default team | `ADO_MCP_TEAM` |
| `daily_hours_target` | Hours per working day for `/workday` and `/timesheet` (default 6) | — |
| `profile_stale_days` | Days before the SessionStart check suggests `/init profile --refresh` (default 14) | — |

How the fallback works: `.mcp.json` cannot say "use this option, else that variable", so it
starts `scripts/ado-mcp-launch.js`, which takes each value from the plugin option when it is
set and from the environment variable otherwise, then runs `npx -y @azure-devops/mcp@2.8.0
<org> --authentication envvar`. If neither is set the server does not start and `/mcp`
shows which value is missing. Existing setups that use only the environment variables keep
working unchanged.

Other environment variables: `AZURE_DEVOPS_EXT_PAT` (the Azure CLI's own PAT variable).

**Process presets.** Your profile's `process` field picks a preset in
`data/state_machine.json`; `/init` detects it from the project's work item types and asks
you to confirm.

| Preset | Work item types | Role / naming rules |
|--------|-----------------|---------------------|
| `basic` | Epic, Issue, Task | none |
| `agile` (default) | Epic, Feature, User Story, Task, Bug, Issue | none |
| `scrum` | Epic, Feature, Product Backlog Item, Bug, Task, Impediment | none |
| `cmmi` | Epic, Feature, Requirement, Task, Bug, Change Request, Issue, Risk, Review | none |
| `custom-scrum-qc` (opt-in) | Scrum + Enhancement, In Progress / Ready For QC / Return states | QA-only Bug creation, PM/Lead-only Close/Remove, required Task prefixes |

Profile fields that change hook behaviour:

```yaml
process: "scrum"          # basic | agile | scrum | cmmi | custom-scrum-qc
enforcement: "ask"        # ask (default) | block | advise
roleRules: off            # or inline JSON replacing the preset's role rules
taskNaming: off           # or inline JSON, e.g. {"appliesTo": ["Task"], "prefixes": ["[BE]", "[FE]"]}
```

**Per-project files:** none.

## Platform support

| Platform | Status |
|----------|--------|
| Windows | Supported. Hooks run through Git Bash (`py -3` fallback); `/init` shows PowerShell commands for the environment-variable route; `--copy` uses `clip` |
| macOS | Supported (`python3`, `pbcopy`) |
| Linux | Supported (`python3`; `wl-copy` or `xclip` for `--copy`) |
| WSL | Works inside WSL with Node and Python installed there. The Windows registry advice in `/init` does not apply; use the plugin options or your shell profile |

## Data & privacy

| Data | Where | Leaves the machine? |
|------|-------|---------------------|
| PAT | OS credential store (plugin option) or your environment | Sent only to `dev.azure.com` by the MCP server and the Azure CLI |
| Organization, project, team, hours target | `settings.json` `pluginConfigs` | No |
| Profile: your name, e-mail, identity GUID, role, process, and **your teammates' display names, e-mail addresses and GUIDs**, project and repository names | `${CLAUDE_PLUGIN_DATA}/profile.md` (older versions: `~/.claude/devops.md`, still read as a fallback) | No. `/init profile` can store teammates without e-mail |
| Local time entries | `${CLAUDE_PLUGIN_DATA}/timesheet.json` | No |

The plugin data directory survives updates and is deleted when you uninstall the plugin.
Work item, PR, wiki and build content that Claude reads is shown in your session and sent
to the model like any other tool output. The plugin treats that content as data: an
instruction written inside a work item or PR is never followed without asking you
(`rules/guards.md` Guard 4). `npx` downloads `@azure-devops/mcp@2.8.0` from the npm
registry on first start. Nothing is sent anywhere else.

## Limitations

- Azure DevOps only (Services; Server/TFS is untested).
- Pinned to `@azure-devops/mcp` 2.8.0 on purpose: 2.9.0 renames every tool and would break
  the hooks, agents and rules. The pin covers the package version, not an integrity hash.
- The server has no team-members or "who am I" tool; `/init profile` uses the Azure CLI or
  asks for your sign-in e-mail.
- Presets encode Microsoft's default processes. A customized inherited process may define
  states the preset does not; the hook then asks instead of assuming.
- Raw `/cli-run` commands do not pass through the PreToolUse hooks; the command classifies
  them by verb and asks before any write.
- Evals exist under `evals/` but no trigger-rate result has been recorded yet.

## License

MIT (`LICENSE`). `@azure-devops/mcp` (Microsoft, MIT) is fetched at runtime by `npx` and is
not bundled. The Azure CLI is installed separately under its own licence.

Development notes: `ARCHITECTURE.md` (layer ownership), `CHANGELOG.md`. Tests run offline:
`python -m pytest -q -p no:cacheprovider` from this directory.
