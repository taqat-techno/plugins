---
title: 'DevOps'
read_only: false
type: 'command'
description: 'Azure DevOps integration skill for TaqaTechno organization. Manages work items, pull requests, pipelines, repositories, wiki, test plans, and security alerts through the official Microsoft Azure DevOps MCP server. Use when user asks about: tasks, bugs, PRs, builds, sprints, standups, code reviews, deployments, or any Azure DevOps operations.'
---

# Azure DevOps Integration

Comprehensive Azure DevOps integration via MCP server with 100+ tools.

## Sub-Commands

| Sub-Command | Description |
|-------------|-------------|
| `/devops setup` | Configure Azure DevOps MCP server |
| `/devops status` | Check MCP server connection status |
| `/devops help` | Show available DevOps capabilities |

---

## `/devops setup` - MCP Server Configuration

### Step 1: Detect Platform and Settings Location

**Detect the user's platform and Claude Code settings file location:**

| Platform | Settings File Location |
|----------|------------------------|
| **Windows** | `%USERPROFILE%\.claude\settings.json` or `C:\Users\{USERNAME}\.claude\settings.json` |
| **macOS** | `~/.claude/settings.json` or `/Users/{USERNAME}/.claude/settings.json` |
| **Linux/Ubuntu** | `~/.claude/settings.json` or `/home/{USERNAME}/.claude/settings.json` |

**Quick Detection Commands:**

```bash
# Windows (PowerShell)
echo $env:USERPROFILE\.claude\settings.json

# Windows (CMD)
echo %USERPROFILE%\.claude\settings.json

# macOS/Linux
echo ~/.claude/settings.json
```

### Step 2: Gather Configuration Information

**Ask the user for:**
1. **Organization Name** (required): Azure DevOps organization (e.g., `TaqaTechno`, `MyCompany`)
2. **PAT Token** (required): Personal Access Token from Azure DevOps

**How to create a PAT token:**
1. Go to `https://dev.azure.com/{organization}/_usersSettings/tokens`
2. Click "New Token"
3. Give it a name (e.g., "Claude Code MCP")
4. Select required scopes:
   - **Code**: Read, Write
   - **Work Items**: Read, Write, Manage
   - **Build**: Read, Execute
   - **Release**: Read, Write, Execute
   - **Wiki**: Read, Write
   - **Test Management**: Read
5. Click "Create" and copy the token

### Step 3: Configure MCP Server

**Read current settings file or create new one:**

```javascript
// Read existing settings
Read({ file_path: "{SETTINGS_PATH}" })

// If file doesn't exist, create with base structure
```

**MCP Server Configuration (add to mcpServers object):**

```json
{
  "mcpServers": {
    "azure-devops": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic-ai/azure-devops-mcp", "{ORGANIZATION_NAME}"],
      "env": {
        "ADO_MCP_AUTH_TOKEN": "{PAT_TOKEN}"
      }
    }
  }
}
```

**IMPORTANT Security Notes:**
- Never commit PAT tokens to version control
- Consider using environment variables for tokens in shared configs:
  ```json
  "env": {
    "ADO_MCP_AUTH_TOKEN": "${ADO_PAT_TOKEN}"
  }
  ```
  Then set `ADO_PAT_TOKEN` in your system environment

### Step 4: Environment Variable Setup (Recommended)

**For enhanced security, set PAT as system environment variable:**

**Windows (PowerShell - Admin):**
```powershell
[System.Environment]::SetEnvironmentVariable('ADO_PAT_TOKEN', 'your-pat-token-here', 'User')
```

**Windows (CMD - Admin):**
```cmd
setx ADO_PAT_TOKEN "your-pat-token-here"
```

**macOS/Linux (add to ~/.bashrc or ~/.zshrc):**
```bash
export ADO_PAT_TOKEN="your-pat-token-here"
```

**Then use in settings.json:**
```json
{
  "mcpServers": {
    "azure-devops": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic-ai/azure-devops-mcp", "{ORGANIZATION_NAME}"],
      "env": {
        "ADO_MCP_AUTH_TOKEN": "${ADO_PAT_TOKEN}"
      }
    }
  }
}
```

