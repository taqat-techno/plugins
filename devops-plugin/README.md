# DevOps Plugin for Claude Code

A comprehensive Azure DevOps integration plugin for Claude Code, enabling natural language interaction with your DevOps workflows through **HYBRID** CLI + MCP architecture.

**Version**: 6.0.0 | **Mode**: Hybrid (CLI + MCP)

---

## Business Rules

The plugin enforces mandatory business rules for work item management. All rules are defined in `data/state_machine.json`.

### Quick Reference

| Rule | Description |
|------|-------------|
| **Hierarchy** | Epic > Feature > User Story/PBI > Task \| Bug \| Enhancement (parent required) |
| **User Story Format** | How? > What? > Why? sequence |
| **State Transitions** | Role-based permissions; PBI must pass through "Ready for QC" before "Done" |
| **Task Prefixes** | Fetched from Azure DevOps project settings (e.g., `[Dev]`, `[Front]`, `[IMP]`, `[QC Bug Fixing]`, `[QC Test Execution]`) |
| **Auto-Sprint** | Tasks auto-assigned to current sprint by date |
| **Task Completion** | Requires Original Estimate + Completed Hours |
| **Bug Completion** | Requires Completed Work + Resolved Reason |
| **Bug Creation** | QA/QC roles only; developers create `[Dev-Internal-fix]` Tasks instead |
| **State Permissions** | Role-based transition matrix (Developer, QA/QC, PM/Lead) |

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
| "comment on #1234 @mahmoud" | Adds comment with validated @mentions |
| "switch to relief center" | Changes project context |
| "any failing builds?" | Shows pipeline status |
| "create PR from feature to main" | Creates pull request |
| "set up CI/CD" | Generates GitHub Actions workflows |

---

## User Profile System

The plugin stores a persistent user profile at `~/.claude/devops.md`.

| Section | Data |
|---------|------|
| **Identity** | Display name, email, Azure DevOps GUID |
| **Role** | Developer, QA/QC, PM/Lead (controls permissions) |
| **Default Project** | Auto-selected for all commands |
| **Team Members** | Names, GUIDs, and aliases for fast @mention resolution |
| **Task Templates** | Role-specific prefixes from Azure DevOps |
| **State Permissions** | Which transitions the user's role can perform |

Profile generation workflow is in `commands/init.md`.

---

## Role-Based State Transitions

State transitions are controlled by role. The complete permission matrix is defined in `data/state_machine.json`.

### Work Item States

| Type | States |
|------|--------|
| **Task** | To Do > In Progress > Done > Closed > Removed |
| **Bug** | New > Approved > In Progress > Resolved > Return > Done > Closed > Removed |
| **PBI** | New > Approved > Committed > In Progress > Ready For QC > Return > Done > Removed |
| **User Story** | New > Committed > Done |
| **Enhancement** | New > Committed > Return > Done > Closed |

### Permission Matrix

| Action | Developer | QA/QC | PM/Lead |
|--------|-----------|-------|---------|
| Start work | Yes | Yes | Yes |
| Complete work | Yes | Yes | Yes |
| Initiate Return | - | Yes | Yes |
| Close / Remove | - | - | Yes |
| Approve | - | - | Yes |
| Resolve Bug | Yes | - | - |

Return transitions require a mandatory comment.

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
|   +-- state_machine.json             # States, permissions, business rules, error patterns
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
+-- hooks/                             # Lifecycle hooks (6 files)
|   +-- hooks.json                     # Hook configuration
|   +-- session-start.sh               # Profile check + staleness
|   +-- pre-write-validate.sh          # State/hierarchy/mention validation
|   +-- pre-bash-check.sh, post-bash-suggest.sh, error-recovery.sh
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

**Totals**: 9 commands | 5 data files | 3 rule files | 3 agents | 6 hooks | 4 test files | ~40 files

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

## Support

- **Author**: TaqaTechno
- **License**: MIT — see [LICENSE](LICENSE)
