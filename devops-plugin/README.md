# DevOps Plugin for Claude Code

A comprehensive Azure DevOps integration plugin for Claude Code, enabling natural language interaction with your DevOps workflows.

**Version**: 1.3.0 | **Organization**: TaqaTechno

## Features

### Core Features
- **Work Item Management** - Create, update, query, and link work items
- **Pull Request Workflows** - Create, review, comment, and merge PRs
- **Pipeline Operations** - Run, monitor, and debug builds
- **Sprint Management** - Track progress, generate reports, prepare standups
- **Repository Access** - Browse code, commits, branches
- **Wiki Documentation** - Read, create, and update wiki pages
- **Code Search** - Search across repositories and work items

### New in v1.3.0
- **Required Field Validation** - Validates required fields before updates, asks user for missing values
- **State Transition Rules** - Enforces Task→Done requires Original Estimate + Completed Hours
- **User Story QC Checkpoint** - User Stories must pass through "Ready for QC" before Done
- **15 Team Members Cached** - PearlPixels and Taqat team members with smart aliases

### New in v1.1.0
- **Auto @Mention Processing** - Automatic user lookup and HTML formatting for mentions
- **Work Item Hierarchy Enforcement** - Tasks require parents, proper Epic→Feature→PBI→Task structure
- **What/How/Why Story Format** - Structured user story creation template
- **TODO Sync** - Sync Azure DevOps tasks to Claude Code TODO list

---

## Installation

### Quick Setup (Claude Code Assisted)

The easiest way to configure this plugin is using Claude Code:

```
/devops setup
```

Claude will automatically:
1. Detect your platform (Windows/macOS/Linux)
2. Find your settings file location
3. Guide you through PAT token creation
4. Configure the MCP server
5. Verify the installation

### Manual Installation

#### Step 1: Clone Plugin

Clone this repository to any location on your system.

#### Step 2: Prerequisites

- **Node.js 18+** required for MCP server

```bash
# Check Node.js version
node --version

# Install if needed:
# Windows: winget install OpenJS.NodeJS.LTS
# macOS: brew install node
# Ubuntu: sudo apt install nodejs npm
```

#### Step 3: Create Personal Access Token (PAT)

1. Go to: `https://dev.azure.com/{YOUR_ORG}/_usersSettings/tokens`
2. Click **"New Token"**
3. Configure:
   - **Name**: `Claude Code MCP`
   - **Expiration**: Choose appropriate duration
   - **Scopes**:
     - Code: Read, Write
     - Work Items: Read, Write, Manage
     - Build: Read, Execute
     - Release: Read, Write, Execute
     - Wiki: Read, Write
     - Test Management: Read
4. Click **"Create"** and **copy the token immediately**

#### Step 4: Configure MCP Server

**Find your Claude Code settings file:**

| Platform | Settings File Location |
|----------|------------------------|
| **Windows** | `%USERPROFILE%\.claude\settings.json` |
| **macOS** | `~/.claude/settings.json` |
| **Linux** | `~/.claude/settings.json` |

**Add the MCP server configuration:**

```json
{
  "mcpServers": {
    "azure-devops": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic-ai/azure-devops-mcp", "YOUR_ORGANIZATION"],
      "env": {
        "ADO_MCP_AUTH_TOKEN": "YOUR_PAT_TOKEN"
      }
    }
  }
}
```

Replace:
- `YOUR_ORGANIZATION` with your Azure DevOps organization name
- `YOUR_PAT_TOKEN` with your Personal Access Token

#### Step 5: Secure Token Storage (Recommended)

For better security, store your PAT as an environment variable:

**Windows (PowerShell as Admin):**
```powershell
[System.Environment]::SetEnvironmentVariable('ADO_PAT_TOKEN', 'your-pat-here', 'User')
```

**macOS/Linux (add to ~/.bashrc or ~/.zshrc):**
```bash
export ADO_PAT_TOKEN="your-pat-here"
```

**Then update settings.json to use the variable:**
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

#### Step 6: Restart Claude Code

