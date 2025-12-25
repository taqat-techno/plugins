# Changelog

All notable changes to the DevOps Plugin for Claude Code.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- `team_workflows.md` - TaqaTechno-specific conventions and standards
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
- **Organization**: TaqaTechno

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

*Maintained by TaqaTechno*
