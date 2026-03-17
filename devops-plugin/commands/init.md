---
title: 'Init'
read_only: false
type: 'command'
description: 'Complete Azure DevOps integration - installs CLI, configures MCP, and enables hybrid mode for best performance. Use when user asks about DevOps setup, configuration, or status via /init.'
---

# Azure DevOps Integration - Unified Setup

Complete Azure DevOps integration with BOTH CLI and MCP for optimal performance.

## Sub-Commands

| Sub-Command | Description |
|-------------|-------------|
| `/init setup` | **Full setup**: CLI installation + MCP configuration |
| `/init setup --cli` | Install Azure DevOps CLI only |
| `/init setup --mcp` | Configure MCP server only |
| `/init status` | Check both CLI and MCP connection status |
| `/init upgrade` | Upgrade CLI and MCP to latest versions |
| `/init profile` | Build/refresh user profile (DevOps.md) |
| `/init profile --refresh` | Re-fetch all data from Azure DevOps |
| `/init profile --role` | Change your role only |
| `/init profile --team` | Refresh team members only |
| `/init help` | Show available DevOps capabilities |

---

## `/init setup` - Complete Installation

### Overview

This command performs a complete setup of Azure DevOps integration:
1. Installs Azure CLI (if not present)
2. Adds Azure DevOps CLI extension
3. Configures CLI defaults and authentication
4. Configures MCP server in Claude settings
5. Validates both are working
6. Enables hybrid mode

---

### Phase 1: Environment Detection

**Step 1.1: Detect Platform**

```bash
# Windows detection
if ($env:OS -eq "Windows_NT") { "Windows" }

# macOS detection
if [[ "$OSTYPE" == "darwin"* ]]; then echo "macOS"; fi

# Linux detection
if [[ "$OSTYPE" == "linux-gnu"* ]]; then echo "Linux"; fi
```

**Step 1.2: Locate Settings File**

| Platform | Settings File Location |
|----------|------------------------|
| **Windows** | `C:\Users\{USERNAME}\.claude\settings.json` |
| **macOS** | `/Users/{USERNAME}/.claude/settings.json` |
| **Linux** | `/home/{USERNAME}/.claude/settings.json` |

**Step 1.3: Check Prerequisites**

```bash
# Check Node.js (required for MCP)
node --version  # Must be 18+

# Check npm/npx
npx --version
```

---

### Phase 2: Azure CLI Installation

**Step 2.1: Check if Azure CLI is installed**

```bash
az --version
```

**Step 2.2: Install Azure CLI (if not present)**

#### Windows Installation

```powershell
# Option 1: Winget (Recommended - fastest)
winget install -e --id Microsoft.AzureCLI

# Option 2: Chocolatey
choco install azure-cli -y

# Option 3: PowerShell direct download
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'
Remove-Item .\AzureCLI.msi
```

#### macOS Installation

```bash
# Homebrew (Recommended)
brew update && brew install azure-cli

# Alternative: Direct script
curl -L https://aka.ms/InstallAzureCli | bash
```

#### Linux Installation

```bash
# Ubuntu/Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# RHEL/CentOS/Fedora
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
sudo dnf install -y https://packages.microsoft.com/config/rhel/8/packages-microsoft-prod.rpm
sudo dnf install azure-cli -y

# Alternative: pip install
pip install azure-cli
```

---

### Phase 3: Azure DevOps CLI Extension

**Step 3.1: Install the DevOps extension**

```bash
# Install extension
az extension add --name azure-devops

# Or upgrade if already installed
az extension add --name azure-devops --upgrade
```

**Step 3.2: Verify installation**

```bash
# Check extension is installed
az extension show --name azure-devops

# Expected output includes:
# "name": "azure-devops"
# "version": "1.x.x"
```

---

### Phase 4: Gather User Information

**Ask user for required information:**

1. **Organization Name** (required)
   - Example: `YOUR-ORG`, `MyCompany`
   - Used for both CLI and MCP configuration

2. **Personal Access Token (PAT)** (required)
   - Must have scopes: Code, Work Items, Build, Wiki, Test Management
   - Will be stored securely as environment variable

3. **Default Project** (optional)
   - Sets default project for CLI commands
   - Example: `Project Alpha`, `My Project`

**How to create a PAT:**