Close and reopen Claude Code, then test:
```
"List my Azure DevOps projects"
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| MCP server not responding | Check Node.js installation (`node --version`) |
| Permission denied | Verify PAT scopes and expiration |
| Cannot find module | Run `npm cache clean --force` |
| Settings file not found | Create: `mkdir ~/.claude && echo {} > ~/.claude/settings.json` |

---

## Quick Commands

| Command | Description |
|---------|-------------|
| `/devops setup` | **NEW** - Configure MCP server (cross-platform) |
| `/devops status` | **NEW** - Check MCP connection status |
| `/sync-my-tasks` | Sync DevOps tasks to Claude TODO list |
| `/create-user-story` | Create story with What/How/Why format |
| `/standup` | Generate daily standup notes |
| `/sprint` | Sprint progress summary |
| `/my-tasks` | List your active work items |
| `/create-bug` | Create a new bug |
| `/create-task` | Create a new task (with parent enforcement) |
| `/build-status` | Check recent build status |

---

## User Guide

### Syncing Tasks to TODO List

Keep your Claude Code TODO list in sync with Azure DevOps using a **fast global query**:

```
/sync-my-tasks                           # Sync ALL tasks across all projects (fast!)
/sync-my-tasks --project "Relief Center" # Filter to specific project only
```

The command will:
- Use **single global WIQL query** (faster than per-project queries!)
- Include **project name** in each TODO item for easy identification
- Include **direct links** to work items in Azure DevOps
- Map states: Active → in_progress, New → pending
- Preserve your manually added TODOs

**TODO Format:**
```
[Relief Center] #1234 Task: Fix login bug | https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1234
```

### Creating Work Items with Hierarchy

The plugin enforces proper work item hierarchy:

```
Epic (Strategic Initiative)
  └── Feature (Functional Area)
        └── User Story / PBI (Requirement)
              └── Task (Technical Work)
                    └── Bug (Defect found during task)
```

**Key Rule**: Bugs MUST be under a Task (not standalone or under PBI directly).

**Creating a Task:**
```
"Create task: Fix login validation"
```
Claude will ask for a parent User Story/PBI before creating the task.

**Creating a Bug:**
```
"Create bug: Login button not responding"
```
Claude will ask: "Which Task is this bug related to?" before creating.

**Creating a User Story:**
```
/create-user-story
```
Claude will gather:
- **What?** - Requirements and acceptance criteria
- **How?** - Implementation approach
- **Why?** - Business value and impact

### Mentioning Team Members in Comments

When adding comments with @mentions:

```
"Add comment to #1234: @mahmoud please review this change"
```

The plugin automatically:
1. Detects @mentions in your text
2. Looks up user GUIDs
3. Formats as proper Azure DevOps HTML mentions
4. Sends the comment with working @mention notifications

**Quick Reference - TaqaTechno Team (GUIDs Cached):**

**PearlPixels Team (@pearlpixels.com):**
| Mention | Team Member | Email |
|---------|-------------|-------|
| @lakosha, @alakosha | Ahmed Abdelkhaleq Lakosha | alakosha@pearlpixels.com |
| @abdelaleem, @aabdelalem | Ahmed Abdelaleem | aabdelalem@pearlpixels.com |
| @eslam, @ehafez, @hafez | Eslam Hafez Mohamed | ehafez@pearlpixels.com |
| @mahmoud, @melshahed, @elshahed | Mahmoud Elshahed | melshahed@pearlpixels.com |
| @elafify, @melafify | Mahmoud Abdelrahman El-afify | melafify@pearlpixels.com |
| @hala, @hibrahim | Hala Ibrahim | hibrahim@pearlpixels.com |
| @sameh, @sabdlal | Sameh Abdlal Yussef Btaih | sabdlal@pearlpixels.com |
| @yussef, @yhussein | Yussef Hussein Hussein | yhussein@pearlpixels.com |
| @shehab, @sgamal, @gamal | Shehab Gamal | sgamal@pearlpixels.com |
| @mostafa, @mahmed | Mostafa Ahmed | mahmed@pearlpixels.com |

**Taqat Team (@Taqat.qa):**
| Mention | Team Member | Email |
|---------|-------------|-------|
| @ajay, @akuppakalathil | Ajay Kuppakalathil | akuppakalathil@Taqat.qa |
| @semir, @sworku, @worku | Semir Worku | sworku@Taqat.qa |
| @hacene, @hmeziani, @meziani | Hacene Meziani | hmeziani@Taqat.qa |
| @houssem, @hbenmbarek | Houssem Ben Mbarek | hbenmbarek@Taqat.qa |
| @muram, @mmakkawi, @makawi | Muram Makawi Abuzaid | mmakkawi@Taqat.qa |

**Disambiguation Notes:**
- Two Ahmeds: `@lakosha` for Ahmed Lakosha, `@abdelaleem` for Ahmed Abdelaleem
- Two Mahmouds: `@mahmoud` or `@elshahed` for Mahmoud Elshahed, `@elafify` for Mahmoud El-afify

---

## Usage Examples

### Work Items

```
"Show my active work items"
"Create bug: Login button not responding on mobile"
"Update task #1234 to Done"
"Link bug #456 to user story #123"
"Add comment to #1234: @eslam can you check this?"
```

### User Stories (What/How/Why)

```
"Create user story for implementing dark mode"

