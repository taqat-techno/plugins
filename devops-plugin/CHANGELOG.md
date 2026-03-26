# Changelog

All notable changes to the DevOps Plugin for Claude Code.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [6.3.0] - 2026-03-26 - P2 Polish & Documentation

### Added
- **Workflows 7-9 in SKILL.md**: Natural-language triggers for Log Time ("spent 3h on #ID"), Daily Standup ("prepare standup"), and Monitor Assignments ("any new tasks?"). Commands `/log-time`, `/standup`, `/task-monitor` remain as explicit shortcuts.
- **Schema versioning**: `schemaVersion` field in profile template/example. `compatibility` section in `project_defaults.json` with `minProfileSchema`. SessionStart hook checks profile schema major version against minimum.
- **`devops/MCP_FAILURE_MODES.md`**: Comprehensive documentation for MCP server failures — startup issues, auth failures, timeouts, version incompatibilities, and CLI fallback matrix.
- **MCP unavailable detection** in `error-recovery.sh`: catches ECONNREFUSED/MCP unavailable patterns and points to failure mode docs.

---

## [6.2.0] - 2026-03-26 - P1 Enforcement & Consolidation

### Changed
- **Data files consolidated (7 to 5)**:
  - `work_tracker_defaults.json` merged into `project_defaults.json` as `workTracking` key
  - `error_patterns.json` merged into `state_machine.json` as `errorPatterns` key (inner key renamed to `patterns`)
- **3 hard enforcement blocks** in `pre-write-validate.sh`:
  - Bug creation authority (existing) — developers cannot create Bugs
  - Close/Remove restriction (NEW) — only PM/Lead can transition to Closed or Removed
  - Unresolved @mentions (NEW) — comments with `@name` without GUID resolution are blocked
- **SessionStart consistency checks** added to `session-start.sh`:
  - JSON syntax validation for 3 core data files
  - Plugin version check (must be 6.x)
  - Profile required fields check (role, defaultProject, teamMembers)
  - Core data file existence check

### Removed
- `data/work_tracker_defaults.json` — merged into `project_defaults.json`
- `data/error_patterns.json` — merged into `state_machine.json`

---

## [6.1.0] - 2026-03-26 - P0 Hardening

### Removed
- **Python scripts layer eliminated**: Deleted 5 formatting scripts (`sprint_report.py`, `standup_generator.py`, `release_notes.py`, `sprint_planner.py`, `pr_analyzer.py`). Agents now format output directly using MCP data + inline templates. `consistency_check.py` moved to `tests/`.
- **REFERENCE_FULL.md deleted** (602 lines): MCP tools are self-describing; per-tool parameter docs were redundant.
- **REFERENCE.md deleted** (172 lines): Useful content (WIQL, fields, API limits) merged into SKILL.md Quick Reference appendix.
- **test_scripts.py deleted**: Tests for removed Python scripts.

### Added
- **SKILL.md Quick Reference appendix**: Work item fields, WIQL syntax/macros/common queries, response formatting, API limits — all in one place.
- **`/cli-run` MANDATORY SAFETY section**: Write detection table classifying CLI commands as READ/WRITE, with `rules/write-gate.md` enforcement for writes.
- **`--force` escape hatch** for `/cli-run`: Power users can bypass write-gate confirmation explicitly.
- **CLI write detection in `pre-bash-check.sh`**: Soft-remind hook injects write-gate reminder for `az` write commands.

### Changed
- **Agents updated**: `sprint-planner.md` and `pr-reviewer.md` replaced Scripts/Reference sections with inline Output Formatting / Analysis Approach guidance.
- **File count reduced from ~48 to ~40** (8 files removed, 1 moved).

---

## [6.0.0] - 2026-03-26 - Architecture Simplification