1. Go to: `https://dev.azure.com/{ORGANIZATION}/_usersSettings/tokens`
2. Click **"New Token"**
3. Configure:
   - **Name**: `Claude Code Integration`
   - **Expiration**: 90 days (or custom)
   - **Scopes** (select these):
     - Code: Read, Write
     - Work Items: Read, Write, Manage
     - Build: Read, Execute
     - Release: Read, Write, Execute
     - Wiki: Read, Write
     - Test Management: Read
     - Graph: Read (for user lookups)
4. Click **"Create"** and **copy the token immediately**

---

### Phase 5: CLI Configuration

**Step 5.1: Set organization default**

```bash
az devops configure --defaults organization=https://dev.azure.com/{ORGANIZATION}
```

**Step 5.2: Set project default (optional)**

```bash
az devops configure --defaults project="{PROJECT_NAME}"
```

**Step 5.3: Configure PAT authentication**

#### Option A: Environment Variable (Recommended for security)

**Windows (PowerShell as Admin):**
```powershell
# Set for current user (persistent)
[System.Environment]::SetEnvironmentVariable('AZURE_DEVOPS_EXT_PAT', '{PAT_TOKEN}', 'User')

# Also set for MCP server
[System.Environment]::SetEnvironmentVariable('ADO_PAT_TOKEN', '{PAT_TOKEN}', 'User')

# Refresh current session
$env:AZURE_DEVOPS_EXT_PAT = '{PAT_TOKEN}'
$env:ADO_PAT_TOKEN = '{PAT_TOKEN}'
```

**macOS/Linux (add to ~/.bashrc or ~/.zshrc):**
```bash
# Add to shell profile
echo 'export AZURE_DEVOPS_EXT_PAT="{PAT_TOKEN}"' >> ~/.bashrc
echo 'export ADO_PAT_TOKEN="{PAT_TOKEN}"' >> ~/.bashrc

# Reload profile
source ~/.bashrc
```

#### Option B: Interactive Login

```bash
az devops login --organization https://dev.azure.com/{ORGANIZATION}
# Paste PAT when prompted
```

**Step 5.4: Verify CLI authentication**

```bash
# Test CLI connection
az devops project list --output table
```

---

### Phase 6: MCP Server Configuration

**Step 6.1: Read or create settings.json**

```javascript
// Read existing settings
Read({ file_path: "{SETTINGS_PATH}" })

// If file doesn't exist or empty, start with base structure
{
  "mcpServers": {}
}
```

**Step 6.2: Add MCP server configuration**

```json
{
  "mcpServers": {
    "azure-devops": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic-ai/azure-devops-mcp", "{ORGANIZATION}"],
      "env": {
        "ADO_MCP_AUTH_TOKEN": "${ADO_PAT_TOKEN}"
      }
    }
  }
}
```

**IMPORTANT**: Use `${ADO_PAT_TOKEN}` to reference the environment variable, not the actual token.

**Step 6.3: Write updated settings**

```javascript
// Merge with existing settings and write
Write({ file_path: "{SETTINGS_PATH}", content: JSON.stringify(settings, null, 2) })
```

---

### Phase 7: Enable Hybrid Mode

**Set environment variable to enable hybrid mode:**

**Windows:**
```powershell
[System.Environment]::SetEnvironmentVariable('DEVOPS_HYBRID_MODE', 'true', 'User')
```

**macOS/Linux:**
```bash
echo 'export DEVOPS_HYBRID_MODE="true"' >> ~/.bashrc
source ~/.bashrc
```

---

### Phase 8: Validation

**Step 8.1: Validate CLI**

```bash
# Check Azure CLI version (should be 2.30.0+)
az --version

# Check DevOps extension
az extension show --name azure-devops --query "version" -o tsv

# Test project listing
az devops project list --output table
```

**Step 8.2: Validate MCP**

```javascript
// Test MCP connection by listing projects
mcp__azure-devops__core_list_projects({})
```

**Step 8.3: Report Status**

```
====================================================
  AZURE DEVOPS INTEGRATION - SETUP COMPLETE
====================================================

CLI STATUS:
  Azure CLI Version:     2.65.0
  DevOps Extension:      1.0.1
  Organization:          YOUR-ORG
  Default Project:       Project Alpha
  Authentication:        PAT via AZURE_DEVOPS_EXT_PAT

MCP STATUS:
  Package:               @anthropic-ai/azure-devops-mcp
  Organization:          YOUR-ORG
  Authentication:        PAT via ADO_PAT_TOKEN
  Tools Available:       100+

HYBRID MODE:             ENABLED

NEXT STEPS:
  1. Restart Claude Code to activate MCP
  2. Test with: "List my projects"
  3. Use /init status to check anytime

====================================================
```