Claude will ask:
- What needs to be done? (Requirements)
- How should it be implemented? (Approach)
- Why is this important? (Business value)
```

### Pull Requests

```
"List open PRs"
"Review PR #45"
"Create PR from feature/auth to main"
"Merge PR #45"
```

### Builds

```
"Show recent builds"
"Why did build #789 fail?"
"Run CI pipeline"
```

### Sprint

```
"Sprint summary"
"Prepare standup notes"
"What's blocking the team?"
```

### TODO Sync

```
"/sync-my-tasks"
"Sync my tasks from Relief Center and Property Management"
```

---

## Developer Guide

### Plugin Structure

```
devops-plugin/
├── .claude-plugin/
│   └── plugin.json           # Plugin metadata (v1.2.0)
├── commands/                  # Slash commands
│   ├── devops.md             # NEW - Setup & configuration
│   ├── sync-my-tasks.md      # TODO sync command
│   ├── create-user-story.md  # Structured story creation
│   ├── create-task.md        # Updated - Hierarchy enforcement
│   ├── create-bug.md
│   ├── my-tasks.md
│   ├── standup.md
│   ├── sprint.md
│   └── build-status.md
├── devops/                    # Main skill
│   ├── SKILL.md              # Core skill (550+ lines)
│   ├── REFERENCE.md          # API reference (720+ lines)
│   ├── EXAMPLES.md           # Usage examples
│   └── scripts/
│       ├── mention_helper.py # NEW - @mention processing
│       ├── pr_analyzer.py
│       ├── sprint_report.py
│       └── standup_helper.py
├── hooks/
│   └── hooks.json            # Context hooks
├── LICENSE
└── README.md
```

### Adding New Commands

Create a new `.md` file in `commands/`:

```markdown
---
title: 'Command Name'
read_only: false           # true for read-only commands
type: 'command'
description: 'What this command does'
---

# Command Name

Description and instructions...

## Instructions
1. Step one
2. Step two

## Example
...
```

### Extending the Skill

Edit `devops/SKILL.md` to add:
- New tool references
- WIQL query templates
- Workflow patterns
- Best practices

### Adding Hooks

Edit `hooks/hooks.json` to add contextual suggestions:

```json
{
  "PostToolUse": [
    {
      "name": "Hook name",
      "matcher": "regex pattern",
      "description": "When to trigger",
      "hooks": [
        {
          "type": "suggestion",
          "message": "Suggestion text"
        }
      ]
    }
  ]
}
```

### Work Item Hierarchy Rules

When modifying work item creation:

1. **Bugs** - MUST have parent (Task) - bugs discovered during task work
2. **Tasks** - MUST have parent (User Story/PBI)
3. **PBIs** - MUST have parent (Feature)
4. **Features** - MUST have parent (Epic)
5. **Epics** - Top-level, no parent required

**Hierarchy Flow**: Epic → Feature → PBI → Task → Bug

### Mention Processing

Use the `mention_helper.py` script:

```python
from mention_helper import extract_mentions, format_mention_html

