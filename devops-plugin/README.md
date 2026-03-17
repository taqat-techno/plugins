# DevOps Plugin for Claude Code

A comprehensive Azure DevOps integration plugin for Claude Code, enabling natural language interaction with your DevOps workflows through **HYBRID** CLI + MCP architecture.

**Version**: 4.2.0 | **Organization**: YOUR-ORG | **Mode**: Hybrid (CLI + MCP)

---

## YOUR-ORG Business Rules

The plugin enforces mandatory business rules for work item management. Full documentation: `rules/business_rules.md`

### Quick Reference

| Rule | Description |
|------|-------------|
| **Hierarchy** | Epic > Feature > User Story/PBI > Task \| Bug \| Enhancement (parent required) |
| **User Story Format** | How? > What? > Why? sequence |
| **State Transitions** | Role-based permissions; must pass through "Ready for QC" before "Done" |
| **Task Prefixes** | Fetched from Azure DevOps project settings (e.g., `[Dev]`, `[Front]`, `[IMP]`, `[QC Bug Fixing]`, `[QC Test Execution]`) |
| **Auto-Sprint** | Tasks auto-assigned to current sprint by date |
| **Task Completion** | Requires Original Estimate + Completed Hours |
| **Bug Completion** | Requires Completed Work |
| **Bug Creation** | QA/QC roles only; developers create `[Dev-Internal-fix]` Tasks instead |
| **State Permissions** | Role-based transition matrix (Developer, QA/QC, PM/Lead) |

See `rules/business_rules.md` for complete documentation.

---

## Features

### Core Features
- **Work Item Management** - Create, update, query, and link work items
- **Pull Request Workflows** - Create, review, comment, and merge PRs
- **Pipeline Operations** - Run, monitor, and debug builds
- **Sprint Management** - Track progress, generate reports, prepare standups
- **Repository Access** - Browse code, commits, branches
- **Wiki Documentation** - Read, create, and update wiki pages
- **Code Search** - Search across repositories and work items
- **Test Plans** - Manage test plans, cases, and results
- **Security Alerts** - Monitor and analyze security vulnerabilities

### v4.2 - Role-Based State Transition Permissions
- **Real states from Azure DevOps** fetched via REST API (TaqaTechno Scrum process)
- **Complete state definitions** for all work item types (Task, Bug, PBI, User Story, Enhancement)
- **Role-based permission matrix** controlling which roles can perform which transitions
- **Universal rules**: Only PM can Close/Remove, QA initiates Returns, developers do the work
- **Return loop handling** with mandatory comments
- **`data/state_permissions.json`** - Complete role-to-permission lookup

### v4.1 - User Profile System
- **`DevOps.md` profile** (`~/.claude/devops.md`) - Persistent user identity, role, team, projects
- **`/init profile`** - Generate profile from Azure DevOps with one command
- **Profile-aware shortcuts** - "assign to me", `@ahmed`, team member resolution by alias
- **Task templates from Azure DevOps** - Prefixes fetched from project settings API, not hardcoded
- **Cache-first @mention resolution** - Resolves from profile before calling API
- **Bug Creation SOP** - Role-based gate enforcing QA-only bug creation

### v4.0 - Command Consolidation (24 > 9 commands)
- **9 commands** instead of 24 - streamlined, easier to remember
- **`/create`** - Unified work item creation with auto-type detection
- **`/init`** - Renamed from `/devops` for cleaner naming
- **6 skill-handled workflows** - Update items, add comments, switch projects, check builds, create PRs, set up CI/CD via natural language
- **Enhanced commands** - `/workday` absorbs sync commands, `/timesheet` absorbs time-off, `/sprint` absorbs full report, `/cli-run` absorbs pipeline vars and extensions

### Previous Versions
- **v3.1** - Task Monitor with `/loop` support for periodic new assignment alerts
- **v3.0** - Work Tracking System (workday dashboard, time logging, persistent cache)
- **v2.0** - Hybrid CLI + MCP mode, automated CLI setup, predefined memories, business rules
- **v1.3** - Required field validation, state transition rules, QC checkpoint, @mention processing
- **v1.1** - TODO sync, work item hierarchy enforcement

---

## Quick Start

```
/init setup
```

This installs both CLI and MCP:
1. Detects your platform
2. Installs Azure CLI + DevOps extension
3. Configures MCP server
4. Sets up authentication
5. Validates both connections

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
| `/workday` | Daily dashboard: tasks, time log, compliance. Flags: `--sync`, `--tasks`, `--todo`, `--quick` |
| `/log-time` | Log hours: `/log-time 3h #1828 "description"` |
| `/standup` | Generate daily standup notes |
| `/create` | Create work item: `/create --task`, `/create --bug`, `/create --story`, `/create --enhancement` |

### Sprint & Monitoring

| Command | Description |
|---------|-------------|
| `/sprint` | Sprint progress. Use `--full` for comprehensive hybrid report |
| `/task-monitor` | Periodic new assignment alerts. Use with `/loop 15m /task-monitor` |

### Setup & Admin

