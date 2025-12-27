# DevOps Plugin for Claude Code

A comprehensive Azure DevOps integration plugin for Claude Code, enabling natural language interaction with your DevOps workflows through **HYBRID** CLI + MCP architecture.

**Version**: 2.0.0 | **Organization**: TaqaTechno | **Mode**: Hybrid (CLI + MCP)

---

## What's New in v2.0.0 - Hybrid Mode

🚀 **Major Release**: Combines Azure DevOps CLI power with MCP convenience for optimal performance.

### Highlights

| Feature | Description |
|---------|-------------|
| **Hybrid Architecture** | CLI for automation, MCP for interactive queries |
| **Intelligent Routing** | Claude automatically selects best tool for each task |
| **CLI Installation** | Automated setup for Windows, macOS, Linux |
| **Predefined Memories** | Best practices cached for instant Claude reference |
| **Automation Scripts** | PowerShell and Python scripts for common workflows |
| **4 New Commands** | `/cli-run`, `/setup-pipeline-vars`, `/install-extension`, `/full-sprint-report` |

### Hybrid Mode Benefits

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CLI (Azure DevOps CLI)          MCP (100+ Tools)           │
│  ├─ Batch operations             ├─ Interactive queries     │
│  ├─ Pipeline variables           ├─ Code review threads     │
│  ├─ Service connections          ├─ Test plan management    │
│  ├─ Extension management         ├─ Security alerts         │
│  ├─ Project creation             ├─ Search (code/wiki)      │
│  └─ Parallel execution           └─ Natural language        │
│                                                             │
│              Claude Intelligently Routes Tasks              │
└─────────────────────────────────────────────────────────────┘
```

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
- **New Commands** - `/cli-run`, `/setup-pipeline-vars`, `/install-extension`, `/full-sprint-report`
- **Automation Scripts** - PowerShell (batch_update, sprint_report, pr_automation)
- **Python Scripts** - Hybrid standup, sprint planner, release notes generators

### Previous Features (v1.3.0)
- **Required Field Validation** - Validates required fields before updates
- **State Transition Rules** - Enforces Task→Done requires hours
- **User Story QC Checkpoint** - Stories must pass through "Ready for QC"
- **@Mention Processing** - Automatic user lookup and HTML formatting
- **Work Item Hierarchy** - Epic→Feature→PBI→Task→Bug enforcement
- **TODO Sync** - Sync Azure DevOps tasks to Claude Code TODO list

---

## Quick Start

### Option 1: Full Hybrid Setup (Recommended)

```
/devops:devops setup
```

This installs both CLI and MCP:
1. ✅ Detects your platform
2. ✅ Installs Azure CLI + DevOps extension
3. ✅ Configures MCP server
4. ✅ Sets up authentication
5. ✅ Validates both connections

### Option 2: CLI Only

```
/devops:devops setup --cli
```

Or run the installer script directly:

**Windows (PowerShell):**
```powershell
.\devops\scripts\cli\install_cli.ps1 -Organization "TaqaTechno"
```

**macOS/Linux (Bash):**
```bash
./devops/scripts/cli/install_cli.sh --org TaqaTechno
```

### Option 3: MCP Only

```
/devops:devops setup --mcp
```

---

## Installation

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Node.js | 18+ | MCP server runtime |
| Azure CLI | 2.30+ | CLI operations |
| Python | 3.8+ | Hybrid scripts (optional) |

### Step 1: Install Azure CLI

**Windows:**
```powershell
winget install -e --id Microsoft.AzureCLI
```

**macOS:**
```bash
brew install azure-cli
```

**Linux:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Step 2: Install DevOps Extension

```bash
az extension add --name azure-devops
```

### Step 3: Create Personal Access Token (PAT)

1. Go to: `https://dev.azure.com/{YOUR_ORG}/_usersSettings/tokens`
2. Click **"New Token"**
3. Configure scopes:
   - Code: Read, Write
   - Work Items: Read, Write, Manage
   - Build: Read, Execute
   - Release: Read, Write, Execute
   - Wiki: Read, Write
   - Test Management: Read
   - Variable Groups: Read, Create