# Extract @mentions
mentions = extract_mentions("Review this @mahmoud")
# Returns: ['mahmoud']

# Format for Azure DevOps
html = format_mention_html("guid-123", "Mahmoud Elshahed")
# Returns: '<a href="#" data-vss-mention="version:2.0,guid:guid-123">@Mahmoud Elshahed</a>'
```

### TODO Sync Format & State Mapping

**TODO Content Format:**
```
[{PROJECT_NAME}] #{ID} {TYPE}: {TITLE} | {LINK}
```

Example:
```
[Relief Center] #1234 Task: Fix login bug | https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1234
```

**State Mapping:**
| Azure DevOps State | TODO Status |
|-------------------|-------------|
| New, To Do | pending |
| Active, In Progress | in_progress |
| Done, Closed | completed |
| Removed | (skip) |

**Performance:**
- Uses single global WIQL query across all projects
- ~500ms total vs N * 500ms for per-project queries

---

## Documentation

- [SKILL.md](devops/SKILL.md) - Complete skill reference with hierarchy rules
- [REFERENCE.md](devops/REFERENCE.md) - Tool and WIQL reference
- [EXAMPLES.md](devops/EXAMPLES.md) - Usage examples

---

## Requirements

- Claude Code CLI
- Azure DevOps account with PAT
- Node.js 18+ (for MCP server)

## PAT Scopes Required

- Code (Read, Write)
- Work Items (Read, Write)
- Build (Read, Execute)
- Wiki (Read, Write)
- Test Management (Read)

---

## Changelog

### v1.3.0 (2024-12)
- **Added** Required field validation before create/update operations
- **Added** State transition validation rules (Task→Done requires hours)
- **Added** User Story→Done requires "Ready for QC" state first (QA checkpoint)
- **Added** Pre-update validation workflow with user prompts
- **Added** Proactive missing field detection and user guidance
- **Added** 6 new team members to mention cache (15 total)
- **Added** Bug→Task hierarchy rule (bugs must be under tasks)
- **Updated** SKILL.md with comprehensive validation section (300+ lines)
- **Updated** User Story state machine with mandatory QC checkpoint
- **Updated** Error handling with field validation guidance
- **Updated** Hierarchy: Epic→Feature→PBI→Task→Bug
- **Fixed** Don't silently skip required fields - ask user instead
- **Fixed** User Stories cannot skip to Done without QA review

### v1.2.0 (2024-12)
- **Added** `/devops setup` command for cross-platform MCP configuration
- **Added** `/devops status` command to check MCP connection
- **Added** Platform detection (Windows/macOS/Linux)
- **Added** Environment variable support for secure PAT storage
- **Added** Claude Code assisted setup workflow
- **Updated** Installation guide with cross-platform instructions
- **Updated** Troubleshooting section with common issues

### v1.1.2 (2024-12)
- **Fixed** Critical: `search_workitem` returns 0 results for field filters
- **Added** Clear warnings: `search_workitem` is TEXT SEARCH only, not field filter
- **Updated** Recommended tool: `wit_my_work_items` for "Assigned to Me" queries
- **Updated** Tool reference tables with correct MCP tool names
- **Updated** `/sync-my-tasks` workflow to use `wit_my_work_items` per project

### v1.1.1 (2024-12)
- **Enhanced** `/sync-my-tasks` with global WIQL query (faster!)
- **Enhanced** TODO format now includes project name and direct link
- **Added** WIQL query reference section with common queries

### v1.1.0 (2024-12)
- **Added** `/sync-my-tasks` command for TODO list synchronization
- **Added** `/create-user-story` command with What/How/Why format
- **Added** `mention_helper.py` for automatic @mention processing
- **Updated** Work item creation with hierarchy enforcement
- **Updated** `create-task.md` to require parent work item
- **Added** Sync suggestion hook on session start

### v1.0.0 (2024-11)
- Initial release with core DevOps features
- 100+ tools across 10 domains
- 6 slash commands
- WIQL query support

---

## Support

- **Organization**: TaqaTechno
- **Email**: info@taqatechno.com
- **Repository**: https://github.com/taqat-techno-eg/plugins

## License

MIT License - see [LICENSE](LICENSE)