---

### Phase 9: Restart Instructions

**IMPORTANT: Claude Code must be restarted for MCP to take effect.**

```
To complete setup:
1. Close Claude Code completely
2. Reopen Claude Code
3. Test with: "List my Azure DevOps projects"
```

---

## `/init profile` - Build User Profile

Create or refresh your personal DevOps profile at `~/.claude/devops.md`. This file caches your identity, projects, team members, and preferences for instant resolution.

### Why This Matters

Without a profile:
- "assign to me" requires an API call to resolve your identity every time
- "@mahmoud" requires an API call to resolve the GUID every time
- Your role/task prefix must be inferred from keywords
- Project context is lost between sessions

With a profile:
- "assign to me" → instant (cached GUID)
- "@mahmoud" → instant (cached GUID from team members)
- Task prefix auto-applied from your role
- Project context persists across sessions

### Profile Generation Workflow

**Reference**: `devops/profile_generator.md`

#### Step 1: Resolve Your Identity

```javascript
// Get current authenticated user
mcp__azure-devops__core_get_connection_data({})
// Returns: authenticatedUser with id, displayName, uniqueName

// Get full identity details
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": authenticatedUser.uniqueName
})
```

#### Step 2: Fetch Your Projects & Teams

```javascript
// List all projects
const projects = await mcp__azure-devops__core_list_projects({})

// For each project, find teams you belong to
for (const project of projects) {
  const teams = await mcp__azure-devops__work_list_teams({ "project": project.name })
  // Check membership in each team
}
```

#### Step 3: Fetch Team Members

```javascript
// For each of your teams, get all members with GUIDs
for (const team of userTeams) {
  const members = await mcp__azure-devops__work_get_team_members({
    "project": team.project,
    "team": team.name
  })
  // Resolve each member's GUID via core_get_identity_ids
}
```

#### Step 4: Ask for Your Role

```
What is your primary role?

| # | Role | Task Prefix | Description |
|---|------|-------------|-------------|
| 1 | Backend Developer | [DEV] | APIs, database, server-side |
| 2 | Frontend Developer | [FRONT] | UI, CSS, JavaScript |
| 3 | Full-Stack Developer | [DEV] | Both backend and frontend |
| 4 | QA / Tester | [QA] | Testing, verification |
| 5 | DevOps Engineer | [IMP] | Infrastructure, CI/CD |
| 6 | Project Manager | [IMP] | Planning, coordination |
| 7 | Team Lead | [IMP] | Technical leadership |
```

#### Step 5: Generate ~/.claude/devops.md

Use the template from `data/profile_template.md` and fill with collected data.

#### Step 6: Confirm

```
User Profile created at ~/.claude/devops.md

Identity: Ahmed Mohamed (ahmed@company.com)
Role: Developer → Task prefix: [DEV]
Projects: 2 (Project Alpha, Project Beta)
Team Members: 5 cached with GUIDs

This file is used as context for all DevOps operations.
- "assign to me" → uses your cached GUID
- "@teammate" → uses cached team member GUIDs
- /create tasks → auto-applies your [DEV] prefix
```

### Refresh Options

| Flag | What It Does |
|------|-------------|
| `--refresh` | Re-fetch everything from Azure DevOps (identity, projects, teams, repos) |
| `--role` | Change your role and task prefix only (no API calls) |
| `--team` | Refresh team members only (fetch latest from Azure DevOps) |

### Example Session

**User**: `/init profile`

**Claude**:
```
Building your DevOps profile...

Step 1: Resolving your identity...
  Found: Ahmed Mohamed (ahmed@company.com)

Step 2: Fetching your projects...
  Found 2 projects: Project Alpha, Project Beta

Step 3: Fetching team members...
  Found 5 team members across 2 teams

Step 4: What is your primary role?
  1. Backend Developer [DEV]
  2. Frontend Developer [FRONT]
  3. Full-Stack Developer [DEV]
  4. QA / Tester [QA]
  5. DevOps Engineer [IMP]
  6. Project Manager [IMP]
  7. Team Lead [IMP]
```

**User**: 1

**Claude**:
```
Profile created at ~/.claude/devops.md

Identity: Ahmed Mohamed (ahmed@company.com)
Role: Backend Developer → [DEV]
Default Project: Project Alpha
Team: Project Alpha Team
Team Members: 5 cached

Your profile will be loaded automatically at session start.
```