4. Copy the token immediately

### Step 4: Configure Authentication

**CLI Authentication:**
```bash
# Set environment variable (recommended)
# Windows:
[System.Environment]::SetEnvironmentVariable('AZURE_DEVOPS_EXT_PAT', 'your-pat', 'User')

# macOS/Linux:
export AZURE_DEVOPS_EXT_PAT="your-pat"

# Set defaults
az devops configure --defaults organization=https://dev.azure.com/YOUR_ORG
```

**MCP Authentication:**

Add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "azure-devops": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic-ai/azure-devops-mcp", "YOUR_ORGANIZATION"],
      "env": {
        "ADO_MCP_AUTH_TOKEN": "${ADO_PAT_TOKEN}"
      }
    }
  }
}
```

### Step 5: Verify Installation

```
/devops:devops status
```

Expected output:
```
Azure DevOps Integration Status
================================
CLI Status:     ✅ Installed (v2.65.0)
MCP Status:     ✅ Connected
Hybrid Mode:    ✅ Enabled
Organization:   TaqaTechno
```

---

## Commands Reference

### Setup & Status

| Command | Description |
|---------|-------------|
| `/devops:devops setup` | Complete hybrid setup (CLI + MCP) |
| `/devops:devops setup --cli` | Install Azure CLI only |
| `/devops:devops setup --mcp` | Configure MCP server only |
| `/devops:devops status` | Check connection status |

### CLI Operations (New in v2.0)

| Command | Description |
|---------|-------------|
| `/devops:cli-run <command>` | Execute any Azure DevOps CLI command |
| `/devops:setup-pipeline-vars` | Manage pipeline variables and groups |
| `/devops:install-extension` | Install marketplace extensions |
| `/devops:full-sprint-report` | Comprehensive hybrid sprint report |

### Work Items

| Command | Description |
|---------|-------------|
| `/devops:my-tasks` | List your active work items |
| `/devops:create-task` | Create task (with parent enforcement) |
| `/devops:create-bug` | Create a new bug |
| `/devops:create-user-story` | Create story with What/How/Why format |
| `/devops:sync-my-tasks` | Sync tasks to Claude TODO list |

### Sprint & Standup

| Command | Description |
|---------|-------------|
| `/devops:standup` | Generate daily standup notes |
| `/devops:sprint` | Sprint progress summary |
| `/devops:build-status` | Check recent build status |

---

## Hybrid Routing

Claude automatically selects CLI or MCP based on task characteristics:

### When CLI is Used

| Task | Reason |
|------|--------|
| Batch work item updates | Scripting faster for loops |
| Create infrastructure | CLI-only features |
| Pipeline variables | CLI-only feature |
| Service connections | CLI-only feature |
| Extensions | CLI-only feature |
| Parallel operations | Performance |

### When MCP is Used

| Task | Reason |
|------|--------|
| Interactive queries | More convenient |
| Code review threads | Dedicated tools |
| Test plan management | MCP-only feature |
| Security alerts | MCP-only feature |
| Search (code/wiki) | MCP-only feature |
| Natural language | Better UX |

### Hybrid Example

```
User: "Create 10 tasks for implementing authentication"