| Command | Description |
|---------|-------------|
| `/init` | Setup, status, upgrade, profile. Sub: `/init setup`, `/init status`, `/init profile` |
| `/timesheet` | Time views + time-off. Flags: `--week`, `--month`, `--off` |
| `/cli-run` | Execute raw CLI commands. Includes pipeline vars and extensions recipes |

### Skill-Handled (Natural Language)

| Say this | What happens |
|----------|-------------|
| "mark #1234 as done" | Updates work item with pre-flight validation and role-based permission check |
| "comment on #1234 @mahmoud" | Adds comment with validated @mentions (cache-first from profile) |
| "switch to relief center" | Changes project context |
| "any failing builds?" | Shows pipeline status |
| "create PR from feature to main" | Creates pull request |
| "set up CI/CD" | Generates GitHub Actions workflows |

---

## User Profile System

The plugin stores a persistent user profile at `~/.claude/devops.md` (referred to as `DevOps.md`).

### What the profile contains

| Section | Data |
|---------|------|
| **Identity** | Display name, email, Azure DevOps GUID |
| **Role** | Developer, QA/QC, PM/Lead (controls permissions) |
| **Default Project** | Auto-selected for all commands |
| **Team Members** | Names, GUIDs, and aliases for fast @mention resolution |
| **Task Templates** | Role-specific prefixes fetched from Azure DevOps (e.g., `[Dev]`, `[Front]`, `[IMP]`) |
| **State Permissions** | Which state transitions the user's role can perform |

### How it works

1. Run `/init profile` once - fetches everything from Azure DevOps REST API
2. Profile is loaded at **Step 0** of every session (before any operation)
3. Commands use profile for defaults: "assign to me" resolves your GUID, `/create` applies your role prefix
4. @mentions resolve from profile cache first, falling back to API only if needed

See `devops/profile_generator.md` and `data/profile_template.md` for details.

---

## Role-Based State Transitions

State transitions are controlled by role. The permission matrix is defined in `data/state_permissions.json` and enforced by `validators/state_transition_validator.md`.

### Work Item States (from Azure DevOps REST API)

| Type | States |
|------|--------|
| **Task** | To Do > In Progress > Done > Closed > Removed |
| **Bug** | New > Approved > In Progress > Resolved > Return > Committed > Done > Closed > Removed |
| **PBI** | New > Approved > Committed > In Progress > Ready For QC > Return > Done > Removed |
| **User Story** | New > Committed > Done |
| **Enhancement** | New > Committed > Return > Done > Closed |

### Permission Matrix

| Action | Developer | QA/QC | PM/Lead |
|--------|-----------|-------|---------|
| Start work (To Do > In Progress) | Yes | Yes | Yes |
| Complete work (In Progress > Done) | Yes | Yes | Yes |
| Initiate Return | - | Yes | Yes |
| Close / Remove | - | - | Yes |
| Approve | - | - | Yes |
| Resolve Bug | Yes | - | - |

Return transitions require a mandatory comment explaining the reason.

---

## Bug Creation SOP

Bug creation follows a strict role-based gate. See `data/bug_report_template.md` for the full template.

### Rules

| Role | Can create Bug? | Alternative |
|------|-----------------|-------------|
| **QA/QC** | Yes | Uses full bug template (Steps to Reproduce, Expected vs Actual, Severity, etc.) |
| **Developer** | No | Creates a `[Dev-Internal-fix]` Task instead |
| **PM/Lead** | Yes | Same template as QA |

### Developer Fix Workflow

1. **During active PBI** - Log fix on the existing task (no new work item)
2. **After PBI is done** - Create new `[Dev-Internal-fix]` child Task under the PBI
3. **Auto-mention** - QC team member is mentioned on every `[Dev-Internal-fix]` Task as FYI
4. **Raise Flag Rule** - If the fix changes user-facing behavior, the QA Lead is flagged

---

## Work Item Hierarchy

```
Epic
  > Feature
      > User Story / PBI
          > Task
          > Bug          (sibling of Task, not child)
          > Enhancement  (sibling of Task, not child)
```

Task, Bug, and Enhancement are all direct children of User Story/PBI. They are peers, not nested under each other. Hierarchy rules are defined in `data/hierarchy_rules.json` and enforced by `helpers/hierarchy_helper.md`.

---

## Plugin Structure