---

## `/init setup --cli` - CLI Only Installation

Run only the CLI installation phases (2-5) without MCP configuration.

**Use case**: When MCP is already configured but CLI is missing.

```
/init setup --cli
```

---

## `/init setup --mcp` - MCP Only Configuration

Run only the MCP configuration phases (6) without CLI installation.

**Use case**: When CLI is already installed but MCP needs configuration.

```
/init setup --mcp
```

---

## `/init status` - Check Status

**Comprehensive status check for both CLI and MCP:**

### CLI Status Check

```bash
# Check CLI version
az --version 2>&1

# Check extension
az extension show --name azure-devops 2>&1

# Check defaults
az devops configure --list 2>&1

# Test connection
az devops project list --output table 2>&1
```

### MCP Status Check

```javascript
// Test MCP by listing projects
mcp__azure-devops__core_list_projects({})
```

### Status Report Format

```
====================================================
  AZURE DEVOPS INTEGRATION STATUS
====================================================

CLI STATUS:
  Installed:             YES
  Azure CLI Version:     2.65.0
  DevOps Extension:      1.0.1 (azure-devops)
  Organization Default:  https://dev.azure.com/YOUR-ORG
  Project Default:       Project Alpha
  PAT Configured:        YES (via AZURE_DEVOPS_EXT_PAT)
  Connection Test:       SUCCESS (5 projects found)

MCP STATUS:
  Configured:            YES
  Server Package:        @anthropic-ai/azure-devops-mcp
  Organization:          YOUR-ORG
  PAT Configured:        YES (via ADO_PAT_TOKEN)
  Connection Test:       SUCCESS (5 projects found)
  Tools Available:       100+ across 10 domains

HYBRID MODE:             ENABLED

CAPABILITIES:
  CLI-Exclusive:         Variables, Extensions, Service Connections
  MCP-Exclusive:         Test Plans, Search, Security Alerts
  Hybrid:                Work Items, PRs, Pipelines, Wiki

RECOMMENDATIONS:
  - All systems operational
  - Consider updating CLI (newer version available)

====================================================
```

---

## `/init upgrade` - Upgrade Components

**Upgrade both CLI extension and MCP package:**

### Upgrade CLI Extension

```bash
az extension update --name azure-devops
```

### Upgrade MCP Package

MCP package updates automatically with `npx -y` flag, but you can clear cache:

```bash
# Clear npm cache to force latest version
npm cache clean --force

# Or remove cached package
npx clear-npx-cache
```

### Verify Upgrades

```bash
# Check CLI extension version
az extension show --name azure-devops --query "version"

# MCP will use latest on next Claude restart
```

---

## `/init help` - Capabilities Overview

### Available Tool Categories

| Category | CLI | MCP | Tools |
|----------|:---:|:---:|-------|
| **Work Items** | Y | Y | Create, update, query, link, comment |
| **Pull Requests** | Y | Y | Create, review, merge, threads |
| **Pipelines** | Y | Y | Run, monitor, logs |
| **Repositories** | Y | Y | List, branches, commits |
| **Wiki** | Y | Y | Read, create, update |
| **Test Plans** | | Y | Plans, suites, cases, results |
| **Search** | | Y | Code, wiki, work items |
| **Security** | | Y | Advanced security alerts |
| **Variables** | Y | | Pipeline and variable groups |
| **Extensions** | Y | | Marketplace extensions |
| **Service Connections** | Y | | Azure RM, GitHub, etc. |
| **Projects** | Y | Y | Create, list, manage |

### Quick Commands

| Command | Description |
|---------|-------------|
| `/workday` | Daily dashboard with tasks, time log, compliance |
| `/workday --tasks` | List your active work items |
| `/create` | Create work item (task, bug, story) |
| `/standup` | Generate daily standup notes |
| `/sprint` | Sprint progress summary (`--full` for comprehensive) |
| `/log-time` | Log hours against work items |
| `/timesheet` | Time tracking views (`--off` for time-off) |
| `/task-monitor` | Periodic new assignment alerts |
| `/cli-run` | Execute CLI commands (includes vars & extensions) |

### Hybrid Mode Benefits

When hybrid mode is enabled:
- **CLI** handles: Batch operations, infrastructure, variables, scripting
- **MCP** handles: Interactive queries, reviews, tests, search, security
- **Claude** automatically routes to the best tool for each task

