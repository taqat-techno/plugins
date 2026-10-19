# DevOps Plugin for Claude Code

A comprehensive Azure DevOps integration plugin for Claude Code, enabling natural language interaction with your DevOps workflows through **HYBRID** CLI + MCP architecture.

**Version**: 6.5.0 | **Mode**: Hybrid (CLI + MCP)

---

## Process Presets

Azure DevOps projects run different processes, so the plugin does not assume one. The
process model lives in `data/state_machine.json` `processPresets`, and your profile's
`process` field picks the active preset. `/init` detects it (Step 3.5 in
`commands/init.md`): it reads the project's work item types with `wit_list_backlogs` and
`wit_get_work_item_type`, maps them to a preset (`presetDetection`), and asks you to
confirm. If detection fails, it asks you, and falls back to `agile`.

| Preset | Source | Work item types | Role / naming rules |
|--------|--------|-----------------|---------------------|
| `basic` | Microsoft default | Epic, Issue, Task (To Do / Doing / Done) | none |
| `agile` | Microsoft default | Epic, Feature, User Story, Task, Bug, Issue | none |
| `scrum` | Microsoft default | Epic, Feature, Product Backlog Item, Bug, Task, Impediment | none |
| `cmmi` | Microsoft default | Epic, Feature, Requirement, Task, Bug, Change Request, Issue, Risk, Review | none |
| `custom-scrum-qc` | Custom, opt-in | Scrum + Enhancement, In Progress / Ready For QC / Return states on PBIs and Bugs | QA-only Bug creation, PM/Lead-only Close/Remove, required Task prefixes (`[Dev]`, `[Front]`, `[QC Bug Fixing]`, `[QC Test Execution]`, `[IMP]`, `[Dev-Internal-fix]`) |

The stock presets encode Microsoft's documented default states. Inherited processes allow
a transition between any two states of a type, so these presets list the states and the
usual forward flow (`happyPath`). If your project customized its process, the hook asks
before any state the preset does not define.

### How the write hook applies them

`hooks/pre_write_validate.py` reads the active preset on every work item create/update:

| Situation | Result |
|-----------|--------|
| Stock preset, no profile, a profile without `process`, or an unknown preset | No role or naming rules. You get reminders only |
| A role or naming rule is broken (only when the preset or profile defines one) | `permissionDecision: "ask"` with the reason. You decide |
| Same, with `enforcement: "block"` in the profile | Hard block (exit 2) |
| Same, with `enforcement: "advise"` | Reminder only |
| Target state not defined by the active preset | Always `ask`, never a hard block |
| Comment with unresolved `@mentions` | Hard block (correctness guard, any process) |

### Profile fields (`~/.claude/devops.md` frontmatter)

```yaml
process: "scrum"          # basic | agile | scrum | cmmi | custom-scrum-qc
enforcement: "ask"        # ask (default) | block | advise
# Optional overrides. Each one replaces the preset's rules. Write it as inline JSON, or as off:
roleRules: {"restrictedStates": {"Closed": {"allowedRoles": ["pm", "lead"]}}, "createRestrictions": {"Bug": {"deniedRoles": ["developer"]}}}
taskNaming: {"appliesTo": ["Task"], "prefixes": ["[BE]", "[FE]"]}
```

To keep the earlier hard-enforced customized-Scrum behavior, set
`process: "custom-scrum-qc"` and `enforcement: "block"`. Profiles created before
process presets have no `process` field, so they get generic rules until you run
`/init profile --refresh` or add the field yourself.

### Other rules

| Rule | Description |
|------|-------------|
| **Hierarchy** | Epic > Feature > requirement (User Story / PBI / Requirement / Issue) > Task or Bug (parent required), `data/hierarchy_rules.json` |
| **Auto-Sprint** | Tasks are auto-assigned to the current sprint by date |
| **Required fields** | Per-transition `requiredFields` in the preset (e.g. hours on Task Done in `custom-scrum-qc`). Azure DevOps errors are mapped in `errorPatterns` |