```
devops-plugin/
+-- .claude-plugin/
|   +-- plugin.json                    # Plugin metadata
+-- commands/                          # 9 slash command definitions
|   +-- cli-run.md
|   +-- create.md
|   +-- init.md
|   +-- log-time.md
|   +-- sprint.md
|   +-- standup.md
|   +-- task-monitor.md
|   +-- timesheet.md
|   +-- workday.md
+-- context/
|   +-- project_context.md             # Project context management
+-- data/                              # Configuration and data files
|   +-- bug_report_template.md         # QA bug report template
|   +-- error_patterns.json            # Error recovery patterns
|   +-- hierarchy_rules.json           # Work item hierarchy rules
|   +-- profile_template.md            # DevOps.md profile template
|   +-- project_defaults.json          # Default project settings
|   +-- repository_cache.json          # Repository lookup cache
|   +-- required_fields.json           # Field validation rules
|   +-- state_permissions.json         # Role-based state transition permissions
|   +-- team_members.json              # Team member cache
|   +-- work_tracker_defaults.json     # Work tracking defaults
+-- devops/                            # Core skill implementation
|   +-- SKILL.md                       # Main skill definition
|   +-- EXAMPLES.md                    # Usage examples
|   +-- REFERENCE.md                   # API reference
|   +-- profile_generator.md           # Profile generation workflow
|   +-- workflows.md                   # Skill-handled workflow definitions
|   +-- scripts/                       # Automation scripts
|       +-- cli/                       # PowerShell/Bash CLI scripts (6)
|       +-- hybrid/                    # Python hybrid scripts (3)
|       +-- mention_helper.py
|       +-- pr_analyzer.py
|       +-- sprint_report.py
|       +-- standup_helper.py
+-- errors/
|   +-- error_recovery.md              # Error handling procedures
+-- guards/
|   +-- tool_selection_guard.md        # CLI vs MCP routing guard
|   +-- write_operation_guard.md       # Write operation safety gate
+-- helpers/
|   +-- hierarchy_helper.md            # Work item hierarchy enforcement
+-- hooks/
|   +-- hooks.json                     # Event hooks configuration
+-- memories/                          # Predefined memory files (10)
|   +-- automation_templates.md
|   +-- cicd_patterns.md
|   +-- cli_best_practices.md
|   +-- github_integration.md
|   +-- hybrid_routing.md
|   +-- mcp_best_practices.md
|   +-- team_workflows.md
|   +-- wiql_queries.md
|   +-- work_tracking.md
+-- processors/
|   +-- mention_processor.md           # @mention resolution (cache-first)
+-- resolvers/
|   +-- repository_resolver.md         # Repository name resolution
+-- rules/
|   +-- business_rules.md              # Mandatory business rules
+-- validators/
|   +-- state_transition_validator.md  # Role-based state transition validation
+-- CHANGELOG.md
+-- LICENSE
+-- MIGRATION.md
+-- README.md
```

**Totals**: 9 commands | 10 data files | 10 memories | 13 scripts | 50+ files

---

## Changelog

### v4.2.0 - Role-Based State Transition Permissions
- Real states fetched from Azure DevOps REST API (TaqaTechno Scrum process)
- Complete state definitions for Task, Bug, PBI, User Story, Enhancement
- Role-based permission matrix (Developer, QA/QC, PM/Lead)
- Universal rules: Only PM can Close/Remove, QA initiates Returns
- Return loop handling with mandatory comments
- `data/state_permissions.json` added
- Profile auto-populates `statePermissions` from role during `/init profile`

### v4.1.3 - Task Templates from Azure DevOps
- Task naming prefixes fetched from project settings API (not hardcoded)
- Real templates: `[Dev]`, `[Front]`, `[IMP]`, `[QC Bug Fixing]`, `[QC Test Execution]`
- Role-to-prefix mapping updated to match real org templates

### v4.1.2 - Bug Creation SOP (Role-Based Gate)
- Developers cannot create Bugs; they create `[Dev-Internal-fix]` Tasks instead
- Only QA/QC roles can create Bugs (template enforced)
- Auto-mention QC member on every `[Dev-Internal-fix]` Task as FYI
- Raise Flag Rule: if fix changes user-facing behavior, flag QA Lead

### v4.1.1 - Hierarchy Fix + Enhancement Work Item
- Fixed hierarchy: Bug and Enhancement are siblings of Task under User Story/PBI
- Added Enhancement work item type across all files
- Correct hierarchy: `Epic > Feature > User Story/PBI > Task | Bug | Enhancement`

### v4.1.0 - User Profile System
- `/init profile` sub-command to generate `~/.claude/devops.md`
- DevOps.md stores identity, role, team, projects, task templates
- Profile-aware shortcuts and cache-first @mention resolution
- Profile loaded at session start (Step 0 in SKILL.md)

### v4.0.0 - Command Consolidation (24 > 9)
- Merged 24 commands into 9: `/init`, `/workday`, `/create`, `/log-time`, `/timesheet`, `/standup`, `/sprint`, `/task-monitor`, `/cli-run`
- 6 workflows moved to SKILL.md for natural language handling
- `/create` with auto-type detection (Task, Bug, User Story, Enhancement)

### v3.1.0 - Task Monitor
- `/task-monitor` with loop support for periodic new assignment alerts

### v3.0.0 - Work Tracking System
- Workday dashboard, time logging, compliance enforcement, persistent cache

### v2.0.0 - Hybrid Mode
- CLI + MCP architecture, automated CLI setup, predefined memories, business rules

See [CHANGELOG.md](CHANGELOG.md) for full version history.

---

## Support

- **Organization**: YOUR-ORG
- **Email**: support@example.com
- **Repository**: https://github.com/taqat-techno/plugins

## License

MIT License - see [LICENSE](LICENSE)