Claude's Approach:
1. MCP: Get team member identities
2. CLI: Batch create tasks in parallel
3. MCP: Verify and report results
```

---

## Predefined Memories

Claude automatically loads best practices from the `memories/` directory:

| Memory | Purpose |
|--------|---------|
| `cli_best_practices.md` | CLI command patterns, JMESPath queries |
| `mcp_best_practices.md` | MCP tool patterns by domain |
| `automation_templates.md` | Reusable PowerShell/Bash/Python scripts |
| `wiql_queries.md` | 40+ WIQL query templates |
| `team_workflows.md` | TaqaTechno-specific conventions |
| `hybrid_routing.md` | CLI vs MCP decision matrix |

---

## Automation Scripts

### CLI Scripts (PowerShell)

Located in `devops/scripts/cli/`:

| Script | Description |
|--------|-------------|
| `install_cli.ps1` | Windows CLI installer |
| `install_cli.sh` | Unix CLI installer |
| `configure_defaults.ps1` | Set CLI defaults |
| `batch_update.ps1` | Bulk work item updates |
| `sprint_report.ps1` | Sprint report generator |
| `pr_automation.ps1` | PR workflow automation |

**Example - Batch Update:**
```powershell
.\batch_update.ps1 -WorkItemIds 1,2,3,4,5 -State "Done" -Parallel
```

### Hybrid Scripts (Python)

Located in `devops/scripts/hybrid/`:

| Script | Description |
|--------|-------------|
| `standup_generator.py` | Daily standup notes |
| `sprint_planner.py` | Sprint planning with capacity |
| `release_notes.py` | Release notes from completed work |

**Example - Standup:**
```bash
python standup_generator.py "Relief Center" --format markdown
```

---

## Plugin Structure

```
devops-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata (v2.0.0)
├── commands/                     # Slash commands
│   ├── devops.md                # Setup & configuration (enhanced)
│   ├── cli-run.md               # NEW - Execute CLI commands
│   ├── setup-pipeline-vars.md   # NEW - Variable management
│   ├── install-extension.md     # NEW - Extension installation
│   ├── full-sprint-report.md    # NEW - Hybrid sprint report
│   ├── sync-my-tasks.md
│   ├── create-user-story.md
│   ├── create-task.md
│   ├── create-bug.md
│   ├── my-tasks.md
│   ├── standup.md
│   ├── sprint.md
│   └── build-status.md
├── devops/                       # Main skill
│   ├── SKILL.md                 # Core skill (1500+ lines, v2.0)
│   ├── REFERENCE.md             # API reference
│   ├── EXAMPLES.md              # Usage examples
│   └── scripts/
│       ├── cli/                 # NEW - CLI scripts
│       │   ├── install_cli.ps1
│       │   ├── install_cli.sh
│       │   ├── configure_defaults.ps1
│       │   ├── batch_update.ps1
│       │   ├── sprint_report.ps1
│       │   └── pr_automation.ps1
│       ├── hybrid/              # NEW - Hybrid scripts
│       │   ├── standup_generator.py
│       │   ├── sprint_planner.py
│       │   └── release_notes.py
│       ├── mention_helper.py
│       ├── pr_analyzer.py
│       ├── sprint_report.py
│       ├── standup_helper.py
│       └── README.md            # Scripts documentation
├── memories/                     # NEW - Predefined memories
│   ├── README.md
│   ├── cli_best_practices.md
│   ├── mcp_best_practices.md
│   ├── automation_templates.md
│   ├── wiql_queries.md
│   └── team_workflows.md
├── hooks/
│   └── hooks.json
├── hybrid_routing.md            # NEW - Routing decision guide
├── MIGRATION.md                 # NEW - v1.3 to v2.0 guide
├── CHANGELOG.md                 # NEW - Version history
├── LICENSE
└── README.md
```

---

## Usage Examples

### CLI Operations

```bash
# Execute CLI command
/devops:cli-run az boards work-item create --title "New Task" --type Task

# Manage variables
/devops:setup-pipeline-vars create "Production-Secrets"
/devops:setup-pipeline-vars add "Production-Secrets" API_URL "https://api.example.com"
/devops:setup-pipeline-vars secret "Production-Secrets" API_KEY

# Install extension
/devops:install-extension ms-devlabs.workitem-feature-timeline-extension
```

### Hybrid Workflows

```bash
# Full sprint report (uses both CLI and MCP)
/devops:full-sprint-report "Relief Center" "Relief Center Team"

# Batch update (CLI for speed)
"Update tasks 100-110 to Active state"