### Architecture Overhaul
- **Reduced file count from 50+ to ~45** through aggressive consolidation
- **Single source of truth**: `data/state_machine.json` merges state permissions, required fields, and business rules
- **SKILL.md reduced from 1,196 to 346 lines** (71% reduction) — references data files instead of restating rules
- **Middleware renamed to rules/**: 9 files consolidated into 3 (`write-gate.md`, `guards.md`, `profile-loader.md`)
- **References directory deleted**: 10 generic knowledge files removed, WIQL templates merged into REFERENCE.md
- **Scripts consolidated to Python only**: PowerShell/Bash scripts deleted

### Added
- **`hooks/pre-write-validate.sh`** — Programmatic enforcement of state transitions, bug creation authority, hierarchy, and mention format before MCP write tools execute
- **`hooks/session-start.sh`** — Profile staleness detection (warns if >30 days since last refresh)
- **`data/state_machine.json`** — Unified schema for states, transitions, required fields, role permissions, gates, and business rules
- **`rules/write-gate.md`** — Confirmation protocol (from write_operation_guard.md)
- **`rules/guards.md`** — Tool selection, mention processing, and repository resolution guards (merged 3 files)
- **`rules/profile-loader.md`** — Profile loading and project context management (merged 2 files)
- **`scripts/consistency_check.py`** — Cross-file drift detection script
- **`tests/test_state_machine.py`** — 40+ tests validating state_machine.json schema, transitions, roles, fields, gates
- **`tests/test_consistency.py`** — Cross-file reference tests (stale paths, hook scripts, agent references)
- **`lastRefresh` field in profile** — Enables TTL-based staleness detection in session-start hook
- **PreToolUse hook for 5 MCP write tools** — `wit_create`, `wit_update`, `wit_add_comment`, `wit_link`, `repo_create_pr`

### Changed
- **hooks.json** — Added PreToolUse matcher targeting 5 MCP write tools; SessionStart now uses `session-start.sh`
- **Agent tool lists trimmed** — work-item-ops: 14->8, sprint-planner: 23->11, pr-reviewer: 33->13
- **Profile generation moved to commands/init.md** — Profile workflow is a setup task, not runtime behavior
- **All agents updated** — Reference `rules/` and `data/state_machine.json` instead of middleware/

### Removed
- **`middleware/` directory** (9 files) — Replaced by `rules/` (3 files)
- **`references/` directory** (10 files) — Generic knowledge removed, WIQL templates moved to REFERENCE.md
- **`devops/workflows.md`** (560 lines) — Replaced by routing table in SKILL.md (~60 lines)
- **`devops/profile_generator.md`** — Merged into `commands/init.md`
- **`data/state_permissions.json`** — Merged into `data/state_machine.json`
- **`data/required_fields.json`** — Merged into `data/state_machine.json`
- **`data/repository_cache.json`** — Session-level cache, not persistent data
- **`data/team_members.json`** — Already stored in profile
- **`hooks/check-profile.sh`** — Replaced by `hooks/session-start.sh`
- **`MIGRATION.md`** — No longer relevant
- **All PowerShell scripts** — Python only
- **Redundant Python scripts** (`standup_helper.py`, `mention_helper.py`)

---

## [4.1.0] - 2026-03 - User Profile System

### Added
- **`/init profile`** — New sub-command to generate persistent user profile at `~/.claude/devops.md`
- **DevOps.md user profile** — Caches user identity (GUID, email, role), projects, and team members with GUIDs
- **Cache-first @mention resolution** — Resolves team members from profile before calling API
- **Profile-aware task creation** — Auto-applies task prefix from user's role, auto-assigns to current user
- **Session persistence** — Default project and user context restored from profile across sessions
- **`devops/profile_generator.md`** — Full reference for profile generation workflow
- **`data/profile_template.md`** — Template structure for DevOps.md generation

### Changed
- **SKILL.md** — Added Step 0: Load User Profile preamble (runs before all operations)
- **mention_processor.md** — Added Step 1.5: cache-first resolution from profile teamMembers
- **create.md** — Added Step 0: profile-aware defaults (prefix, assignee, project)
- **workflows.md** — Added profile-aware preamble and assignment resolution

---

## [4.0.0] - 2026-03 - Plugin Consolidation

### Changed - Command Consolidation (24 → 9 commands)

#### Merged Commands
- **`/create`** — Unified work item creation (replaces `/create-task`, `/create-bug`, `/create-user-story`). Auto-detects type from context, supports explicit `--task`, `--bug`, `--story` flags.
- **`/workday`** — Absorbs `/my-tasks` (`--tasks` flag), `/work-sync` (`--sync` flag), `/sync-my-tasks` (`--todo` flag).
- **`/timesheet`** — Absorbs `/time-off` (`--off`, `--off-list`, `--off-remove` flags).
- **`/sprint`** — Absorbs `/full-sprint-report` (`--full` flag).
- **`/cli-run`** — Absorbs `/setup-pipeline-vars` and `/install-extension` as documented recipes.

#### Renamed Commands
- **`/init`** — Renamed from `/devops`. Sub-commands: `/init setup`, `/init status`, `/init upgrade`, `/init help`.

#### Moved to Skill (Natural Language)
- `/update-workitem` → Say "mark #1234 as done"
- `/add-comment` → Say "comment on #1234"
- `/switch-project` → Say "switch to relief center"
- `/build-status` → Say "any failing builds?"
- `/create-pr` → Say "create PR from feature/login to main"
- `/ci-setup` → Say "set up CI/CD for my project"

### Added
- `devops/workflows.md` — Full workflow documentation for 6 skill-handled operations
- Auto-type detection in `/create` command (keywords, structural cues, explicit flags)
- 6 new trigger examples in SKILL.md frontmatter

### Removed
- 17 command files (functionality preserved in merged commands and skill workflows)

---

## [2.0.0] - 2025-12 - Hybrid Mode Release

### Added

#### Hybrid Architecture
- **CLI + MCP Integration**: Combines Azure DevOps CLI with MCP server for optimal performance
- **Intelligent Routing**: Claude automatically selects best tool (CLI or MCP) for each task
- **Cross-Platform CLI Installation**: Automated setup for Windows, macOS, and Linux

#### New Commands
- `/cli-run` - Execute any Azure DevOps CLI command directly
- `/setup-pipeline-vars` - Manage pipeline variables and variable groups (CLI-only feature)
- `/install-extension` - Install Azure DevOps marketplace extensions (CLI-only feature)
- `/full-sprint-report` - Comprehensive hybrid sprint report combining CLI speed with MCP details

#### CLI Scripts (PowerShell)
- `install_cli.ps1` - Windows Azure CLI installer with DevOps extension
- `install_cli.sh` - Unix/Linux/macOS CLI installer
- `configure_defaults.ps1` - Configure organization, project, and PAT defaults
- `batch_update.ps1` - Bulk work item updates with parallel execution support
- `sprint_report.ps1` - Sprint report generator (Console, Markdown, JSON, HTML formats)
- `pr_automation.ps1` - PR workflow automation (Create, Merge, AutoComplete, AddReviewers)

#### Hybrid Scripts (Python)
- `standup_generator.py` - Daily standup notes using CLI for speed
- `sprint_planner.py` - Sprint planning with capacity analysis and suggestions
- `release_notes.py` - Release notes generator from completed work items and PRs

#### Predefined Memories
- `cli_best_practices.md` - CLI command patterns, JMESPath queries, batch operations
- `mcp_best_practices.md` - MCP tool patterns organized by domain
- `automation_templates.md` - Reusable PowerShell/Bash/Python automation templates
- `wiql_queries.md` - 40+ WIQL query templates for common scenarios
- `team_workflows.md` - organization-specific conventions and standards
- `hybrid_routing.md` - CLI vs MCP decision matrix for intelligent routing

#### Documentation
- `MIGRATION.md` - Complete migration guide from v1.3 to v2.0
- `CHANGELOG.md` - Version history (this file)
- `hybrid_routing.md` - Routing decision guide
- `scripts/README.md` - Complete scripts documentation

### Enhanced
- `/devops setup` - Now supports hybrid setup with CLI installation options
- `SKILL.md` - Updated to v2.0 with hybrid mode section (~1500 lines)
- `plugin.json` - Updated metadata for hybrid mode capabilities
- `README.md` - Complete rewrite with v2.0 documentation

### Technical Details
- Environment variable: `AZURE_DEVOPS_EXT_PAT` for CLI authentication
- Environment variable: `DEVOPS_HYBRID_MODE` for explicit hybrid mode control
- Parallel execution support in batch scripts (`-Parallel` flag)
- UTF-8 encoding throughout all scripts

---

## [1.3.0] - 2024-12

### Added
- **Required Field Validation**: Validates required fields before work item updates
- **State Transition Rules**: Enforces Task→Done requires hours (OriginalEstimate, CompletedWork)
- **User Story QC Checkpoint**: Stories must pass through "Ready for QC" before Done
- **15 Team Members Cached**: Eslam, Ahmed, Mahmoud, Mohamed, and 11 more for @mention lookup

### Enhanced
- Work item update validation with clear error messages
- @mention processing with cached team member resolution

---

## [1.2.0] - 2024-12

### Added
- `/devops setup` command for guided configuration
- Cross-platform setup support (Windows, macOS, Linux)
- Environment variable configuration guide
- MCP server installation instructions

### Enhanced
- README with comprehensive setup documentation
- Error messages with actionable solutions

---

## [1.1.0] - 2024-12

### Added
- `/sync-my-tasks` - Sync Azure DevOps tasks to Claude Code TODO list
- **@Mention Processing**: Automatic user lookup and HTML formatting
- **Work Item Hierarchy Enforcement**: Epic→Feature→PBI→Task→Bug structure
- **What/How/Why Story Format**: Structured user story descriptions

### Enhanced
- `/create-user-story` with What/How/Why template
- `/create-task` with parent work item enforcement
- Comment formatting with @mention HTML conversion

---

## [1.0.0] - 2024-11

### Added
- Initial release of DevOps Plugin for Claude Code
- **100+ MCP Tools**: Full Azure DevOps integration via MCP server
- **Organization**: YOUR-ORG

#### Slash Commands
- `/devops` - Main skill invocation
- `/my-tasks` - List assigned work items
- `/create-task` - Create new task
- `/create-bug` - Create new bug
- `/create-user-story` - Create user story
- `/standup` - Generate standup notes
- `/sprint` - Sprint progress summary
- `/build-status` - Check build status

#### MCP Tool Categories
- **Work Items**: Create, update, query, link, comment (20+ tools)
- **Repositories**: Browse code, commits, branches (15+ tools)
- **Pull Requests**: Create, review, approve, merge (15+ tools)
- **Pipelines**: Run, monitor, view logs (10+ tools)
- **Wiki**: Read, create, update pages (8+ tools)
- **Search**: Code, work items, wiki search (5+ tools)
- **Test Plans**: Manage test plans and cases (10+ tools)
- **Security**: Advanced security alerts (5+ tools)
- **Projects**: List projects, teams, iterations (10+ tools)

#### Documentation
- `SKILL.md` - Core skill implementation (~800 lines)
- `REFERENCE.md` - API reference
- `EXAMPLES.md` - Usage examples
- `README.md` - User documentation

---

## Version Comparison

| Feature | v1.0 | v1.1 | v1.2 | v1.3 | v2.0 |
|---------|------|------|------|------|------|
| MCP Tools | 100+ | 100+ | 100+ | 100+ | 100+ |
| Slash Commands | 8 | 9 | 9 | 9 | 12 |
| CLI Support | - | - | - | - | ✅ |
| Hybrid Mode | - | - | - | - | ✅ |
| @Mentions | - | ✅ | ✅ | ✅ | ✅ |
| TODO Sync | - | ✅ | ✅ | ✅ | ✅ |
| State Rules | - | - | - | ✅ | ✅ |
| Field Validation | - | - | - | ✅ | ✅ |
| Setup Command | - | - | ✅ | ✅ | ✅ |
| Memory Files | - | - | - | - | 6 |
| CLI Scripts | - | - | - | - | 6 |
| Python Scripts | 4 | 4 | 4 | 4 | 7 |

---

## Upgrade Path

| From | To | Guide |
|------|-----|-------|
| v1.3.x | v2.0.0 | [MIGRATION.md](MIGRATION.md) |
| v1.2.x | v2.0.0 | [MIGRATION.md](MIGRATION.md) |
| v1.1.x | v2.0.0 | [MIGRATION.md](MIGRATION.md) |
| v1.0.x | v2.0.0 | [MIGRATION.md](MIGRATION.md) |

All upgrades to v2.0 are backward compatible. No breaking changes.

---

## Links

- [README](README.md) - Main documentation
- [MIGRATION](MIGRATION.md) - Migration guide
- [SKILL.md](devops/SKILL.md) - Skill implementation

---

*Maintained by your organization*