---

## Quick Start

```
/init setup
```

This installs both CLI and MCP, configures authentication, and validates connectivity.

Then generate your user profile:
```
/init profile
```

This creates `~/.claude/devops.md` with your identity, role, team members, and project defaults.

---

## Commands Reference (9 commands)

### Daily Use

| Command | Description |
|---------|-------------|
| `/workday` | Daily dashboard: tasks, time log, compliance |
| `/log-time` | Log hours: `/log-time 3h #1828 "description"` |
| `/standup` | Generate daily standup notes |
| `/create` | Create work item with auto-type detection |

### Sprint & Monitoring

| Command | Description |
|---------|-------------|
| `/sprint` | Sprint progress. Use `--full` for comprehensive report |
| `/task-monitor` | Periodic alerts. Use with `/loop 15m /task-monitor` |

### Setup & Admin

| Command | Description |
|---------|-------------|
| `/init` | Setup, status, profile generation |
| `/timesheet` | Time views + time-off management |
| `/cli-run` | Execute raw CLI commands |

### Skill-Handled (Natural Language)

| Say this | What happens |
|----------|-------------|
| "mark #1234 as done" | Updates work item with pre-flight validation |
| "comment on #1234 @teammate" | Adds comment with validated @mentions |
| "switch to billing service" | Changes project context |
| "any failing builds?" | Shows pipeline status |
| "create PR from feature to main" | Creates pull request |
| "set up CI/CD" | Generates GitHub Actions workflows |

---

## User Profile System

The plugin stores a persistent user profile at `~/.claude/devops.md`.

| Section | Data |
|---------|------|
| **Identity** | Display name, email, Azure DevOps GUID |
| **Process** | Active process preset (`process`) and optional `enforcement` / rule overrides |
| **Role** | Developer, QA/QC, PM/Lead (used only by presets with role rules) |
| **Default Project** | Auto-selected for all commands |
| **Team Members** | Names, GUIDs, and aliases for fast @mention resolution |
| **Task Templates** | Role-specific prefixes from Azure DevOps |
| **State Permissions** | Which transitions the user's role can perform (custom presets only) |

Profile generation workflow is in `commands/init.md`.

---

## Role-Based State Transitions

Role-based transitions exist only in presets that define them. Of the shipped presets,
only `custom-scrum-qc` does (`processPresets["custom-scrum-qc"].rolePermissions`). Its
matrix: developers start and complete work, QA/QC verifies and initiates Return (a
comment is required), and PM/Lead approves, closes and removes. Under a stock preset,
your role does not restrict transitions.

---

## Work Item Hierarchy

```
Epic
  > Feature
      > User Story / PBI
          > Task
          > Bug          (sibling of Task)
          > Enhancement  (sibling of Task)
```

Hierarchy rules are defined in `data/hierarchy_rules.json`.

---

## Plugin Structure

