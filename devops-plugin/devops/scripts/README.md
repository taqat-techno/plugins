# Azure DevOps Automation Scripts

Collection of automation scripts for Azure DevOps operations. Scripts are organized by execution mode: CLI-only, MCP-only, and Hybrid (using both).

## Directory Structure

```
scripts/
├── cli/                        # PowerShell/Bash scripts using Azure CLI
│   ├── install_cli.ps1         # Windows CLI installer
│   ├── install_cli.sh          # Unix/Linux CLI installer
│   ├── configure_defaults.ps1  # Configure CLI defaults
│   ├── batch_update.ps1        # Bulk work item updates
│   ├── sprint_report.ps1       # Sprint report generator
│   └── pr_automation.ps1       # PR workflow automation
├── hybrid/                     # Python scripts using CLI + MCP
│   ├── standup_generator.py    # Daily standup notes
│   ├── sprint_planner.py       # Sprint planning with capacity
│   └── release_notes.py        # Release notes generator
├── mention_helper.py           # MCP: Process @mentions
├── pr_analyzer.py              # MCP: Analyze PRs
├── sprint_report.py            # MCP: Sprint report (MCP version)
├── standup_helper.py           # MCP: Standup helper
└── README.md                   # This file
```

## Prerequisites

### For CLI Scripts (PowerShell)
- Azure CLI 2.30.0+
- Azure DevOps CLI extension
- PowerShell 5.1+ (Windows) or PowerShell Core 7+ (cross-platform)

```powershell
# Install Azure CLI (Windows)
winget install -e --id Microsoft.AzureCLI

# Install DevOps extension
az extension add --name azure-devops

# Configure defaults
az devops configure --defaults organization=https://dev.azure.com/YOUR-ORG
```

### For Python Scripts
- Python 3.8+
- Azure CLI (for hybrid scripts)
- No additional packages required (uses stdlib only)

---

## CLI Scripts

### install_cli.ps1 / install_cli.sh

Install and configure Azure DevOps CLI.

```powershell
# Windows
.\install_cli.ps1 -Organization "YOUR-ORG"

# Unix/Linux
./install_cli.sh --org YOUR-ORG
```

### configure_defaults.ps1

Set up CLI defaults for your organization and project.

```powershell
# Set defaults with project selection
.\configure_defaults.ps1 -Project "Project Alpha"

# List available projects first
.\configure_defaults.ps1 -ListProjects

# Set PAT token
.\configure_defaults.ps1 -PAT "your-pat-token"

# Validate configuration
.\configure_defaults.ps1 -Validate

# Reset to clean state
.\configure_defaults.ps1 -Reset
```

**Parameters:**
| Parameter | Description | Default |
|-----------|-------------|---------|
| `-Organization` | DevOps organization name | YOUR-ORG |
| `-Project` | Default project name | (prompts) |
| `-PAT` | Personal Access Token | (env var) |
| `-ListProjects` | List available projects | false |
| `-Validate` | Test connection after setup | false |
| `-Reset` | Clear all defaults | false |

### batch_update.ps1

Bulk update multiple work items at once.

```powershell
# Update state for multiple items
.\batch_update.ps1 -WorkItemIds 1,2,3,4,5 -State "Done"

# Assign to team member
.\batch_update.ps1 -WorkItemIds 100,101,102 -AssignedTo "ahmed@example.com"

# Update with hours (for marking tasks done)
.\batch_update.ps1 -WorkItemIds 200,201 -State "Done" -OriginalEstimate 8 -CompletedWork 6

# Run in parallel for speed
.\batch_update.ps1 -WorkItemIds (1..20) -State "Active" -Parallel

# Dry run to preview changes
.\batch_update.ps1 -WorkItemIds 1,2,3 -State "Done" -DryRun
```

**Parameters:**
| Parameter | Description | Required |
|-----------|-------------|----------|
| `-WorkItemIds` | Array of IDs to update | Yes |
| `-State` | New state value | No |
| `-AssignedTo` | Assign to user email | No |
| `-IterationPath` | Move to iteration | No |
| `-AreaPath` | Move to area | No |
| `-Priority` | Set priority (1-4) | No |
| `-OriginalEstimate` | Original estimate hours | No |
| `-CompletedWork` | Completed work hours | No |
| `-Parallel` | Run updates in parallel | No |
| `-DryRun` | Preview without changes | No |

### sprint_report.ps1

Generate comprehensive sprint reports.

```powershell
# Console output
.\sprint_report.ps1 -Project "Project Alpha" -Team "Project Alpha Team"

# Markdown format
.\sprint_report.ps1 -Project "Project Alpha" -OutputFormat Markdown

# Save to file
.\sprint_report.ps1 -Project "Project Alpha" -OutputFormat Markdown -OutputFile "sprint_report.md"

# Include build status
.\sprint_report.ps1 -Project "Project Alpha" -IncludeBuilds
```

**Output includes:**
- Sprint progress with visual bar
- Work items by state and type
- Story points velocity
- Team contribution breakdown
- Build health (if `-IncludeBuilds`)
- Blockers and high priority items

### pr_automation.ps1

Automate pull request workflows.