# Code review (MCP for rich features)
"Review PR #45 and add comments"
```

### Work Items

```bash
"Show my active work items"
"Create bug: Login button not responding on mobile"
"Update task #1234 to Done with 6 hours completed"
"Link bug #456 to user story #123"
"Add comment to #1234: @eslam please review"
```

### Sprint & Standup

```bash
"/devops:standup"
"/devops:sprint"
"What's blocking the team?"
"Sprint summary for Relief Center"
```

---

## Environment Variables

| Variable | Purpose | Used By |
|----------|---------|---------|
| `AZURE_DEVOPS_EXT_PAT` | CLI authentication | CLI scripts |
| `ADO_PAT_TOKEN` | MCP authentication | MCP server |
| `DEVOPS_HYBRID_MODE` | Enable hybrid mode | All components |

---

## Troubleshooting

### CLI Issues

| Issue | Solution |
|-------|----------|
| "az not found" | Install Azure CLI for your platform |
| "devops extension not found" | Run `az extension add --name azure-devops` |
| "Not logged in" | Set `AZURE_DEVOPS_EXT_PAT` or run `az devops login` |
| "Organization not found" | Check organization name spelling |

### MCP Issues

| Issue | Solution |
|-------|----------|
| "MCP server not responding" | Check Node.js 18+ installed |
| "Authentication failed" | Verify PAT token in settings.json |
| "npx command failed" | Run `npm cache clean --force` |

### Hybrid Issues

| Issue | Solution |
|-------|----------|
| "CLI not being used" | Check `DEVOPS_HYBRID_MODE=true` |
| "Slow batch operations" | Use CLI scripts with `-Parallel` |

---

## Changelog

### v2.0.0 (2025-12) - Hybrid Mode Release

**Major Features:**
- **Hybrid Architecture** - Combines CLI and MCP for optimal performance
- **Intelligent Routing** - Claude automatically selects best tool
- **CLI Installation** - Automated setup for all platforms
- **Predefined Memories** - 6 memory files with best practices

**New Commands:**
- `/cli-run` - Execute any CLI command
- `/setup-pipeline-vars` - Manage pipeline variables (CLI-only)
- `/install-extension` - Install marketplace extensions (CLI-only)
- `/full-sprint-report` - Comprehensive hybrid report

**New Scripts:**
- `install_cli.ps1/sh` - CLI installers
- `configure_defaults.ps1` - CLI configuration
- `batch_update.ps1` - Bulk work item updates
- `sprint_report.ps1` - Sprint report generator
- `pr_automation.ps1` - PR workflow automation
- `standup_generator.py` - Hybrid standup notes
- `sprint_planner.py` - Sprint planning with capacity
- `release_notes.py` - Release notes generator

**New Memories:**
- `cli_best_practices.md` - CLI patterns and tips
- `mcp_best_practices.md` - MCP tool patterns
- `automation_templates.md` - Reusable scripts
- `wiql_queries.md` - 40+ WIQL queries
- `team_workflows.md` - TaqaTechno workflows
- `hybrid_routing.md` - Decision matrix

**Enhanced:**
- `SKILL.md` - Updated to v2.0 with hybrid mode section (1500+ lines)
- `plugin.json` - Updated metadata for hybrid mode
- `devops.md` - Enhanced setup with CLI installation

### v1.3.0 (2024-12)
- Required field validation
- State transition rules
- User Story QC checkpoint
- 15 team members cached

### v1.2.0 (2024-12)
- `/devops setup` command
- Cross-platform configuration
- Environment variable support

### v1.1.0 (2024-12)
- TODO sync command
- @mention processing
- Work item hierarchy enforcement
- What/How/Why story format

### v1.0.0 (2024-11)
- Initial release
- 100+ MCP tools
- 6 slash commands

---

## Migration from v1.3

See [MIGRATION.md](MIGRATION.md) for upgrade guide.

**Quick Migration:**
1. Run `/devops:devops setup` to install CLI
2. Set `AZURE_DEVOPS_EXT_PAT` environment variable
3. Restart Claude Code

All v1.3 features continue to work. New hybrid features are additive.

---

## Support

- **Organization**: TaqaTechno
- **Email**: info@taqatechno.com
- **Repository**: https://github.com/taqat-techno/plugins

## License

MIT License - see [LICENSE](LICENSE)
