# DevOps Plugin for Claude Code

A comprehensive Azure DevOps integration plugin for Claude Code, enabling natural language interaction with your DevOps workflows through **HYBRID** CLI + MCP architecture.

**Version**: 2.0.0 | **Organization**: TaqaTechno | **Mode**: Hybrid (CLI + MCP)

---

## TaqaTechno Business Rules

The plugin enforces mandatory business rules for work item management. Full documentation: `rules/business_rules.md`

### Quick Reference

| Rule | Description |
|------|-------------|
| **Hierarchy** | Epic → Feature → User Story → Task → Bug (parent required) |
| **User Story Format** | How? → What? → Why? sequence |
| **State Transitions** | Must pass through "Ready for QC" before "Done" |
| **Task Prefixes** | [DEV] backend, [FRONT] frontend, [QA] test, [IMP] deploy |
| **Auto-Sprint** | Tasks auto-assigned to current sprint by date |
| **Task Completion** | Requires Original Estimate + Completed Hours |
| **Bug Completion** | Requires Completed Work |

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

### v2.0.0 Features
- **Hybrid Mode** - CLI + MCP for optimal performance
- **Automated CLI Setup** - Cross-platform installation scripts
- **Predefined Memories** - Best practices, WIQL queries, automation templates
- **Business Rules Enforcement** - 7 mandatory rules for work item management

### Previous Features (v1.3.0)
- **Required Field Validation** - Validates required fields before updates
- **State Transition Rules** - Enforces Task→Done requires hours
- **User Story QC Checkpoint** - Stories must pass through "Ready for QC"
- **@Mention Processing** - Automatic user lookup and HTML formatting
- **Work Item Hierarchy** - Epic→Feature→PBI→Task→Bug enforcement
- **TODO Sync** - Sync Azure DevOps tasks to Claude Code TODO list

---

## Quick Start

```
/devops setup
```

This installs both CLI and MCP:
1. Detects your platform
2. Installs Azure CLI + DevOps extension
3. Configures MCP server
4. Sets up authentication
5. Validates both connections

---

## Commands Reference

### Work Items

| Command | Description |
|---------|-------------|
| `/my-tasks` | List your active work items |
| `/create-task` | Create task (with parent enforcement + naming conventions) |
| `/create-bug` | Create a new bug |
| `/create-user-story` | Create story with How/What/Why format |
| `/sync-my-tasks` | Sync tasks to Claude TODO list |

### Sprint & Standup

| Command | Description |
|---------|-------------|
| `/standup` | Generate daily standup notes |
| `/sprint` | Sprint progress summary |
| `/build-status` | Check recent build status |

---

## Support

- **Organization**: TaqaTechno
- **Email**: info@taqatechno.com
- **Repository**: https://github.com/taqat-techno-eg/plugins

## License

MIT License - see [LICENSE](LICENSE)