```powershell
# Create PR from current branch
.\pr_automation.ps1 -Action Create -Title "Feature: New Login" -WorkItems "123,124"

# Auto-complete approved PRs
.\pr_automation.ps1 -Action AutoComplete -Squash -DeleteSourceBranch

# Merge specific PRs
.\pr_automation.ps1 -Action Merge -PRIds 45,46,47 -Squash

# Add reviewers to active PRs
.\pr_automation.ps1 -Action AddReviewers -Reviewers "ahmed@example.com,mahmoud@example.com"

# Get PR summary
.\pr_automation.ps1 -Action Summary
```

**Actions:**
| Action | Description |
|--------|-------------|
| `Create` | Create new PR from current branch |
| `AutoComplete` | Set auto-complete on approved PRs |
| `Merge` | Complete/merge PRs |
| `AddReviewers` | Add reviewers to PRs |
| `Summary` | Show PR status summary |
| `Cleanup` | Delete merged branches |

---

## Hybrid Scripts (Python)

These scripts use Azure CLI for speed and can be enhanced with MCP for rich details.

### standup_generator.py

Generate daily standup notes.

```bash
# Basic usage
python standup_generator.py "Project Alpha"

# With specific format
python standup_generator.py "Project Alpha" --format markdown

# Save to file
python standup_generator.py "Project Alpha" --output standup.md

# Copy to clipboard (Windows)
python standup_generator.py "Project Alpha" --copy
```

**Output format:**
```markdown
# Daily Standup - 2025-12-25
**Project:** Project Alpha

## Yesterday
- [#1234] Completed login feature ✅
- [#1235] Fixed validation bug ✅

## Today
- [#1236] Working on dashboard 🔄
- [#1237] Review PR #45 📋

## Blockers
- None
```

### sprint_planner.py

Sprint planning with capacity analysis.

```bash
# Basic planning
python sprint_planner.py "Project Alpha"

# With custom capacity
python sprint_planner.py "Project Alpha" --capacity 200 --velocity 40

# Specific team
python sprint_planner.py "Project Alpha" --team "Backend Team"

# Save plan
python sprint_planner.py "Project Alpha" --output sprint_plan.md
```

**Features:**
- Current sprint metrics
- Backlog analysis
- Capacity-based suggestions
- Work item prioritization

### release_notes.py

Generate release notes from completed work.

```bash
# Generate from last 2 weeks
python release_notes.py "Project Alpha"

# Specific date range
python release_notes.py "Project Alpha" --since 2025-12-01

# Include PR analysis
python release_notes.py "Project Alpha" --repository "main-repo"

# With version number
python release_notes.py "Project Alpha" --version "2.0.0" --output CHANGELOG.md
```

**Output includes:**
- Breaking changes (tagged items)
- New features (User Stories)
- Bug fixes
- Improvements
- Contributors list
- Merged PRs

---

## MCP Scripts (Existing)

These scripts are designed to work with Claude and MCP tools.

### mention_helper.py
Processes @mentions in comments, resolving usernames to GUIDs.

### pr_analyzer.py
Analyzes pull requests for code review insights.

### sprint_report.py
MCP-based sprint report generation.

### standup_helper.py
MCP-based standup notes helper.

---

## Environment Variables

| Variable | Purpose | Used By |
|----------|---------|---------|
| `AZURE_DEVOPS_EXT_PAT` | CLI authentication | CLI scripts |
| `ADO_PAT_TOKEN` | MCP authentication | MCP scripts |
| `DEVOPS_HYBRID_MODE` | Enable hybrid mode | All scripts |

---

## Common Patterns

### Running from Claude

Claude can execute these scripts directly:

```
User: "Generate a sprint report for Project Alpha"

Claude: I'll run the sprint report script for you.
[Executes: .\scripts\cli\sprint_report.ps1 -Project "Project Alpha"]
```

### Batch Operations

For large operations, use CLI scripts with `-Parallel`:

```powershell
# Update 50 items in parallel
$ids = (Get-Content work_items.txt)
.\batch_update.ps1 -WorkItemIds $ids -State "Active" -Parallel
```

### Scheduled Automation

Use with Windows Task Scheduler or cron:

```powershell
# Daily standup (7:00 AM)
schtasks /create /tn "Daily Standup" /tr "powershell -File C:\scripts\standup.ps1" /sc daily /st 07:00
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "az not found" | Install Azure CLI or check PATH |
| "Not logged in" | Run `az devops login` or set PAT |
| "Project not found" | Check project name spelling |
| "Permission denied" | Verify PAT has required scopes |
| "Python not found" | Install Python 3.8+ |

---

## Contributing

1. Follow naming conventions:
   - CLI scripts: `verb_noun.ps1` (e.g., `batch_update.ps1`)
   - Python scripts: `noun_action.py` (e.g., `standup_generator.py`)

2. Include help documentation:
   - PowerShell: Use `<# .SYNOPSIS #>` comment blocks
   - Python: Use docstrings and argparse

3. Support common parameters:
   - `-DryRun` / `--dry-run`: Preview without changes
   - `-Verbose` / `--verbose`: Detailed output
   - `-Output` / `--output`: File output

---

*Part of DevOps Plugin v2.0.0 - Hybrid Mode*