```
devops-plugin/
+-- .claude-plugin/
|   +-- plugin.json                    # Plugin metadata (v6.0.0)
+-- commands/                          # 9 slash commands
|   +-- init.md, create.md, workday.md, log-time.md,
|   +-- timesheet.md, standup.md, sprint.md,
|   +-- task-monitor.md, cli-run.md
+-- data/                              # Source of truth (5 files)
|   +-- state_machine.json             # Process presets, detection, error patterns
|   +-- hierarchy_rules.json           # Parent-child validation
|   +-- project_defaults.json          # Project aliases, work tracking config
|   +-- profile_template.md            # DevOps.md template
|   +-- bug_report_template.md         # QA bug report format
+-- devops/                            # Core skill (3 files)
|   +-- SKILL.md                       # Main skill definition (9 workflows + WIQL appendix)
|   +-- EXAMPLES.md                    # Usage examples
|   +-- MCP_FAILURE_MODES.md           # MCP server recovery + CLI fallback matrix
+-- rules/                             # Behavioral rules (3 files)
|   +-- write-gate.md                  # Confirmation protocol for all writes
|   +-- guards.md                      # Tool selection, mentions, repo resolution
|   +-- profile-loader.md             # Profile loading + project context
+-- hooks/                             # Lifecycle hooks (3 files)
|   +-- hooks.json                     # Hook configuration
|   +-- session_start_check.py         # Lightweight profile/data health check (advisory)
|   +-- pre_write_validate.py          # Azure DevOps work-item write validation (role-based)
|                                      #   (no git-push gate — git pushes are unrestricted)
+-- agents/                            # Specialized subagents (3)
|   +-- work-item-ops.md              # Haiku — CRUD, queries
|   +-- sprint-planner.md             # Sonnet — reports, capacity
|   +-- pr-reviewer.md                # Sonnet — PR review, diffs
+-- tests/                             # Test suite (4 files, 260+ tests)
|   +-- test_state_machine.py          # State machine schema validation
|   +-- test_consistency.py            # Cross-file reference checks
|   +-- test_integration_flows.py      # End-to-end flow contracts
|   +-- consistency_check.py           # Cross-file drift detection
+-- .mcp.json                          # MCP server declaration
+-- ARCHITECTURE.md                    # Layer ownership + anti-patterns
+-- CHANGELOG.md, LICENSE, README.md
```

**Totals**: 9 commands | 5 data files | 4 rule files | 3 agents | 7 hooks | 4 test files | ~40 files

---

## Testing

Run the full test suite:

```bash
cd devops-plugin
pytest tests/ -v
```

Run individual test groups:

```bash
# State machine schema validation (states, transitions, roles, required fields)
pytest tests/test_state_machine.py -v

# Cross-file consistency (references, naming, deleted files)
pytest tests/test_consistency.py -v

# Integration flows (write gate wiring, guard ownership, hook targeting)
pytest tests/test_integration_flows.py -v

# Script unit tests (sprint reports, standup, release notes formatting)
pytest tests/test_scripts.py -v
```

Tests validate plugin structure and contracts — they do **not** require Azure DevOps API access.

---

## Safety hooks

The plugin layers conservative, false-positive-averse safety hooks (see `ARCHITECTURE.md`
for layer ownership):

| Hook | Event | Behavior |
|------|-------|----------|
| `session_start_check.py` | SessionStart | Advisory profile / data-file health check; always exits 0, never blocks. |
| `pre_write_validate.py` | PreToolUse (5 work-item/PR writes: `wit_create_work_item`, `wit_update_work_item`, `wit_add_work_item_comment`, `wit_work_items_link`, `repo_create_pull_request`) | Injects state/hierarchy context; asks on process-preset role/naming violations and on states the preset does not define (hard-blocks them only with `enforcement: block`); hard-blocks unresolved @mentions |
| `pre_write_confirm.py` | PreToolUse (every other ADO MCP write tool - pipelines, PR complete/merge/abandon/vote/reviewers/threads, branches, batch/child/link work-item writes, wiki, iterations/capacity, test plans) | Returns `permissionDecision: "ask"` with the action and its target, so **you** confirm each write even if the model skipped its confirmation summary. Fails open. The gated tool set is listed in `rules/write-gate.md` ("Hook-Enforced Confirmation"). |

There is **no git-push gate** — git pushes (including force-push) are **not** gated by this plugin.
`rules/git-remote-write-gate.md` remains as advisory guidance only (permission-first +
identity-correctness) and is not enforced by any hook; the assistant applies it judgmentally
(and your global `CLAUDE.md` permission/auto-switch policy still governs pushes).

Release-safety review guidance — deployed-SHA-to-environment reconciliation and pre-promotion
secret-key diffing — lives in `devops/CI_HARDENING.md` (items 6 and 6a).

---

## Support

- **Author**: TaqaTechno
- **License**: MIT — see [LICENSE](LICENSE)
