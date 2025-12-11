# DevOps Plugin for Claude Code

A comprehensive Azure DevOps integration plugin for Claude Code, enabling natural language interaction with your DevOps workflows.

## Features

- **Work Item Management** - Create, update, query, and link work items
- **Pull Request Workflows** - Create, review, comment, and merge PRs
- **Pipeline Operations** - Run, monitor, and debug builds
- **Sprint Management** - Track progress, generate reports, prepare standups
- **Repository Access** - Browse code, commits, branches
- **Wiki Documentation** - Read, create, and update wiki pages
- **Code Search** - Search across repositories and work items

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
      "args": ["-y", "@azure-devops/mcp", "YOUR_ORG_NAME"],
      "env": {
        "ADO_MCP_AUTH_TOKEN": "YOUR_PAT_TOKEN"
      }
    }
  }
}
```

## Quick Commands

| Command | Description |
|---------|-------------|
| `/standup` | Generate daily standup notes |
| `/sprint` | Sprint progress summary |
| `/my-tasks` | List your active work items |
| `/create-bug` | Create a new bug |
| `/create-task` | Create a new task |
| `/build-status` | Check recent build status |

## Usage Examples

### Work Items

```
"Show my active work items"
"Create bug: Login button not responding on mobile"
"Update task #1234 to Done"
"Link bug #456 to user story #123"
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

## Documentation

- [SKILL.md](devops/SKILL.md) - Complete skill reference
- [REFERENCE.md](devops/REFERENCE.md) - Tool and WIQL reference
- [EXAMPLES.md](devops/EXAMPLES.md) - Usage examples

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

## Support

- **Organization**: TaqaTechno
- **Email**: info@taqatechno.com
- **Repository**: https://github.com/taqat-techno-eg/plugins

## License

MIT License - see [LICENSE](LICENSE)