---

## Example Setup Session

**User:** `/init setup`

**Claude:**
```
Let me set up complete Azure DevOps integration with both CLI and MCP.

PHASE 1: Environment Detection
Platform: Windows
Settings: C:\Users\ahmed\.claude\settings.json
Node.js: v20.10.0 (OK)

PHASE 2: Azure CLI Check
Azure CLI is already installed (version 2.65.0)

PHASE 3: DevOps Extension
Installing azure-devops extension...
Extension installed successfully (version 1.0.1)

I need some information to complete setup:

1. Organization name: (e.g., YOUR-ORG)
2. Personal Access Token (PAT)
   - Create at: https://dev.azure.com/_usersSettings/tokens
   - Required scopes: Code, Work Items, Build, Wiki, Test Management

3. Default project (optional): (e.g., Project Alpha)
```

**User:** Organization is YOUR-ORG, project is Project Alpha, PAT is [token]

**Claude:**
```
Configuring Azure DevOps integration...

PHASE 5: CLI Configuration
Setting organization default... Done
Setting project default... Done
Configuring PAT authentication... Done
Testing CLI connection... SUCCESS (5 projects found)

PHASE 6: MCP Configuration
Reading settings.json...
Adding azure-devops MCP server...
Writing updated settings... Done

PHASE 7: Hybrid Mode
Enabling hybrid mode... Done

PHASE 8: Validation
CLI Test: SUCCESS
MCP Test: Pending restart

====================================================
  SETUP COMPLETE
====================================================

CLI: Configured and working
MCP: Configured (restart required)
Hybrid Mode: ENABLED

NEXT STEPS:
1. Restart Claude Code to activate MCP
2. Test with: "List my projects"
3. Use /init status to verify

Your PAT has been stored securely as environment variables:
- AZURE_DEVOPS_EXT_PAT (for CLI)
- ADO_PAT_TOKEN (for MCP)
```

---

## Troubleshooting

### CLI Issues

| Issue | Solution |
|-------|----------|
| `'az' is not recognized` | Install Azure CLI for your platform |
| `No module named 'azure.devops'` | Run `az extension add --name azure-devops` |
| `Please run 'az login'` | Run `az devops login` or set `AZURE_DEVOPS_EXT_PAT` |
| `TF400813: Resource not available` | Check organization name spelling |
| `TF401019: The work item does not exist` | Verify project access permissions |

### MCP Issues

| Issue | Solution |
|-------|----------|
| `MCP server not responding` | Check Node.js 18+ is installed |
| `Cannot find module` | Run `npm cache clean --force` |
| `Authentication failed` | Verify PAT token in `ADO_PAT_TOKEN` |
| `npx command not found` | Install Node.js which includes npx |
| `ENOENT settings.json` | Create: `mkdir ~/.claude && echo {} > ~/.claude/settings.json` |

### Hybrid Mode Issues

| Issue | Solution |
|-------|----------|
| `CLI commands not working` | Verify `AZURE_DEVOPS_EXT_PAT` is set |
| `Slow batch operations` | Ensure CLI is being used (check logs) |
| `Some features missing` | Run `/init status` to diagnose |

### Common Fixes

```bash
# Reset CLI extension
az extension remove --name azure-devops
az extension add --name azure-devops

# Clear npm cache for MCP
npm cache clean --force

# Verify environment variables (Windows)
echo $env:AZURE_DEVOPS_EXT_PAT
echo $env:ADO_PAT_TOKEN

# Verify environment variables (Unix)
echo $AZURE_DEVOPS_EXT_PAT
echo $ADO_PAT_TOKEN
```

---

## Security Best Practices

1. **Never commit PAT tokens** to version control
2. **Use environment variables** instead of hardcoding tokens
3. **Set short expiration** (30-90 days) for PATs
4. **Use minimal scopes** - only grant what's needed
5. **Rotate PATs regularly** - create new ones before expiration
6. **Use System.AccessToken** in Azure Pipelines instead of personal PATs

---

## Files Modified by Setup

| File | Changes |
|------|---------|
| `~/.claude/settings.json` | MCP server configuration added |
| User environment | `AZURE_DEVOPS_EXT_PAT`, `ADO_PAT_TOKEN`, `DEVOPS_HYBRID_MODE` |
| Azure CLI config | Organization and project defaults |

---

*Part of DevOps Plugin v4.0*