### Step 5: Verify Installation

**Prerequisites Check:**
```bash
# Check Node.js version (requires 18+)
node --version

# Check npm
npm --version

# Test npx
npx --version
```

**If Node.js is not installed:**
- Windows: Download from https://nodejs.org/ or use `winget install OpenJS.NodeJS.LTS`
- macOS: `brew install node` or download from https://nodejs.org/
- Ubuntu: `sudo apt update && sudo apt install nodejs npm`

### Step 6: Restart Claude Code

**After configuration:**
1. Close Claude Code completely
2. Reopen Claude Code
3. Test with: "List my Azure DevOps projects"

---

## `/devops status` - Check Connection

**Verify MCP server is working:**

```javascript
// Try to list projects - this will test the connection
mcp__azure-devops__core_list_projects({})
```

**Expected Response:**
- Success: Returns list of projects in the organization
- Error: Check PAT token, organization name, or Node.js installation

---

## `/devops help` - Capabilities Overview

**Available Tool Categories:**

| Category | Tools | Examples |
|----------|-------|----------|
| **Work Items** | 20+ | Create, update, query, link, comment |
| **Repositories** | 15+ | List repos, branches, commits, PRs |
| **Pull Requests** | 10+ | Create, review, approve, merge |
| **Pipelines** | 10+ | Run builds, view logs, check status |
| **Wiki** | 5+ | Read, create, update pages |
| **Search** | 3+ | Code search, work item search, wiki search |
| **Test Plans** | 5+ | Create plans, suites, test cases |
| **Security** | 2+ | View advanced security alerts |

**Quick Commands:**
- `/my-tasks` - List your active work items
- `/standup` - Generate daily standup notes
- `/sprint` - Sprint progress summary
- `/create-task` - Create new task (with hierarchy)
- `/create-user-story` - Create story with What/How/Why format
- `/create-bug` - Create new bug
- `/sync-my-tasks` - Sync tasks to TODO list
- `/build-status` - Check recent builds

---

## Example Setup Session

**User:** `/devops setup`

**Claude:**
```
Let me help you configure the Azure DevOps MCP server.

First, I'll detect your platform and settings location...

Your platform: Windows
Settings file: C:\Users\ahmed\.claude\settings.json

I need some information:
1. What is your Azure DevOps organization name?
2. Do you have a Personal Access Token (PAT)?

If you don't have a PAT yet, here's how to create one:
1. Go to: https://dev.azure.com/_usersSettings/tokens
2. Click "New Token"
3. Name: "Claude Code MCP"
4. Scopes: Code (Read/Write), Work Items (Read/Write/Manage), Build (Read/Execute), Wiki (Read/Write)
5. Click "Create" and copy the token
```

**User:** Organization is TaqaTechno, here's my PAT: [token]

**Claude:**
```
Great! I'll configure the MCP server now.

Reading your current settings...
Adding azure-devops MCP server configuration...

Configuration added successfully!

Next steps:
1. Restart Claude Code
2. Test with: "List my projects"

Optional: For better security, set your PAT as an environment variable:
[System.Environment]::SetEnvironmentVariable('ADO_PAT_TOKEN', 'your-token', 'User')

Then I can update the config to use ${ADO_PAT_TOKEN} instead.
```

---

## Troubleshooting

### "MCP server not responding"
1. Check Node.js is installed: `node --version`
2. Verify PAT token is valid and not expired
3. Ensure organization name is correct
4. Restart Claude Code

### "Permission denied" errors
1. Check PAT token has required scopes
2. Verify you have access to the project/resource
3. Token may have expired - create a new one

### "Cannot find module" errors
```bash
# Clear npm cache and retry
npm cache clean --force

# Or install the MCP package manually
npm install -g @anthropic-ai/azure-devops-mcp
```

### Settings file not found
```bash
# Create the .claude directory
# Windows
mkdir %USERPROFILE%\.claude

# macOS/Linux
mkdir -p ~/.claude

# Create empty settings.json
echo {} > ~/.claude/settings.json
```
