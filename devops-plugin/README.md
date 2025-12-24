# DevOps Plugin for Claude Code

A comprehensive Azure DevOps integration plugin for Claude Code, enabling natural language interaction with your DevOps workflows.

**Version**: 1.1.0 | **Organization**: TaqaTechno

## Features

### Core Features
- **Work Item Management** - Create, update, query, and link work items
- **Pull Request Workflows** - Create, review, comment, and merge PRs
- **Pipeline Operations** - Run, monitor, and debug builds
- **Sprint Management** - Track progress, generate reports, prepare standups
- **Repository Access** - Browse code, commits, branches
- **Wiki Documentation** - Read, create, and update wiki pages
- **Code Search** - Search across repositories and work items

### New in v1.1.0
- **Auto @Mention Processing** - Automatic user lookup and HTML formatting for mentions
- **Work Item Hierarchy Enforcement** - Tasks require parents, proper Epic→Feature→PBI→Task structure
- **What/How/Why Story Format** - Structured user story creation template
- **TODO Sync** - Sync Azure DevOps tasks to Claude Code TODO list

---

## Installation

1. Clone this plugin to your Claude Code plugins directory
2. Configure Azure DevOps MCP server in your settings
3. Restart Claude Code

### MCP Server Configuration

Add to your `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "azure-devops": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@azure-devops/mcp", "TaqaTechno"],
      "env": {
        "ADO_MCP_AUTH_TOKEN": "YOUR_PAT_TOKEN"
      }
    }
  }
}
```

---

## Quick Commands

| Command | Description |
|---------|-------------|
| `/sync-my-tasks` | **NEW** - Sync DevOps tasks to Claude TODO list |
| `/create-user-story` | **NEW** - Create story with What/How/Why format |
| `/standup` | Generate daily standup notes |
| `/sprint` | Sprint progress summary |
| `/my-tasks` | List your active work items |
| `/create-bug` | Create a new bug |
| `/create-task` | Create a new task (with parent enforcement) |
| `/build-status` | Check recent build status |

---

## User Guide

### Syncing Tasks to TODO List

Keep your Claude Code TODO list in sync with Azure DevOps:

```
/sync-my-tasks                    # Auto-detect project from git
/sync-my-tasks Relief Center      # Sync from specific project
/sync-my-tasks --all              # Sync from all projects
```

The command will:
- Fetch work items assigned to you
- Map Azure DevOps states to TODO states (Active → in_progress, New → pending)
- Add new items and update existing ones
- Preserve your manually added TODOs

### Creating Work Items with Hierarchy

The plugin enforces proper work item hierarchy:

```
Epic (Strategic Initiative)
  └── Feature (Functional Area)
        └── User Story / PBI (Requirement)
              ├── Task (Technical Work)
              └── Bug (Defect)
```

**Creating a Task:**
```
"Create task: Fix login validation"
```
Claude will ask for a parent PBI/Bug before creating the task.

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

**Quick Reference - TaqaTechno Team:**
| Mention | Team Member |
|---------|-------------|
| @ahmed | Ahmed Abdelkhaleq |
| @eslam | Eslam Hafez Mohamed |
| @yussef | Yussef Hussein Hussein |
| @sameh | Sameh Abdlal Yussef |
| @mahmoud | Mahmoud Elshahed |

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
│   └── plugin.json           # Plugin metadata (v1.1.0)
├── commands/                  # Slash commands
│   ├── sync-my-tasks.md      # NEW - TODO sync command
│   ├── create-user-story.md  # NEW - Structured story creation
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

1. **Tasks** - MUST have parent (Bug or PBI)
2. **Bugs** - SHOULD have parent (PBI) but can be standalone
3. **PBIs** - MUST have parent (Feature)
4. **Features** - MUST have parent (Epic)
5. **Epics** - Top-level, no parent required

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

### TODO Sync State Mapping

| Azure DevOps State | TODO Status |
|-------------------|-------------|
| New, To Do | pending |
| Active, In Progress | in_progress |
| Done, Closed | completed |
| Removed | (skip) |

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
