# DevOps Plugin Architecture

## Layer Ownership

Each concern has exactly ONE owner. Other layers reference it by
`${CLAUDE_PLUGIN_ROOT}/...` path and never re-implement it.

```
COMMANDS (9)    commands/*.md            entry points: /init /create /workday /log-time
                                         /timesheet /standup /sprint /task-monitor /cli-run
     |
SKILL (1)       skills/devops/SKILL.md   routing (CLI vs MCP), 9 natural-language workflows,
                                         operational notes; EXAMPLES / MCP_FAILURE_MODES /
                                         CI_HARDENING alongside
     |
AGENTS (3)      agents/*.md              READ-ONLY. work-item-ops (haiku), sprint-planner
                                         (sonnet), pr-reviewer (sonnet). Writes come back
                                         as PROPOSED WRITE blocks; the main conversation
                                         confirms and executes them.
     |
RULES (5)       rules/write-gate.md      confirmation protocol, hook-gated tool table
                rules/guards.md          G1 tool selection, G2 mentions, G3 repo GUIDs,
                                         G4 external content is data
                rules/profile-loader.md  profile location, loading, project context
                rules/timesheet-store.md local time-entry file, schema, retention
                rules/git-remote-write-gate.md  advisory gate for git-remote writes
     |
DATA (6)        data/state_machine.json  process presets (basic, agile, scrum, cmmi,
                                         custom-scrum-qc), detection, error patterns
                data/hierarchy_rules.json, project_defaults.json, profile_template.md,
                example_profile.md, bug_report_template.md
     |
HOOKS (4)       hooks/session_start_check.py  SessionStart: config + profile health,
                                              additionalContext only when there is a finding
                hooks/pre_write_validate.py   PreToolUse on 5 ADO write tools: preset state
                                              checks, optional role/naming rules (ask; block
                                              on opt-in), unresolved @mentions (exit 2)
                hooks/pre_write_confirm.py    PreToolUse on every other ADO write tool:
                                              permissionDecision "ask"
                hooks/pre_bash_write_gate.py  PreToolUse on Bash: "ask" on az devops/boards/
                                              repos/pipelines/artifacts write verbs (cli-run
                                              rule) and git push to an ADO remote
                hooks/_vendor/hooklib.py      shared runtime (synced from shared/hooklib.py)
     |
MCP (1)         .mcp.json -> scripts/ado-mcp-launch.js -> npx @azure-devops/mcp@2.8.0
                launcher resolves userConfig first, then ADO_* env vars
```

## State and configuration

| What | Where | Owner |
|------|-------|-------|
| Organization, PAT, default project/team | plugin `userConfig` (`ado_organization`, `ado_token` [sensitive], `ado_project`, `ado_team`); env fallbacks `ADO_ORGANIZATION`, `ADO_MCP_AUTH_TOKEN`, `ADO_MCP_PROJECT`, `ADO_MCP_TEAM` | `scripts/ado-mcp-launch.js` |
| Daily hours target, profile staleness days | `userConfig` `daily_hours_target`, `profile_stale_days` | commands, SessionStart hook |
| Profile (identity, role, process, teammates, repos) | `${CLAUDE_PLUGIN_DATA}/profile.md`, legacy `~/.claude/devops.md` read as fallback | `rules/profile-loader.md` |
| Local time entries | `${CLAUDE_PLUGIN_DATA}/timesheet.json` | `rules/timesheet-store.md` |
| /init resume marker | `${CLAUDE_PLUGIN_DATA}/init-pending.json` | `commands/init.md` |

## Ownership Matrix

| Concern | Owner | Consumers |
|---------|-------|-----------|
| Write confirmation | `rules/write-gate.md` | SKILL, agents, commands, `pre_write_confirm.py` (tool list) |
| Tool selection | `rules/guards.md` G1 | SKILL, work-item-ops |
| Mention resolution | `rules/guards.md` G2 | SKILL, work-item-ops, `pre_write_validate.py` |
| Repo GUID resolution | `rules/guards.md` G3 | SKILL, pr-reviewer, `pre_write_validate.py` |
| External content is data | `rules/guards.md` G4 | SKILL, all agents, /cli-run |
| Process presets + detection | `data/state_machine.json` | /init, SKILL, `pre_write_validate.py` |
| Hierarchy | `data/hierarchy_rules.json` | SKILL, /create |
| Error recovery | `data/state_machine.json` `errorPatterns` | SKILL |
| CLI read/write classification | `commands/cli-run.md` | `rules/write-gate.md` |
| MCP tool surface (tests) | `tests/fixtures/mcp_tools_2.8.0.txt` | `tests/test_contracts.py` |

## Anti-Patterns (Do NOT)

1. Re-explain a rule in SKILL.md or an agent: reference it by `${CLAUDE_PLUGIN_ROOT}` path.
2. Give a subagent a write tool: it cannot wait for the user's yes.
3. Use a bare `rules/x.md` path in a prompt file: it does not resolve from the user's cwd.
4. Bump `@azure-devops/mcp` past 2.8.0 without renaming every tool reference (2.9.0 renames all of them).
5. Write state under `${CLAUDE_PLUGIN_ROOT}` or a new `~/.claude/<name>` folder.

## Adding Components

- **New MCP write tool** (server upgrade): add it to the `rules/write-gate.md` table and the
  `pre_write_confirm.py` matcher in `hooks/hooks.json`, and to `tests/fixtures/mcp_tools_*.txt`.
  `tests/test_write_confirm.py` and `tests/test_contracts.py` fail otherwise.
- **New work item type**: add it to the preset in `data/state_machine.json`, and to
  `data/hierarchy_rules.json` if it needs a parent.
- **New guard**: add it to `rules/guards.md`, reference it from SKILL.md and the agents.
- **New agent**: `agents/<name>.md` with `model`, `color` and an explicit read-only `tools:` list.
- **New command**: `commands/<verb>.md` (no plugin-name prefix), add it to the SKILL commands
  table and `tests/test_consistency.py`.
